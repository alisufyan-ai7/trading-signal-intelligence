from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from trading_signal_intelligence.backtesting.s02 import (
    S02Config,
    run_s02,
    summarize_trades,
)
from trading_signal_intelligence.storage import CandleStore


SOURCE = "exness_mt5_demo"
UNIVERSE = [
    ("EURUSD", "EUR/USD"),
    ("GBPUSD", "GBP/USD"),
    ("USDJPY", "USD/JPY"),
    ("XAUUSD", "XAU/USD"),
]
ANALYSIS_START = pd.Timestamp("2019-01-01", tz="UTC")
MIN_TRADES_INTERPRETABLE = 30


def point_size_from_registry(canonical: str, config_path: str) -> float:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    for instrument in payload["instruments"]:
        if instrument["canonical"] != canonical:
            continue
        source_cfg = instrument.get("sources", {}).get(SOURCE)
        if not source_cfg:
            break
        digits = source_cfg.get("digits")
        if digits is None:
            raise ValueError(f"Missing digits for {canonical} on {SOURCE}")
        return 10.0 ** (-int(digits))
    raise ValueError(f"No registry mapping for {canonical!r} on {SOURCE!r}")


def _slice(trades: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    if trades.empty:
        return trades.copy()
    ts = pd.to_datetime(trades["signal_timestamp_utc"], utc=True)
    return trades[(ts >= start) & (ts < end)].copy()


def _metrics(trades: pd.DataFrame) -> dict[str, Any]:
    summary = summarize_trades(trades)
    return {
        "trades": summary.get("trades", 0),
        "net_expectancy_r": summary.get("net_expectancy_r"),
        "profit_factor": summary.get("profit_factor"),
        "max_drawdown_r": summary.get("max_drawdown_r"),
        "long_trades": summary.get("long_trades", 0),
        "short_trades": summary.get("short_trades", 0),
        "low_sample": int(summary.get("trades", 0)) < MIN_TRADES_INTERPRETABLE,
    }


def _complete_windows(
    *,
    start: pd.Timestamp,
    data_end: pd.Timestamp,
    length_months: int,
    step_months: int,
):
    cursor = start
    while True:
        end = cursor + pd.DateOffset(months=length_months)
        if end > data_end:
            break
        yield cursor, end
        cursor = cursor + pd.DateOffset(months=step_months)


def _window_row(
    *,
    source_symbol: str,
    canonical: str,
    analysis_type: str,
    start: pd.Timestamp,
    end: pd.Timestamp,
    trades: pd.DataFrame,
) -> dict[str, Any]:
    row = {
        "source_symbol": source_symbol,
        "canonical_symbol": canonical,
        "analysis_type": analysis_type,
        "window_start_utc": start.isoformat(),
        "window_end_utc": end.isoformat(),
    }
    row.update(_metrics(trades))
    return row


def _summary_for_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"windows": 0}
    frame = pd.DataFrame(rows)
    interpretable = frame[~frame["low_sample"].astype(bool)].copy()
    result: dict[str, Any] = {
        "windows": int(len(frame)),
        "low_sample_windows": int(frame["low_sample"].astype(bool).sum()),
        "interpretable_windows": int(len(interpretable)),
    }
    if interpretable.empty:
        result.update(
            {
                "positive_fraction": None,
                "expectancy_min": None,
                "expectancy_median": None,
                "expectancy_max": None,
            }
        )
        return result
    expectancy = interpretable["net_expectancy_r"].astype(float)
    result.update(
        {
            "positive_fraction": float((expectancy > 0).mean()),
            "expectancy_min": float(expectancy.min()),
            "expectancy_median": float(expectancy.median()),
            "expectancy_max": float(expectancy.max()),
        }
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run frozen fixed-rule temporal stability analysis for S02 v0.1"
    )
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--registry", default="config/instruments.json")
    parser.add_argument("--output", default="outputs/s02_temporal_stability_v0_1.json")
    parser.add_argument("--csv", default="outputs/s02_temporal_stability_v0_1.csv")
    args = parser.parse_args()

    store = CandleStore(args.database)
    config = S02Config()
    all_rows: list[dict[str, Any]] = []
    market_summary: dict[str, Any] = {}

    for source_symbol, canonical in UNIVERSE:
        h1 = store.load_candles(
            source=SOURCE, source_symbol=source_symbol, timeframe="H1", closed_only=True
        )
        h4 = store.load_candles(
            source=SOURCE, source_symbol=source_symbol, timeframe="H4", closed_only=True
        )
        if not h1 or not h4:
            raise RuntimeError(f"Missing H1/H4 data for {source_symbol}")

        point_size = point_size_from_registry(canonical, args.registry)
        _, trades = run_s02(h1, h4, point_size=point_size, config=config)

        h1_last = pd.Timestamp(h1[-1].timestamp_utc)
        if h1_last.tzinfo is None:
            h1_last = h1_last.tz_localize("UTC")
        else:
            h1_last = h1_last.tz_convert("UTC")
        data_end = h1_last + pd.Timedelta(hours=1)

        half_rows: list[dict[str, Any]] = []
        for start, end in _complete_windows(
            start=ANALYSIS_START,
            data_end=data_end,
            length_months=6,
            step_months=6,
        ):
            row = _window_row(
                source_symbol=source_symbol,
                canonical=canonical,
                analysis_type="half_year",
                start=start,
                end=end,
                trades=_slice(trades, start, end),
            )
            half_rows.append(row)
            all_rows.append(row)

        rolling_rows: list[dict[str, Any]] = []
        for start, end in _complete_windows(
            start=ANALYSIS_START,
            data_end=data_end,
            length_months=12,
            step_months=3,
        ):
            row = _window_row(
                source_symbol=source_symbol,
                canonical=canonical,
                analysis_type="rolling_12m",
                start=start,
                end=end,
                trades=_slice(trades, start, end),
            )
            rolling_rows.append(row)
            all_rows.append(row)

        wf_rows: list[dict[str, Any]] = []
        reference_start = ANALYSIS_START
        while True:
            reference_end = reference_start + pd.DateOffset(months=12)
            forward_end = reference_end + pd.DateOffset(months=6)
            if forward_end > data_end:
                break

            reference = _metrics(_slice(trades, reference_start, reference_end))
            forward = _metrics(_slice(trades, reference_end, forward_end))
            row = {
                "source_symbol": source_symbol,
                "canonical_symbol": canonical,
                "analysis_type": "fixed_rule_12m_to_next_6m",
                "window_start_utc": reference_start.isoformat(),
                "window_end_utc": reference_end.isoformat(),
                **reference,
                "forward_start_utc": reference_end.isoformat(),
                "forward_end_utc": forward_end.isoformat(),
                "forward_trades": forward["trades"],
                "forward_net_expectancy_r": forward["net_expectancy_r"],
                "forward_profit_factor": forward["profit_factor"],
                "forward_max_drawdown_r": forward["max_drawdown_r"],
                "forward_long_trades": forward["long_trades"],
                "forward_short_trades": forward["short_trades"],
                "forward_low_sample": forward["low_sample"],
            }
            wf_rows.append(row)
            all_rows.append(row)
            reference_start = reference_start + pd.DateOffset(months=6)

        interpretable_wf = [
            row
            for row in wf_rows
            if not row["low_sample"] and not row["forward_low_sample"]
        ]
        positive_refs = [
            row
            for row in interpretable_wf
            if row["net_expectancy_r"] is not None and row["net_expectancy_r"] > 0
        ]
        positive_ref_forward_positive = [
            row
            for row in positive_refs
            if row["forward_net_expectancy_r"] is not None
            and row["forward_net_expectancy_r"] > 0
        ]

        market_summary[source_symbol] = {
            "data_end_utc": data_end.isoformat(),
            "half_year": _summary_for_rows(half_rows),
            "rolling_12m": _summary_for_rows(rolling_rows),
            "fixed_rule_walk_forward": {
                "pairs": len(wf_rows),
                "interpretable_pairs": len(interpretable_wf),
                "positive_reference_pairs": len(positive_refs),
                "positive_reference_followed_by_positive_forward": len(
                    positive_ref_forward_positive
                ),
                "positive_reference_persistence_fraction": (
                    len(positive_ref_forward_positive) / len(positive_refs)
                    if positive_refs
                    else None
                ),
            },
        }

    table = pd.DataFrame(all_rows)
    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)

    payload = {
        "strategy": "S02-structure-breakout-v0.1",
        "purpose": "fixed-rule temporal stability and persistence diagnostic; no parameter fitting or selection",
        "protocol_frozen": "2026-09-18",
        "analysis_start_utc": ANALYSIS_START.isoformat(),
        "minimum_trades_interpretable": MIN_TRADES_INTERPRETABLE,
        "baseline_config": asdict(config),
        "methodology": {
            "half_year": "complete non-overlapping 6-month calendar windows",
            "rolling_12m": "complete rolling 12-month windows stepped every 3 months",
            "fixed_rule_walk_forward": "prior 12 months compared with immediately following 6 months; baseline unchanged",
            "partial_final_windows": "excluded",
            "low_sample_windows": "retained in CSV and flagged; excluded from positive-fraction summaries",
        },
        "market_summary": market_summary,
        "full_table_csv": str(csv_path),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(json.dumps(payload, indent=2, default=str))
    print(f"temporal table written: {csv_path}")
    print(f"temporal summary written: {output_path}")


if __name__ == "__main__":
    main()
