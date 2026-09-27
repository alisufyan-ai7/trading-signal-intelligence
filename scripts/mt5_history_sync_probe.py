from __future__ import annotations

import argparse
import json
import time
from datetime import timedelta, timezone

from trading_signal_intelligence.connectors.mt5 import MT5Connector


def _latest_iso(rows) -> str | None:
    if rows is None or len(rows) == 0:
        return None
    latest = max(int(row["time"]) for row in rows)
    from datetime import datetime
    return datetime.fromtimestamp(latest, tz=timezone.utc).isoformat()


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Probe/encourage MT5 recent-history synchronization by requesting recent bars "
            "through position, from-date and date-range APIs"
        )
    )
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--terminal-path", default=None)
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--delay", type=float, default=5.0)
    parser.add_argument("--recent-days", type=int, default=14)
    args = parser.parse_args()

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        mt5 = connector._mt5()
        connector.ensure_symbol(args.symbol)
        quote = connector.latest_quote(args.symbol, args.canonical)
        out = {
            "source_symbol": args.symbol,
            "canonical_symbol": args.canonical,
            "quote_timestamp_utc": quote.timestamp_utc.isoformat(),
            "attempts": [],
            "final": {},
        }

        for attempt in range(1, args.attempts + 1):
            attempt_out = {"attempt": attempt, "timeframes": {}}
            for timeframe, nominal_hours in (("H1", 1), ("H4", 4)):
                mt5_tf = getattr(mt5, f"TIMEFRAME_{timeframe}")
                from_pos = mt5.copy_rates_from_pos(args.symbol, mt5_tf, 0, 20)
                from_date = mt5.copy_rates_from(
                    args.symbol,
                    mt5_tf,
                    quote.timestamp_utc,
                    50,
                )
                from_range = mt5.copy_rates_range(
                    args.symbol,
                    mt5_tf,
                    quote.timestamp_utc - timedelta(days=args.recent_days),
                    quote.timestamp_utc,
                )

                latest_values = [
                    value for value in (
                        _latest_iso(from_pos),
                        _latest_iso(from_date),
                        _latest_iso(from_range),
                    )
                    if value is not None
                ]
                latest = max(latest_values) if latest_values else None
                attempt_out["timeframes"][timeframe] = {
                    "copy_rates_from_pos_latest_utc": _latest_iso(from_pos),
                    "copy_rates_from_latest_utc": _latest_iso(from_date),
                    "copy_rates_range_latest_utc": _latest_iso(from_range),
                    "latest_any_method_utc": latest,
                    "last_error": list(mt5.last_error()),
                }

            out["attempts"].append(attempt_out)
            if attempt < args.attempts:
                time.sleep(args.delay)

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
                out["final"][timeframe] = {
                    "latest_bar_timestamp_utc": None,
                    "appears_recent": False,
                }
                continue

            lag_hours = (quote.timestamp_utc - latest).total_seconds() / 3600.0
            out["final"][timeframe] = {
                "latest_bar_timestamp_utc": latest.isoformat(),
                "lag_vs_quote_hours": lag_hours,
                "nominal_bar_hours": nominal_hours,
                "appears_recent": lag_hours <= nominal_hours + 2,
            }

        print(json.dumps(out, indent=2))
    finally:
        connector.disconnect()


if __name__ == "__main__":
    main()
