from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd

from trading_signal_intelligence.models import Candle


@dataclass(frozen=True, slots=True)
class S02Config:
    structure_window: int = 20
    atr_period: int = 14
    breakout_margin_atr: float = 0.10
    tr_expansion_window: int = 20
    tr_expansion_multiple: float = 1.25
    volume_expansion_window: int = 20
    volume_expansion_multiple: float = 1.10
    h4_ema: int = 50
    h4_slope_lookback: int = 3
    stop_atr: float = 1.75
    target_r: float = 2.50
    max_hold_bars: int = 72
    cost_multiplier: float = 1.25
    spread_fallback_window: int = 20


def _candles_to_frame(candles: list[Candle]) -> pd.DataFrame:
    rows = [
        {
            "timestamp_utc": candle.timestamp_utc,
            "open": float(candle.open),
            "high": float(candle.high),
            "low": float(candle.low),
            "close": float(candle.close),
            "volume": float(candle.volume) if candle.volume is not None else np.nan,
            "spread": float(candle.spread) if candle.spread is not None else np.nan,
        }
        for candle in candles
        if candle.is_closed
    ]
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return frame.sort_values("timestamp_utc").drop_duplicates("timestamp_utc").reset_index(drop=True)


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.ewm(span=span, adjust=False, min_periods=span).mean()


def _true_range(frame: pd.DataFrame) -> pd.Series:
    previous_close = frame["close"].shift(1)
    return pd.concat(
        [
            frame["high"] - frame["low"],
            (frame["high"] - previous_close).abs(),
            (frame["low"] - previous_close).abs(),
        ],
        axis=1,
    ).max(axis=1)


def _atr(frame: pd.DataFrame, period: int) -> pd.Series:
    return _true_range(frame).ewm(alpha=1 / period, adjust=False, min_periods=period).mean()


def _prepare_features(h1: pd.DataFrame, h4: pd.DataFrame, config: S02Config) -> pd.DataFrame:
    h1 = h1.copy()
    h4 = h4.copy()

    h1["true_range"] = _true_range(h1)
    h1["atr14"] = _atr(h1, config.atr_period)

    h1["upper_structure"] = (
        h1["high"].shift(1).rolling(config.structure_window, min_periods=config.structure_window).max()
    )
    h1["lower_structure"] = (
        h1["low"].shift(1).rolling(config.structure_window, min_periods=config.structure_window).min()
    )

    h1["prior_tr_median"] = (
        h1["true_range"]
        .shift(1)
        .rolling(config.tr_expansion_window, min_periods=config.tr_expansion_window)
        .median()
    )
    h1["prior_volume_median"] = (
        h1["volume"]
        .shift(1)
        .rolling(config.volume_expansion_window, min_periods=config.volume_expansion_window)
        .median()
    )

    h1["tr_expansion_ratio"] = h1["true_range"] / h1["prior_tr_median"]
    h1["volume_expansion_ratio"] = h1["volume"] / h1["prior_volume_median"]

    h4["h4_ema50"] = _ema(h4["close"], config.h4_ema)
    h4["h4_ema50_lag"] = h4["h4_ema50"].shift(config.h4_slope_lookback)
    h4["h4_available_at"] = h4["timestamp_utc"] + pd.to_timedelta(4, unit="h")
    h4_features = h4[
        ["h4_available_at", "close", "h4_ema50", "h4_ema50_lag"]
    ].rename(columns={"close": "h4_close"})

    h1["signal_close_time"] = h1["timestamp_utc"] + pd.to_timedelta(1, unit="h")
    h1 = pd.merge_asof(
        h1.sort_values("signal_close_time"),
        h4_features.sort_values("h4_available_at"),
        left_on="signal_close_time",
        right_on="h4_available_at",
        direction="backward",
    ).reset_index(drop=True)

    h1["h4_long"] = (
        (h1["h4_close"] > h1["h4_ema50"])
        & (h1["h4_ema50"] > h1["h4_ema50_lag"])
    )
    h1["h4_short"] = (
        (h1["h4_close"] < h1["h4_ema50"])
        & (h1["h4_ema50"] < h1["h4_ema50_lag"])
    )

    h1["long_breakout"] = (
        h1["close"] > h1["upper_structure"] + config.breakout_margin_atr * h1["atr14"]
    )
    h1["short_breakout"] = (
        h1["close"] < h1["lower_structure"] - config.breakout_margin_atr * h1["atr14"]
    )

    h1["long_gap_exclusion_ok"] = h1["open"] <= h1["upper_structure"]
    h1["short_gap_exclusion_ok"] = h1["open"] >= h1["lower_structure"]
    h1["tr_expansion_ok"] = h1["tr_expansion_ratio"] >= config.tr_expansion_multiple
    h1["volume_expansion_ok"] = (
        h1["volume_expansion_ratio"] >= config.volume_expansion_multiple
    )

    h1["long_signal"] = (
        h1["h4_long"]
        & h1["long_breakout"]
        & h1["long_gap_exclusion_ok"]
        & (h1["close"] > h1["open"])
        & h1["tr_expansion_ok"]
        & h1["volume_expansion_ok"]
    )
    h1["short_signal"] = (
        h1["h4_short"]
        & h1["short_breakout"]
        & h1["short_gap_exclusion_ok"]
        & (h1["close"] < h1["open"])
        & h1["tr_expansion_ok"]
        & h1["volume_expansion_ok"]
    )

    valid_spread = h1["spread"].where(h1["spread"] > 0)
    h1["spread_fallback"] = (
        valid_spread.shift(1)
        .rolling(config.spread_fallback_window, min_periods=1)
        .median()
    )
    h1["known_spread_points"] = valid_spread.fillna(h1["spread_fallback"])

    h1["long_breakout_distance_atr"] = (
        (h1["close"] - h1["upper_structure"]) / h1["atr14"]
    )
    h1["short_breakout_distance_atr"] = (
        (h1["lower_structure"] - h1["close"]) / h1["atr14"]
    )
    return h1


def _simulate_trade(
    frame: pd.DataFrame,
    *,
    signal_index: int,
    direction: int,
    point_size: float,
    config: S02Config,
) -> dict[str, Any] | None:
    entry_index = signal_index + 1
    if entry_index >= len(frame):
        return None

    signal = frame.iloc[signal_index]
    entry_bar = frame.iloc[entry_index]
    atr = float(signal["atr14"])
    if not np.isfinite(atr) or atr <= 0:
        return None

    spread_points = float(signal["known_spread_points"])
    if not np.isfinite(spread_points) or spread_points <= 0:
        return None

    entry = float(entry_bar["open"])
    risk = config.stop_atr * atr
    if direction > 0:
        stop = entry - risk
        target = entry + config.target_r * risk
        structure_level = float(signal["upper_structure"])
        breakout_distance_atr = float(signal["long_breakout_distance_atr"])
    else:
        stop = entry + risk
        target = entry - config.target_r * risk
        structure_level = float(signal["lower_structure"])
        breakout_distance_atr = float(signal["short_breakout_distance_atr"])

    cost_price = config.cost_multiplier * spread_points * point_size
    final_index = min(entry_index + config.max_hold_bars - 1, len(frame) - 1)
    enough_bars_for_timeout = final_index == entry_index + config.max_hold_bars - 1

    exit_price: float | None = None
    exit_index: int | None = None
    exit_reason: str | None = None

    for bar_index in range(entry_index, final_index + 1):
        bar = frame.iloc[bar_index]
        bar_open = float(bar["open"])
        bar_high = float(bar["high"])
        bar_low = float(bar["low"])

        if direction > 0:
            if bar_open <= stop:
                exit_price, exit_index, exit_reason = bar_open, bar_index, "gap_stop"
                break
            if bar_open >= target:
                exit_price, exit_index, exit_reason = target, bar_index, "gap_target"
                break
            stop_hit = bar_low <= stop
            target_hit = bar_high >= target
        else:
            if bar_open >= stop:
                exit_price, exit_index, exit_reason = bar_open, bar_index, "gap_stop"
                break
            if bar_open <= target:
                exit_price, exit_index, exit_reason = target, bar_index, "gap_target"
                break
            stop_hit = bar_high >= stop
            target_hit = bar_low <= target

        if stop_hit and target_hit:
            exit_price, exit_index, exit_reason = stop, bar_index, "same_bar_stop_first"
            break
        if stop_hit:
            exit_price, exit_index, exit_reason = stop, bar_index, "stop"
            break
        if target_hit:
            exit_price, exit_index, exit_reason = target, bar_index, "target"
            break

    if exit_price is None:
        if not enough_bars_for_timeout:
            return None
        exit_index = final_index
        exit_price = float(frame.iloc[exit_index]["close"])
        exit_reason = "time_stop"

    gross_pnl = direction * (exit_price - entry)
    net_pnl = gross_pnl - cost_price
    gross_r = gross_pnl / risk
    net_r = net_pnl / risk

    return {
        "signal_timestamp_utc": frame.iloc[signal_index]["timestamp_utc"],
        "entry_timestamp_utc": frame.iloc[entry_index]["timestamp_utc"],
        "exit_timestamp_utc": frame.iloc[exit_index]["timestamp_utc"] if exit_index is not None else None,
        "direction": "long" if direction > 0 else "short",
        "entry": entry,
        "stop": stop,
        "target": target,
        "exit": exit_price,
        "exit_reason": exit_reason,
        "atr14": atr,
        "risk_price": risk,
        "structure_level": structure_level,
        "breakout_distance_atr": breakout_distance_atr,
        "tr_expansion_ratio": float(signal["tr_expansion_ratio"]),
        "volume_expansion_ratio": float(signal["volume_expansion_ratio"]),
        "spread_points": spread_points,
        "cost_price": cost_price,
        "gross_r": gross_r,
        "net_r": net_r,
        "bars_held": (exit_index - entry_index + 1) if exit_index is not None else None,
        "entry_index": entry_index,
        "exit_index": exit_index,
    }


def run_s02(
    h1_candles: list[Candle],
    h4_candles: list[Candle],
    *,
    point_size: float,
    config: S02Config | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    config = config or S02Config()
    h1 = _candles_to_frame(h1_candles)
    h4 = _candles_to_frame(h4_candles)
    if h1.empty or h4.empty:
        return pd.DataFrame(), pd.DataFrame()

    frame = _prepare_features(h1, h4, config)
    trades: list[dict[str, Any]] = []
    next_signal_index = 0

    for index, row in frame.iterrows():
        if index < next_signal_index:
            continue

        direction = 0
        if bool(row["long_signal"]):
            direction = 1
        elif bool(row["short_signal"]):
            direction = -1
        if direction == 0:
            continue

        trade = _simulate_trade(
            frame,
            signal_index=index,
            direction=direction,
            point_size=point_size,
            config=config,
        )
        if trade is None:
            continue
        trades.append(trade)
        next_signal_index = int(trade["exit_index"])

    return frame, pd.DataFrame(trades)


def summarize_trades(trades: pd.DataFrame) -> dict[str, Any]:
    if trades.empty:
        return {
            "trades": 0,
            "win_rate": None,
            "gross_expectancy_r": None,
            "net_expectancy_r": None,
            "median_net_r": None,
            "profit_factor": None,
            "max_drawdown_r": None,
        }

    net = trades["net_r"].astype(float)
    gross = trades["gross_r"].astype(float)
    winners = net[net > 0]
    losers = net[net < 0]
    gross_profit = winners.sum()
    gross_loss = -losers.sum()
    profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else None

    cumulative = net.cumsum()
    running_peak = cumulative.cummax().clip(lower=0)
    drawdown = cumulative - running_peak

    return {
        "trades": int(len(trades)),
        "win_rate": float((net > 0).mean()),
        "gross_expectancy_r": float(gross.mean()),
        "net_expectancy_r": float(net.mean()),
        "median_net_r": float(net.median()),
        "profit_factor": float(profit_factor) if profit_factor is not None else None,
        "max_drawdown_r": float(drawdown.min()),
        "long_trades": int((trades["direction"] == "long").sum()),
        "short_trades": int((trades["direction"] == "short").sum()),
        "targets": int(trades["exit_reason"].isin(["target", "gap_target"]).sum()),
        "stops": int(
            trades["exit_reason"].isin(["stop", "gap_stop", "same_bar_stop_first"]).sum()
        ),
        "time_stops": int((trades["exit_reason"] == "time_stop").sum()),
    }


def split_name(timestamp: pd.Timestamp) -> str:
    ts = pd.Timestamp(timestamp)
    if ts < pd.Timestamp("2023-01-01", tz="UTC"):
        return "development"
    if ts < pd.Timestamp("2025-01-01", tz="UTC"):
        return "validation"
    return "final_test"
