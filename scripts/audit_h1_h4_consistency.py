from __future__ import annotations

import argparse
import json
from datetime import timedelta

import pandas as pd

from trading_signal_intelligence.storage import CandleStore


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare stored broker H4 bars with H4 bars reconstructed from stored H1 data"
    )
    parser.add_argument("--symbol", required=True, help="Source symbol, e.g. EURUSD")
    parser.add_argument("--canonical", required=True, help="Canonical symbol, e.g. EUR/USD")
    parser.add_argument("--point-size", type=float, required=True)
    parser.add_argument("--source", default="exness_mt5_demo")
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--max-examples", type=int, default=10)
    args = parser.parse_args()

    store = CandleStore(args.database)
    h1 = store.load_candles(
        source=args.source,
        source_symbol=args.symbol,
        timeframe="H1",
        closed_only=True,
    )
    h4 = store.load_candles(
        source=args.source,
        source_symbol=args.symbol,
        timeframe="H4",
        closed_only=True,
    )
    if not h1 or not h4:
        raise RuntimeError("Both H1 and H4 datasets are required")

    h1_rows = pd.DataFrame(
        {
            "timestamp": [c.timestamp_utc for c in h1],
            "open": [float(c.open) for c in h1],
            "high": [float(c.high) for c in h1],
            "low": [float(c.low) for c in h1],
            "close": [float(c.close) for c in h1],
        }
    ).sort_values("timestamp")
    h4_rows = pd.DataFrame(
        {
            "timestamp": [c.timestamp_utc for c in h4],
            "open": [float(c.open) for c in h4],
            "high": [float(c.high) for c in h4],
            "low": [float(c.low) for c in h4],
            "close": [float(c.close) for c in h4],
        }
    ).sort_values("timestamp")

    h1_start = h1_rows["timestamp"].min()
    h1_end = h1_rows["timestamp"].max()
    comparable_h4 = h4_rows[
        (h4_rows["timestamp"] >= h1_start)
        & (h4_rows["timestamp"] + pd.Timedelta(hours=3) <= h1_end)
    ].copy()

    comparisons = []
    incomplete_groups = 0
    for _, broker_bar in comparable_h4.iterrows():
        start = broker_bar["timestamp"]
        end = start + pd.Timedelta(hours=4)
        group = h1_rows[(h1_rows["timestamp"] >= start) & (h1_rows["timestamp"] < end)]
        if len(group) != 4:
            incomplete_groups += 1
            continue

        reconstructed = {
            "open": float(group.iloc[0]["open"]),
            "high": float(group["high"].max()),
            "low": float(group["low"].min()),
            "close": float(group.iloc[-1]["close"]),
        }
        diffs_points = {
            key: abs(float(broker_bar[key]) - reconstructed[key]) / args.point_size
            for key in ("open", "high", "low", "close")
        }
        comparisons.append(
            {
                "timestamp_utc": str(start),
                "broker": {key: float(broker_bar[key]) for key in ("open", "high", "low", "close")},
                "reconstructed": reconstructed,
                "diff_points": diffs_points,
                "max_diff_points": max(diffs_points.values()),
            }
        )

    if not comparisons:
        raise RuntimeError("No complete four-H1-bar groups overlap stored H4 history")

    max_diffs = pd.Series([row["max_diff_points"] for row in comparisons], dtype=float)
    mismatches = [row for row in comparisons if row["max_diff_points"] > 0.5]

    summary = {
        "source": args.source,
        "source_symbol": args.symbol,
        "canonical_symbol": args.canonical,
        "h1_first_timestamp_utc": str(h1_start),
        "h1_last_timestamp_utc": str(h1_end),
        "stored_h4_first_timestamp_utc": str(h4_rows["timestamp"].min()),
        "stored_h4_last_timestamp_utc": str(h4_rows["timestamp"].max()),
        "overlapping_h4_bars": int(len(comparable_h4)),
        "complete_four_h1_groups_compared": int(len(comparisons)),
        "incomplete_h1_groups_skipped": int(incomplete_groups),
        "max_ohlc_difference_points": float(max_diffs.max()),
        "median_max_difference_points": float(max_diffs.median()),
        "p95_max_difference_points": float(max_diffs.quantile(0.95)),
        "bars_over_half_point_difference": int(len(mismatches)),
        "match_fraction_within_half_point": float(1 - len(mismatches) / len(comparisons)),
        "largest_mismatch_examples": sorted(
            mismatches,
            key=lambda row: row["max_diff_points"],
            reverse=True,
        )[: args.max_examples],
        "interpretation": (
            "This compares broker-provided H4 OHLC with exact four-bar H1 reconstruction over the "
            "shared history. Large or frequent differences require investigation before using H4 as a regime feed."
        ),
    }
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
