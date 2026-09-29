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


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    decoder = json.JSONDecoder()
    rows: list[dict[str, Any]] = []
    index = 0
    while index < len(text):
        if text[index] != "{":
            index += 1
            continue
        try:
            obj, consumed = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            index += 1
            continue
        if isinstance(obj, dict):
            rows.append(obj)
        index += max(consumed, 1)
    return rows


def extract_s02_secondary_scans(text: str) -> dict[str, list[datetime]]:
    result: dict[str, list[datetime]] = {symbol: [] for symbol in INDEX_MARKETS}
    for obj in _extract_json_objects(text):
        entity = str(obj.get("test_entity") or "")
        scanned = obj.get("scanned_at_utc")
        if not scanned:
            continue
        symbol = None
        if ":USTEC:" in entity:
            symbol = "USTEC"
        elif ":US30:" in entity:
            symbol = "US30"
        if symbol is None:
            continue
        result[symbol].append(_parse_utc(str(scanned)))

    for symbol in INDEX_MARKETS:
        result[symbol].sort()
    return result


def extract_probe_accesses(diagnostics_dir: Path) -> dict[str, list[datetime]]:
    result: dict[str, list[datetime]] = {symbol: [] for symbol in INDEX_MARKETS}
    if not diagnostics_dir.is_dir():
        return result

    for path in sorted(
        diagnostics_dir.glob("ai_v1_index_h1_boundary_probe_*.jsonl")
    ):
        for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            symbol = str(row.get("symbol") or "")
            observed = row.get("observed_at_utc")
            if symbol not in result or not observed:
                continue
            result[symbol].append(_parse_utc(str(observed)))

    for symbol in INDEX_MARKETS:
        result[symbol].sort()
    return result


def _ai_scan_times(log_text: str) -> dict[str, list[datetime]]:
    result: dict[str, list[datetime]] = {symbol: [] for symbol in MARKETS}
    for summary in extract_run_summaries(log_text):
        market_results = summary.get("market_results") or {}
        for symbol in MARKETS:
            market_result = market_results.get(symbol)
            if not isinstance(market_result, dict):
                continue
            scanned = market_result.get("scanned_at_utc")
            if scanned:
                result[symbol].append(_parse_utc(str(scanned)))
    for symbol in MARKETS:
        result[symbol].sort()
    return result


def _nearest_scan(
    scans: list[datetime],
    boundary: datetime,
    *,
    max_delta_seconds: int = 600,
) -> datetime | None:
    target = boundary + timedelta(seconds=120)
    candidates = [
        scan
        for scan in scans
        if abs((scan - target).total_seconds()) <= max_delta_seconds
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda scan: abs((scan - target).total_seconds()))


def _cycle_rows(records: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in records:
        if row["record_type"] not in {"INFERENCE", "MISSED_INFERENCE"}:
            continue
        payload = row.get("payload") or {}
        if payload.get("source_symbol") not in {None, symbol}:
            continue
        value = payload.get("source_bar_close_utc") or row.get("effective_at_utc")
        if not value:
            continue
        boundary = _parse_utc(str(value))
        key = (row["record_type"], _iso(boundary))
        if key in seen:
            continue
        seen.add(key)
        rows.append(
            {
                "outcome": row["record_type"],
                "boundary": boundary,
            }
        )
    rows.sort(key=lambda item: item["boundary"])
    return rows


def _between(
    values: list[datetime],
    start: datetime,
    end: datetime,
) -> list[datetime]:
    return [value for value in values if start <= value <= end]


def _nearest_prior(
    values: list[datetime],
    point: datetime,
    *,
    max_age_seconds: int,
) -> datetime | None:
    eligible = [
        value
        for value in values
        if value <= point and (point - value).total_seconds() <= max_age_seconds
    ]
    return max(eligible) if eligible else None


def summarize_correlation(cases: list[dict[str, Any]]) -> dict[str, Any]:
    counts = {
        "valid_with_known_pre_ai_same_hour_access": 0,
        "valid_without_known_pre_ai_same_hour_access": 0,
        "missed_with_known_pre_ai_same_hour_access": 0,
        "missed_without_known_pre_ai_same_hour_access": 0,
        "valid_with_probe_pre_ai_access": 0,
        "missed_with_probe_pre_ai_access": 0,
        "valid_with_s02_pre_ai_same_hour_access": 0,
        "missed_with_s02_pre_ai_same_hour_access": 0,
    }
    valid = 0
    missed = 0
    valid_prior_s02 = 0
    missed_prior_s02 = 0

    for case in cases:
        outcome = case["outcome"]
        known = bool(case["known_pre_ai_same_hour_access"])
        probe = bool(case["probe_pre_ai_access_count"])
        s02_same_hour = bool(case["s02_pre_ai_same_hour_count"])
        prior_s02 = case["nearest_prior_s02_scan_utc"] is not None

        if outcome == "INFERENCE":
            valid += 1
            counts[
                "valid_with_known_pre_ai_same_hour_access"
                if known
                else "valid_without_known_pre_ai_same_hour_access"
            ] += 1
            if probe:
                counts["valid_with_probe_pre_ai_access"] += 1
            if s02_same_hour:
                counts["valid_with_s02_pre_ai_same_hour_access"] += 1
            if prior_s02:
                valid_prior_s02 += 1
        else:
            missed += 1
            counts[
                "missed_with_known_pre_ai_same_hour_access"
                if known
                else "missed_without_known_pre_ai_same_hour_access"
            ] += 1
            if probe:
                counts["missed_with_probe_pre_ai_access"] += 1
            if s02_same_hour:
                counts["missed_with_s02_pre_ai_same_hour_access"] += 1
            if prior_s02:
                missed_prior_s02 += 1

    return {
        "classification_counts": counts,
        "valid_cycles": valid,
        "missed_cycles": missed,
        "valid_known_pre_ai_same_hour_fraction": (
            counts["valid_with_known_pre_ai_same_hour_access"] / valid
            if valid
            else None
        ),
        "missed_known_pre_ai_same_hour_fraction": (
            counts["missed_with_known_pre_ai_same_hour_access"] / missed
            if missed
            else None
        ),
        "valid_with_prior_s02_within_70m_fraction": (
            valid_prior_s02 / valid if valid else None
        ),
        "missed_with_prior_s02_within_70m_fraction": (
            missed_prior_s02 / missed if missed else None
        ),
        "interpretation": (
            "Correlation only. Known pre-AI access can support a cache-warming "
            "hypothesis but cannot prove that an undocumented/manual/terminal access "
            "did or did not occur."
        ),
    }


def build_rates_cache_access_correlation(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    ai_log = root / "data" / "forward-task-logs" / "ai_v1_shadow.log"
    s02_log = root / "data" / "forward-task-logs" / "s02_secondary_forward.log"
    if not ai_log.is_file():
        raise ObservabilityError(f"AI task log missing: {ai_log}")
    if not s02_log.is_file():
        raise ObservabilityError(f"S02 secondary task log missing: {s02_log}")

    db_paths = {symbol: root / DATABASE_PATHS[symbol] for symbol in MARKETS}
    before = {symbol: _sha256(path) for symbol, path in db_paths.items()}
    records = {
        symbol: read_records_read_only(path)
        for symbol, path in db_paths.items()
    }

    ai_scans = _ai_scan_times(
        ai_log.read_text(encoding="utf-8", errors="replace")
    )
    s02_scans = extract_s02_secondary_scans(
        s02_log.read_text(encoding="utf-8", errors="replace")
    )
    probe_accesses = extract_probe_accesses(root / "data" / "diagnostics")

    cases: list[dict[str, Any]] = []
    for symbol in INDEX_MARKETS:
        for cycle in _cycle_rows(records[symbol], symbol):
            boundary = cycle["boundary"]
            ai_scan = _nearest_scan(ai_scans[symbol], boundary)
            if ai_scan is None:
                cases.append(
                    {
                        "symbol": symbol,
                        "outcome": cycle["outcome"],
                        "source_bar_close_utc": _iso(boundary),
                        "ai_scan_utc": None,
                        "s02_pre_ai_same_hour_count": 0,
                        "probe_pre_ai_access_count": 0,
                        "known_pre_ai_same_hour_access": False,
                        "nearest_prior_s02_scan_utc": None,
                        "nearest_prior_s02_age_seconds": None,
                    }
                )
                continue

            same_hour_s02 = _between(s02_scans[symbol], boundary, ai_scan)
            same_hour_probe = _between(
                probe_accesses[symbol],
                boundary,
                ai_scan,
            )
            prior_s02 = _nearest_prior(
                s02_scans[symbol],
                ai_scan,
                max_age_seconds=4200,
            )
            cases.append(
                {
                    "symbol": symbol,
                    "outcome": cycle["outcome"],
                    "source_bar_close_utc": _iso(boundary),
                    "ai_scan_utc": _iso(ai_scan),
                    "s02_pre_ai_same_hour_count": len(same_hour_s02),
                    "s02_pre_ai_same_hour_times_utc": [
                        _iso(value) for value in same_hour_s02
                    ],
                    "probe_pre_ai_access_count": len(same_hour_probe),
                    "probe_pre_ai_access_times_utc": [
                        _iso(value) for value in same_hour_probe
                    ],
                    "known_pre_ai_same_hour_access": bool(
                        same_hour_s02 or same_hour_probe
                    ),
                    "nearest_prior_s02_scan_utc": (
                        _iso(prior_s02) if prior_s02 else None
                    ),
                    "nearest_prior_s02_age_seconds": (
                        (ai_scan - prior_s02).total_seconds()
                        if prior_s02
                        else None
                    ),
                }
            )

    summary = summarize_correlation(cases)

    after = {symbol: _sha256(path) for symbol, path in db_paths.items()}
    if before != after:
        raise ObservabilityError(
            "AI ledger bytes changed during rates-cache access correlation"
        )

    return {
        "diagnostic_version": "AI-v1-MT5-Rates-Cache-Access-Correlation-v0.1",
        "mode": "READ_ONLY",
        "summary": summary,
        "s02_secondary_scan_counts": {
            symbol: len(s02_scans[symbol]) for symbol in INDEX_MARKETS
        },
        "boundary_probe_access_counts": {
            symbol: len(probe_accesses[symbol]) for symbol in INDEX_MARKETS
        },
        "cases": cases,
        "mutation_safety": {
            "database_sha256_before": before,
            "database_sha256_after": after,
            "byte_identical": True,
        },
        "mt5_call_made": False,
        "provider_call_made": False,
        "ledger_write_made": False,
        "broker_order_made": False,
    }


def format_report(report: dict[str, Any]) -> str:
    summary = report["summary"]
    return "\n".join(
        [
            "SignalProof AI-v1 MT5 Rates-Cache Access Correlation v0.1",
            "Mode: READ_ONLY",
            f"Valid cycles: {summary['valid_cycles']}",
            f"Missed cycles: {summary['missed_cycles']}",
            f"Classification counts: {summary['classification_counts']}",
            "Valid known pre-AI same-hour access fraction: "
            f"{summary['valid_known_pre_ai_same_hour_fraction']}",
            "Missed known pre-AI same-hour access fraction: "
            f"{summary['missed_known_pre_ai_same_hour_fraction']}",
            "Valid prior-S02-within-70m fraction: "
            f"{summary['valid_with_prior_s02_within_70m_fraction']}",
            "Missed prior-S02-within-70m fraction: "
            f"{summary['missed_with_prior_s02_within_70m_fraction']}",
            f"Database byte-identical: {report['mutation_safety']['byte_identical']}",
        ]
    )
