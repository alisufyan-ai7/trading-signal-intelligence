from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import pandas as pd

from trading_signal_intelligence.backtesting.s02 import S02Config, run_s02, split_name, summarize_trades
from trading_signal_intelligence.storage import CandleStore


SOURCE = "exness_mt5_demo"
UNIVERSE = [
    ("XAGUSD", "XAG/USD"),
    ("USTEC", "NASDAQ 100"),
    ("US500", "S&P 500"),
    ("US30", "DOW 30"),
    ("USOIL", "WTI"),
]
MIN_OOS_TRADES = 50


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run frozen S02 v0.1 on the predeclared transfer universe")
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--registry", default="config/instruments.json")
    parser.add_argument("--output", default="outputs/s02_transfer_v0_1.json")
    parser.add_argument("--csv", default="outputs/s02_transfer_v0_1.csv")
    args = parser.parse_args()

    store = CandleStore(args.database)
    config = S02Config()
    market_results: dict[str, Any] = {}
    ledgers: list[pd.DataFrame] = []

    for source_symbol, canonical in UNIVERSE:
        h1 = store.load_candles(
            source=SOURCE, source_symbol=source_symbol, timeframe="H1", closed_only=True
        )
        h4 = store.load_candles(
            source=SOURCE, source_symbol=source_symbol, timeframe="H4", closed_only=True
        )
        if not h1 or not h4:
            raise RuntimeError(
                f"Missing H1/H4 data for {source_symbol}. Backfill both timeframes before running transfer."
            )

        point_size = point_size_from_registry(canonical, args.registry)
        _, trades = run_s02(h1, h4, point_size=point_size, config=config)

        work = trades.copy()
        if not work.empty:
            work["split"] = work["signal_timestamp_utc"].apply(split_name)
            work["year"] = pd.to_datetime(work["signal_timestamp_utc"], utc=True).dt.year
            work.insert(0, "canonical_symbol", canonical)
            work.insert(0, "source_symbol", source_symbol)
            ledgers.append(work)

        by_split: dict[str, Any] = {}
        by_year: dict[str, Any] = {}
        if not work.empty:
            for split, group in work.groupby("split"):
                by_split[str(split)] = summarize_trades(group)
            for year, group in work.groupby("year"):
                by_year[str(int(year))] = summarize_trades(group)

        validation = by_split.get("validation", {})
        final_test = by_split.get("final_test", {})
        transfer_support = bool(
            validation.get("net_expectancy_r") is not None
            and final_test.get("net_expectancy_r") is not None
            and validation.get("net_expectancy_r") > 0
            and final_test.get("net_expectancy_r") > 0
            and int(validation.get("trades", 0)) >= MIN_OOS_TRADES
            and int(final_test.get("trades", 0)) >= MIN_OOS_TRADES
        )

        market_results[source_symbol] = {
            "canonical_symbol": canonical,
            "point_size": point_size,
            "overall": summarize_trades(work),
            "by_split": by_split,
            "by_year": by_year,
            "historical_transfer_support": transfer_support,
            "transfer_support_rule": (
                f"validation and final net expectancy > 0 with >= {MIN_OOS_TRADES} trades in each"
            ),
        }

    combined = pd.concat(ledgers, ignore_index=True) if ledgers else pd.DataFrame()
    csv_path = Path(args.csv)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    combined.drop(columns=["entry_index", "exit_index"], errors="ignore").to_csv(csv_path, index=False)

    payload = {
        "strategy": "S02-structure-breakout-v0.1",
        "purpose": "predeclared new-market transfer test; no parameter fitting or selection",
        "source": SOURCE,
        "universe": [{"source_symbol": s, "canonical_symbol": c} for s, c in UNIVERSE],
        "minimum_oos_trades_for_descriptive_support": MIN_OOS_TRADES,
        "baseline_config": asdict(config),
        "market_results": market_results,
        "supportive_markets": [
            symbol for symbol, result in market_results.items()
            if result["historical_transfer_support"]
        ],
        "combined_trade_ledger_csv": str(csv_path),
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")

    print(json.dumps(payload, indent=2, default=str))
    print(f"transfer ledger written: {csv_path}")
    print(f"transfer summary written: {output_path}")


if __name__ == "__main__":
    main()
