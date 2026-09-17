from __future__ import annotations

import argparse
import json
import time

from trading_signal_intelligence.connectors.mt5 import MT5Connector
from trading_signal_intelligence.storage import CandleStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill MT5 bars into the local research store")
    parser.add_argument("--symbol", required=True, help="Broker source symbol")
    parser.add_argument("--canonical", required=True, help="Canonical internal symbol")
    parser.add_argument("--timeframe", default="H1", help="M1/M5/M15/H1/H4/D1")
    parser.add_argument("--bars", type=int, default=50_000, help="Maximum recent bars")
    parser.add_argument("--chunk-size", type=int, default=5_000, help="Bars per MT5 IPC request")
    parser.add_argument("--retries", type=int, default=3, help="Retries for a transient MT5 call failure")
    parser.add_argument("--retry-delay", type=float, default=1.0, help="Seconds between retries")
    parser.add_argument("--database", default="data/research.sqlite", help="SQLite path")
    parser.add_argument("--terminal-path", default=None, help="Optional terminal64.exe path")
    args = parser.parse_args()

    if args.bars <= 0:
        raise ValueError("--bars must be positive")
    if args.chunk_size <= 0:
        raise ValueError("--chunk-size must be positive")
    if args.retries <= 0:
        raise ValueError("--retries must be positive")

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    candles_by_timestamp = {}
    chunks = 0
    start_pos = 0
    remaining = args.bars

    try:
        while remaining > 0:
            request_count = min(args.chunk_size, remaining)
            last_error: Exception | None = None
            chunk = None

            for attempt in range(1, args.retries + 1):
                try:
                    chunk = connector.bars_from_pos(
                        args.symbol,
                        args.canonical,
                        args.timeframe,
                        start_pos=start_pos,
                        count=request_count,
                    )
                    last_error = None
                    break
                except RuntimeError as exc:
                    last_error = exc
                    if attempt < args.retries:
                        time.sleep(args.retry_delay)

            if last_error is not None:
                raise RuntimeError(
                    f"MT5 backfill failed after {args.retries} attempts at "
                    f"start_pos={start_pos}, count={request_count}: {last_error}"
                ) from last_error

            if not chunk:
                break

            chunks += 1
            for candle in chunk:
                candles_by_timestamp[candle.timestamp_utc] = candle

            returned = len(chunk)
            start_pos += returned
            remaining -= returned

            # A short page means MT5 reached the oldest history it currently exposes.
            if returned < request_count:
                break

            # Avoid hammering the local terminal IPC when many pages are required.
            time.sleep(0.05)
    finally:
        connector.disconnect()

    candles = sorted(candles_by_timestamp.values(), key=lambda candle: candle.timestamp_utc)
    closed = [candle for candle in candles if candle.is_closed]
    store = CandleStore(args.database)
    written = store.upsert_candles(closed)

    print(
        json.dumps(
            {
                "database": args.database,
                "source": "exness_mt5_demo",
                "source_symbol": args.symbol,
                "canonical_symbol": args.canonical,
                "timeframe": args.timeframe.upper(),
                "requested_bars": args.bars,
                "chunk_size": args.chunk_size,
                "chunks": chunks,
                "received_unique_bars": len(candles),
                "closed_bars_written": written,
                "first_timestamp_utc": str(closed[0].timestamp_utc) if closed else None,
                "last_timestamp_utc": str(closed[-1].timestamp_utc) if closed else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
