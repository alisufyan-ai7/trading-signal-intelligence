from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
    ARTIFACT_PATHS,
    DATABASE_PATHS,
    DECISION_PROTOCOL_VERSION,
    MARKETS,
    PROGRAM_ID,
    RUNTIME_VERSION,
    validate_activation_anchor_document_v1_3,
    validate_review_gates,
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

REPORT_VERSION = "AI-v1.3-Crypto-Observability-v0.1"
TASK_NAME = "VowSig AI-v1.3 Crypto Shadow Scan"


def _activation(
    records: list[dict[str, Any]],
    symbol: str,
) -> dict[str, Any]:
    rows = [row for row in records if row["record_type"] == "ACTIVATION"]
    if len(rows) != 1:
        raise ObservabilityError(
            f"{symbol} expected exactly one AI-v1.3 ACTIVATION; found {len(rows)}"
        )
    if not records or records[0]["record_hash"] != rows[0]["record_hash"]:
        raise ObservabilityError(f"{symbol} AI-v1.3 ACTIVATION is not first")
    payload = rows[0]["payload"]
    if payload.get("runtime_version") != RUNTIME_VERSION:
        raise ObservabilityError(f"{symbol} runtime version mismatch")
    if payload.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ObservabilityError(f"{symbol} decision protocol mismatch")
    if payload.get("public_signal_exposure_enabled") is not False:
        raise ObservabilityError(f"{symbol} public exposure must remain disabled")
    if payload.get("broker_execution_enabled") is not False:
        raise ObservabilityError(f"{symbol} broker execution must remain disabled")
    return rows[0]


def _load_anchor(path: Path) -> dict[str, Any]:
    try:
        anchor = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ObservabilityError(
            f"unable to load AI-v1.3 activation anchor: {path}"
        ) from exc
    if not isinstance(anchor, dict):
        raise ObservabilityError("AI-v1.3 activation anchor root must be object")
    try:
        validate_activation_anchor_document_v1_3(anchor)
    except Exception as exc:
        raise ObservabilityError(f"invalid AI-v1.3 activation anchor: {path}") from exc
    return anchor


def discover_active_anchor_v1_3(
    repo_root: Path,
    records_by_market: dict[str, list[dict[str, Any]]],
) -> tuple[Path, dict[str, Any]]:
    candidates = sorted(
        (repo_root / "research" / "forward").glob(
            "AI-v1.3-crypto-expansion-activation-*.json"
        ),
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
            and activations[symbol]["payload"]
            == markets[symbol].get("payload")
            for symbol in MARKETS
        ):
            return path, anchor
    raise ObservabilityError(
        "no AI-v1.3 activation anchor matches all crypto ledgers"
    )


def verify_crypto_artifacts_v1_3(
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
    for name, relative in ARTIFACT_PATHS.items():
        expected_hash = expected.get(name)
        actual = _file_sha256(repo_root / relative)
        if actual != expected_hash:
            mismatches[name] = {
                "expected": str(expected_hash) if expected_hash else None,
                "actual": actual,
            }
    for name in sorted(set(expected) - set(ARTIFACT_PATHS)):
        mismatches[name] = {
            "expected": str(expected[name]),
            "actual": None,
        }
    return {
        "valid": not mismatches,
        "checked": len(ARTIFACT_PATHS),
        "mismatches": mismatches,
    }


def verify_anchor_upstream_v1_3(
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


def probe_windows_scheduler_v1_3() -> dict[str, Any]:
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
    return {
        "available": True,
        "healthy": state in {"Ready", "Running"} and last_result == 0,
        "task_name": str(payload["TaskName"]),
        "state": state,
        "last_run_time": str(payload["LastRunTime"]),
        "last_task_result": last_result,
        "next_run_time": str(payload["NextRunTime"]),
    }


def _is_weekend_timestamp(value: str) -> bool:
    return datetime.fromisoformat(value).astimezone(UTC).weekday() >= 5


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
    inferences = [
        row for row in records if row["record_type"] == "INFERENCE"
    ]

    weekday_inferences = sum(
        not _is_weekend_timestamp(row["effective_at_utc"])
        for row in inferences
    )
    weekend_inferences = len(inferences) - weekday_inferences
    weekday_exits = sum(
        not _is_weekend_timestamp(row["effective_at_utc"])
        for row in exits
    )
    weekend_exits = len(exits) - weekday_exits

    rejection_reasons: dict[str, int] = {}
    for row in records:
        if row["record_type"] != "REJECTED_INFERENCE":
            continue
        for reason in row["payload"].get("rejection_reasons", []):
            key = str(reason)
            rejection_reasons[key] = rejection_reasons.get(key, 0) + 1

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
        "valid_inferences": len(inferences),
        "completed_shadow_trades": len(exits),
        "open_signal_entities": sorted(signals - exited),
        "open_signals": len(signals - exited),
        "weekday_weekend": {
            "weekday_valid_inferences": weekday_inferences,
            "weekend_valid_inferences": weekend_inferences,
            "weekday_completed_shadow_trades": weekday_exits,
            "weekend_completed_shadow_trades": weekend_exits,
        },
        "rejection_reason_counts": dict(sorted(rejection_reasons.items())),
        "performance_observational_only": _performance(exits),
    }


def build_report_v1_3(
    repo_root: Path,
    *,
    now_utc: datetime | None = None,
    include_scheduler: bool = True,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    now = (now_utc or datetime.now(UTC)).astimezone(UTC)

    records = {
        symbol: read_records_read_only(repo_root / DATABASE_PATHS[symbol])
        for symbol in MARKETS
    }
    anchor_path, anchor = discover_active_anchor_v1_3(repo_root, records)
    anchored_markets = anchor.get("markets")
    if not isinstance(anchored_markets, dict):
        raise ObservabilityError("AI-v1.3 anchor markets must be object")

    markets = {
        symbol: _market_report(
            symbol,
            records[symbol],
            anchored_markets[symbol],
        )
        for symbol in MARKETS
    }
    artifacts = verify_crypto_artifacts_v1_3(repo_root, anchor)
    upstream = (
        verify_anchor_upstream_v1_3(repo_root, anchor_path)
        if verify_upstream
        else {"valid": None, "skipped": True}
    )
    scheduler = (
        probe_windows_scheduler_v1_3()
        if include_scheduler
        else {"available": False, "healthy": None, "skipped": True}
    )
    gates_cfg = validate_review_gates(repo_root)
    frozen_gates = gates_cfg["gates"]

    valid_inferences = sum(
        market["valid_inferences"] for market in markets.values()
    )
    completed = sum(
        market["completed_shadow_trades"] for market in markets.values()
    )
    open_signals = sum(market["open_signals"] for market in markets.values())

    activation_utc = datetime.fromisoformat(
        str(anchor["activated_at_utc"])
    ).astimezone(UTC)
    gates = {
        name: _gate(
            name,
            valid_inferences,
            completed,
            int(spec["valid_inferences"]),
            int(spec["completed_shadow_trades"]),
            now,
            activation_utc,
            int(spec["minimum_calendar_days"]),
        )
        for name, spec in frozen_gates.items()
    }

    aggregate_exits = sorted(
        [
            row
            for symbol in MARKETS
            for row in records[symbol]
            if row["record_type"] == "EXIT"
        ],
        key=lambda row: (row["effective_at_utc"], row["recorded_at_utc"]),
    )
    weekday_valid = sum(
        market["weekday_weekend"]["weekday_valid_inferences"]
        for market in markets.values()
    )
    weekend_valid = sum(
        market["weekday_weekend"]["weekend_valid_inferences"]
        for market in markets.values()
    )
    weekday_completed = sum(
        market["weekday_weekend"]["weekday_completed_shadow_trades"]
        for market in markets.values()
    )
    weekend_completed = sum(
        market["weekday_weekend"]["weekend_completed_shadow_trades"]
        for market in markets.values()
    )

    ledgers_valid = all(
        market["ledger_verification"]["valid"] for market in markets.values()
    )
    anchor_matches = all(
        market["activation_anchor_match"] for market in markets.values()
    )
    scheduler_ok = scheduler.get("healthy") is True if include_scheduler else True
    upstream_ok = upstream.get("valid") is True if verify_upstream else True
    broker_disabled = anchor.get("broker_execution_enabled") is False
    public_disabled = (
        anchor.get("public_signal_exposure_enabled") is False
    )
    healthy = (
        ledgers_valid
        and anchor_matches
        and artifacts["valid"]
        and upstream_ok
        and scheduler_ok
        and broker_disabled
        and public_disabled
    )

    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "program_id": PROGRAM_ID,
        "report_version": REPORT_VERSION,
        "generated_at_utc": now.isoformat(),
        "mode": "READ_ONLY",
        "performance_metrics_are_observational_only": True,
        "per_market_reporting_required": True,
        "weekday_weekend_reporting_required": True,
        "health": {
            "healthy": healthy,
            "ledgers_valid": ledgers_valid,
            "activation_anchor_matches_ledgers": anchor_matches,
            "crypto_artifacts_valid": artifacts["valid"],
            "activation_anchor_upstream_valid": upstream.get("valid"),
            "scheduler_healthy": scheduler.get("healthy"),
            "public_signal_exposure_disabled": public_disabled,
            "broker_execution_disabled": broker_disabled,
        },
        "activation": {
            "anchor_file": str(anchor_path.relative_to(repo_root)),
            "activated_at_utc": anchor["activated_at_utc"],
            "gate_counts_carry_forward": False,
            "calendar_carry_forward": False,
            "backfill_prior_missed": False,
            "provider_call_made_at_activation": anchor["provider_call_made"],
            "binance_call_made_at_activation": anchor[
                "binance_call_made_at_activation"
            ],
            "public_signal_exposure_enabled": anchor[
                "public_signal_exposure_enabled"
            ],
            "broker_execution_enabled": anchor["broker_execution_enabled"],
            "upstream": upstream,
            "artifact_verification": artifacts,
        },
        "scheduler": scheduler,
        "totals": {
            "valid_inferences": valid_inferences,
            "completed_shadow_trades": completed,
            "open_shadow_signals": open_signals,
            "weekday_weekend": {
                "weekday_valid_inferences": weekday_valid,
                "weekend_valid_inferences": weekend_valid,
                "weekday_completed_shadow_trades": weekday_completed,
                "weekend_completed_shadow_trades": weekend_completed,
            },
            "performance_observational_only": _performance(aggregate_exits),
        },
        "gates": gates,
        "markets": markets,
    }
