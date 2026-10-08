from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from trading_signal_intelligence.ai_v1.contract import validate_decision
from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    CryptoCostBreakdown,
    CryptoCostPolicyError,
    CryptoExecutionContext,
    calculate_crypto_cost,
)


@dataclass(frozen=True, slots=True)
class CryptoGuardResult:
    publishable: bool
    reasons: tuple[str, ...]
    estimated_cost_r: float | None
    cost_breakdown: CryptoCostBreakdown | None


def evaluate_crypto_guard(
    *,
    decision_payload: dict[str, Any],
    feature_snapshot: dict[str, Any],
    guardrails: dict[str, Any],
    cost_policy: dict[str, Any],
    execution_context: CryptoExecutionContext,
    active_signal_exists: bool,
    now_utc: datetime,
) -> CryptoGuardResult:
    reasons: list[str] = []

    try:
        decision = validate_decision(decision_payload)
    except ValueError:
        return CryptoGuardResult(False, ("schema_invalid",), None, None)

    age = float(feature_snapshot["data_age_seconds"])
    if (
        not math.isfinite(age)
        or age < 0
        or age > float(guardrails["max_data_age_seconds"])
    ):
        reasons.append("stale_data")

    if active_signal_exists and decision["decision"] != "NO_TRADE":
        reasons.append("active_signal_exists")

    if decision["decision"] == "NO_TRADE":
        return CryptoGuardResult(
            publishable=False,
            reasons=tuple(reasons or ["no_trade"]),
            estimated_cost_r=None,
            cost_breakdown=None,
        )

    stop_atr = float(decision["stop_atr"])
    tp1_r = float(decision["tp1_r"])
    tp2_r = float(decision["tp2_r"])

    if not (
        float(guardrails["stop_atr_min"])
        <= stop_atr
        <= float(guardrails["stop_atr_max"])
    ):
        reasons.append("stop_out_of_bounds")
    if not (
        float(guardrails["tp1_r_min"])
        <= tp1_r
        <= float(guardrails["tp1_r_max"])
    ):
        reasons.append("tp1_out_of_bounds")
    if not (
        float(guardrails["tp2_r_min"])
        <= tp2_r
        <= float(guardrails["tp2_r_max"])
    ):
        reasons.append("tp2_out_of_bounds")
    if bool(guardrails["require_tp2_gt_tp1"]) and tp2_r <= tp1_r:
        reasons.append("target_order_invalid")

    atr = float(feature_snapshot["atr_14"])
    if not math.isfinite(atr) or atr <= 0:
        reasons.append("arithmetic_invalid")
        return CryptoGuardResult(
            publishable=False,
            reasons=tuple(reasons),
            estimated_cost_r=None,
            cost_breakdown=None,
        )

    try:
        breakdown = calculate_crypto_cost(
            policy=cost_policy,
            context=execution_context,
            source_symbol=str(feature_snapshot["source_symbol"]),
            atr_14=atr,
            stop_atr=stop_atr,
            now_utc=now_utc,
            max_data_age_seconds=float(guardrails["max_data_age_seconds"]),
        )
    except CryptoCostPolicyError:
        reasons.append("crypto_cost_context_invalid")
        return CryptoGuardResult(
            publishable=False,
            reasons=tuple(reasons),
            estimated_cost_r=None,
            cost_breakdown=None,
        )

    estimated_cost_r = float(breakdown.estimated_cost_r)
    if not breakdown.passes_cost_guard:
        reasons.append("cost_too_high")

    return CryptoGuardResult(
        publishable=not reasons,
        reasons=tuple(reasons),
        estimated_cost_r=estimated_cost_r,
        cost_breakdown=breakdown,
    )
