from __future__ import annotations

import argparse
import json

import numpy as np
import pandas as pd

from trading_signal_intelligence.backtesting.s02 import S02Config, run_s02
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
    parser = argparse.ArgumentParser(description="Audit sampled S02 trades against stored candles/features")
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--canonical", required=True)
    parser.add_argument("--point-size", type=float, required=True)
    parser.add_argument("--source", default="exness_mt5_demo")
    parser.add_argument("--database", default="data/research.sqlite")
    parser.add_argument("--samples", type=int, default=10)
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

    config = S02Config()
    frame, trades = run_s02(h1, h4, point_size=args.point_size, config=config)
    if trades.empty:
        raise RuntimeError("No S02 trades found")

    sample_count = max(1, min(args.samples, len(trades)))
    positions = sorted(set(np.linspace(0, len(trades) - 1, sample_count, dtype=int).tolist()))
    output = []

    for trade_pos in positions:
        trade = trades.iloc[trade_pos]
        entry_index = int(trade["entry_index"])
        signal_index = entry_index - 1
        signal = frame.iloc[signal_index]
        entry_bar = frame.iloc[entry_index]
        structure_start = max(0, signal_index - config.structure_window)
        prior_structure = frame.iloc[structure_start:signal_index]

        expected_upper = float(prior_structure["high"].max()) if len(prior_structure) == config.structure_window else np.nan
        expected_lower = float(prior_structure["low"].min()) if len(prior_structure) == config.structure_window else np.nan
        direction = trade["direction"]
        atr = float(signal["atr14"])
        risk = float(trade["risk_price"])
        entry = float(trade["entry"])
        stop = float(trade["stop"])
        target = float(trade["target"])

        if direction == "long":
            breakout_ok = bool(
                float(signal["close"])
                > float(signal["upper_structure"]) + config.breakout_margin_atr * atr
            )
            gap_ok = bool(float(signal["open"]) <= float(signal["upper_structure"]))
            candle_direction_ok = bool(float(signal["close"]) > float(signal["open"]))
            stop_math_ok = np.isclose(stop, entry - config.stop_atr * atr)
            target_math_ok = np.isclose(target, entry + config.target_r * risk)
        else:
            breakout_ok = bool(
                float(signal["close"])
                < float(signal["lower_structure"]) - config.breakout_margin_atr * atr
            )
            gap_ok = bool(float(signal["open"]) >= float(signal["lower_structure"]))
            candle_direction_ok = bool(float(signal["close"]) < float(signal["open"]))
            stop_math_ok = np.isclose(stop, entry + config.stop_atr * atr)
            target_math_ok = np.isclose(target, entry - config.target_r * risk)

        assertions = {
            "h4_available_by_signal_close": bool(
                pd.notna(signal["h4_available_at"])
                and pd.Timestamp(signal["h4_available_at"]) <= pd.Timestamp(signal["signal_close_time"])
            ),
            "entry_is_next_stored_h1_bar": bool(entry_index == signal_index + 1),
            "entry_after_signal_open_time": bool(
                pd.Timestamp(entry_bar["timestamp_utc"]) > pd.Timestamp(signal["timestamp_utc"])
            ),
            "direction_signal_flag_matches": bool(
                (direction == "long" and bool(signal["long_signal"]))
                or (direction == "short" and bool(signal["short_signal"]))
            ),
            "structure_window_has_20_bars": bool(len(prior_structure) == config.structure_window),
            "upper_structure_matches_prior_20_high": bool(
                np.isfinite(expected_upper)
                and np.isclose(float(signal["upper_structure"]), expected_upper)
            ),
            "lower_structure_matches_prior_20_low": bool(
                np.isfinite(expected_lower)
                and np.isclose(float(signal["lower_structure"]), expected_lower)
            ),
            "breakout_margin_passes": breakout_ok,
            "gap_open_exclusion_passes": gap_ok,
            "signal_candle_direction_passes": candle_direction_ok,
            "tr_expansion_passes": bool(
                float(signal["tr_expansion_ratio"]) >= config.tr_expansion_multiple
            ),
            "volume_expansion_passes": bool(
                float(signal["volume_expansion_ratio"]) >= config.volume_expansion_multiple
            ),
            "stop_risk_math_passes": bool(stop_math_ok),
            "target_r_math_passes": bool(target_math_ok),
        }

        output.append(
            {
                "trade_number": int(trade_pos + 1),
                "assertions": assertions,
                "signal": {
                    "timestamp_utc": _json_value(signal["timestamp_utc"]),
                    "signal_close_time": _json_value(signal["signal_close_time"]),
                    "direction": direction,
                    "open": _json_value(signal["open"]),
                    "high": _json_value(signal["high"]),
                    "low": _json_value(signal["low"]),
                    "close": _json_value(signal["close"]),
                    "atr14": _json_value(signal["atr14"]),
                    "upper_structure": _json_value(signal["upper_structure"]),
                    "lower_structure": _json_value(signal["lower_structure"]),
                    "tr_expansion_ratio": _json_value(signal["tr_expansion_ratio"]),
                    "volume_expansion_ratio": _json_value(signal["volume_expansion_ratio"]),
                    "known_spread_points": _json_value(signal["known_spread_points"]),
                    "long_signal": bool(signal["long_signal"]),
                    "short_signal": bool(signal["short_signal"]),
                },
                "h4_regime": {
                    "available_at": _json_value(signal["h4_available_at"]),
                    "close": _json_value(signal["h4_close"]),
                    "ema50": _json_value(signal["h4_ema50"]),
                    "ema50_lag3": _json_value(signal["h4_ema50_lag"]),
                    "long": bool(signal["h4_long"]),
                    "short": bool(signal["h4_short"]),
                },
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

    all_assertions_pass = all(all(item["assertions"].values()) for item in output)

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
