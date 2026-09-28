from __future__ import annotations

import hashlib
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from trading_signal_intelligence.ai_v1.features import canonical_json


class OpenAIProviderError(RuntimeError):
    """Base error for OpenAI Responses API failures."""


class OpenAIHTTPError(OpenAIProviderError):
    pass


class OpenAIIncompleteError(OpenAIProviderError):
    pass


class OpenAIRefusalError(OpenAIProviderError):
    pass


class OpenAIResponseParseError(OpenAIProviderError):
    pass


Transport = Callable[
    [str, dict[str, str], dict[str, Any], float],
    tuple[dict[str, Any], Mapping[str, str]],
]


def _sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _default_transport(
    endpoint: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout_seconds: float,
) -> tuple[dict[str, Any], Mapping[str, str]]:
    request = urllib.request.Request(
        endpoint,
        data=canonical_json(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            response_headers = dict(response.headers.items())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        # Provider error bodies are safe to report only in bounded form. Never
        # include request headers or the API key in an exception.
        raise OpenAIHTTPError(
            f"OpenAI HTTP {exc.code}: {body[:1000]}"
        ) from None
    except urllib.error.URLError as exc:
        raise OpenAIHTTPError(f"OpenAI transport error: {exc.reason}") from None

    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OpenAIResponseParseError(
            f"OpenAI returned non-JSON response: {raw[:500]}"
        ) from exc
    if not isinstance(decoded, dict):
        raise OpenAIResponseParseError("OpenAI response root must be an object")
    return decoded, response_headers


def _extract_output_text(response: dict[str, Any]) -> str:
    refusals: list[str] = []
    texts: list[str] = []

    for item in response.get("output", []) or []:
        if not isinstance(item, dict) or item.get("type") != "message":
            continue
        for content in item.get("content", []) or []:
            if not isinstance(content, dict):
                continue
            content_type = content.get("type")
            if content_type == "refusal":
                refusals.append(str(content.get("refusal") or "refused"))
            elif content_type == "output_text":
                text = content.get("text")
                if isinstance(text, str):
                    texts.append(text)

    if refusals:
        raise OpenAIRefusalError("; ".join(refusals)[:1000])

    # Some API clients expose a convenience output_text field. Accept it as a
    # defensive fallback while preferring the canonical output item structure.
    if not texts and isinstance(response.get("output_text"), str):
        texts.append(str(response["output_text"]))

    if len(texts) != 1:
        raise OpenAIResponseParseError(
            f"expected exactly one output_text item; found {len(texts)}"
        )
    return texts[0]


@dataclass(frozen=True, slots=True)
class OpenAIResponsesAdapter:
    config: dict[str, Any]
    provider_response_schema: dict[str, Any]
    api_key: str
    timeout_seconds: float = 45.0
    transport: Transport = _default_transport

    @classmethod
    def from_environment(
        cls,
        *,
        config: dict[str, Any],
        provider_response_schema: dict[str, Any],
        timeout_seconds: float = 45.0,
        transport: Transport = _default_transport,
    ) -> "OpenAIResponsesAdapter":
        env_name = str(config["api_key_env"])
        api_key = os.getenv(env_name, "").strip()
        if not api_key:
            raise OpenAIProviderError(
                f"{env_name} is not configured in the local environment"
            )
        return cls(
            config=config,
            provider_response_schema=provider_response_schema,
            api_key=api_key,
            timeout_seconds=timeout_seconds,
            transport=transport,
        )

    @property
    def provider(self) -> str:
        return str(self.config["provider"])

    @property
    def model_id(self) -> str:
        return str(self.config["model_id"])

    @property
    def parameters(self) -> dict[str, Any]:
        # Deliberately excludes api_key_env and file paths; includes every
        # inference-affecting HTTP parameter plus the exact provider schema hash.
        return {
            "api": self.config["api"],
            "endpoint": self.config["endpoint"],
            "reasoning_effort": self.config["reasoning_effort"],
            "service_tier": self.config["service_tier"],
            "store": self.config["store"],
            "truncation": self.config["truncation"],
            "max_output_tokens": self.config["max_output_tokens"],
            "tools": self.config["tools"],
            "temperature": self.config["temperature"],
            "top_p": self.config["top_p"],
            "conversation": self.config["conversation"],
            "previous_response_id": self.config["previous_response_id"],
            "structured_output_name": self.config["structured_output_name"],
            "provider_response_schema_sha256": _sha256_json(
                self.provider_response_schema
            ),
        }

    def request_payload(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model_id,
            "instructions": policy_text,
            "input": canonical_json(feature_snapshot),
            "reasoning": {"effort": self.config["reasoning_effort"]},
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": self.config["structured_output_name"],
                    "strict": True,
                    "schema": self.provider_response_schema,
                }
            },
            "max_output_tokens": int(self.config["max_output_tokens"]),
            "service_tier": self.config["service_tier"],
            "store": bool(self.config["store"]),
            "truncation": self.config["truncation"],
            "tools": list(self.config["tools"]),
        }

        # These are frozen as null for AI-v1 and therefore intentionally
        # omitted rather than translated into provider defaults.
        if self.config.get("temperature") is not None:
            payload["temperature"] = self.config["temperature"]
        if self.config.get("top_p") is not None:
            payload["top_p"] = self.config["top_p"]
        if self.config.get("conversation") is not None:
            payload["conversation"] = self.config["conversation"]
        if self.config.get("previous_response_id") is not None:
            payload["previous_response_id"] = self.config["previous_response_id"]
        return payload

    def infer(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
        decision_schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        # decision_schema remains part of the provider-neutral adapter contract.
        # Semantic enforcement happens again in validate_decision() after this
        # adapter returns. The OpenAI request uses the separately frozen subset
        # schema because OpenAI Structured Outputs does not support conditional
        # JSON-Schema composition used by the canonical contract.
        if decision_schema.get("title") != "SignalProof AI-v1 model decision":
            raise OpenAIProviderError("unexpected canonical AI-v1 decision schema")

        payload = self.request_payload(
            policy_text=policy_text,
            feature_snapshot=feature_snapshot,
        )
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        response, response_headers = self.transport(
            str(self.config["endpoint"]),
            headers,
            payload,
            self.timeout_seconds,
        )

        status = str(response.get("status") or "")
        if status != "completed":
            details = response.get("incomplete_details")
            if status == "incomplete":
                raise OpenAIIncompleteError(
                    f"OpenAI response incomplete: {details!r}"
                )
            raise OpenAIProviderError(
                f"OpenAI response status is {status or 'missing'}"
            )

        output_text = _extract_output_text(response)
        try:
            structured = json.loads(output_text)
        except json.JSONDecodeError as exc:
            raise OpenAIResponseParseError(
                "OpenAI output_text was not valid JSON"
            ) from exc
        if not isinstance(structured, dict):
            raise OpenAIResponseParseError(
                "OpenAI structured decision must be a JSON object"
            )

        metadata: dict[str, Any] = {
            "response_id": response.get("id"),
            "served_model": response.get("model"),
            "service_tier": response.get("service_tier"),
            "status": status,
            "usage": response.get("usage"),
        }
        request_id = None
        for key, value in response_headers.items():
            if key.lower() == "x-request-id":
                request_id = value
                break
        if request_id:
            metadata["request_id"] = request_id

        return structured, metadata
