from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from trading_signal_intelligence.backtesting.s01 import run_s01
from trading_signal_intelligence.storage import CandleStore


def _json_value(value):
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if isinstance(value, np.generic):
        return value.item()
    if pd.isna(value):
        return None
    return value


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit sampled S01 trades against stored candles/features")
    parser.add_argument("--symbol", required=True, help="Source symbol, e.g. XAUUSD")
    parser.add_argument("--canonical", required=True, help="Canonical symbol, e.g. XAU/USD")
    parser.add_argument("--point-size", type=float, required=True, help="Source symbol point size")
    parser.add_argument("--source", default="exness_mt5_demo")
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--samples", type=int, default=10, help="Evenly spaced trades to inspect")
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

    frame, trades = run_s01(h1, h4, point_size=args.point_size)
    if trades.empty:
        raise RuntimeError("No S01 trades found")

    sample_count = max(1, min(args.samples, len(trades)))
    positions = sorted(set(np.linspace(0, len(trades) - 1, sample_count, dtype=int).tolist()))
    output = []

    for trade_pos in positions:
        trade = trades.iloc[trade_pos]
        entry_index = int(trade["entry_index"])
        signal_index = entry_index - 1
        signal = frame.iloc[signal_index]
        entry_bar = frame.iloc[entry_index]
        previous = frame.iloc[signal_index - 1] if signal_index > 0 else None
        pullback_start = max(0, signal_index - 3)
        pullback = frame.iloc[pullback_start:signal_index]

        h4_available = signal["h4_available_at"]
        signal_close = signal["signal_close_time"]
        direction = trade["direction"]

        assertions = {
            "h4_available_by_signal_close": bool(
                pd.notna(h4_available) and pd.Timestamp(h4_available) <= pd.Timestamp(signal_close)
            ),
            "entry_is_next_stored_h1_bar": bool(entry_index == signal_index + 1),
            "entry_after_signal_open_time": bool(
                pd.Timestamp(entry_bar["timestamp_utc"]) > pd.Timestamp(signal["timestamp_utc"])
            ),
            "direction_signal_flag_matches": bool(
                (direction == "long" and bool(signal["long_signal"]))
                or (direction == "short" and bool(signal["short_signal"]))
            ),
            "pullback_window_has_three_bars": bool(len(pullback) == 3),
        }

        pullback_rows = []
        for _, row in pullback.iterrows():
            pullback_rows.append(
                {
                    "timestamp_utc": _json_value(row["timestamp_utc"]),
                    "low": _json_value(row["low"]),
                    "high": _json_value(row["high"]),
                    "ema20": _json_value(row["ema20"]),
                    "ema50": _json_value(row["ema50"]),
                    "atr14": _json_value(row["atr14"]),
                    "long_touch": bool(row["long_touch"]),
                    "long_guard_ok": bool(row["long_guard_ok"]),
                    "short_touch": bool(row["short_touch"]),
                    "short_guard_ok": bool(row["short_guard_ok"]),
                }
            )

        output.append(
            {
                "trade_number": int(trade_pos + 1),
                "assertions": assertions,
                "signal": {
                    "timestamp_utc": _json_value(signal["timestamp_utc"]),
                    "signal_close_time": _json_value(signal_close),
                    "direction": direction,
                    "open": _json_value(signal["open"]),
                    "high": _json_value(signal["high"]),
                    "low": _json_value(signal["low"]),
                    "close": _json_value(signal["close"]),
                    "ema20": _json_value(signal["ema20"]),
                    "ema50": _json_value(signal["ema50"]),
                    "atr14": _json_value(signal["atr14"]),
                    "previous_high": _json_value(previous["high"]) if previous is not None else None,
                    "previous_low": _json_value(previous["low"]) if previous is not None else None,
                    "long_pullback": bool(signal["long_pullback"]),
                    "short_pullback": bool(signal["short_pullback"]),
                    "long_signal": bool(signal["long_signal"]),
                    "short_signal": bool(signal["short_signal"]),
                    "effective_spread_points": _json_value(signal["effective_spread_points"]),
                },
                "h4_regime": {
                    "available_at": _json_value(h4_available),
                    "close": _json_value(signal["h4_close"]),
                    "ema50": _json_value(signal["h4_ema50"]),
                    "ema200": _json_value(signal["h4_ema200"]),
                    "ema50_lag3": _json_value(signal["h4_ema50_lag"]),
                    "long": bool(signal["h4_long"]),
                    "short": bool(signal["h4_short"]),
                },
                "pullback_prior_three": pullback_rows,
                "entry_exit": {
                    "entry_timestamp_utc": _json_value(entry_bar["timestamp_utc"]),
                    "entry": _json_value(trade["entry"]),
                    "stop": _json_value(trade["stop"]),
                    "target": _json_value(trade["target"]),
                    "exit_timestamp_utc": _json_value(trade["exit_timestamp_utc"]),
                    "exit": _json_value(trade["exit"]),
                    "exit_reason": _json_value(trade["exit_reason"]),
                    "gross_r": _json_value(trade["gross_r"]),
                    "net_r": _json_value(trade["net_r"]),
                    "bars_held": int(trade["bars_held"]),
                },
            }
        )

    all_assertions_pass = all(
        all(item["assertions"].values())
        for item in output
    )

    print(
        json.dumps(
            {
                "source": args.source,
                "source_symbol": args.symbol,
                "canonical_symbol": args.canonical,
                "total_trades": int(len(trades)),
                "sampled_trades": len(output),
                "all_sample_assertions_pass": all_assertions_pass,
                "samples": output,
            },
            indent=2,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
