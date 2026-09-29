from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SYMBOLS = ("XAUUSD", "USTEC", "US30")


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def next_hour_boundary(now_utc: datetime) -> datetime:
    now = _utc(now_utc)
    floored = now.replace(minute=0, second=0, microsecond=0)
    return floored + timedelta(hours=1)


def _iso(value: datetime) -> str:
    return _utc(value).isoformat().replace("+00:00", "Z")


def summarize_observations(
    observations: list[dict[str, Any]],
    *,
    boundary_utc: datetime,
) -> dict[str, Any]:
    boundary = _utc(boundary_utc)
    by_symbol: dict[str, list[dict[str, Any]]] = {symbol: [] for symbol in SYMBOLS}
    for row in observations:
        symbol = str(row.get("symbol"))
        if symbol in by_symbol:
            by_symbol[symbol].append(row)

    markets: dict[str, Any] = {}
    for symbol in SYMBOLS:
        rows = sorted(
            by_symbol[symbol],
            key=lambda row: str(row.get("observed_at_utc")),
        )
        present_rows = [
            row for row in rows
            if row.get("boundary_row_present") is True
        ]
        first_seen = present_rows[0] if present_rows else None
        first_seen_offset = (
            float(first_seen["seconds_from_boundary"])
            if first_seen is not None
            else None
        )

        closest_to_120 = None
        if rows:
            closest_to_120 = min(
                rows,
                key=lambda row: abs(float(row["seconds_from_boundary"]) - 120.0),
            )

        markets[symbol] = {
            "observations": len(rows),
            "read_successes": sum(1 for row in rows if row.get("read_ok") is True),
            "first_boundary_row_seen_at_utc": (
                first_seen.get("observed_at_utc") if first_seen else None
            ),
            "first_boundary_row_seen_offset_seconds": first_seen_offset,
            "first_seen_after_nominal_scheduler_120s": (
                first_seen_offset > 120.0
                if first_seen_offset is not None
                else None
            ),
            "closest_observation_to_scheduler_120s": (
                {
                    "observed_at_utc": closest_to_120.get("observed_at_utc"),
                    "seconds_from_boundary": closest_to_120.get(
                        "seconds_from_boundary"
                    ),
                    "boundary_row_present": closest_to_120.get(
                        "boundary_row_present"
                    ),
                    "latest_h1_open_utc": closest_to_120.get(
                        "latest_h1_open_utc"
                    ),
                    "latest_tick_utc": closest_to_120.get("latest_tick_utc"),
                }
                if closest_to_120 is not None
                else None
            ),
        }

    first_seen = {
        symbol: markets[symbol]["first_boundary_row_seen_offset_seconds"]
        for symbol in SYMBOLS
    }
    comparison = {
        "xauusd_first_seen_offset_seconds": first_seen["XAUUSD"],
        "ustec_first_seen_offset_seconds": first_seen["USTEC"],
        "us30_first_seen_offset_seconds": first_seen["US30"],
        "ustec_minus_xau_seconds": (
            first_seen["USTEC"] - first_seen["XAUUSD"]
            if first_seen["USTEC"] is not None and first_seen["XAUUSD"] is not None
            else None
        ),
        "us30_minus_xau_seconds": (
            first_seen["US30"] - first_seen["XAUUSD"]
            if first_seen["US30"] is not None and first_seen["XAUUSD"] is not None
            else None
        ),
    }

    return {
        "probe_version": "AI-v1-Index-H1-Boundary-Probe-v0.1",
        "mode": "READ_ONLY",
        "boundary_utc": _iso(boundary),
        "nominal_scheduler_offset_seconds": 120,
        "markets": markets,
        "comparison": comparison,
        "provider_call_made": False,
        "ledger_write_made": False,
        "broker_order_made": False,
        "symbol_selection_made": False,
    }


def capture_boundary(
    *,
    boundary_utc: datetime,
    pre_seconds: int,
    post_seconds: int,
    interval_seconds: float,
    output_jsonl: Path,
) -> dict[str, Any]:
    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:
        raise RuntimeError("MetaTrader5 package is not installed") from exc

    boundary = _utc(boundary_utc)
    start = boundary - timedelta(seconds=pre_seconds)
    end = boundary + timedelta(seconds=post_seconds)

    output_jsonl.parent.mkdir(parents=True, exist_ok=True)

    if not mt5.initialize():
        raise RuntimeError(f"MT5 initialize() failed: {mt5.last_error()}")

    observations: list[dict[str, Any]] = []
    boundary_epoch = int(boundary.timestamp())

    try:
        while True:
            now = datetime.now(timezone.utc)
            if now < start:
                time.sleep(min(1.0, max(0.05, (start - now).total_seconds())))
                continue
            if now > end:
                break

            for symbol in SYMBOLS:
                observed = datetime.now(timezone.utc)
                row: dict[str, Any] = {
                    "probe_version": "AI-v1-Index-H1-Boundary-Probe-v0.1",
                    "symbol": symbol,
                    "observed_at_utc": _iso(observed),
                    "boundary_utc": _iso(boundary),
                    "seconds_from_boundary": (
                        observed - boundary
                    ).total_seconds(),
                    "read_ok": False,
                    "provider_call_made": False,
                    "ledger_write_made": False,
                    "broker_order_made": False,
                    "symbol_selection_made": False,
                }

                rates = mt5.copy_rates_from_pos(
                    symbol,
                    mt5.TIMEFRAME_H1,
                    0,
                    3,
                )
                tick = mt5.symbol_info_tick(symbol)

                if rates is None:
                    row["mt5_last_error"] = list(mt5.last_error())
                else:
                    rate_rows = sorted(
                        (
                            {
                                "open_utc": _iso(
                                    datetime.fromtimestamp(
                                        int(rate["time"]),
                                        tz=timezone.utc,
                                    )
                                ),
                                "open": float(rate["open"]),
                                "high": float(rate["high"]),
                                "low": float(rate["low"]),
                                "close": float(rate["close"]),
                                "tick_volume": int(rate["tick_volume"]),
                                "spread": int(rate["spread"]),
                            }
                            for rate in rates
                        ),
                        key=lambda item: item["open_utc"],
                    )
                    latest = rate_rows[-1] if rate_rows else None
                    row["read_ok"] = True
                    row["h1_rows"] = rate_rows
                    row["latest_h1_open_utc"] = (
                        latest["open_utc"] if latest else None
                    )
                    row["boundary_row_present"] = any(
                        int(rate["time"]) == boundary_epoch for rate in rates
                    )

                if tick is not None:
                    row["latest_tick_utc"] = _iso(
                        datetime.fromtimestamp(int(tick.time), tz=timezone.utc)
                    )
                    row["latest_tick_bid"] = (
                        float(tick.bid) if getattr(tick, "bid", 0) else None
                    )
                    row["latest_tick_ask"] = (
                        float(tick.ask) if getattr(tick, "ask", 0) else None
                    )
                else:
                    row["latest_tick_utc"] = None

                observations.append(row)
                with output_jsonl.open("a", encoding="utf-8", newline="\n") as handle:
                    handle.write(
                        json.dumps(
                            row,
                            sort_keys=True,
                            separators=(",", ":"),
                        )
                        + "\n"
                    )

            now_after = datetime.now(timezone.utc)
            target = now_after + timedelta(seconds=interval_seconds)
            remaining = (end - now_after).total_seconds()
            if remaining <= 0:
                break
            time.sleep(min(interval_seconds, remaining))
    finally:
        mt5.shutdown()

    return summarize_observations(observations, boundary_utc=boundary)
