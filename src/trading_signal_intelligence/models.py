from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal


@dataclass(frozen=True, slots=True)
class Candle:
    source: str
    source_symbol: str
    symbol: str
    timeframe: str
    timestamp_utc: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal | None = None
    volume_kind: str | None = None
    spread: Decimal | None = None
    is_closed: bool = True

    def __post_init__(self) -> None:
        if self.timestamp_utc.tzinfo is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if self.timestamp_utc.utcoffset() != timezone.utc.utcoffset(self.timestamp_utc):
            raise ValueError("timestamp_utc must be UTC")
        if self.high < max(self.open, self.close, self.low):
            raise ValueError("high is inconsistent with OHLC values")
        if self.low > min(self.open, self.close, self.high):
            raise ValueError("low is inconsistent with OHLC values")


@dataclass(frozen=True, slots=True)
class Quote:
    source: str
    source_symbol: str
    symbol: str
    timestamp_utc: datetime
    bid: Decimal | None
    ask: Decimal | None
    last: Decimal | None = None

    @property
    def spread(self) -> Decimal | None:
        if self.bid is None or self.ask is None:
            return None
        return self.ask - self.bid
