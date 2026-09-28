from __future__ import annotations

import json
from typing import Any, Mapping

import pytest

from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.inference import run_inference
from trading_signal_intelligence.ai_v1.openai_responses import (
    OpenAIIncompleteError,
    OpenAIRefusalError,
    OpenAIResponsesAdapter,
)


def provider_config() -> dict[str, Any]:
    return {
        "protocol_version": "AI-v1.0",
        "provider": "openai",
        "api": "responses",
        "endpoint": "https://api.openai.com/v1/responses",
        "model_id": "gpt-5.4-2026-03-05",
        "reasoning_effort": "medium",
        "service_tier": "default",
        "store": False,
        "truncation": "disabled",
        "max_output_tokens": 8192,
        "tools": [],
        "temperature": None,
        "top_p": None,
        "conversation": None,
        "previous_response_id": None,
        "structured_output_name": "signalproof_ai_v1_decision",
        "provider_response_schema": "config/ai_v1_openai_response_schema.json",
        "policy_path": "config/ai_v1_policy.txt",
        "canonical_decision_schema": "config/ai_v1_decision_schema.json",
        "api_key_env": "OPENAI_API_KEY",
    }


def provider_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "additionalProperties": False,
        "required": [
            "protocol_version",
            "decision",
            "raw_confidence",
            "regime",
            "stop_atr",
            "tp1_r",
            "tp2_r",
            "rationale",
            "supporting_factors",
            "risk_factors",
        ],
        "properties": {
            "protocol_version": {"type": "string", "enum": ["AI-v1.0"]},
            "decision": {"type": "string", "enum": ["BUY", "SELL", "NO_TRADE"]},
            "raw_confidence": {"type": "integer", "minimum": 0, "maximum": 100},
            "regime": {
                "type": "string",
                "enum": [
                    "TREND_UP",
                    "TREND_DOWN",
                    "RANGE",
                    "VOLATILE",
                    "MIXED",
                    "UNCLEAR",
                ],
            },
            "stop_atr": {"type": ["number", "null"], "minimum": 1.0, "maximum": 3.0},
            "tp1_r": {"type": ["number", "null"], "minimum": 0.75, "maximum": 2.0},
            "tp2_r": {"type": ["number", "null"], "minimum": 1.5, "maximum": 4.0},
            "rationale": {"type": "string"},
            "supporting_factors": {"type": "array", "items": {"type": "string"}},
            "risk_factors": {"type": "array", "items": {"type": "string"}},
        },
    }


def canonical_schema() -> dict[str, Any]:
    return {"title": "SignalProof AI-v1 model decision"}


def no_trade_json() -> str:
    return json.dumps(
        {
            "protocol_version": "AI-v1.0",
            "decision": "NO_TRADE",
            "raw_confidence": 42,
            "regime": "MIXED",
            "stop_atr": None,
            "tp1_r": None,
            "tp2_r": None,
            "rationale": "Signals conflict.",
            "supporting_factors": ["return_sign_mixed"],
            "risk_factors": ["regime_mixed"],
        }
    )


def test_request_payload_is_frozen_and_stateless() -> None:
    adapter = OpenAIResponsesAdapter(
        config=provider_config(),
        provider_response_schema=provider_schema(),
        api_key="test-key",
    )
    payload = adapter.request_payload(
        policy_text="frozen policy",
        feature_snapshot={"feature_schema_version": "AI-v1.0", "x": 1},
    )

    assert payload["model"] == "gpt-5.4-2026-03-05"
    assert payload["reasoning"] == {"effort": "medium"}
    assert payload["service_tier"] == "default"
    assert payload["store"] is False
    assert payload["truncation"] == "disabled"
    assert payload["max_output_tokens"] == 8192
    assert payload["tools"] == []
    assert "temperature" not in payload
    assert "top_p" not in payload
    assert "conversation" not in payload
    assert "previous_response_id" not in payload
    assert payload["text"]["format"]["strict"] is True
    assert payload["text"]["format"]["schema"] == provider_schema()
    assert json.loads(payload["input"])["x"] == 1


def test_adapter_parses_completed_structured_response_and_metadata() -> None:
    captured: dict[str, Any] = {}

    def transport(
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> tuple[dict[str, Any], Mapping[str, str]]:
        captured.update(
            {
                "endpoint": endpoint,
                "headers": headers,
                "payload": payload,
                "timeout": timeout,
            }
        )
        return (
            {
                "id": "resp_test",
                "status": "completed",
                "model": "gpt-5.4-2026-03-05",
                "service_tier": "default",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": no_trade_json()}
                        ],
                    }
                ],
                "usage": {
                    "input_tokens": 500,
                    "output_tokens": 80,
                    "total_tokens": 580,
                },
            },
            {"x-request-id": "req_test"},
        )

    adapter = OpenAIResponsesAdapter(
        config=provider_config(),
        provider_response_schema=provider_schema(),
        api_key="super-secret",
        transport=transport,
    )
    decision, metadata = adapter.infer(
        policy_text="policy",
        feature_snapshot={"feature_schema_version": "AI-v1.0"},
        decision_schema=canonical_schema(),
    )

    assert decision["decision"] == "NO_TRADE"
    assert metadata["response_id"] == "resp_test"
    assert metadata["request_id"] == "req_test"
    assert metadata["usage"]["input_tokens"] == 500
    assert captured["headers"]["Authorization"] == "Bearer super-secret"
    assert "super-secret" not in json.dumps(metadata)


def test_run_inference_uses_exact_snapshot_and_validates_output() -> None:
    def transport(
        endpoint: str,
        headers: dict[str, str],
        payload: dict[str, Any],
        timeout: float,
    ) -> tuple[dict[str, Any], Mapping[str, str]]:
        return (
            {
                "id": "resp_test",
                "status": "completed",
                "model": "gpt-5.4-2026-03-05",
                "service_tier": "default",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": no_trade_json()}
                        ],
                    }
                ],
                "usage": {},
            },
            {},
        )

    adapter = OpenAIResponsesAdapter(
        config=provider_config(),
        provider_response_schema=provider_schema(),
        api_key="test-key",
        transport=transport,
    )
    result = run_inference(
        adapter=adapter,
        feature_snapshot=FeatureSnapshot(
            payload={"feature_schema_version": "AI-v1.0"},
            sha256="a" * 64,
        ),
        policy_text="policy",
        decision_schema=canonical_schema(),
    )

    assert result.provider == "openai"
    assert result.model_id == "gpt-5.4-2026-03-05"
    assert result.decision["decision"] == "NO_TRADE"
    assert len(result.model_parameter_fingerprint) == 64


def test_incomplete_and_refusal_fail_closed() -> None:
    def incomplete_transport(*args, **kwargs):
        return (
            {
                "id": "resp_incomplete",
                "status": "incomplete",
                "incomplete_details": {"reason": "max_output_tokens"},
                "output": [],
            },
            {},
        )

    adapter = OpenAIResponsesAdapter(
        config=provider_config(),
        provider_response_schema=provider_schema(),
        api_key="test-key",
        transport=incomplete_transport,
    )
    with pytest.raises(OpenAIIncompleteError):
        adapter.infer(
            policy_text="policy",
            feature_snapshot={"feature_schema_version": "AI-v1.0"},
            decision_schema=canonical_schema(),
        )

    def refusal_transport(*args, **kwargs):
        return (
            {
                "id": "resp_refusal",
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {
                                "type": "refusal",
                                "refusal": "Request refused.",
                            }
                        ],
                    }
                ],
            },
            {},
        )

    refusing = OpenAIResponsesAdapter(
        config=provider_config(),
        provider_response_schema=provider_schema(),
        api_key="test-key",
        transport=refusal_transport,
    )
    with pytest.raises(OpenAIRefusalError):
        refusing.infer(
            policy_text="policy",
            feature_snapshot={"feature_schema_version": "AI-v1.0"},
            decision_schema=canonical_schema(),
        )
