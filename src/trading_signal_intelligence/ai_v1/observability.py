from __future__ import annotations

import hashlib
import json
import math
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import quote

PROTOCOL_VERSION = "AI-v1.0"
REPORT_VERSION = "AI-v1-Observability-v0.1"
MARKETS = ("XAUUSD", "USTEC", "US30")
DATABASE_PATHS = {
    "XAUUSD": "data/ai_v1_xauusd.sqlite",
    "USTEC": "data/ai_v1_ustec.sqlite",
    "US30": "data/ai_v1_us30.sqlite",
}
TASK_NAME = "SignalProof AI-v1 Shadow Scan"
FROZEN_ARTIFACT_PATHS = {
    "provider_selection": "docs/ai-v1-provider-selection.md",
    "architecture": "docs/ai-v1-architecture.md",
    "ledger_spec": "docs/ai-v1-ledger-spec.md",
    "runtime_spec": "docs/ai-v1-shadow-runtime.md",
    "policy": "config/ai_v1_policy.txt",
    "feature_definitions": "docs/ai-v1-feature-definitions.md",
    "feature_schema": "config/ai_v1_feature_schema.json",
    "decision_schema": "config/ai_v1_decision_schema.json",
    "guardrails": "config/ai_v1_guardrails.json",
    "provider_config": "config/ai_v1_provider.json",
    "provider_response_schema": "config/ai_v1_openai_response_schema.json",
    "activation_schema": "config/ai_v1_activation_schema.json",
    "feature_builder_source": "src/trading_signal_intelligence/ai_v1/features.py",
    "inference_adapter_source": "src/trading_signal_intelligence/ai_v1/openai_responses.py",
    "provider_neutral_inference_source": "src/trading_signal_intelligence/ai_v1/inference.py",
    "contract_source": "src/trading_signal_intelligence/ai_v1/contract.py",
    "guard_source": "src/trading_signal_intelligence/ai_v1/guardrails.py",
    "ai_ledger_source": "src/trading_signal_intelligence/ai_v1/ledger.py",
    "engine_source": "src/trading_signal_intelligence/ai_v1/engine.py",
    "lifecycle_evaluator_source": "src/trading_signal_intelligence/ai_v1/signals.py",
    "activation_builder_source": "src/trading_signal_intelligence/ai_v1/activation.py",
    "shadow_runtime_source": "src/trading_signal_intelligence/ai_v1/shadow_runtime.py",
    "shadow_runner_script": "scripts/run_ai_v1_shadow.py",
    "shadow_task_runner_script": "scripts/run_ai_v1_shadow_task.cmd",
    "shadow_task_installer_script": "scripts/install_ai_v1_shadow_task.ps1",
}


class ObservabilityError(RuntimeError):
    pass


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _record_hash(row: dict[str, Any], previous_hash: str | None) -> str:
    material = {
        "record_id": row["record_id"],
        "record_type": row["record_type"],
        "entity_id": row["entity_id"],
        "recorded_at_utc": row["recorded_at_utc"],
        "effective_at_utc": row["effective_at_utc"],
        "payload_json": _canonical_json(row["payload"]),
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(_canonical_json(material).encode("utf-8")).hexdigest()


def read_records_read_only(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ObservabilityError(f"AI-v1 ledger does not exist: {path}")
    encoded = quote(path.resolve().as_posix(), safe="/:")
    connection = sqlite3.connect(f"file:{encoded}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    try:
        if connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='ai_records'"
        ).fetchone() is None:
            raise ObservabilityError(f"ai_records table missing: {path}")
        rows = connection.execute(
            """
            SELECT sequence, record_id, record_type, entity_id,
                   recorded_at_utc, effective_at_utc,
                   payload_json, previous_hash, record_hash
            FROM ai_records ORDER BY sequence ASC
            """
        ).fetchall()
    finally:
        connection.close()
    result = []
    for row in rows:
        try:
            payload = json.loads(row["payload_json"])
        except json.JSONDecodeError as exc:
            raise ObservabilityError(
                f"invalid payload JSON at sequence {row['sequence']}: {path}"
            ) from exc
        result.append(
            {
                "sequence": int(row["sequence"]),
                "record_id": str(row["record_id"]),
                "record_type": str(row["record_type"]),
                "entity_id": str(row["entity_id"]),
                "recorded_at_utc": str(row["recorded_at_utc"]),
                "effective_at_utc": str(row["effective_at_utc"]),
                "payload": payload,
                "previous_hash": row["previous_hash"],
                "record_hash": str(row["record_hash"]),
            }
        )
    return result


def verify_records(records: list[dict[str, Any]]) -> dict[str, Any]:
    previous: str | None = None
    for row in records:
        if row["previous_hash"] != previous:
            return {
                "valid": False,
                "records": len(records),
                "failed_sequence": row["sequence"],
                "reason": "previous_hash_mismatch",
            }
        if row["record_hash"] != _record_hash(row, previous):
            return {
                "valid": False,
                "records": len(records),
                "failed_sequence": row["sequence"],
                "reason": "record_hash_mismatch",
            }
        previous = row["record_hash"]
    return {"valid": True, "records": len(records), "head_hash": previous}


def _activation(records: list[dict[str, Any]], symbol: str) -> dict[str, Any]:
    rows = [row for row in records if row["record_type"] == "ACTIVATION"]
    if len(rows) != 1:
        raise ObservabilityError(
            f"{symbol} expected exactly one ACTIVATION; found {len(rows)}"
        )
    if not records or records[0]["record_hash"] != rows[0]["record_hash"]:
        raise ObservabilityError(f"{symbol} ACTIVATION is not first")
    return rows[0]


def _load_anchor(path: Path) -> dict[str, Any]:
    try:
        anchor = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObservabilityError(f"unable to load activation anchor: {path}") from exc
    if anchor.get("protocol_version") != PROTOCOL_VERSION:
        raise ObservabilityError(f"unexpected activation protocol: {path}")
    if anchor.get("broker_execution_enabled") is not False:
        raise ObservabilityError(f"broker execution not disabled in anchor: {path}")
    return anchor


def discover_active_anchor_read_only(
    repo_root: Path,
    records_by_market: dict[str, list[dict[str, Any]]],
) -> tuple[Path, dict[str, Any]]:
    candidates = sorted(
        (
            path
            for path in (repo_root / "research" / "forward").glob(
                "AI-v1-activation-*.json"
            )
            if "SUPERSEDED" not in path.name.upper()
        ),
        reverse=True,
    )
    activations = {
        symbol: _activation(records_by_market[symbol], symbol) for symbol in MARKETS
    }
    for path in candidates:
        try:
            anchor = _load_anchor(path)
        except ObservabilityError:
            continue
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
    raise ObservabilityError("no activation anchor matches all active AI-v1 ledgers")


def _file_sha256(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_frozen_artifacts(repo_root: Path, anchor: dict[str, Any]) -> dict[str, Any]:
    expected = anchor.get("artifact_hashes")
    if not isinstance(expected, dict):
        return {"valid": False, "checked": 0, "mismatches": {"artifact_hashes": {}}}
    mismatches: dict[str, dict[str, str | None]] = {}
    for name, expected_hash in expected.items():
        relative = FROZEN_ARTIFACT_PATHS.get(str(name))
        actual = _file_sha256(repo_root / relative) if relative else None
        if actual != expected_hash:
            mismatches[str(name)] = {"expected": str(expected_hash), "actual": actual}
    return {
        "valid": not mismatches,
        "checked": len(expected),
        "mismatches": mismatches,
    }


def verify_anchor_upstream(repo_root: Path, anchor_path: Path) -> dict[str, Any]:
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
        "valid": hashlib.sha256(local).digest() == hashlib.sha256(upstream_bytes).digest(),
        "upstream_commit": upstream,
        "local_sha256": hashlib.sha256(local).hexdigest(),
        "upstream_sha256": hashlib.sha256(upstream_bytes).hexdigest(),
    }


def probe_windows_scheduler() -> dict[str, Any]:
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


def _counts(records: list[dict[str, Any]]) -> dict[str, int]:
    result: dict[str, int] = {}
    for row in records:
        key = row["record_type"]
        result[key] = result.get(key, 0) + 1
    return dict(sorted(result.items()))


def _performance(exits: list[dict[str, Any]]) -> dict[str, Any]:
    values = [
        float(row["payload"].get("total_combined_signal_net_r", 0.0))
        for row in exits
    ]
    equity = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for value in values:
        equity += value
        peak = max(peak, equity)
        max_drawdown = min(max_drawdown, equity - peak)
    gains = sum(value for value in values if value > 0)
    losses = -sum(value for value in values if value < 0)
    holds = [
        int(row["payload"]["bars_held"])
        for row in exits
        if row["payload"].get("bars_held") is not None
    ]
    return {
        "completed_trades": len(exits),
        "cumulative_net_r": equity,
        "average_net_r": equity / len(exits) if exits else None,
        "profit_factor": gains / losses if losses > 0 else None,
        "max_drawdown_r": max_drawdown,
        "average_hold_h1_bars": sum(holds) / len(holds) if holds else None,
    }


def _market_report(
    symbol: str,
    records: list[dict[str, Any]],
    anchored: dict[str, Any],
) -> dict[str, Any]:
    verification = verify_records(records)
    activation = _activation(records, symbol)
    counts = _counts(records)
    signals = {r["entity_id"] for r in records if r["record_type"] == "SIGNAL"}
    exits = [r for r in records if r["record_type"] == "EXIT"]
    exited = {r["entity_id"] for r in exits}
    partials = [r for r in records if r["record_type"] == "PARTIAL_EXIT"]
    reasons: dict[str, int] = {}
    for row in exits:
        reason = str(row["payload"].get("reason", "UNKNOWN"))
        reasons[reason] = reasons.get(reason, 0) + 1
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
        "latest_recorded_at_utc": records[-1]["recorded_at_utc"] if records else None,
        "counts_by_type": counts,
        "valid_inferences": inferences,
        "missed_inferences": missed,
        "errors": errors,
        "error_rate_of_attempted_cycles": errors / attempted if attempted else 0.0,
        "missed_rate_of_processed_opportunities": missed / processed if processed else 0.0,
        "open_signal_entities": sorted(signals - exited),
        "open_signals": len(signals - exited),
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


def _gate(
    name: str,
    valid_inferences: int,
    completed_trades: int,
    required_inferences: int,
    required_trades: int,
    now_utc: datetime,
    activation_utc: datetime,
    minimum_days: int = 0,
) -> dict[str, Any]:
    eligible_at = activation_utc + timedelta(days=minimum_days)
    calendar_met = now_utc >= eligible_at
    return {
        "gate": name,
        "eligible": (
            valid_inferences >= required_inferences
            and completed_trades >= required_trades
            and calendar_met
        ),
        "valid_inferences": {
            "current": valid_inferences,
            "required": required_inferences,
            "met": valid_inferences >= required_inferences,
        },
        "completed_shadow_trades": {
            "current": completed_trades,
            "required": required_trades,
            "met": completed_trades >= required_trades,
        },
        "minimum_calendar_days": minimum_days,
        "calendar_eligible_at_utc": eligible_at.isoformat(),
        "calendar_requirement_met": calendar_met,
        "calendar_days_remaining": max(
            0, math.ceil((eligible_at - now_utc).total_seconds() / 86400)
        ),
    }


def build_report(
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
    anchor_path, anchor = discover_active_anchor_read_only(repo_root, records)
    anchored_markets = anchor.get("markets")
    if not isinstance(anchored_markets, dict):
        raise ObservabilityError("activation anchor markets must be an object")
    markets = {
        symbol: _market_report(symbol, records[symbol], anchored_markets[symbol])
        for symbol in MARKETS
    }
    artifacts = verify_frozen_artifacts(repo_root, anchor)
    upstream = (
        verify_anchor_upstream(repo_root, anchor_path)
        if verify_upstream
        else {"valid": None, "skipped": True}
    )
    scheduler = (
        probe_windows_scheduler()
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
    aggregate_exits = sorted(
        [
            row
            for symbol in MARKETS
            for row in records[symbol]
            if row["record_type"] == "EXIT"
        ],
        key=lambda row: (row["effective_at_utc"], row["recorded_at_utc"]),
    )
    activated = datetime.fromisoformat(
        str(anchor["activated_at_utc"]).replace("Z", "+00:00")
    ).astimezone(timezone.utc)
    gates = {
        "A1": _gate("A1", valid_inferences, completed, 100, 20, now, activated),
        "A2": _gate("A2", valid_inferences, completed, 500, 50, now, activated, 60),
        "A3": _gate("A3", valid_inferences, completed, 1000, 100, now, activated, 120),
    }
    broker_disabled = (
        anchor.get("broker_execution_enabled") is False
        and all(
            _activation(records[symbol], symbol)["payload"].get(
                "broker_execution_enabled"
            )
            is False
            for symbol in MARKETS
        )
    )
    ledgers_valid = all(
        m["ledger_verification"]["valid"] and m["activation_anchor_match"]
        for m in markets.values()
    )
    scheduler_ok = (
        scheduler.get("healthy") is True
        if scheduler.get("available") is True
        else True
    )
    upstream_ok = upstream.get("valid") is True if verify_upstream else True
    healthy = (
        ledgers_valid
        and artifacts["valid"]
        and upstream_ok
        and broker_disabled
        and scheduler_ok
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
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
            "provider_call_made_at_activation": anchor.get("provider_call_made"),
            "broker_execution_enabled": anchor.get("broker_execution_enabled"),
            "upstream": upstream,
            "artifact_verification": artifacts,
        },
        "scheduler": scheduler,
        "totals": {
            "valid_inferences": valid_inferences,
            "completed_shadow_trades": completed,
            "open_shadow_signals": open_signals,
            "missed_inferences": missed,
            "errors": errors,
            "performance_observational_only": _performance(aggregate_exits),
        },
        "gates": gates,
        "markets": markets,
    }


def format_text_report(report: dict[str, Any]) -> str:
    totals = report["totals"]
    scheduler = report["scheduler"]
    lines = [
        "SignalProof AI-v1 Observability v0.1",
        f"Health: {'HEALTHY' if report['health']['healthy'] else 'ATTENTION_REQUIRED'}",
        f"Mode: {report['mode']}",
        f"Activation: {report['activation']['activated_at_utc']}",
        f"Broker execution disabled: {report['health']['broker_execution_disabled']}",
    ]
    if scheduler.get("available"):
        lines += [
            f"Scheduler: {scheduler.get('state')} / last_result={scheduler.get('last_task_result')}",
            f"Scheduler last run: {scheduler.get('last_run_time')}",
            f"Scheduler next run: {scheduler.get('next_run_time')}",
        ]
    else:
        lines.append(f"Scheduler: unavailable ({scheduler.get('reason', 'skipped')})")
    lines += [
        "",
        "Totals",
        f"  Valid inferences: {totals['valid_inferences']}",
        f"  Completed shadow trades: {totals['completed_shadow_trades']}",
        f"  Open shadow signals: {totals['open_shadow_signals']}",
        f"  Missed inferences: {totals['missed_inferences']}",
        f"  Errors: {totals['errors']}",
        f"  Cumulative net R (observational): {totals['performance_observational_only']['cumulative_net_r']:.6f}",
        f"  Max drawdown R (observational): {totals['performance_observational_only']['max_drawdown_r']:.6f}",
        "",
        "Gate progress",
    ]
    for name in ("A1", "A2", "A3"):
        gate = report["gates"][name]
        lines.append(
            f"  {name}: {'ELIGIBLE' if gate['eligible'] else 'NOT ELIGIBLE'} "
            f"| inferences {gate['valid_inferences']['current']}/{gate['valid_inferences']['required']} "
            f"| completed {gate['completed_shadow_trades']['current']}/{gate['completed_shadow_trades']['required']} "
            f"| calendar days remaining {gate['calendar_days_remaining']}"
        )
    lines += ["", "Markets"]
    for symbol in MARKETS:
        market = report["markets"][symbol]
        counts = market["counts_by_type"]
        lines.append(
            f"  {symbol}: ledger={'PASS' if market['ledger_verification']['valid'] else 'FAIL'} "
            f"| inference={counts.get('INFERENCE', 0)} "
            f"| signal={counts.get('SIGNAL', 0)} "
            f"| open={market['open_signals']} "
            f"| completed={market['performance_observational_only']['completed_trades']} "
            f"| no_trade={counts.get('NO_TRADE', 0)} "
            f"| rejected={counts.get('REJECTED_INFERENCE', 0)} "
            f"| missed={counts.get('MISSED_INFERENCE', 0)} "
            f"| errors={counts.get('ERROR', 0)}"
        )
    return "\n".join(lines)
