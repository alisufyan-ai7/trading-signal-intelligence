from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

import numpy as np
import pandas as pd

from trading_signal_intelligence.models import Candle


FEATURE_SCHEMA_VERSION = "AI-v1.0"


class FeatureSnapshotError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class FeatureSnapshot:
    payload: dict[str, Any]
    sha256: str


def _iso_z(value: datetime | pd.Timestamp) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise FeatureSnapshotError("timestamp must be timezone-aware")
    ts = ts.tz_convert("UTC")
    return ts.isoformat().replace("+00:00", "Z")


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def snapshot_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def _frame(candles: list[Candle], timeframe: str) -> pd.DataFrame:
    rows = []
    tf = timeframe.upper()
    for candle in candles:
        if not candle.is_closed or candle.timeframe.upper() != tf:
            continue
        rows.append(
            {
                "timestamp_utc": pd.Timestamp(candle.timestamp_utc),
                "open": float(candle.open),
                "high": float(candle.high),
                "low": float(candle.low),
                "close": float(candle.close),
                "volume": float(candle.volume) if candle.volume is not None else np.nan,
                "spread": float(candle.spread) if candle.spread is not None else np.nan,
            }
        )
    frame = pd.DataFrame(rows)
    if frame.empty:
        return frame
    return (
        frame.sort_values("timestamp_utc")
        .drop_duplicates("timestamp_utc", keep="last")
        .reset_index(drop=True)
    )


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


def _wilder_average(values: pd.Series, period: int) -> pd.Series:
    array = values.astype(float).to_numpy()
    result = np.full(len(array), np.nan, dtype=float)
    if len(array) < period:
        return pd.Series(result, index=values.index, dtype=float)

    first = array[:period]
    if not np.isfinite(first).all():
        return pd.Series(result, index=values.index, dtype=float)

    result[period - 1] = float(first.mean())
    for idx in range(period, len(array)):
        value = array[idx]
        prev = result[idx - 1]
        if not math.isfinite(value) or not math.isfinite(prev):
            result[idx] = np.nan
        else:
            result[idx] = ((prev * (period - 1)) + value) / period
    return pd.Series(result, index=values.index, dtype=float)


def _atr(frame: pd.DataFrame, period: int = 14) -> pd.Series:
    return _wilder_average(_true_range(frame), period)


def _rsi(close: pd.Series, period: int = 14) -> pd.Series:
    delta = close.astype(float).diff()
    gain = delta.clip(lower=0)
    loss = (-delta.clip(upper=0))

    result = np.full(len(close), np.nan, dtype=float)
    if len(close) <= period:
        return pd.Series(result, index=close.index, dtype=float)

    initial_gain = gain.iloc[1 : period + 1].to_numpy(dtype=float)
    initial_loss = loss.iloc[1 : period + 1].to_numpy(dtype=float)
    if not np.isfinite(initial_gain).all() or not np.isfinite(initial_loss).all():
        return pd.Series(result, index=close.index, dtype=float)

    avg_gain = float(initial_gain.mean())
    avg_loss = float(initial_loss.mean())

    def rsi_value(g: float, l: float) -> float:
        if l == 0 and g == 0:
            return 50.0
        if l == 0:
            return 100.0
        rs = g / l
        return 100.0 - 100.0 / (1.0 + rs)

    result[period] = rsi_value(avg_gain, avg_loss)
    for idx in range(period + 1, len(close)):
        g = float(gain.iloc[idx])
        l = float(loss.iloc[idx])
        avg_gain = ((avg_gain * (period - 1)) + g) / period
        avg_loss = ((avg_loss * (period - 1)) + l) / period
        result[idx] = rsi_value(avg_gain, avg_loss)

    return pd.Series(result, index=close.index, dtype=float)


def _ema(series: pd.Series, span: int) -> pd.Series:
    return series.astype(float).ewm(span=span, adjust=False, min_periods=span).mean()


def _percentile_against_previous(
    series: pd.Series,
    *,
    index: int,
    lookback: int,
) -> float:
    current = float(series.iloc[index])
    prior = series.iloc[:index].dropna().tail(lookback)
    if len(prior) < lookback or not math.isfinite(current):
        raise FeatureSnapshotError(
            f"need {lookback} prior valid observations for percentile"
        )
    return float((prior <= current).mean())


def _finite(name: str, value: Any) -> float:
    number = float(value)
    if not math.isfinite(number):
        raise FeatureSnapshotError(f"{name} is not finite")
    return number


def _session_bucket(hour: int) -> str:
    if 0 <= hour < 7:
        return "ASIA"
    if 7 <= hour < 13:
        return "LONDON"
    if 13 <= hour < 21:
        return "NEW_YORK"
    return "LATE"


def _latest_complete(
    frame: pd.DataFrame,
    *,
    inference_started_utc: datetime,
    hours: int,
) -> pd.DataFrame:
    cutoff = pd.Timestamp(inference_started_utc)
    available = frame["timestamp_utc"] + pd.to_timedelta(hours, unit="h")
    return frame.loc[available <= cutoff].reset_index(drop=True)


def build_feature_snapshot(
    *,
    h1_candles: list[Candle],
    h4_candles: list[Candle],
    point_size: float,
    inference_started_utc: datetime,
    source_symbol: str,
    canonical_symbol: str,
) -> FeatureSnapshot:
    if inference_started_utc.tzinfo is None:
        raise FeatureSnapshotError("inference_started_utc must be timezone-aware")
    inference_started_utc = inference_started_utc.astimezone(timezone.utc)
    if point_size <= 0:
        raise FeatureSnapshotError("point_size must be positive")

    h1 = _latest_complete(
        _frame(h1_candles, "H1"),
        inference_started_utc=inference_started_utc,
        hours=1,
    )
    h4 = _latest_complete(
        _frame(h4_candles, "H4"),
        inference_started_utc=inference_started_utc,
        hours=4,
    )
    if h1.empty or h4.empty:
        raise FeatureSnapshotError("completed H1 and H4 history required")

    h1["tr"] = _true_range(h1)
    h1["atr14"] = _atr(h1, 14)
    h1["ema20"] = _ema(h1["close"], 20)
    h1["ema50"] = _ema(h1["close"], 50)
    h1["rsi14"] = _rsi(h1["close"], 14)

    log_return = np.log(h1["close"] / h1["close"].shift(1))
    h1["rv24"] = log_return.rolling(24, min_periods=24).std(ddof=0)

    h4["atr14"] = _atr(h4, 14)
    h4["ema20"] = _ema(h4["close"], 20)
    h4["ema50"] = _ema(h4["close"], 50)

    idx = len(h1) - 1
    h4_idx = len(h4) - 1
    if idx < 276:
        raise FeatureSnapshotError("insufficient H1 history for 252-observation regimes")
    if h4_idx < 53:
        raise FeatureSnapshotError("insufficient H4 history for EMA/slope features")

    current = h1.iloc[idx]
    h4_current = h4.iloc[h4_idx]

    source_bar_open = pd.Timestamp(current["timestamp_utc"])
    source_bar_close = source_bar_open + pd.Timedelta(hours=1)
    age_seconds = (
        pd.Timestamp(inference_started_utc) - source_bar_close
    ).total_seconds()
    if age_seconds < 0:
        raise FeatureSnapshotError("latest H1 bar is incomplete/future at inference time")

    atr14 = _finite("atr14", current["atr14"])
    if atr14 <= 0:
        raise FeatureSnapshotError("atr14 must be positive")

    h4_atr14 = _finite("h4_atr14", h4_current["atr14"])
    if h4_atr14 <= 0:
        raise FeatureSnapshotError("h4 atr14 must be positive")

    atr_percentile = _percentile_against_previous(
        h1["atr14"], index=idx, lookback=252
    )
    rv_percentile = _percentile_against_previous(
        h1["rv24"], index=idx, lookback=252
    )
    if rv_percentile < 0.33:
        volatility_regime = "LOW"
    elif rv_percentile <= 0.67:
        volatility_regime = "NORMAL"
    else:
        volatility_regime = "HIGH"

    close = _finite("close_h1", current["close"])
    ret_1 = close / _finite("close_t_minus_1", h1.iloc[idx - 1]["close"]) - 1.0
    ret_4 = close / _finite("close_t_minus_4", h1.iloc[idx - 4]["close"]) - 1.0
    ret_12 = close / _finite("close_t_minus_12", h1.iloc[idx - 12]["close"]) - 1.0
    ret_24 = close / _finite("close_t_minus_24", h1.iloc[idx - 24]["close"]) - 1.0

    return_signs = [ret_4, ret_12, ret_24]
    if all(value > 0 for value in return_signs):
        return_sign_agreement = "ALL_UP"
    elif all(value < 0 for value in return_signs):
        return_sign_agreement = "ALL_DOWN"
    else:
        return_sign_agreement = "MIXED"

    prior20 = h1.iloc[idx - 20 : idx]
    prior20_high = _finite("prior20_high", prior20["high"].max())
    prior20_low = _finite("prior20_low", prior20["low"].min())
    if prior20_high == prior20_low:
        raise FeatureSnapshotError("prior 20-bar range is zero")

    tr_prior20 = prior20["tr"].dropna()
    if len(tr_prior20) != 20:
        raise FeatureSnapshotError("prior 20 true-range values unavailable")
    tr_median = _finite("prior20_tr_median", tr_prior20.median())
    if tr_median <= 0:
        raise FeatureSnapshotError("prior true-range median must be positive")
    tr_expansion_ratio = _finite("tr", current["tr"]) / tr_median

    volume_window = prior20["volume"]
    current_volume = _finite("volume", current["volume"])
    if volume_window.isna().any():
        raise FeatureSnapshotError("prior tick-volume values unavailable")
    volume_mean = float(volume_window.mean())
    volume_std = float(volume_window.std(ddof=0))
    quality_flags: list[str] = []
    if volume_std == 0:
        volume_z = 0.0
        quality_flags.append("ZERO_VOLUME_VARIANCE")
    else:
        volume_z = (current_volume - volume_mean) / volume_std

    row_dates = h1["timestamp_utc"].dt.date
    close_date = source_bar_close.date()
    eligible_dates = sorted({d for d in row_dates if d < close_date})
    if not eligible_dates:
        raise FeatureSnapshotError("no previous UTC day with H1 bars")
    previous_day = eligible_dates[-1]
    previous_day_rows = h1.loc[row_dates == previous_day]
    previous_day_high = _finite("previous_day_high", previous_day_rows["high"].max())
    previous_day_low = _finite("previous_day_low", previous_day_rows["low"].min())

    ema20_h1 = _finite("ema20_h1", current["ema20"])
    ema50_h1 = _finite("ema50_h1", current["ema50"])
    ema20_h1_lag = _finite("ema20_h1_lag", h1.iloc[idx - 3]["ema20"])
    ema50_h1_lag = _finite("ema50_h1_lag", h1.iloc[idx - 3]["ema50"])

    h4_close = _finite("h4_close", h4_current["close"])
    ema20_h4 = _finite("ema20_h4", h4_current["ema20"])
    ema50_h4 = _finite("ema50_h4", h4_current["ema50"])
    ema20_h4_lag = _finite("ema20_h4_lag", h4.iloc[h4_idx - 3]["ema20"])
    ema50_h4_lag = _finite("ema50_h4_lag", h4.iloc[h4_idx - 3]["ema50"])

    ema20_slope_h1 = ema20_h1 / ema20_h1_lag - 1.0
    ema50_slope_h1 = ema50_h1 / ema50_h1_lag - 1.0
    ema20_slope_h4 = ema20_h4 / ema20_h4_lag - 1.0
    ema50_slope_h4 = ema50_h4 / ema50_h4_lag - 1.0

    if (
        close > ema20_h1 > ema50_h1
        and h4_close > ema20_h4 > ema50_h4
        and ema20_slope_h1 > 0
        and ema20_slope_h4 > 0
    ):
        trend_regime = "TREND_UP"
    elif (
        close < ema20_h1 < ema50_h1
        and h4_close < ema20_h4 < ema50_h4
        and ema20_slope_h1 < 0
        and ema20_slope_h4 < 0
    ):
        trend_regime = "TREND_DOWN"
    elif (
        abs(close - ema50_h1) / atr14 <= 0.50
        and abs(ema20_h1 - ema50_h1) / atr14 <= 0.25
    ):
        trend_regime = "RANGE"
    else:
        trend_regime = "MIXED"

    spread_points = _finite("spread_points", current["spread"])
    if spread_points < 0:
        raise FeatureSnapshotError("spread cannot be negative")
    spread_price = spread_points * point_size

    inference_ts = pd.Timestamp(inference_started_utc)
    payload = {
        "feature_schema_version": FEATURE_SCHEMA_VERSION,
        "source_symbol": source_symbol,
        "canonical_symbol": canonical_symbol,
        "source_bar_open_utc": _iso_z(source_bar_open),
        "source_bar_close_utc": _iso_z(source_bar_close),
        "inference_started_utc": _iso_z(inference_ts),
        "data_age_seconds": float(age_seconds),
        "close_h1": close,
        "ret_1": float(ret_1),
        "ret_4": float(ret_4),
        "ret_12": float(ret_12),
        "ret_24": float(ret_24),
        "atr_14": atr14,
        "atr_percentile_252": atr_percentile,
        "price_vs_ema20_h1_atr": (close - ema20_h1) / atr14,
        "price_vs_ema50_h1_atr": (close - ema50_h1) / atr14,
        "ema20_slope_h1": ema20_slope_h1,
        "ema50_slope_h1": ema50_slope_h1,
        "price_vs_ema20_h4_atr": (h4_close - ema20_h4) / h4_atr14,
        "price_vs_ema50_h4_atr": (h4_close - ema50_h4) / h4_atr14,
        "ema20_slope_h4": ema20_slope_h4,
        "ema50_slope_h4": ema50_slope_h4,
        "rsi_14": _finite("rsi14", current["rsi14"]),
        "range_position_20": (close - prior20_low) / (prior20_high - prior20_low),
        "distance_prior20_high_atr": (prior20_high - close) / atr14,
        "distance_prior20_low_atr": (close - prior20_low) / atr14,
        "distance_previous_day_high_atr": (previous_day_high - close) / atr14,
        "distance_previous_day_low_atr": (close - previous_day_low) / atr14,
        "previous_day_utc": previous_day.isoformat(),
        "tr_expansion_ratio": float(tr_expansion_ratio),
        "volume_z_20": float(volume_z),
        "return_sign_agreement": return_sign_agreement,
        "volatility_regime": volatility_regime,
        "trend_regime": trend_regime,
        "session_bucket": _session_bucket(inference_ts.hour),
        "utc_hour": int(inference_ts.hour),
        "utc_day_of_week": int(inference_ts.dayofweek),
        "spread_price": float(spread_price),
        "spread_atr_fraction": float(spread_price / atr14),
        "quality_flags": sorted(quality_flags),
    }

    for key, value in payload.items():
        if isinstance(value, float) and not math.isfinite(value):
            raise FeatureSnapshotError(f"{key} is not finite")

    return FeatureSnapshot(payload=payload, sha256=snapshot_sha256(payload))
