from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS,
    MARKETS,
    ObservabilityError,
    read_records_read_only,
)
from trading_signal_intelligence.ai_v1.scheduled_run_forensic import (
    extract_run_summaries,
)


INDEX_MARKETS = ("USTEC", "US30")
TICK_WINDOW_SECONDS = 600


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ObservabilityError(f"naive timestamp: {value}")
    return dt.astimezone(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _cycle_close(row: dict[str, Any]) -> datetime | None:
    payload = row.get("payload") or {}
    value = payload.get("source_bar_close_utc") or row.get("effective_at_utc")
    return _parse_utc(str(value)) if value else None


def _cycle_rows(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in records:
        if row["record_type"] not in {"INFERENCE", "MISSED_INFERENCE"}:
            continue
        close = _cycle_close(row)
        if close is None:
            continue
        key = (row["record_type"], _iso(close))
        if key in seen:
            continue
        seen.add(key)
        result.append(
            {
                "outcome": row["record_type"],
                "source_bar_close_utc": close,
                "recorded_at_utc": _parse_utc(str(row["recorded_at_utc"])),
            }
        )
    result.sort(key=lambda x: x["source_bar_close_utc"])
    return result


def _run_market_scan_times(
    log_text: str,
) -> dict[str, list[datetime]]:
    by_symbol: dict[str, list[datetime]] = {s: [] for s in MARKETS}
    for summary in extract_run_summaries(log_text):
        market_results = summary.get("market_results") or {}
        for symbol in MARKETS:
            result = market_results.get(symbol)
            if not isinstance(result, dict):
                continue
            value = result.get("scanned_at_utc")
            if value:
                by_symbol[symbol].append(_parse_utc(str(value)))
    for symbol in MARKETS:
        by_symbol[symbol].sort()
    return by_symbol


def _nearest_scan(
    scans: list[datetime],
    boundary: datetime,
    *,
    max_delta_seconds: int = 600,
) -> datetime | None:
    target = boundary + timedelta(seconds=120)
    candidates = [
        dt for dt in scans
        if abs((dt - target).total_seconds()) <= max_delta_seconds
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda dt: abs((dt - target).total_seconds()))


def _tick_timestamp(row: Any) -> datetime:
    names = getattr(getattr(row, "dtype", None), "names", ()) or ()
    if "time_msc" in names:
        msc = int(row["time_msc"])
        return datetime.fromtimestamp(msc / 1000.0, tz=timezone.utc)
    return datetime.fromtimestamp(int(row["time"]), tz=timezone.utc)


def _first_tick_after_boundary(
    mt5: Any,
    *,
    symbol: str,
    boundary: datetime,
    window_seconds: int = TICK_WINDOW_SECONDS,
) -> dict[str, Any]:
    end = boundary + timedelta(seconds=window_seconds)
    ticks = mt5.copy_ticks_range(
        symbol,
        boundary,
        end,
        mt5.COPY_TICKS_ALL,
    )
    if ticks is None:
        return {
            "tick_history_available": False,
            "mt5_last_error": list(mt5.last_error()),
            "first_tick_utc": None,
            "first_tick_offset_seconds": None,
            "ticks_returned": None,
        }

    first: datetime | None = None
    for row in ticks:
        ts = _tick_timestamp(row)
        if ts >= boundary:
            first = ts
            break

    return {
        "tick_history_available": True,
        "mt5_last_error": list(mt5.last_error()),
        "first_tick_utc": _iso(first) if first else None,
        "first_tick_offset_seconds": (
            (first - boundary).total_seconds() if first else None
        ),
        "ticks_returned": int(len(ticks)),
    }


def classify_tick_relation(
    *,
    outcome: str,
    scan_offset_seconds: float | None,
    first_tick_offset_seconds: float | None,
    tick_history_available: bool,
) -> str:
    prefix = "missed" if outcome == "MISSED_INFERENCE" else "valid"
    if not tick_history_available:
        return f"{prefix}_tick_history_unavailable"
    if first_tick_offset_seconds is None:
        return f"{prefix}_no_tick_within_window"
    if scan_offset_seconds is None:
        return f"{prefix}_scan_time_unavailable"
    if first_tick_offset_seconds <= scan_offset_seconds:
        return f"{prefix}_first_tick_before_or_at_scan"
    return f"{prefix}_first_tick_after_scan"


def summarize_cases(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {}
    for case in cases:
        key = str(case["classification"])
        counts[key] = counts.get(key, 0) + 1

    missed_total = sum(
        count for key, count in counts.items() if key.startswith("missed_")
    )
    valid_total = sum(
        count for key, count in counts.items() if key.startswith("valid_")
    )
    missed_support = (
        counts.get("missed_first_tick_after_scan", 0)
        + counts.get("missed_no_tick_within_window", 0)
    )
    valid_expected = counts.get("valid_first_tick_before_or_at_scan", 0)

    missed_support_fraction = (
        missed_support / missed_total if missed_total else None
    )
    valid_expected_fraction = (
        valid_expected / valid_total if valid_total else None
    )

    if (
        missed_total >= 5
        and valid_total >= 2
        and missed_support_fraction is not None
        and valid_expected_fraction is not None
        and missed_support_fraction >= 0.70
        and valid_expected_fraction >= 0.70
    ):
        diagnosis = "FIRST_TICK_AFTER_SCAN_MECHANISM_SUPPORTED"
    elif missed_total:
        diagnosis = "FIRST_TICK_MECHANISM_NOT_CONFIRMED"
    else:
        diagnosis = "NO_MISSED_CASES"

    return {
        "classification_counts": dict(sorted(counts.items())),
        "missed_cases": missed_total,
        "valid_cases": valid_total,
        "missed_support_fraction": missed_support_fraction,
        "valid_expected_fraction": valid_expected_fraction,
        "diagnosis": diagnosis,
    }


def build_historical_tick_boundary_report(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    log_path = root / "data" / "forward-task-logs" / "ai_v1_shadow.log"
    if not log_path.is_file():
        raise ObservabilityError(f"task log missing: {log_path}")

    db_paths = {s: root / DATABASE_PATHS[s] for s in MARKETS}
    before = {s: _sha256(p) for s, p in db_paths.items()}
    records = {s: read_records_read_only(p) for s, p in db_paths.items()}
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    scan_times = _run_market_scan_times(log_text)

    try:
        import MetaTrader5 as mt5  # type: ignore
    except ImportError as exc:
        raise ObservabilityError("MetaTrader5 package is not installed") from exc

    if not mt5.initialize():
        raise ObservabilityError(f"MT5 initialize() failed: {mt5.last_error()}")

    cases: list[dict[str, Any]] = []
    try:
        for symbol in INDEX_MARKETS:
            for cycle in _cycle_rows(records[symbol]):
                boundary = cycle["source_bar_close_utc"]
                scan = _nearest_scan(scan_times[symbol], boundary)
                tick = _first_tick_after_boundary(
                    mt5,
                    symbol=symbol,
                    boundary=boundary,
                )
                scan_offset = (
                    (scan - boundary).total_seconds() if scan else None
                )
                classification = classify_tick_relation(
                    outcome=cycle["outcome"],
                    scan_offset_seconds=scan_offset,
                    first_tick_offset_seconds=tick["first_tick_offset_seconds"],
                    tick_history_available=bool(tick["tick_history_available"]),
                )
                cases.append(
                    {
                        "symbol": symbol,
                        "outcome": cycle["outcome"],
                        "source_bar_close_utc": _iso(boundary),
                        "original_market_scan_utc": _iso(scan) if scan else None,
                        "scan_offset_seconds": scan_offset,
                        **tick,
                        "classification": classification,
                    }
                )
    finally:
        mt5.shutdown()

    summary = summarize_cases(cases)
    after = {s: _sha256(p) for s, p in db_paths.items()}
    if before != after:
        raise ObservabilityError("AI ledger bytes changed during tick diagnostic")

    return {
        "diagnostic_version": "AI-v1-Historical-Tick-Boundary-v0.1",
        "mode": "READ_ONLY",
        "tick_window_seconds": TICK_WINDOW_SECONDS,
        "summary": summary,
        "cases": cases,
        "mutation_safety": {
            "database_sha256_before": before,
            "database_sha256_after": after,
            "byte_identical": True,
        },
        "provider_call_made": False,
        "ledger_write_made": False,
        "broker_order_made": False,
        "symbol_selection_made": False,
        "mt5_read_only_tick_history_used": True,
    }


def format_report(report: dict[str, Any]) -> str:
    s = report["summary"]
    return "\n".join(
        [
            "SignalProof AI-v1 Historical Tick Boundary Diagnostic v0.1",
            "Mode: READ_ONLY",
            f"Missed cases: {s['missed_cases']}",
            f"Valid cases: {s['valid_cases']}",
            f"Classification counts: {s['classification_counts']}",
            f"Missed support fraction: {s['missed_support_fraction']}",
            f"Valid expected fraction: {s['valid_expected_fraction']}",
            f"Diagnosis: {s['diagnosis']}",
            f"Database byte-identical: {report['mutation_safety']['byte_identical']}",
        ]
    )
