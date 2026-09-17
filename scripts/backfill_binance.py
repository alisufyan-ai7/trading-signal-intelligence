from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone

from trading_signal_intelligence.connectors.binance import BinanceSpotConnector
from trading_signal_intelligence.storage import CandleStore


_INTERVAL_MS = {
    "M1": 60_000,
    "M5": 300_000,
    "M15": 900_000,
    "H1": 3_600_000,
    "H4": 14_400_000,
    "D1": 86_400_000,
}


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill Binance Spot bars into the research store")
    parser.add_argument("--symbol", required=True, help="Binance source symbol, e.g. BTCUSDT")
    parser.add_argument("--canonical", required=True, help="Canonical internal symbol")
    parser.add_argument("--timeframe", default="H1", help="M1/M5/M15/H1/H4/D1")
    parser.add_argument("--start", default="2018-01-01T00:00:00+00:00", help="UTC ISO start")
    parser.add_argument("--end", default=None, help="UTC ISO end; defaults to now")
    parser.add_argument("--database", default="data/research.sqlite", help="SQLite path")
    args = parser.parse_args()

    timeframe = args.timeframe.upper()
    if timeframe not in _INTERVAL_MS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    start = parse_utc(args.start)
    end = parse_utc(args.end) if args.end else datetime.now(tz=timezone.utc)
    cursor_ms = int(start.timestamp() * 1000)
    end_ms = int(end.timestamp() * 1000)
    step_ms = _INTERVAL_MS[timeframe]

    connector = BinanceSpotConnector()
    store = CandleStore(args.database)

    total_received = 0
    total_written = 0
    first_timestamp = None
    last_timestamp = None

    while cursor_ms <= end_ms:
        batch = connector.klines(
            args.symbol,
            args.canonical,
            timeframe,
            limit=1000,
            start_time_ms=cursor_ms,
            end_time_ms=end_ms,
        )
        if not batch:
            break

        closed = [candle for candle in batch if candle.is_closed]
        total_received += len(batch)
        total_written += store.upsert_candles(closed)

        if closed:
            first_timestamp = first_timestamp or closed[0].timestamp_utc
            last_timestamp = closed[-1].timestamp_utc

        final_open_ms = int(batch[-1].timestamp_utc.timestamp() * 1000)
        next_cursor = final_open_ms + step_ms
        if next_cursor <= cursor_ms:
            raise RuntimeError("Binance pagination failed to advance")
        cursor_ms = next_cursor

        if len(batch) < 1000:
            break

    print(
        json.dumps(
            {
                "database": args.database,
                "source": "binance_spot",
                "source_symbol": args.symbol.upper(),
                "canonical_symbol": args.canonical,
                "timeframe": timeframe,
                "requested_start_utc": str(start),
                "requested_end_utc": str(end),
                "received_bars": total_received,
                "closed_bars_written": total_written,
                "first_timestamp_utc": str(first_timestamp) if first_timestamp else None,
                "last_timestamp_utc": str(last_timestamp) if last_timestamp else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
