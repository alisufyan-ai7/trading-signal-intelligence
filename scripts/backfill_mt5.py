from __future__ import annotations

import argparse
import json

from trading_signal_intelligence.connectors.mt5 import MT5Connector
from trading_signal_intelligence.storage import CandleStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill MT5 bars into the local research store")
    parser.add_argument("--symbol", required=True, help="Broker source symbol")
    parser.add_argument("--canonical", required=True, help="Canonical internal symbol")
    parser.add_argument("--timeframe", default="H1", help="M1/M5/M15/H1/H4/D1")
    parser.add_argument("--bars", type=int, default=50_000, help="Maximum recent bars")
    parser.add_argument("--database", default="data/research.sqlite", help="SQLite path")
    parser.add_argument("--terminal-path", default=None, help="Optional terminal64.exe path")
    args = parser.parse_args()

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        candles = connector.bars_from_pos(
            args.symbol,
            args.canonical,
            args.timeframe,
            start_pos=0,
            count=args.bars,
        )
    finally:
        connector.disconnect()

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
                "received_bars": len(candles),
                "closed_bars_written": written,
                "first_timestamp_utc": str(closed[0].timestamp_utc) if closed else None,
                "last_timestamp_utc": str(closed[-1].timestamp_utc) if closed else None,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
