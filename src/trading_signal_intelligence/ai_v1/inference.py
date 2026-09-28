from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from trading_signal_intelligence.ai_v1.contract import validate_decision
from trading_signal_intelligence.ai_v1.features import FeatureSnapshot, canonical_json


class ReasoningModelAdapter(Protocol):
    @property
    def provider(self) -> str: ...

    @property
    def model_id(self) -> str: ...

    @property
    def parameters(self) -> dict[str, Any]: ...

    def infer(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
        decision_schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Return (structured_response, metadata).

        Metadata may include request_id, usage and estimated_cost. It must not
        contain credentials or authorization material.
        """


@dataclass(frozen=True, slots=True)
class InferenceResult:
    provider: str
    model_id: str
    model_parameter_fingerprint: str
    started_at_utc: datetime
    completed_at_utc: datetime
    latency_ms: float
    raw_response: dict[str, Any]
    decision: dict[str, Any]
    metadata: dict[str, Any]


def parameter_fingerprint(
    *,
    provider: str,
    model_id: str,
    parameters: dict[str, Any],
) -> str:
    material = {
        "provider": provider,
        "model_id": model_id,
        "parameters": parameters,
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


def sanitize_metadata(metadata: dict[str, Any] | None) -> dict[str, Any]:
    if metadata is None:
        return {}
    forbidden = {
        "authorization",
        "api_key",
        "apikey",
        "api-key",
        "token",
        "secret",
        "password",
    }
    sanitized: dict[str, Any] = {}
    for key, value in metadata.items():
        normalized = key.lower().replace("_", "-")
        if normalized in forbidden or any(
            term in normalized for term in ("authorization", "api-key", "secret", "password")
        ):
            continue
        # Ensure metadata is canonical-JSON serializable before it reaches a ledger.
        json.dumps(value, allow_nan=False, default=str)
        sanitized[key] = value
    return sanitized


def run_inference(
    *,
    adapter: ReasoningModelAdapter,
    feature_snapshot: FeatureSnapshot,
    policy_text: str,
    decision_schema: dict[str, Any],
) -> InferenceResult:
    started = datetime.now(timezone.utc)
    start_clock = time.perf_counter()
    raw_response, metadata = adapter.infer(
        policy_text=policy_text,
        feature_snapshot=feature_snapshot.payload,
        decision_schema=decision_schema,
    )
    latency_ms = (time.perf_counter() - start_clock) * 1000.0
    completed = datetime.now(timezone.utc)

    decision = validate_decision(raw_response)
    fingerprint = parameter_fingerprint(
        provider=adapter.provider,
        model_id=adapter.model_id,
        parameters=adapter.parameters,
    )

    return InferenceResult(
        provider=adapter.provider,
        model_id=adapter.model_id,
        model_parameter_fingerprint=fingerprint,
        started_at_utc=started,
        completed_at_utc=completed,
        latency_ms=latency_ms,
        raw_response=raw_response,
        decision=decision,
        metadata=sanitize_metadata(metadata),
    )
