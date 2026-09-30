from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    DECISION_PROTOCOL_VERSION,
    RUNTIME_VERSION,
    V11_ARTIFACT_PATHS,
)
from trading_signal_intelligence.ai_v1.observability import (
    ObservabilityError,
    _counts,
    _file_sha256,
    _gate,
    _performance,
    read_records_read_only,
    verify_records,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS,
    MARKETS,
)


REPORT_VERSION = "AI-v1.1-Observability-v0.1"
TASK_NAME = "SignalProof AI-v1.1 Shadow Scan"


def _activation(records: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    rows = [row for row in records if row["record_type"] == "ACTIVATION"]
    if len(rows) != 1:
        raise ObservabilityError(
            f"{symbol} expected exactly one AI-v1.1 ACTIVATION; found {len(rows)}"
        )
    if not records or records[0]["record_hash"] != rows[0]["record_hash"]:
        raise ObservabilityError(f"{symbol} AI-v1.1 ACTIVATION is not first")
    payload = rows[0]["payload"]
    if payload.get("runtime_version") != RUNTIME_VERSION:
        raise ObservabilityError(f"{symbol} runtime_version mismatch")
    if payload.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ObservabilityError(f"{symbol} decision protocol mismatch")
    if payload.get("broker_execution_enabled") is not False:
        raise ObservabilityError(f"{symbol} broker execution not disabled")
    return rows[0]


def _load_anchor(path: Path) -> dict[str, Any]:
    try:
        anchor = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObservabilityError(f"unable to load AI-v1.1 anchor: {path}") from exc
    if anchor.get("runtime_version") != RUNTIME_VERSION:
        raise ObservabilityError(f"unexpected runtime version in {path}")
    if anchor.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ObservabilityError(f"unexpected decision protocol in {path}")
    if anchor.get("broker_execution_enabled") is not False:
        raise ObservabilityError(f"broker execution not disabled in {path}")
    if anchor.get("gate_counts_carry_forward") is not False:
        raise ObservabilityError(f"gate counts must not carry forward in {path}")
    if anchor.get("backfill_prior_missed") is not False:
        raise ObservabilityError(f"backfill must be false in {path}")
    return anchor


def discover_active_anchor_v1_1(
    repo_root: Path,
    records_by_market: dict[str, list[dict[str, Any]]],
) -> tuple[Path, dict[str, Any]]:
    candidates = sorted(
        (repo_root / "research" / "forward").glob("AI-v1.1-activation-*.json"),
        reverse=True,
    )
    activations = {
        symbol: _activation(records_by_market[symbol], symbol)
        for symbol in MARKETS
    }
    for path in candidates:
        anchor = _load_anchor(path)
        markets = anchor.get("markets")
        if not isinstance(markets, dict):
            continue
        if all(
            isinstance(markets.get(symbol), dict)
            and activations[symbol]["record_hash"]
            == markets[symbol].get("record_hash")
            and activations[symbol]["payload"] == markets[symbol].get("payload")
            for symbol in MARKETS
        ):
            return path, anchor
    raise ObservabilityError(
        "no AI-v1.1 activation anchor matches all AI-v1.1 ledgers"
    )


def verify_v1_1_artifacts(
    repo_root: Path,
    anchor: dict[str, Any],
) -> dict[str, Any]:
    expected = anchor.get("artifact_hashes")
    if not isinstance(expected, dict):
        return {
            "valid": False,
            "checked": 0,
            "mismatches": {"artifact_hashes": {"expected": "object"}},
        }

    mismatches: dict[str, dict[str, str | None]] = {}
    for name, relative in V11_ARTIFACT_PATHS.items():
        expected_hash = expected.get(name)
        actual = _file_sha256(repo_root / relative)
        if actual != expected_hash:
            mismatches[name] = {
                "expected": str(expected_hash) if expected_hash else None,
                "actual": actual,
            }

    return {
        "valid": not mismatches,
        "checked": len(V11_ARTIFACT_PATHS),
        "mismatches": mismatches,
    }


def verify_anchor_upstream_v1_1(
    repo_root: Path,
    anchor_path: Path,
) -> dict[str, Any]:
    relative = anchor_path.relative_to(repo_root).as_posix()
    try:
        upstream = subprocess.check_output(
            ["git", "rev-parse", "@{u}"],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        ).strip()
        upstream_bytes = subprocess.check_output(
            ["git", "show", f"{upstream}:{relative}"],
            cwd=repo_root,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return {
            "valid": False,
            "upstream_commit": None,
            "reason": "upstream_anchor_unavailable",
            "detail": str(exc)[:300],
        }

    local = anchor_path.read_bytes()
    return {
        "valid": hashlib.sha256(local).digest()
        == hashlib.sha256(upstream_bytes).digest(),
        "upstream_commit": upstream,
        "local_sha256": hashlib.sha256(local).hexdigest(),
        "upstream_sha256": hashlib.sha256(upstream_bytes).hexdigest(),
    }


def probe_windows_scheduler_v1_1() -> dict[str, Any]:
    if os.name != "nt":
        return {
            "available": False,
            "healthy": None,
            "reason": "windows_task_scheduler_unavailable_on_this_platform",
        }

    command = (
        "$ErrorActionPreference='Stop';"
        f"$t=Get-ScheduledTask -TaskName '{TASK_NAME}';"
        f"$i=Get-ScheduledTaskInfo -TaskName '{TASK_NAME}';"
        "$o=[pscustomobject]@{TaskName=$t.TaskName;State=[string]$t.State;"
        "LastRunTime=$i.LastRunTime.ToString('o');"
        "LastTaskResult=[int64]$i.LastTaskResult;"
        "NextRunTime=$i.NextRunTime.ToString('o')};"
        "$o|ConvertTo-Json -Compress"
    )
    try:
        payload = json.loads(
            subprocess.check_output(
                ["powershell.exe", "-NoProfile", "-Command", command],
                text=True,
                stderr=subprocess.STDOUT,
            ).strip()
        )
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError) as exc:
        return {
            "available": False,
            "healthy": False,
            "reason": "scheduler_probe_failed",
            "detail": str(exc)[:300],
        }

    last_result = int(payload["LastTaskResult"])
    state = str(payload["State"])
    last_run = str(payload["LastRunTime"])
    return {
        "available": True,
        "healthy": state in {"Ready", "Running"} and last_result == 0,
        "task_name": str(payload["TaskName"]),
        "state": state,
        "last_run_time": last_run,
        "last_task_result": last_result,
        "last_successful_run_time": last_run if last_result == 0 else None,
        "next_run_time": str(payload["NextRunTime"]),
    }


def _market_report(
    symbol: str,
    records: list[dict[str, Any]],
    anchored: dict[str, Any],
) -> dict[str, Any]:
    verification = verify_records(records)
    activation = _activation(records, symbol)
    counts = _counts(records)
    signals = {
        row["entity_id"]
        for row in records
        if row["record_type"] == "SIGNAL"
    }
    exits = [row for row in records if row["record_type"] == "EXIT"]
    exited = {row["entity_id"] for row in exits}
    partials = [
        row for row in records if row["record_type"] == "PARTIAL_EXIT"
    ]

    reasons: dict[str, int] = {}
    for row in exits:
        reason = str(row["payload"].get("reason", "UNKNOWN"))
        reasons[reason] = reasons.get(reason, 0) + 1

    sync_reasons: dict[str, int] = {}
    for row in records:
        if row["record_type"] not in {"MISSED_INFERENCE", "SYNC_STATUS"}:
            continue
        reason = str(row["payload"].get("reason", "UNKNOWN"))
        if reason.startswith("rates_") or reason.startswith("no_current_"):
            sync_reasons[reason] = sync_reasons.get(reason, 0) + 1

    inferences = counts.get("INFERENCE", 0)
    errors = counts.get("ERROR", 0)
    missed = counts.get("MISSED_INFERENCE", 0)
    attempted = inferences + errors
    processed = attempted + missed

    return {
        "symbol": symbol,
        "ledger_path": DATABASE_PATHS[symbol],
        "records": len(records),
        "ledger_verification": verification,
        "activation_anchor_match": (
            activation["record_hash"] == anchored.get("record_hash")
            and activation["payload"] == anchored.get("payload")
        ),
        "activation_record_hash": activation["record_hash"],
        "current_head_hash": records[-1]["record_hash"] if records else None,
        "latest_recorded_at_utc": (
            records[-1]["recorded_at_utc"] if records else None
        ),
        "counts_by_type": counts,
        "valid_inferences": inferences,
        "missed_inferences": missed,
        "errors": errors,
        "error_rate_of_attempted_cycles": (
            errors / attempted if attempted else 0.0
        ),
        "missed_rate_of_processed_opportunities": (
            missed / processed if processed else 0.0
        ),
        "open_signal_entities": sorted(signals - exited),
        "open_signals": len(signals - exited),
        "sync_operational_counts": dict(sorted(sync_reasons.items())),
        "lifecycle": {
            "tp1_partial_count": sum(
                1
                for row in partials
                if row["payload"].get("trigger_reason") == "TP1"
            ),
            "tp2_exit_count": reasons.get("TP2", 0),
            "stop_exit_count": sum(
                reasons.get(reason, 0)
                for reason in ("STOP", "GAP_STOP", "SAME_BAR_STOP_FIRST")
            ),
            "timeout_exit_count": reasons.get("TIMEOUT", 0),
            "exit_reasons": dict(sorted(reasons.items())),
        },
        "performance_observational_only": _performance(exits),
    }


def build_report_v1_1(
    repo_root: Path,
    *,
    now_utc: datetime | None = None,
    include_scheduler: bool = True,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    now = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)

    records = {
        symbol: read_records_read_only(repo_root / DATABASE_PATHS[symbol])
        for symbol in MARKETS
    }
    anchor_path, anchor = discover_active_anchor_v1_1(repo_root, records)
    anchored_markets = anchor.get("markets")
    if not isinstance(anchored_markets, dict):
        raise ObservabilityError("AI-v1.1 anchor markets must be an object")

    markets = {
        symbol: _market_report(
            symbol,
            records[symbol],
            anchored_markets[symbol],
        )
        for symbol in MARKETS
    }

    artifacts = verify_v1_1_artifacts(repo_root, anchor)
    upstream = (
        verify_anchor_upstream_v1_1(repo_root, anchor_path)
        if verify_upstream
        else {"valid": None, "skipped": True}
    )
    scheduler = (
        probe_windows_scheduler_v1_1()
        if include_scheduler
        else {"available": False, "healthy": None, "skipped": True}
    )

    valid_inferences = sum(m["valid_inferences"] for m in markets.values())
    completed = sum(
        m["performance_observational_only"]["completed_trades"]
        for m in markets.values()
    )
    open_signals = sum(m["open_signals"] for m in markets.values())
    missed = sum(m["missed_inferences"] for m in markets.values())
    errors = sum(m["errors"] for m in markets.values())
    no_trade = sum(
        m["counts_by_type"].get("NO_TRADE", 0) for m in markets.values()
    )
    rejected = sum(
        m["counts_by_type"].get("REJECTED_INFERENCE", 0)
        for m in markets.values()
    )
    signals = sum(
        m["counts_by_type"].get("SIGNAL", 0) for m in markets.values()
    )
    attempted_cycles = valid_inferences + errors
    processed_opportunities = attempted_cycles + missed

    lifecycle_totals = {
        "tp1_partial_count": sum(
            m["lifecycle"]["tp1_partial_count"] for m in markets.values()
        ),
        "tp2_exit_count": sum(
            m["lifecycle"]["tp2_exit_count"] for m in markets.values()
        ),
        "stop_exit_count": sum(
            m["lifecycle"]["stop_exit_count"] for m in markets.values()
        ),
        "timeout_exit_count": sum(
            m["lifecycle"]["timeout_exit_count"] for m in markets.values()
        ),
    }

    aggregate_exits = [
        row
        for symbol in MARKETS
        for row in records[symbol]
        if row["record_type"] == "EXIT"
    ]

    activated_at = datetime.fromisoformat(
        str(anchor["activated_at_utc"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    gates = {
        "A1": _gate(
            "A1",
            valid_inferences,
            completed,
            100,
            20,
            now,
            activated_at,
        ),
        "A2": _gate(
            "A2",
            valid_inferences,
            completed,
            500,
            50,
            now,
            activated_at,
            60,
        ),
        "A3": _gate(
            "A3",
            valid_inferences,
            completed,
            1000,
            100,
            now,
            activated_at,
            120,
        ),
    }

    broker_disabled = (
        anchor.get("broker_execution_enabled") is False
        and all(
            m["activation_anchor_match"] for m in markets.values()
        )
    )
    ledgers_valid = all(
        m["ledger_verification"]["valid"] for m in markets.values()
    )
    scheduler_ok = scheduler.get("healthy") is True if include_scheduler else True
    upstream_ok = upstream.get("valid") is True if verify_upstream else True
    healthy = (
        ledgers_valid
        and artifacts["valid"]
        and upstream_ok
        and broker_disabled
        and scheduler_ok
    )

    sync_counts: dict[str, int] = {}
    for market in markets.values():
        for reason, count in market["sync_operational_counts"].items():
            sync_counts[reason] = sync_counts.get(reason, 0) + int(count)

    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "protocol_version": DECISION_PROTOCOL_VERSION,
        "report_version": REPORT_VERSION,
        "generated_at_utc": now.isoformat(),
        "mode": "READ_ONLY",
        "performance_metrics_are_observational_only": True,
        "health": {
            "healthy": healthy,
            "ledgers_valid": ledgers_valid,
            "frozen_artifacts_valid": artifacts["valid"],
            "activation_anchor_upstream_valid": upstream.get("valid"),
            "scheduler_healthy": scheduler.get("healthy"),
            "broker_execution_disabled": broker_disabled,
        },
        "activation": {
            "anchor_file": str(anchor_path.relative_to(repo_root)),
            "activated_at_utc": anchor["activated_at_utc"],
            "provider_call_made_at_activation": anchor.get(
                "provider_call_made"
            ),
            "broker_execution_enabled": anchor.get(
                "broker_execution_enabled"
            ),
            "gate_counts_carry_forward": False,
            "backfill_prior_missed": False,
            "upstream": upstream,
            "artifact_verification": artifacts,
        },
        "scheduler": scheduler,
        "totals": {
            "valid_inferences": valid_inferences,
            "completed_shadow_trades": completed,
            "open_shadow_signals": open_signals,
            "signals": signals,
            "no_trade": no_trade,
            "rejected_inferences": rejected,
            "missed_inferences": missed,
            "errors": errors,
            "error_rate_of_attempted_cycles": (
                errors / attempted_cycles if attempted_cycles else 0.0
            ),
            "missed_rate_of_processed_opportunities": (
                missed / processed_opportunities
                if processed_opportunities
                else 0.0
            ),
            "lifecycle": lifecycle_totals,
            "sync_operational_counts": dict(sorted(sync_counts.items())),
            "performance_observational_only": _performance(aggregate_exits),
        },
        "gates": gates,
        "markets": markets,
    }
