from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.signals import (
    append_signal_from_approved_inference,
    evaluate_signal,
)
from trading_signal_intelligence.models import Candle


def guardrails() -> dict:
    return {
        "entry_policy": "next_eligible_h1_open",
        "max_hold_h1_bars": 24,
        "tp1_position_fraction": 0.5,
        "tp2_position_fraction": 0.5,
        "move_stop_after_tp1": False,
        "cost_multiplier": 1.25,
    }


def inference_payload() -> dict:
    return {
        "protocol_version": "AI-v1.0",
        "source_symbol": "XAUUSD",
        "source_bar_open_utc": "2026-09-28T07:00:00Z",
        "source_bar_close_utc": "2026-09-28T08:00:00Z",
        "feature_snapshot_sha256": "a" * 64,
        "feature_snapshot": {
            "source_symbol": "XAUUSD",
            "canonical_symbol": "XAU/USD",
            "source_bar_close_utc": "2026-09-28T08:00:00Z",
            "atr_14": 10.0,
            "spread_price": 0.5,
        },
        "normalized_decision": {
            "protocol_version": "AI-v1.0",
            "decision": "BUY",
            "raw_confidence": 65,
            "regime": "TREND_UP",
            "stop_atr": 1.5,
            "tp1_r": 1.0,
            "tp2_r": 2.0,
            "rationale": "Trend aligned.",
            "supporting_factors": ["trend"],
            "risk_factors": ["volatility"],
        },
        "guard_publishable": True,
        "guard_reasons": [],
        "estimated_cost_r": 0.041666666666666664,
    }


def candle(
    ts: datetime,
    *,
    open_: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        source="exness_mt5_demo",
        source_symbol="XAUUSD",
        symbol="XAU/USD",
        timeframe="H1",
        timestamp_utc=ts,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal("1000"),
        volume_kind="tick",
        spread=Decimal("125"),
        is_closed=True,
    )


def seeded_signal(tmp_path):
    ledger = AILedger(tmp_path / "ai.sqlite")
    entity = "AI-v1.0:XAUUSD:2026-09-28T08:00:00Z"
    now = datetime(2026, 9, 28, 8, 0, 30, tzinfo=timezone.utc)
    ledger.append(
        record_type="INFERENCE",
        entity_id=entity,
        effective_at_utc=datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
        recorded_at_utc=now,
        payload=inference_payload(),
    )
    entry_bar = candle(
        datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
        open_=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
    )
    signal = append_signal_from_approved_inference(
        ledger=ledger,
        entity_id=entity,
        entry_bar=entry_bar,
        guardrails=guardrails(),
        recorded_at_utc=now,
    )
    return ledger, entity, signal


def test_signal_levels_are_deterministic(tmp_path) -> None:
    ledger, _, signal = seeded_signal(tmp_path)
    p = signal["payload"]

    assert p["entry"] == 100.0
    assert p["risk_price"] == 15.0
    assert p["stop"] == 85.0
    assert p["tp1"] == 115.0
    assert p["tp2"] == 130.0
    assert p["total_cost_price"] == 0.625
    assert ledger.verify()["valid"] is True


def test_same_bar_stop_first_before_tp1(tmp_path) -> None:
    ledger, entity, _ = seeded_signal(tmp_path)
    bar = candle(
        datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
        open_=100.0,
        high=116.0,
        low=84.0,
        close=100.0,
    )

    actions = evaluate_signal(
        ledger=ledger,
        entity_id=entity,
        closed_h1=[bar],
        recorded_at_utc=datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc),
    )

    assert [row["record_type"] for row in actions] == ["EXIT"]
    assert actions[0]["payload"]["reason"] == "SAME_BAR_STOP_FIRST"
    assert actions[0]["payload"]["total_combined_signal_net_r"] < -1.0


def test_tp1_then_tp2_combines_fractional_r(tmp_path) -> None:
    ledger, entity, _ = seeded_signal(tmp_path)
    bar1 = candle(
        datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
        open_=100.0,
        high=116.0,
        low=95.0,
        close=114.0,
    )
    bar2 = candle(
        datetime(2026, 9, 28, 9, 0, tzinfo=timezone.utc),
        open_=114.0,
        high=131.0,
        low=110.0,
        close=129.0,
    )

    actions = evaluate_signal(
        ledger=ledger,
        entity_id=entity,
        closed_h1=[bar1, bar2],
        recorded_at_utc=datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc),
    )

    assert [row["record_type"] for row in actions] == ["PARTIAL_EXIT", "EXIT"]
    assert actions[-1]["payload"]["reason"] == "TP2"
    expected = 1.5 - (0.625 / 15.0)
    assert actions[-1]["payload"]["total_combined_signal_net_r"] == pytest.approx(expected)


def test_timeout_after_24_bars(tmp_path) -> None:
    ledger, entity, _ = seeded_signal(tmp_path)
    start = datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc)
    bars = [
        candle(
            start + timedelta(hours=i),
            open_=100.0,
            high=105.0,
            low=95.0,
            close=101.0,
        )
        for i in range(24)
    ]

    actions = evaluate_signal(
        ledger=ledger,
        entity_id=entity,
        closed_h1=bars,
        recorded_at_utc=datetime(2026, 9, 29, 8, 0, tzinfo=timezone.utc),
    )

    assert [row["record_type"] for row in actions] == ["EXIT"]
    assert actions[0]["payload"]["reason"] == "TIMEOUT"
    assert actions[0]["payload"]["bars_held"] == 24
