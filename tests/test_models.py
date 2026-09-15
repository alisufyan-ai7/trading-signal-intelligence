from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_signal_intelligence.models import Candle, Quote


def test_candle_accepts_valid_utc_ohlc() -> None:
    candle = Candle(
        source="test",
        source_symbol="BTCUSDT",
        symbol="BTC/USDT",
        timeframe="H1",
        timestamp_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("95"),
        close=Decimal("105"),
    )
    assert candle.is_closed is True


def test_candle_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError):
        Candle(
            source="test",
            source_symbol="BTCUSDT",
            symbol="BTC/USDT",
            timeframe="H1",
            timestamp_utc=datetime(2026, 1, 1),
            open=Decimal("100"),
            high=Decimal("110"),
            low=Decimal("95"),
            close=Decimal("105"),
        )


def test_quote_spread() -> None:
    quote = Quote(
        source="test",
        source_symbol="EURUSD",
        symbol="EUR/USD",
        timestamp_utc=datetime(2026, 1, 1, tzinfo=timezone.utc),
        bid=Decimal("1.1000"),
        ask=Decimal("1.1002"),
    )
    assert quote.spread == Decimal("0.0002")
