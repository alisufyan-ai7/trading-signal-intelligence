from __future__ import annotations

import json
from datetime import UTC, datetime
from decimal import Decimal
from urllib.parse import urlencode
from urllib.request import urlopen

from trading_signal_intelligence.models import Candle, Quote

_INTERVALS = {
    "M1": "1m",
    "M5": "5m",
    "M15": "15m",
    "H1": "1h",
    "H4": "4h",
    "D1": "1d",
}


class BinanceSpotConnector:
    """Minimal public Binance Spot market-data adapter.

    This intentionally uses only documented public market-data endpoints for the
    first R&D probe. Authentication/trading concerns belong in separate adapters.
    """

    def __init__(self, base_url: str = "https://api.binance.com") -> None:
        self.base_url = base_url.rstrip("/")
        self.source_name = "binance_spot"

    def klines(
        self,
        source_symbol: str,
        canonical_symbol: str,
        timeframe: str,
        *,
        limit: int = 500,
        start_time_ms: int | None = None,
        end_time_ms: int | None = None,
    ) -> list[Candle]:
        interval = _INTERVALS.get(timeframe.upper())
        if interval is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")
        if not 1 <= limit <= 1000:
            raise ValueError("Binance kline limit must be between 1 and 1000")

        params: dict[str, str | int] = {
            "symbol": source_symbol.upper(),
            "interval": interval,
            "limit": limit,
        }
        if start_time_ms is not None:
            params["startTime"] = start_time_ms
        if end_time_ms is not None:
            params["endTime"] = end_time_ms

        url = f"{self.base_url}/api/v3/klines?{urlencode(params)}"
        with urlopen(url, timeout=20) as response:  # nosec B310: fixed configured HTTPS API base
            payload = json.loads(response.read().decode("utf-8"))

        now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
        candles: list[Candle] = []
        for row in payload:
            open_time_ms = int(row[0])
            close_time_ms = int(row[6])
            candles.append(
                Candle(
                    source=self.source_name,
                    source_symbol=source_symbol.upper(),
                    symbol=canonical_symbol,
                    timeframe=timeframe.upper(),
                    timestamp_utc=datetime.fromtimestamp(open_time_ms / 1000, tz=UTC),
                    open=Decimal(row[1]),
                    high=Decimal(row[2]),
                    low=Decimal(row[3]),
                    close=Decimal(row[4]),
                    volume=Decimal(row[5]),
                    volume_kind="base_asset_volume",
                    spread=None,
                    is_closed=close_time_ms < now_ms,
                )
            )
        return candles

    def book_ticker(
        self,
        source_symbol: str,
        canonical_symbol: str,
    ) -> Quote:
        """Read the current public Binance Spot best bid / best ask.

        The public book-ticker response does not carry an exchange timestamp, so
        the quote timestamp records the local UTC time immediately after the
        HTTPS response is read. This method performs no authentication and has no
        trading side effect.
        """

        params = {"symbol": source_symbol.upper()}
        url = f"{self.base_url}/api/v3/ticker/bookTicker?{urlencode(params)}"
        with urlopen(url, timeout=20) as response:  # nosec B310: fixed configured HTTPS API base
            payload = json.loads(response.read().decode("utf-8"))

        observed_at_utc = datetime.now(tz=UTC)
        bid = Decimal(str(payload["bidPrice"]))
        ask = Decimal(str(payload["askPrice"]))
        if bid <= 0 or ask <= 0:
            raise ValueError("Binance best bid/ask must be positive")
        if ask < bid:
            raise ValueError("Binance best ask must be greater than or equal to best bid")

        return Quote(
            source=self.source_name,
            source_symbol=source_symbol.upper(),
            symbol=canonical_symbol,
            timestamp_utc=observed_at_utc,
            bid=bid,
            ask=ask,
            last=None,
        )
