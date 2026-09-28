from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

import pytest

from trading_signal_intelligence.ai_v1.contract import (
    DecisionValidationError,
    validate_decision,
)
from trading_signal_intelligence.ai_v1.guardrails import evaluate_guard
from trading_signal_intelligence.ai_v1.ledger import AILedger


def _buy() -> dict:
    return {
        "protocol_version": "AI-v1.0",
        "decision": "BUY",
        "raw_confidence": 64,
        "regime": "TREND_UP",
        "stop_atr": 1.5,
        "tp1_r": 1.0,
        "tp2_r": 2.0,
        "rationale": "Trend and structure align.",
        "supporting_factors": ["trend_up", "momentum_positive"],
        "risk_factors": ["volatility_high"],
    }


def test_decision_contract() -> None:
    result = validate_decision(_buy())
    assert result["decision"] == "BUY"

    bad = _buy()
    bad["tp2_r"] = 0.9
    with pytest.raises(DecisionValidationError):
        validate_decision(bad)

    no_trade = _buy()
    no_trade.update(
        {
            "decision": "NO_TRADE",
            "stop_atr": None,
            "tp1_r": None,
            "tp2_r": None,
        }
    )
    assert validate_decision(no_trade)["decision"] == "NO_TRADE"


def test_guard_rejects_cost_and_active_signal() -> None:
    config = {
        "max_data_age_seconds": 300,
        "stop_atr_min": 1.0,
        "stop_atr_max": 3.0,
        "tp1_r_min": 0.75,
        "tp1_r_max": 2.0,
        "tp2_r_min": 1.5,
        "tp2_r_max": 4.0,
        "require_tp2_gt_tp1": True,
        "cost_multiplier": 1.25,
        "max_round_trip_cost_r": 0.15,
    }
    feature = {
        "data_age_seconds": 30.0,
        "atr_14": 10.0,
        "spread_price": 0.5,
    }

    passed = evaluate_guard(
        decision_payload=_buy(),
        feature_snapshot=feature,
        guardrails=config,
        active_signal_exists=False,
    )
    assert passed.publishable is True
    assert passed.estimated_cost_r is not None

    active = evaluate_guard(
        decision_payload=_buy(),
        feature_snapshot=feature,
        guardrails=config,
        active_signal_exists=True,
    )
    assert active.publishable is False
    assert "active_signal_exists" in active.reasons

    expensive = dict(feature)
    expensive["spread_price"] = 5.0
    rejected = evaluate_guard(
        decision_payload=_buy(),
        feature_snapshot=expensive,
        guardrails=config,
        active_signal_exists=False,
    )
    assert rejected.publishable is False
    assert "cost_too_high" in rejected.reasons


def test_ai_ledger_hash_chain_and_append_only(tmp_path) -> None:
    ledger = AILedger(tmp_path / "ai.sqlite")
    now = datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc)

    activation = ledger.append(
        record_type="ACTIVATION",
        entity_id="AI-v1.0:XAUUSD:ACTIVATION",
        effective_at_utc=now,
        recorded_at_utc=now,
        payload={"protocol_version": "AI-v1.0"},
    )
    inference = ledger.append(
        record_type="INFERENCE",
        entity_id="AI-v1.0:XAUUSD:2026-09-28T08:00:00Z",
        effective_at_utc=now,
        recorded_at_utc=now,
        payload={"decision": "BUY"},
    )

    assert inference["previous_hash"] == activation["record_hash"]
    assert ledger.verify()["valid"] is True
    assert ledger.counts_by_type() == {"ACTIVATION": 1, "INFERENCE": 1}

    with sqlite3.connect(ledger.path) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute(
                "UPDATE ai_records SET entity_id='changed' WHERE sequence=1"
            )

    with pytest.raises(ValueError):
        ledger.append(
            record_type="NOT_ALLOWED",
            entity_id="x",
            effective_at_utc=now,
            recorded_at_utc=now,
            payload={},
        )
