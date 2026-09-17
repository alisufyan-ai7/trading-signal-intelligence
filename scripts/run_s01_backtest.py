from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from trading_signal_intelligence.backtesting.s01 import S01Config, run_s01, split_name, summarize_trades
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
    parser = argparse.ArgumentParser(description="Run frozen S01 trend-pullback v0.1")
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
    config = S01Config()
    _, trades = run_s01(h1, h4, point_size=point_size, config=config)

    if not trades.empty:
        trades["split"] = trades["signal_timestamp_utc"].apply(split_name)
        trades["year"] = pd.to_datetime(trades["signal_timestamp_utc"], utc=True).dt.year

    result = {
        "strategy": "S01-trend-pullback-v0.1",
        "source": args.source,
        "source_symbol": args.symbol,
        "canonical_symbol": args.canonical,
        "point_size": point_size,
        "config": {
            "h4_ema_fast": config.h4_ema_fast,
            "h4_ema_slow": config.h4_ema_slow,
            "h4_slope_lookback": config.h4_slope_lookback,
            "h1_ema_pullback": config.h1_ema_pullback,
            "h1_ema_guard": config.h1_ema_guard,
            "atr_period": config.atr_period,
            "pullback_window": config.pullback_window,
            "pullback_tolerance_atr": config.pullback_tolerance_atr,
            "guard_tolerance_atr": config.guard_tolerance_atr,
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
