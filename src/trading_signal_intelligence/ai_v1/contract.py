from __future__ import annotations

import math
from typing import Any


PROTOCOL_VERSION = "AI-v1.0"
DECISIONS = {"BUY", "SELL", "NO_TRADE"}
REGIMES = {"TREND_UP", "TREND_DOWN", "RANGE", "VOLATILE", "MIXED", "UNCLEAR"}
REQUIRED_KEYS = {
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
}


class DecisionValidationError(ValueError):
    pass


def _number(name: str, value: Any, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise DecisionValidationError(f"{name} must be numeric")
    number = float(value)
    if not math.isfinite(number):
        raise DecisionValidationError(f"{name} must be finite")
    if number < low or number > high:
        raise DecisionValidationError(
            f"{name} must be between {low} and {high}"
        )
    return number


def _tag_list(name: str, value: Any) -> list[str]:
    if not isinstance(value, list):
        raise DecisionValidationError(f"{name} must be an array")
    if len(value) > 8:
        raise DecisionValidationError(f"{name} has more than 8 items")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise DecisionValidationError(f"{name} items must be strings")
        cleaned = item.strip()
        if not 1 <= len(cleaned) <= 100:
            raise DecisionValidationError(
                f"{name} items must contain 1-100 characters"
            )
        result.append(cleaned)
    return result


def validate_decision(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise DecisionValidationError("AI decision must be a JSON object")

    keys = set(payload)
    missing = REQUIRED_KEYS - keys
    extra = keys - REQUIRED_KEYS
    if missing:
        raise DecisionValidationError(f"missing keys: {sorted(missing)}")
    if extra:
        raise DecisionValidationError(f"unexpected keys: {sorted(extra)}")

    if payload["protocol_version"] != PROTOCOL_VERSION:
        raise DecisionValidationError("protocol_version must be AI-v1.0")

    decision = payload["decision"]
    if decision not in DECISIONS:
        raise DecisionValidationError("decision must be BUY, SELL or NO_TRADE")

    confidence = payload["raw_confidence"]
    if isinstance(confidence, bool) or not isinstance(confidence, int):
        raise DecisionValidationError("raw_confidence must be an integer")
    if not 0 <= confidence <= 100:
        raise DecisionValidationError("raw_confidence must be 0-100")

    regime = payload["regime"]
    if regime not in REGIMES:
        raise DecisionValidationError(f"unsupported regime: {regime!r}")

    rationale = payload["rationale"]
    if not isinstance(rationale, str):
        raise DecisionValidationError("rationale must be a string")
    rationale = rationale.strip()
    if not 1 <= len(rationale) <= 800:
        raise DecisionValidationError("rationale must contain 1-800 characters")

    supporting = _tag_list("supporting_factors", payload["supporting_factors"])
    risks = _tag_list("risk_factors", payload["risk_factors"])

    if decision == "NO_TRADE":
        if any(payload[name] is not None for name in ("stop_atr", "tp1_r", "tp2_r")):
            raise DecisionValidationError(
                "NO_TRADE requires stop_atr, tp1_r and tp2_r to be null"
            )
        stop_atr = tp1_r = tp2_r = None
    else:
        stop_atr = _number("stop_atr", payload["stop_atr"], 1.0, 3.0)
        tp1_r = _number("tp1_r", payload["tp1_r"], 0.75, 2.0)
        tp2_r = _number("tp2_r", payload["tp2_r"], 1.5, 4.0)
        if tp2_r <= tp1_r:
            raise DecisionValidationError("tp2_r must be greater than tp1_r")

    return {
        "protocol_version": PROTOCOL_VERSION,
        "decision": decision,
        "raw_confidence": confidence,
        "regime": regime,
        "stop_atr": stop_atr,
        "tp1_r": tp1_r,
        "tp2_r": tp2_r,
        "rationale": rationale,
        "supporting_factors": supporting,
        "risk_factors": risks,
    }
