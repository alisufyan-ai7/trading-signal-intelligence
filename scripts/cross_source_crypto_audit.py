from __future__ import annotations

import argparse
import json
import math
import statistics

from trading_signal_intelligence.connectors.binance import BinanceSpotConnector
from trading_signal_intelligence.connectors.mt5 import MT5Connector


def percentile(values: list[float], p: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    index = (len(ordered) - 1) * p
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    weight = index - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def correlation(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    mean_x = statistics.fmean(xs)
    mean_y = statistics.fmean(ys)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    denom_x = math.sqrt(sum((x - mean_x) ** 2 for x in xs))
    denom_y = math.sqrt(sum((y - mean_y) ** 2 for y in ys))
    if denom_x == 0 or denom_y == 0:
        return None
    return numerator / (denom_x * denom_y)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare Exness MT5 crypto CFD candles with Binance Spot candles"
    )
    parser.add_argument("--terminal-path", default=None, help="Optional path to terminal64.exe")
    parser.add_argument("--mt5-symbol", default="BTCUSDT")
    parser.add_argument("--binance-symbol", default="BTCUSDT")
    parser.add_argument("--canonical", default="BTC/USDT")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=1000)
    args = parser.parse_args()

    if not 2 <= args.bars <= 1000:
        raise ValueError("--bars must be between 2 and 1000 for this audit")

    mt5 = MT5Connector(source_name="exness_mt5_demo")
    mt5.connect(args.terminal_path)
    try:
        mt5_bars = mt5.bars_from_pos(
            args.mt5_symbol,
            args.canonical,
            args.timeframe,
            start_pos=0,
            count=args.bars,
        )
    finally:
        mt5.disconnect()

    binance = BinanceSpotConnector()
    binance_bars = binance.klines(
        args.binance_symbol,
        args.canonical,
        args.timeframe,
        limit=args.bars,
    )

    mt5_map = {bar.timestamp_utc: bar for bar in mt5_bars if bar.is_closed}
    binance_map = {bar.timestamp_utc: bar for bar in binance_bars if bar.is_closed}
    common = sorted(set(mt5_map) & set(binance_map))
    if len(common) < 3:
        raise RuntimeError(f"Only {len(common)} closed timestamps overlap")

    basis_bps: list[float] = []
    for ts in common:
        mt5_close = float(mt5_map[ts].close)
        binance_close = float(binance_map[ts].close)
        basis_bps.append((mt5_close / binance_close - 1.0) * 10_000)

    mt5_returns: list[float] = []
    binance_returns: list[float] = []
    return_diff_bps: list[float] = []
    for left, right in zip(common, common[1:]):
        # Skip any non-consecutive H1 observations so a gap is not treated as a one-hour return.
        if args.timeframe.upper() == "H1" and (right - left).total_seconds() != 3600:
            continue
        mt5_return = float(mt5_map[right].close / mt5_map[left].close - 1)
        binance_return = float(binance_map[right].close / binance_map[left].close - 1)
        mt5_returns.append(mt5_return)
        binance_returns.append(binance_return)
        return_diff_bps.append((mt5_return - binance_return) * 10_000)

    summary = {
        "mt5_source_symbol": args.mt5_symbol,
        "binance_source_symbol": args.binance_symbol,
        "canonical_symbol": args.canonical,
        "timeframe": args.timeframe.upper(),
        "closed_overlap_bars": len(common),
        "overlap_start_utc": str(common[0]),
        "overlap_end_utc": str(common[-1]),
        "close_basis_bps": {
            "median": statistics.median(basis_bps),
            "median_abs": statistics.median(abs(value) for value in basis_bps),
            "p95_abs": percentile([abs(value) for value in basis_bps], 0.95),
            "max_abs": max(abs(value) for value in basis_bps),
        },
        "consecutive_return_samples": len(mt5_returns),
        "h1_return_correlation": correlation(mt5_returns, binance_returns),
        "return_difference_bps": {
            "median_abs": statistics.median(abs(value) for value in return_diff_bps)
            if return_diff_bps
            else None,
            "p95_abs": percentile([abs(value) for value in return_diff_bps], 0.95),
            "max_abs": max((abs(value) for value in return_diff_bps), default=None),
        },
        "interpretation_note": (
            "Exness MT5 and Binance Spot are different venues/instruments. High return correlation with "
            "a modest, stable basis can support cross-source sanity checking; it does not make the feeds interchangeable."
        ),
    }

    print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
