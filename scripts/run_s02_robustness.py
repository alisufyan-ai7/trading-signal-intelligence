from __future__ import annotations

import argparse
import json
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import pandas as pd

from trading_signal_intelligence.backtesting.s02 import (
    S02Config,
    run_s02,
    split_name,
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

# Frozen after the first S02 v0.1 baseline was viewed and before any neighborhood
# result was generated. This is a sensitivity test, not a parameter optimizer.
PERTURBATIONS: list[tuple[str, dict[str, Any]]] = [
    ("baseline", {}),
    ("structure_window_low", {"structure_window": 15}),
    ("structure_window_high", {"structure_window": 25}),
    ("breakout_margin_low", {"breakout_margin_atr": 0.05}),
    ("breakout_margin_high", {"breakout_margin_atr": 0.15}),
    ("tr_expansion_low", {"tr_expansion_multiple": 1.10}),
    ("tr_expansion_high", {"tr_expansion_multiple": 1.40}),
    ("volume_expansion_low", {"volume_expansion_multiple": 1.00}),
    ("volume_expansion_high", {"volume_expansion_multiple": 1.20}),
    ("h4_slope_low", {"h4_slope_lookback": 2}),
    ("h4_slope_high", {"h4_slope_lookback": 4}),
    ("stop_atr_low", {"stop_atr": 1.50}),
    ("stop_atr_high", {"stop_atr": 2.00}),
    ("target_r_low", {"target_r": 2.00}),
    ("target_r_high", {"target_r": 3.00}),
    ("max_hold_low", {"max_hold_bars": 48}),
    ("max_hold_high", {"max_hold_bars": 96}),
]


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


def _split_summaries(trades: pd.DataFrame) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    if trades.empty:
        for name in ("development", "validation", "final_test"):
            result[name] = summarize_trades(trades)
        return result

    work = trades.copy()
    work["split"] = work["signal_timestamp_utc"].apply(split_name)
    for name in ("development", "validation", "final_test"):
        result[name] = summarize_trades(work[work["split"] == name])
    return result


def _cost_stress(trades: pd.DataFrame, baseline_multiplier: float) -> dict[str, Any]:
    if trades.empty:
        return {}
    work = trades.copy()
    work["split"] = work["signal_timestamp_utc"].apply(split_name)
    raw_cost_r = (work["cost_price"].astype(float) / baseline_multiplier) / work[
        "risk_price"
    ].astype(float)
    result: dict[str, Any] = {}
    for multiplier in (1.0, 1.25, 1.5, 2.0, 3.0):
        stressed = work.copy()
        stressed["net_r"] = stressed["gross_r"].astype(float) - raw_cost_r * multiplier
        result[str(multiplier)] = {
            split: summarize_trades(stressed[stressed["split"] == split])
            for split in ("validation", "final_test")
        }
    return result


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the frozen S02 v0.1 one-at-a-time robustness neighborhood"
    )
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--registry", default="config/instruments.json")
    parser.add_argument("--output", default="outputs/s02_robustness_v0_1.json")
    parser.add_argument("--csv", default="outputs/s02_robustness_v0_1.csv")
    args = parser.parse_args()

    store = CandleStore(args.database)
    baseline = S02Config()
    rows: list[dict[str, Any]] = []
    cost_stress: dict[str, Any] = {}

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

        for variant, changes in PERTURBATIONS:
            config = replace(baseline, **changes)
            _, trades = run_s02(h1, h4, point_size=point_size, config=config)
            splits = _split_summaries(trades)
            row: dict[str, Any] = {
                "source_symbol": source_symbol,
                "canonical_symbol": canonical,
                "variant": variant,
                "changed_parameter": next(iter(changes.keys()), "baseline"),
                "changed_value": next(iter(changes.values()), None),
                "overall_trades": len(trades),
            }
            for split in ("development", "validation", "final_test"):
                row[f"{split}_trades"] = splits[split].get("trades")
                row[f"{split}_expectancy_r"] = splits[split].get("net_expectancy_r")
                row[f"{split}_profit_factor"] = splits[split].get("profit_factor")
                row[f"{split}_max_drawdown_r"] = splits[split].get("max_drawdown_r")
            rows.append(row)

            if variant == "baseline":
                cost_stress[source_symbol] = _cost_stress(trades, baseline.cost_multiplier)

    table = pd.DataFrame(rows)
    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(csv_path, index=False)

    market_summary: dict[str, Any] = {}
    for source_symbol, group in table.groupby("source_symbol"):
        validation = group["validation_expectancy_r"].astype(float)
        final = group["final_test_expectancy_r"].astype(float)
        market_summary[source_symbol] = {
            "variants": int(len(group)),
            "validation_positive_fraction": float((validation > 0).mean()),
            "final_test_positive_fraction": float((final > 0).mean()),
            "positive_in_both_oos_splits": int(((validation > 0) & (final > 0)).sum()),
            "validation_expectancy_min": float(validation.min()),
            "validation_expectancy_median": float(validation.median()),
            "validation_expectancy_max": float(validation.max()),
            "final_test_expectancy_min": float(final.min()),
            "final_test_expectancy_median": float(final.median()),
            "final_test_expectancy_max": float(final.max()),
        }

    payload = {
        "strategy": "S02-structure-breakout-v0.1",
        "purpose": "one-at-a-time sensitivity diagnostic; not parameter selection",
        "baseline_config": asdict(baseline),
        "variants": [name for name, _ in PERTURBATIONS],
        "market_summary": market_summary,
        "baseline_cost_stress": cost_stress,
        "full_table_csv": str(csv_path),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
    print(json.dumps(payload, indent=2, default=str))
    print(f"full robustness table written: {csv_path}")
    print(f"robustness summary written: {output_path}")


if __name__ == "__main__":
    main()
