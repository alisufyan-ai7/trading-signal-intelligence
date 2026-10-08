from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    CryptoCostPolicyError,
    CryptoExecutionContext,
    canonical_policy_sha256,
    validate_crypto_cost_policy,
    validate_execution_context,
)
from trading_signal_intelligence.ai_v1.crypto_guardrails_v1_3 import (
    CryptoGuardResult,
    evaluate_crypto_guard,
)
from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.inference import (
    ReasoningModelAdapter,
    run_inference,
)
from trading_signal_intelligence.ai_v1.ledger import AILedger


RUNTIME_VERSION = "AI-v1.3"
DECISION_PROTOCOL_VERSION = "AI-v1.0"


@dataclass(frozen=True, slots=True)
class CryptoCycleResult:
    entity_id: str
    status: str
    inference_record: dict[str, Any] | None
    terminal_record: dict[str, Any] | None
    guard_result: CryptoGuardResult | None


def crypto_cycle_entity_id(snapshot: FeatureSnapshot) -> str:
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


def _execution_context_payload(
    context: CryptoExecutionContext,
) -> dict[str, Any]:
    return {
        "source": context.source,
        "source_symbol": context.source_symbol,
        "observed_at_utc": context.observed_at_utc.astimezone(UTC).isoformat(),
        "best_bid": float(context.best_bid),
        "best_ask": float(context.best_ask),
        "midpoint": float(context.midpoint),
        "spread_price": float(context.spread_price),
    }


def _hash_json(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    ).hexdigest()


def _append_preprovider_error(
    *,
    ledger: AILedger,
    entity_id: str,
    feature_snapshot: FeatureSnapshot,
    source_close: datetime,
    recorded_at_utc: datetime,
    stage: str,
    error: Exception,
) -> dict[str, Any]:
    return ledger.append(
        record_type="ERROR",
        entity_id=entity_id,
        effective_at_utc=source_close,
        recorded_at_utc=recorded_at_utc,
        payload={
            "runtime_version": RUNTIME_VERSION,
            "protocol_version": DECISION_PROTOCOL_VERSION,
            "source_symbol": feature_snapshot.payload["source_symbol"],
            "source_bar_close_utc": feature_snapshot.payload[
                "source_bar_close_utc"
            ],
            "feature_snapshot_sha256": feature_snapshot.sha256,
            "stage": stage,
            "error_class": type(error).__name__,
            "sanitized_message": str(error)[:500],
            "provider_call_made": False,
            "public_signal_exposure_enabled": False,
            "broker_execution_enabled": False,
        },
    )


def process_crypto_inference_cycle(
    *,
    ledger: AILedger,
    adapter: ReasoningModelAdapter,
    feature_snapshot: FeatureSnapshot,
    execution_context: CryptoExecutionContext,
    cost_policy: dict[str, Any],
    policy_text: str,
    decision_schema: dict[str, Any],
    guardrails: dict[str, Any],
    active_signal_exists: bool,
    policy_sha256: str | None = None,
    guardrails_sha256: str | None = None,
    cost_policy_sha256: str | None = None,
    recorded_at_utc: datetime | None = None,
) -> CryptoCycleResult:
    now = recorded_at_utc or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("recorded_at_utc must be timezone-aware")

    if policy_sha256 is None:
        policy_sha256 = hashlib.sha256(
            policy_text.encode("utf-8")
        ).hexdigest()
    if guardrails_sha256 is None:
        guardrails_sha256 = _hash_json(guardrails)
    if cost_policy_sha256 is None:
        cost_policy_sha256 = canonical_policy_sha256(cost_policy)

    entity_id = crypto_cycle_entity_id(feature_snapshot)
    if _already_processed(ledger, entity_id):
        raise RuntimeError(f"AI-v1.3 crypto cycle already processed: {entity_id}")

    source_close = datetime.fromisoformat(
        str(feature_snapshot.payload["source_bar_close_utc"])
    )
    age_seconds = float(feature_snapshot.payload["data_age_seconds"])
    max_age = float(guardrails["max_data_age_seconds"])

    if age_seconds < 0 or age_seconds > max_age:
        missed = ledger.append(
            record_type="MISSED_INFERENCE",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                "runtime_version": RUNTIME_VERSION,
                "protocol_version": DECISION_PROTOCOL_VERSION,
                "source_symbol": feature_snapshot.payload["source_symbol"],
                "source_bar_close_utc": feature_snapshot.payload[
                    "source_bar_close_utc"
                ],
                "detected_at_utc": now.astimezone(UTC).isoformat(),
                "data_age_seconds": age_seconds,
                "max_data_age_seconds": max_age,
                "reason": "stale_before_provider_call",
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "provider_call_made": False,
                "public_signal_exposure_enabled": False,
                "broker_execution_enabled": False,
            },
        )
        return CryptoCycleResult(
            entity_id=entity_id,
            status="MISSED_INFERENCE",
            inference_record=None,
            terminal_record=missed,
            guard_result=None,
        )

    try:
        validate_crypto_cost_policy(cost_policy)
        validate_execution_context(
            execution_context,
            source_symbol=str(feature_snapshot.payload["source_symbol"]),
            now_utc=now,
            max_age_seconds=max_age,
        )
    except CryptoCostPolicyError as exc:
        error_record = _append_preprovider_error(
            ledger=ledger,
            entity_id=entity_id,
            feature_snapshot=feature_snapshot,
            source_close=source_close,
            recorded_at_utc=now,
            stage="crypto_execution_cost_context",
            error=exc,
        )
        return CryptoCycleResult(
            entity_id=entity_id,
            status="ERROR",
            inference_record=None,
            terminal_record=error_record,
            guard_result=None,
        )

    try:
        inference = run_inference(
            adapter=adapter,
            feature_snapshot=feature_snapshot,
            policy_text=policy_text,
            decision_schema=decision_schema,
        )
    except Exception as exc:  # noqa: BLE001
        # Provider/adaptor boundary must fail closed for any provider exception.
        error_record = ledger.append(
            record_type="ERROR",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                "runtime_version": RUNTIME_VERSION,
                "protocol_version": DECISION_PROTOCOL_VERSION,
                "source_symbol": feature_snapshot.payload["source_symbol"],
                "source_bar_close_utc": feature_snapshot.payload[
                    "source_bar_close_utc"
                ],
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "stage": "provider_inference",
                "error_class": type(exc).__name__,
                "sanitized_message": str(exc)[:500],
                "provider": getattr(adapter, "provider", None),
                "model_id": getattr(adapter, "model_id", None),
                "broker_execution_enabled": False,
                "public_signal_exposure_enabled": False,
            },
        )
        return CryptoCycleResult(
            entity_id=entity_id,
            status="ERROR",
            inference_record=None,
            terminal_record=error_record,
            guard_result=None,
        )

    guard = evaluate_crypto_guard(
        decision_payload=inference.decision,
        feature_snapshot=feature_snapshot.payload,
        guardrails=guardrails,
        cost_policy=cost_policy,
        execution_context=execution_context,
        active_signal_exists=active_signal_exists,
        now_utc=now,
    )

    cost_breakdown_payload = (
        guard.cost_breakdown.as_payload()
        if guard.cost_breakdown is not None
        else None
    )

    inference_record = ledger.append(
        record_type="INFERENCE",
        entity_id=entity_id,
        effective_at_utc=source_close,
        recorded_at_utc=now,
        payload={
            "runtime_version": RUNTIME_VERSION,
            "protocol_version": DECISION_PROTOCOL_VERSION,
            "source_symbol": feature_snapshot.payload["source_symbol"],
            "source_bar_open_utc": feature_snapshot.payload[
                "source_bar_open_utc"
            ],
            "source_bar_close_utc": feature_snapshot.payload[
                "source_bar_close_utc"
            ],
            "inference_started_utc": inference.started_at_utc.isoformat(),
            "inference_completed_utc": inference.completed_at_utc.isoformat(),
            "latency_ms": inference.latency_ms,
            "feature_snapshot_sha256": feature_snapshot.sha256,
            "feature_snapshot": feature_snapshot.payload,
            "crypto_execution_context": _execution_context_payload(
                execution_context
            ),
            "crypto_cost_policy_sha256": cost_policy_sha256,
            "crypto_cost_breakdown": cost_breakdown_payload,
            "policy_sha256": policy_sha256,
            "guardrails_sha256": guardrails_sha256,
            "provider": inference.provider,
            "model_id": inference.model_id,
            "model_parameter_fingerprint": (
                inference.model_parameter_fingerprint
            ),
            "raw_structured_response": inference.raw_response,
            "normalized_decision": inference.decision,
            "raw_confidence": inference.decision["raw_confidence"],
            "provider_request_id": inference.metadata.get("request_id"),
            "usage": inference.metadata.get("usage"),
            "metadata": inference.metadata,
            "guard_publishable": guard.publishable,
            "guard_reasons": list(guard.reasons),
            "estimated_cost_r": guard.estimated_cost_r,
            "public_signal_exposure_enabled": False,
            "broker_execution_enabled": False,
        },
    )

    if inference.decision["decision"] == "NO_TRADE":
        terminal = ledger.append(
            record_type="NO_TRADE",
            entity_id=entity_id,
            effective_at_utc=source_close,
            recorded_at_utc=now,
            payload={
                "runtime_version": RUNTIME_VERSION,
                "protocol_version": DECISION_PROTOCOL_VERSION,
                "source_symbol": feature_snapshot.payload["source_symbol"],
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "normalized_decision": inference.decision,
                "raw_confidence": inference.decision["raw_confidence"],
                "regime": inference.decision["regime"],
                "rationale": inference.decision["rationale"],
                "supporting_factors": inference.decision[
                    "supporting_factors"
                ],
                "risk_factors": inference.decision["risk_factors"],
                "originating_inference_record_hash": inference_record[
                    "record_hash"
                ],
            },
        )
        return CryptoCycleResult(
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
                "runtime_version": RUNTIME_VERSION,
                "protocol_version": DECISION_PROTOCOL_VERSION,
                "source_symbol": feature_snapshot.payload["source_symbol"],
                "feature_snapshot_sha256": feature_snapshot.sha256,
                "normalized_proposal": inference.decision,
                "rejection_reasons": list(guard.reasons),
                "guardrails_sha256": guardrails_sha256,
                "crypto_cost_policy_sha256": cost_policy_sha256,
                "crypto_cost_breakdown": cost_breakdown_payload,
                "estimated_cost_r": guard.estimated_cost_r,
                "originating_inference_record_hash": inference_record[
                    "record_hash"
                ],
            },
        )
        return CryptoCycleResult(
            entity_id=entity_id,
            status="REJECTED_INFERENCE",
            inference_record=inference_record,
            terminal_record=terminal,
            guard_result=guard,
        )

    return CryptoCycleResult(
        entity_id=entity_id,
        status="APPROVED_PENDING_ENTRY",
        inference_record=inference_record,
        terminal_record=None,
        guard_result=guard,
    )
