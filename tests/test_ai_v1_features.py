from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_signal_intelligence.ai_v1.features import build_feature_snapshot
from trading_signal_intelligence.models import Candle


def _candle(
    *,
    timeframe: str,
    ts: datetime,
    base: float,
    step: float,
    index: int,
    spread: float,
) -> Candle:
    close = base + step * index + 0.15 * ((index % 7) - 3)
    open_ = close - 0.2
    high = max(open_, close) + 1.0 + 0.01 * (index % 5)
    low = min(open_, close) - 0.9 - 0.01 * (index % 3)
    return Candle(
        source="exness_mt5_demo",
        source_symbol="XAUUSD",
        symbol="XAU/USD",
        timeframe=timeframe,
        timestamp_utc=ts,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(1000 + (index % 23) * 17)),
        volume_kind="tick",
        spread=Decimal(str(spread)),
        is_closed=True,
    )


def _history() -> tuple[list[Candle], list[Candle], datetime]:
    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    h1 = [
        _candle(
            timeframe="H1",
            ts=start + timedelta(hours=i),
            base=4000.0,
            step=0.12,
            index=i,
            spread=125.0,
        )
        for i in range(420)
    ]
    h4 = [
        _candle(
            timeframe="H4",
            ts=start + timedelta(hours=4 * i),
            base=4000.0,
            step=0.45,
            index=i,
            spread=125.0,
        )
        for i in range(110)
    ]
    inference = h1[-1].timestamp_utc + timedelta(hours=1, minutes=2)
    return h1, h4, inference


def test_feature_snapshot_is_deterministic_and_causal() -> None:
    h1, h4, inference = _history()

    first = build_feature_snapshot(
        h1_candles=h1,
        h4_candles=h4,
        point_size=0.001,
        inference_started_utc=inference,
        source_symbol="XAUUSD",
        canonical_symbol="XAU/USD",
    )
    second = build_feature_snapshot(
        h1_candles=list(reversed(list(reversed(h1)))),
        h4_candles=list(h4),
        point_size=0.001,
        inference_started_utc=inference,
        source_symbol="XAUUSD",
        canonical_symbol="XAU/USD",
    )

    assert first.payload == second.payload
    assert first.sha256 == second.sha256
    assert first.payload["feature_schema_version"] == "AI-v1.0"
    assert first.payload["source_symbol"] == "XAUUSD"
    assert first.payload["data_age_seconds"] == 120.0
    assert first.payload["spread_price"] == 0.125
    assert 0.0 <= first.payload["atr_percentile_252"] <= 1.0
    assert first.payload["volatility_regime"] in {"LOW", "NORMAL", "HIGH"}

    future_h1 = _candle(
        timeframe="H1",
        ts=h1[-1].timestamp_utc + timedelta(hours=1),
        base=9000.0,
        step=10.0,
        index=999,
        spread=999.0,
    )
    future_h4 = _candle(
        timeframe="H4",
        ts=h4[-1].timestamp_utc + timedelta(hours=4),
        base=9000.0,
        step=10.0,
        index=999,
        spread=999.0,
    )
    with_future = build_feature_snapshot(
        h1_candles=h1 + [future_h1],
        h4_candles=h4 + [future_h4],
        point_size=0.001,
        inference_started_utc=inference,
        source_symbol="XAUUSD",
        canonical_symbol="XAU/USD",
    )

    assert with_future.payload == first.payload
    assert with_future.sha256 == first.sha256
