from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_signal_intelligence.models import Candle
from trading_signal_intelligence.quality import check_bar_sequence


def _bar(hour: int) -> Candle:
    return Candle(
        source="test",
        source_symbol="BTCUSDT",
        symbol="BTC/USDT",
        timeframe="H1",
        timestamp_utc=datetime(2026, 1, 1, hour, tzinfo=timezone.utc),
        open=Decimal("100"),
        high=Decimal("110"),
        low=Decimal("90"),
        close=Decimal("105"),
    )


def test_quality_accepts_regular_hourly_sequence() -> None:
    report = check_bar_sequence([_bar(0), _bar(1), _bar(2)], timedelta(hours=1))
    assert report.ok


def test_quality_detects_gap() -> None:
    report = check_bar_sequence([_bar(0), _bar(2)], timedelta(hours=1))
    assert report.unexpected_gaps == 1
