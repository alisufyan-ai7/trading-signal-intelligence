from __future__ import annotations

import argparse
import json
from datetime import timezone

from trading_signal_intelligence.connectors.mt5 import MT5Connector


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare latest MT5 quote time with latest bars by timeframe")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--terminal-path", default=None)
    args = parser.parse_args()

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        quote = connector.latest_quote(args.symbol, args.canonical)
        out = {
            "source_symbol": args.symbol,
            "canonical_symbol": args.canonical,
            "quote_timestamp_utc": quote.timestamp_utc.astimezone(timezone.utc).isoformat(),
            "timeframes": {},
        }
        for timeframe, nominal_hours in (("H1", 1), ("H4", 4)):
            bars = connector.bars_from_pos(
                args.symbol,
                args.canonical,
                timeframe,
                start_pos=0,
                count=20,
            )
            latest = max((bar.timestamp_utc for bar in bars), default=None)
            if latest is None:
                out["timeframes"][timeframe] = {"bars_returned": 0, "latest_bar_timestamp_utc": None}
                continue
            lag_hours = (quote.timestamp_utc - latest).total_seconds() / 3600.0
            out["timeframes"][timeframe] = {
                "bars_returned": len(bars),
                "latest_bar_timestamp_utc": latest.astimezone(timezone.utc).isoformat(),
                "lag_vs_quote_hours": lag_hours,
                "nominal_bar_hours": nominal_hours,
                "appears_recent": lag_hours <= nominal_hours + 2,
            }
        print(json.dumps(out, indent=2))
    finally:
        connector.disconnect()


if __name__ == "__main__":
    main()
