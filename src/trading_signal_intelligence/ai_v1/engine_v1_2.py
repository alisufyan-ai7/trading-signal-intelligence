from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.guardrails import GuardResult, evaluate_guard
from trading_signal_intelligence.ai_v1.inference import (
    ReasoningModelAdapter,
    run_inference,
)
from trading_signal_intelligence.ai_v1.ledger import AILedger


RUNTIME_VERSION = "AI-v1.2"
DECISION_PROTOCOL_VERSION = "AI-v1.0"


@dataclass(frozen=True, slots=True)
class CycleResultV12:
    entity_id: str
    status: str
    inference_record: dict[str, Any] | None
    terminal_record: dict[str, Any] | None
    guard_result: GuardResult | None


def cycle_entity_id_v1_2(snapshot: FeatureSnapshot) -> str:
    symbol = str(snapshot.payload["source_symbol"])
    close_utc = str(snapshot.payload["source_bar_close_utc"])
    return f"{RUNTIME_VERSION}:{symbol}:{close_utc}"


def _already_processed(ledger: AILedger, entity_id: str) -> bool:
    return any(
        ledger.has(record_type=record_type, entity_id=entity_id)
        for record_type in (
            "INFERENCE",
            "NO_TRADE",
            "REJECTED_INFERENCE",
            "SIGNAL",
            "MISSED_INFERENCE",
            "ERROR",
        )
    )


def _base_payload(feature_snapshot: FeatureSnapshot) -> dict[str, Any]:
    return {
        "protocol_version": DECISION_PROTOCOL_VERSION,
        "runtime_version": RUNTIME_VERSION,
        "source_symbol": feature_snapshot.payload["source_symbol"],
        "source_bar_close_utc": feature_snapshot.payload["source_bar_close_utc"],
    }


def process_inference_cycle_v1_2(
    *,
    ledger: AILedger,
    adapter: ReasoningModelAdapter,
    feature_snapshot: FeatureSnapshot,
    policy_text: str,
    decision_schema: dict[str, Any],
    guardrails: dict[str, Any],
    active_signal_exists: bool,
    policy_sha256: str | None = None,
    guardrails_sha256: str | None = None,
    recorded_at_utc: datetime | None = None,
) -> CycleResultV12:
    now = recorded_at_utc or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("recorded_at_utc must be timezone-aware")

    if policy_sha256 is None:
        policy_sha256 = hashlib.sha256(policy_text.encode("utf-8")).hexdigest()
    if guardrails_sha256 is None:
        guardrails_sha256 = hashlib.sha256(
            json.dumps(
                guardrails,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()

    entity_id = cycle_entity_id_v1_2(feature_snapshot)
    if _already_processed(ledger, entity_id):
        raise RuntimeError(f"{RUNTIME_VERSION} cycle already processed: {entity_id}")

    source_close = datetime.fromisoformat(
        str(feature_snapshot.payload["source_bar_close_utc"]).replace("Z", "+00:00")
    )
    age_seconds = float(feature_snapshot.payload["data_age_seconds"])
    max_age = float(guardrails["max_data_age_seconds"])
    base = _base_payload(feature_snapshot)

    if age_seconds < 0 or age_seconds > max_age:
        missed = ledger.append(
            record_type="MISSED_INFERENCE",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                **base,
                "detected_at_utc": now.astimezone(timezone.utc).isoformat(),
                "data_age_seconds": age_seconds,
                "max_data_age_seconds": max_age,
                "reason": "stale_before_provider_call",
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "provider_call_made": False,
            },
        )
        return CycleResultV12(
            entity_id=entity_id,
            status="MISSED_INFERENCE",
            inference_record=None,
            terminal_record=missed,
            guard_result=None,
        )

    try:
        inference = run_inference(
            adapter=adapter,
            feature_snapshot=feature_snapshot,
            policy_text=policy_text,
            decision_schema=decision_schema,
        )
    except Exception as exc:
        error_record = ledger.append(
            record_type="ERROR",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                **base,
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "stage": "provider_inference",
                "error_class": type(exc).__name__,
                "sanitized_message": str(exc)[:500],
                "provider": getattr(adapter, "provider", None),
                "model_id": getattr(adapter, "model_id", None),
                "broker_execution_enabled": False,
            },
        )
        return CycleResultV12(
            entity_id=entity_id,
            status="ERROR",
            inference_record=None,
            terminal_record=error_record,
            guard_result=None,
        )

    guard = evaluate_guard(
        decision_payload=inference.decision,
        feature_snapshot=feature_snapshot.payload,
        guardrails=guardrails,
        active_signal_exists=active_signal_exists,
    )

    inference_record = ledger.append(
        record_type="INFERENCE",
        entity_id=entity_id,
        effective_at_utc=source_close,
        recorded_at_utc=now,
        payload={
            **base,
            "source_bar_open_utc": feature_snapshot.payload["source_bar_open_utc"],
            "inference_started_utc": inference.started_at_utc.isoformat(),
            "inference_completed_utc": inference.completed_at_utc.isoformat(),
            "latency_ms": inference.latency_ms,
            "feature_snapshot_sha256": feature_snapshot.sha256,
            "feature_snapshot": feature_snapshot.payload,
            "policy_sha256": policy_sha256,
            "guardrails_sha256": guardrails_sha256,
            "provider": inference.provider,
            "model_id": inference.model_id,
            "model_parameter_fingerprint": inference.model_parameter_fingerprint,
            "raw_structured_response": inference.raw_response,
            "normalized_decision": inference.decision,
            "raw_confidence": inference.decision["raw_confidence"],
            "provider_request_id": inference.metadata.get("request_id"),
            "usage": inference.metadata.get("usage"),
            "metadata": inference.metadata,
            "guard_publishable": guard.publishable,
            "guard_reasons": list(guard.reasons),
            "estimated_cost_r": guard.estimated_cost_r,
        },
    )

    if inference.decision["decision"] == "NO_TRADE":
        terminal = ledger.append(
            record_type="NO_TRADE",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                **base,
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "normalized_decision": inference.decision,
                "raw_confidence": inference.decision["raw_confidence"],
                "regime": inference.decision["regime"],
                "rationale": inference.decision["rationale"],
                "supporting_factors": inference.decision["supporting_factors"],
                "risk_factors": inference.decision["risk_factors"],
                "originating_inference_record_hash": inference_record["record_hash"],
            },
        )
        return CycleResultV12(
            entity_id=entity_id,
            status="NO_TRADE",
            inference_record=inference_record,
            terminal_record=terminal,
            guard_result=guard,
        )

    if not guard.publishable:
        terminal = ledger.append(
            record_type="REJECTED_INFERENCE",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                **base,
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "normalized_proposal": inference.decision,
                "rejection_reasons": list(guard.reasons),
                "guardrails_sha256": guardrails_sha256,
                "estimated_cost_r": guard.estimated_cost_r,
                "originating_inference_record_hash": inference_record["record_hash"],
            },
        )
        return CycleResultV12(
            entity_id=entity_id,
            status="REJECTED_INFERENCE",
            inference_record=inference_record,
            terminal_record=terminal,
            guard_result=guard,
        )

    return CycleResultV12(
        entity_id=entity_id,
        status="APPROVED_PENDING_ENTRY",
        inference_record=inference_record,
        terminal_record=None,
        guard_result=guard,
    )
