from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.shadow_runtime import (
    H1_BARS,
    H4_BARS,
    completed_opportunities,
    cycle_entity_id,
    cycle_processed,
    market_specs,
)
from trading_signal_intelligence.models import Candle


ROOT = Path(__file__).resolve().parents[1]


def candle(ts: datetime, *, closed: bool = True) -> Candle:
    return Candle(
        source="exness_mt5_demo",
        source_symbol="XAUUSD",
        symbol="XAU/USD",
        timeframe="H1",
        timestamp_utc=ts,
        open=Decimal("100"),
        high=Decimal("102"),
        low=Decimal("99"),
        close=Decimal("101"),
        volume=Decimal("1000"),
        volume_kind="tick_volume",
        spread=Decimal("125"),
        is_closed=closed,
    )


def test_runtime_uses_pre_activation_probe_history_sizes() -> None:
    assert H1_BARS == 500
    assert H4_BARS == 200


def test_market_specs_match_frozen_launch_universe() -> None:
    specs = market_specs(ROOT)
    assert set(specs) == {"XAUUSD", "USTEC", "US30"}
    assert specs["XAUUSD"].canonical_symbol == "XAU/USD"
    assert specs["XAUUSD"].point_size == 0.001
    assert specs["USTEC"].point_size == 0.01
    assert specs["US30"].point_size == 0.1


def test_completed_opportunities_excludes_pre_activation_and_incomplete() -> None:
    base = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
    bars = [
        candle(base - timedelta(hours=1)),
        candle(base),
        candle(base + timedelta(hours=1)),
        candle(base + timedelta(hours=2), closed=False),
    ]
    activated = datetime(2026, 9, 28, 10, 30, tzinfo=timezone.utc)
    now = datetime(2026, 9, 28, 12, 2, tzinfo=timezone.utc)

    opportunities = completed_opportunities(
        bars,
        activated_at_utc=activated,
        now_utc=now,
    )

    assert [row[1] for row in opportunities] == [
        datetime(2026, 9, 28, 11, 0, tzinfo=timezone.utc),
        datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc),
    ]
    assert opportunities[-1][2] == 120.0


def test_cycle_entity_and_processed_detection(tmp_path) -> None:
    ledger = AILedger(tmp_path / "ai.sqlite")
    close = datetime(2026, 9, 28, 12, 0, tzinfo=timezone.utc)
    entity = cycle_entity_id("XAUUSD", close)

    assert entity == "AI-v1.0:XAUUSD:2026-09-28T12:00:00Z"
    assert cycle_processed(ledger, entity) is False

    ledger.append(
        record_type="MISSED_INFERENCE",
        entity_id=entity,
        effective_at_utc=close,
        recorded_at_utc=close + timedelta(minutes=10),
        payload={"reason": "test"},
    )
    assert cycle_processed(ledger, entity) is True
