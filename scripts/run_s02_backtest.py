from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from trading_signal_intelligence.backtesting.s02 import S02Config, run_s02, split_name, summarize_trades
from trading_signal_intelligence.storage import CandleStore


def point_size_from_registry(
    *,
    canonical: str,
    source: str,
    config_path: str = "config/instruments.json",
) -> float:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    for instrument in payload["instruments"]:
        if instrument["canonical"] != canonical:
            continue
        source_config = instrument.get("sources", {}).get(source)
        if not source_config:
            break
        digits = source_config.get("digits")
        if digits is None:
            raise ValueError(
                f"No digits/point metadata for {canonical} on {source}; "
                "this runner currently supports the frozen MT5 cost model only."
            )
        return 10.0 ** (-int(digits))
    raise ValueError(f"No registry entry for {canonical!r} on source {source!r}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen S02 structure-breakout v0.1")
    parser.add_argument("--source", default="exness_mt5_demo")
    parser.add_argument("--symbol", required=True, help="Source symbol, e.g. EURUSD")
    parser.add_argument("--canonical", required=True, help="Canonical symbol, e.g. EUR/USD")
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--output", default=None, help="Optional CSV path for trade ledger")
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
        raise RuntimeError(
            "Both H1 and H4 datasets are required. Run the backfill command for each timeframe first."
        )

    point_size = point_size_from_registry(canonical=args.canonical, source=args.source)
    config = S02Config()
    _, trades = run_s02(h1, h4, point_size=point_size, config=config)

    if not trades.empty:
        trades["split"] = trades["signal_timestamp_utc"].apply(split_name)
        trades["year"] = pd.to_datetime(trades["signal_timestamp_utc"], utc=True).dt.year

    result = {
        "strategy": "S02-structure-breakout-v0.1",
        "source": args.source,
        "source_symbol": args.symbol,
        "canonical_symbol": args.canonical,
        "point_size": point_size,
        "config": {
            "structure_window": config.structure_window,
            "atr_period": config.atr_period,
            "breakout_margin_atr": config.breakout_margin_atr,
            "tr_expansion_window": config.tr_expansion_window,
            "tr_expansion_multiple": config.tr_expansion_multiple,
            "volume_expansion_window": config.volume_expansion_window,
            "volume_expansion_multiple": config.volume_expansion_multiple,
            "h4_ema": config.h4_ema,
            "h4_slope_lookback": config.h4_slope_lookback,
            "stop_atr": config.stop_atr,
            "target_r": config.target_r,
            "max_hold_bars": config.max_hold_bars,
            "cost_multiplier": config.cost_multiplier,
        },
        "overall": summarize_trades(trades),
        "by_split": {},
        "by_year": {},
    }

    if not trades.empty:
        for split, group in trades.groupby("split"):
            result["by_split"][str(split)] = summarize_trades(group)
        for year, group in trades.groupby("year"):
            result["by_year"][str(int(year))] = summarize_trades(group)

    print(json.dumps(result, indent=2, default=str))

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        trades.drop(columns=["entry_index", "exit_index"], errors="ignore").to_csv(
            output_path, index=False
        )
        print(f"trade ledger written: {output_path}")


if __name__ == "__main__":
    main()
