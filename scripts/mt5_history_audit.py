from __future__ import annotations

import argparse
import json
import statistics
from collections import Counter
from datetime import timedelta

from trading_signal_intelligence.connectors.mt5 import MT5Connector


EXPECTED_SECONDS = {
    "M1": 60,
    "M5": 300,
    "M15": 900,
    "H1": 3600,
    "H4": 14_400,
    "D1": 86_400,
}


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit MT5 historical bars")
    parser.add_argument("--terminal-path", default=None, help="Optional path to terminal64.exe")
    parser.add_argument("--symbol", required=True, help="Broker source symbol")
    parser.add_argument("--canonical", required=True, help="Canonical symbol label")
    parser.add_argument("--timeframe", default="H1", help="M1/M5/M15/H1/H4/D1")
    parser.add_argument("--bars", type=int, default=50_000, help="Maximum recent bars to request")
    args = parser.parse_args()

    timeframe = args.timeframe.upper()
    expected = EXPECTED_SECONDS[timeframe]

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

    if not bars:
        raise RuntimeError("No bars returned")

    timestamps = [bar.timestamp_utc for bar in bars]
    closed = [bar for bar in bars if bar.is_closed]
    unique_count = len(set(timestamps))
    duplicates = len(timestamps) - unique_count
    ordered = all(left < right for left, right in zip(timestamps, timestamps[1:]))

    gaps: list[int] = []
    for left, right in zip(timestamps, timestamps[1:]):
        seconds = int((right - left).total_seconds())
        if seconds > expected:
            gaps.append(seconds)

    gap_hours = Counter(round(seconds / 3600, 2) for seconds in gaps)
    spreads = [float(bar.spread) for bar in closed if bar.spread is not None]
    volumes = [float(bar.volume) for bar in closed if bar.volume is not None]

    summary = {
        "source_symbol": args.symbol,
        "canonical_symbol": args.canonical,
        "timeframe": timeframe,
        "requested_bars": args.bars,
        "returned_bars": len(bars),
        "closed_bars": len(closed),
        "first_timestamp_utc": str(timestamps[0]),
        "last_timestamp_utc": str(timestamps[-1]),
        "history_span_days": round((timestamps[-1] - timestamps[0]) / timedelta(days=1), 2),
        "strictly_increasing": ordered,
        "duplicate_timestamps": duplicates,
        "gap_count": len(gaps),
        "largest_gap_hours": max((seconds / 3600 for seconds in gaps), default=0),
        "most_common_gap_hours": gap_hours.most_common(10),
        "tick_volume_populated_fraction": (
            round(sum(1 for value in volumes if value > 0) / len(closed), 6) if closed else None
        ),
        "spread_points": {
            "count": len(spreads),
            "min": min(spreads) if spreads else None,
            "median": statistics.median(spreads) if spreads else None,
            "p95": percentile(spreads, 0.95),
            "max": max(spreads) if spreads else None,
        },
    }

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
