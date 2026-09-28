from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from trading_signal_intelligence.ai_v1.contract import validate_decision


@dataclass(frozen=True, slots=True)
class GuardResult:
    publishable: bool
    reasons: tuple[str, ...]
    estimated_cost_r: float | None


def evaluate_guard(
    *,
    decision_payload: dict[str, Any],
    feature_snapshot: dict[str, Any],
    guardrails: dict[str, Any],
    active_signal_exists: bool,
) -> GuardResult:
    reasons: list[str] = []

    try:
        decision = validate_decision(decision_payload)
    except ValueError:
        return GuardResult(False, ("schema_invalid",), None)

    age = float(feature_snapshot["data_age_seconds"])
    if not math.isfinite(age) or age < 0 or age > float(guardrails["max_data_age_seconds"]):
        reasons.append("stale_data")

    if active_signal_exists and decision["decision"] != "NO_TRADE":
        reasons.append("active_signal_exists")

    if decision["decision"] == "NO_TRADE":
        return GuardResult(
            publishable=False,
            reasons=tuple(reasons or ["no_trade"]),
            estimated_cost_r=None,
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
    spread_price = float(feature_snapshot["spread_price"])
    if not math.isfinite(atr) or atr <= 0 or not math.isfinite(spread_price) or spread_price < 0:
        reasons.append("arithmetic_invalid")
        estimated_cost_r = None
    else:
        risk_price = stop_atr * atr
        cost_price = float(guardrails["cost_multiplier"]) * spread_price
        estimated_cost_r = cost_price / risk_price
        if estimated_cost_r > float(guardrails["max_round_trip_cost_r"]):
            reasons.append("cost_too_high")

    return GuardResult(
        publishable=not reasons,
        reasons=tuple(reasons),
        estimated_cost_r=estimated_cost_r,
    )
