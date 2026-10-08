from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Any

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.models import Candle


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(UTC)


def _finite(name: str, value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


def append_crypto_signal_from_approved_inference(
    *,
    ledger: AILedger,
    entity_id: str,
    entry_bar: Candle,
    guardrails: dict[str, Any],
    recorded_at_utc: datetime | None = None,
) -> dict[str, Any]:
    if ledger.has(record_type="SIGNAL", entity_id=entity_id):
        raise RuntimeError(f"signal already exists for {entity_id}")

    inference_rows = ledger.records(record_type="INFERENCE", entity_id=entity_id)
    if len(inference_rows) != 1:
        raise RuntimeError(
            f"expected exactly one INFERENCE for {entity_id}; found {len(inference_rows)}"
        )

    inference = inference_rows[0]
    payload = inference["payload"]
    if payload.get("runtime_version") != "AI-v1.3":
        raise RuntimeError("inference runtime_version is not AI-v1.3")
    if not bool(payload.get("guard_publishable")):
        raise RuntimeError("inference was not approved by the crypto publication guard")

    decision = payload["normalized_decision"]
    if decision["decision"] not in {"BUY", "SELL"}:
        raise RuntimeError("only directional approved inference can become a SIGNAL")

    cost = payload.get("crypto_cost_breakdown")
    if not isinstance(cost, dict):
        raise TypeError("approved crypto inference lacks frozen cost breakdown")
    if cost.get("passes_cost_guard") is not True:
        raise RuntimeError("crypto cost breakdown did not pass the frozen cost guard")

    policy_sha = payload.get("crypto_cost_policy_sha256")
    if not isinstance(policy_sha, str) or len(policy_sha) != 64:
        raise RuntimeError("approved crypto inference lacks cost-policy fingerprint")

    execution_context = payload.get("crypto_execution_context")
    if not isinstance(execution_context, dict):
        raise TypeError("approved crypto inference lacks execution-context provenance")

    feature = payload["feature_snapshot"]
    expected_entry = datetime.fromisoformat(
        str(feature["source_bar_close_utc"])
    ).astimezone(UTC)
    actual_entry = _utc(entry_bar.timestamp_utc)
    if actual_entry != expected_entry:
        raise RuntimeError(
            f"entry bar timestamp {actual_entry.isoformat()} does not match "
            f"required next-H1 open {expected_entry.isoformat()}"
        )

    entry = _finite("entry", entry_bar.open)
    atr = _finite("atr_14", feature["atr_14"])
    stop_atr = _finite("stop_atr", decision["stop_atr"])
    tp1_r = _finite("tp1_r", decision["tp1_r"])
    tp2_r = _finite("tp2_r", decision["tp2_r"])
    risk_price = stop_atr * atr
    if risk_price <= 0:
        raise RuntimeError("risk_price must be positive")

    frozen_risk_price = _finite("frozen risk_price", cost["risk_price"])
    if not math.isclose(
        frozen_risk_price,
        risk_price,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise RuntimeError("frozen crypto cost risk_price does not match signal risk")

    total_cost_price = _finite("total_cost_price", cost["total_cost_price"])
    if total_cost_price < 0:
        raise RuntimeError("total_cost_price must be non-negative")

    estimated_cost_r = _finite("estimated_cost_r", cost["estimated_cost_r"])
    recalculated_cost_r = total_cost_price / risk_price
    if not math.isclose(
        estimated_cost_r,
        recalculated_cost_r,
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise RuntimeError("frozen crypto cost-R does not match signal cost/risk")

    direction = decision["decision"]
    if direction == "BUY":
        stop = entry - risk_price
        tp1 = entry + tp1_r * risk_price
        tp2 = entry + tp2_r * risk_price
    else:
        stop = entry + risk_price
        tp1 = entry - tp1_r * risk_price
        tp2 = entry - tp2_r * risk_price

    signal_payload = {
        "runtime_version": "AI-v1.3",
        "protocol_version": "AI-v1.0",
        "source_symbol": feature["source_symbol"],
        "canonical_symbol": feature["canonical_symbol"],
        "direction": direction,
        "source_bar_close_utc": feature["source_bar_close_utc"],
        "entry_policy": guardrails["entry_policy"],
        "entry_timestamp_utc": actual_entry.isoformat(),
        "entry": entry,
        "atr_14": atr,
        "stop_atr": stop_atr,
        "risk_price": risk_price,
        "stop": stop,
        "tp1_r": tp1_r,
        "tp1": tp1,
        "tp2_r": tp2_r,
        "tp2": tp2,
        "max_hold_h1_bars": int(guardrails["max_hold_h1_bars"]),
        "tp1_position_fraction": float(guardrails["tp1_position_fraction"]),
        "tp2_position_fraction": float(guardrails["tp2_position_fraction"]),
        "move_stop_after_tp1": bool(guardrails["move_stop_after_tp1"]),
        "spread_price": _finite("reference_spread", cost["reference_spread"]),
        "cost_policy_version": cost["policy_version"],
        "cost_policy_sha256": policy_sha,
        "reference_midpoint": _finite(
            "reference_midpoint",
            cost["reference_midpoint"],
        ),
        "round_trip_fee_price": _finite(
            "round_trip_fee_price",
            cost["round_trip_fee_price"],
        ),
        "spread_crossing_price": _finite(
            "spread_crossing_price",
            cost["spread_crossing_price"],
        ),
        "slippage_buffer_price": _finite(
            "slippage_buffer_price",
            cost["slippage_buffer_price"],
        ),
        "total_cost_price": total_cost_price,
        "estimated_cost_r": estimated_cost_r,
        "crypto_execution_context": execution_context,
        "raw_confidence": decision["raw_confidence"],
        "regime": decision["regime"],
        "feature_snapshot_sha256": payload["feature_snapshot_sha256"],
        "originating_inference_record_hash": inference["record_hash"],
        "public_signal_exposure_enabled": False,
        "broker_execution_enabled": False,
    }

    return ledger.append(
        record_type="SIGNAL",
        entity_id=entity_id,
        effective_at_utc=actual_entry,
        recorded_at_utc=recorded_at_utc or datetime.now(UTC),
        payload=signal_payload,
    )
