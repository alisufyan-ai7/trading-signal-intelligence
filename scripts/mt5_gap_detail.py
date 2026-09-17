from __future__ import annotations

import argparse
import json

from trading_signal_intelligence.connectors.mt5 import MT5Connector


EXPECTED_SECONDS = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14_400,
    "D1": 86_400,
}


def main() -> None:
    parser = argparse.ArgumentParser(description="List exact timestamp gaps in MT5 bar history")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=50_000)
    parser.add_argument("--min-gap-hours", type=float, default=2.0)
    parser.add_argument("--max-results", type=int, default=100)
    parser.add_argument("--terminal-path", default=None)
    args = parser.parse_args()

    timeframe = args.timeframe.upper()
    expected = EXPECTED_SECONDS[timeframe]
    minimum_seconds = max(int(args.min_gap_hours * 3600), expected + 1)

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        bars = connector.bars_from_pos(
            args.symbol,
            args.canonical,
            timeframe,
            start_pos=0,
            count=args.bars,
        )
    finally:
        connector.disconnect()

    gaps = []
    for left, right in zip(bars, bars[1:]):
        seconds = int((right.timestamp_utc - left.timestamp_utc).total_seconds())
        if seconds >= minimum_seconds:
            gaps.append(
                {
                    "previous_bar_utc": str(left.timestamp_utc),
                    "next_bar_utc": str(right.timestamp_utc),
                    "gap_hours": seconds / 3600,
                }
            )

    gaps.sort(key=lambda item: (-float(item["gap_hours"]), str(item["previous_bar_utc"])))

    print(
        json.dumps(
            {
                "source_symbol": args.symbol,
                "canonical_symbol": args.canonical,
                "timeframe": timeframe,
                "matching_gap_count": len(gaps),
                "showing": min(len(gaps), args.max_results),
                "gaps": gaps[: args.max_results],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
