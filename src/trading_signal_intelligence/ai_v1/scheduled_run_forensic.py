from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS,
    MARKETS,
    ObservabilityError,
    read_records_read_only,
)


INDEX_MARKETS = ("USTEC", "US30")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _parse_utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        raise ObservabilityError(f"naive timestamp: {value}")
    return dt.astimezone(timezone.utc)


def extract_run_summaries(text: str) -> list[dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    decoder = json.JSONDecoder()
    i = 0
    while i < len(text):
        if text[i] != "{":
            i += 1
            continue
        try:
            obj, consumed = decoder.raw_decode(text[i:])
        except json.JSONDecodeError:
            i += 1
            continue
        if (
            isinstance(obj, dict)
            and obj.get("protocol_version") == "AI-v1.0"
            and obj.get("run_mode") == "SHADOW_ONLY"
            and "market_results" in obj
            and "failures" in obj
        ):
            summaries.append(obj)
        i += max(consumed, 1)
    return summaries


def extract_wrapper_results(text: str) -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    pattern = re.compile(r"run_exit=(\d+)\s+verify_exit=(\d+)")
    for m in pattern.finditer(text):
        rows.append(
            {"run_exit": int(m.group(1)), "verify_exit": int(m.group(2))}
        )
    return rows


def _run_time(summary: dict[str, Any]) -> datetime | None:
    times: list[datetime] = []
    for result in (summary.get("market_results") or {}).values():
        value = result.get("scanned_at_utc") if isinstance(result, dict) else None
        if value:
            times.append(_parse_utc(str(value)))
    if not times:
        return None
    return min(times)


def _entity_for(symbol: str, close: datetime) -> str:
    return f"AI-v1.0:{symbol}:{close.isoformat().replace('+00:00','Z')}"


def _missed_records(records: list[dict[str, Any]], symbol: str) -> list[dict[str, Any]]:
    rows = []
    for row in records:
        if row["record_type"] != "MISSED_INFERENCE":
            continue
        payload = row.get("payload") or {}
        if payload.get("source_symbol") != symbol:
            continue
        rows.append(row)
    return rows


def build_forensic_report(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    log_path = root / "data" / "forward-task-logs" / "ai_v1_shadow.log"
    if not log_path.is_file():
        raise ObservabilityError(f"task log missing: {log_path}")

    db_paths = {s: root / DATABASE_PATHS[s] for s in MARKETS}
    before = {s: _sha256(p) for s, p in db_paths.items()}
    records = {s: read_records_read_only(p) for s, p in db_paths.items()}

    text = log_path.read_text(encoding="utf-8", errors="replace")
    summaries = extract_run_summaries(text)
    wrappers = extract_wrapper_results(text)

    runs: list[dict[str, Any]] = []
    for idx, summary in enumerate(summaries):
        rt = _run_time(summary)
        if rt is None:
            continue
        wrap = wrappers[idx] if idx < len(wrappers) else {}
        runs.append(
            {
                "run_time_utc": rt,
                "summary": summary,
                "run_exit": wrap.get("run_exit"),
                "verify_exit": wrap.get("verify_exit"),
            }
        )

    cases: list[dict[str, Any]] = []
    counts = {
        "market_failure": 0,
        "successful_scan_no_current_close_action": 0,
        "no_matching_run": 0,
        "current_close_action_present": 0,
    }

    for symbol in INDEX_MARKETS:
        for missed in _missed_records(records[symbol], symbol):
            payload = missed.get("payload") or {}
            close = _parse_utc(str(payload["source_bar_close_utc"]))
            target = close + timedelta(seconds=120)

            candidates = [
                run for run in runs
                if abs((run["run_time_utc"] - target).total_seconds()) <= 600
            ]
            run = min(
                candidates,
                key=lambda r: abs((r["run_time_utc"] - target).total_seconds()),
                default=None,
            )
            case: dict[str, Any] = {
                "symbol": symbol,
                "source_bar_close_utc": close.isoformat().replace("+00:00", "Z"),
                "recorded_missed_at_utc": missed["recorded_at_utc"],
                "classification": None,
            }
            if run is None:
                case["classification"] = "no_matching_run"
                counts["no_matching_run"] += 1
                cases.append(case)
                continue

            summary = run["summary"]
            failures = summary.get("failures") or {}
            market_results = summary.get("market_results") or {}
            market_failure = failures.get(symbol)
            result = market_results.get(symbol)

            case.update(
                {
                    "original_run_time_utc": run["run_time_utc"].isoformat(),
                    "run_exit": run["run_exit"],
                    "verify_exit": run["verify_exit"],
                    "market_failure": market_failure,
                }
            )

            if market_failure is not None:
                case["classification"] = "market_failure"
                counts["market_failure"] += 1
            elif isinstance(result, dict):
                entity = _entity_for(symbol, close)
                actions = result.get("actions") or []
                has_current = any(a.get("entity_id") == entity for a in actions)
                if has_current:
                    case["classification"] = "current_close_action_present"
                    counts["current_close_action_present"] += 1
                else:
                    case["classification"] = "successful_scan_no_current_close_action"
                    counts["successful_scan_no_current_close_action"] += 1
                case["market_action_count"] = len(actions)
            else:
                case["classification"] = "no_matching_run"
                counts["no_matching_run"] += 1

            xau_result = market_results.get("XAUUSD")
            if isinstance(xau_result, dict):
                xau_entity = _entity_for("XAUUSD", close)
                case["xau_current_close_action_present"] = any(
                    a.get("entity_id") == xau_entity
                    for a in (xau_result.get("actions") or [])
                )
            cases.append(case)

    total = len(cases)
    dominant = max(counts, key=counts.get) if total else "none"
    dominant_fraction = counts[dominant] / total if total else 0.0

    after = {s: _sha256(p) for s, p in db_paths.items()}
    if before != after:
        raise ObservabilityError("AI ledger bytes changed during forensic diagnostic")

    return {
        "diagnostic_version": "AI-v1-Scheduled-Run-Forensic-v0.1",
        "mode": "READ_ONLY",
        "task_log": str(log_path.relative_to(root)),
        "run_summaries_recovered": len(runs),
        "wrapper_results_recovered": len(wrappers),
        "historical_index_miss_cases": total,
        "classification_counts": counts,
        "dominant_classification": dominant,
        "dominant_fraction": dominant_fraction,
        "cases": cases,
        "mutation_safety": {
            "database_sha256_before": before,
            "database_sha256_after": after,
            "byte_identical": True,
        },
        "provider_call_made": False,
        "mt5_call_made_by_diagnostic": False,
        "broker_execution_enabled": False,
    }


def format_report(report: dict[str, Any]) -> str:
    lines = [
        "SignalProof AI-v1 Scheduled-Run Forensic Diagnostic v0.1",
        "Mode: READ_ONLY",
        f"Recovered run summaries: {report['run_summaries_recovered']}",
        f"Historical index miss cases: {report['historical_index_miss_cases']}",
        f"Classification counts: {report['classification_counts']}",
        f"Dominant classification: {report['dominant_classification']}",
        f"Dominant fraction: {report['dominant_fraction']:.3f}",
        f"Database byte-identical: {report['mutation_safety']['byte_identical']}",
    ]
    return "\n".join(lines)
