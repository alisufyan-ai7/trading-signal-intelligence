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
    FROZEN_DECISION_ARTIFACT_PATHS,
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

PUBLIC_SURFACE_CORRECTION_KIND = "AI-v1.1-public-surface-v0.1"
PUBLIC_SURFACE_CORRECTION_KIND_V2 = "AI-v1.1-public-surface-v0.2"
PUBLIC_SURFACE_CORRECTION_GLOB = "AI-v1.1-public-surface-correction-*.json"
PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS = frozenset(
    {
        "observability_source_v1_1",
        "product_publish_task_runner_script",
        "cloud_app_source",
        "cloud_snapshot_verifier_script",
        "ai_ui_script",
        "ai_ui_index",
    }
)
PUBLIC_SURFACE_V2_SCHEMA_VERSION = 2
PUBLIC_SURFACE_WEB_ROOT = "web"


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


def _is_sha256(value: object) -> bool:
    text = str(value)
    return len(text) == 64 and all(
        ch in "0123456789abcdef" for ch in text
    )


def _tracked_web_hashes(repo_root: Path) -> dict[str, str]:
    try:
        output = subprocess.check_output(
            ["git", "ls-files", "--", PUBLIC_SURFACE_WEB_ROOT],
            cwd=repo_root,
            text=True,
            stderr=subprocess.STDOUT,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise ObservabilityError(
            f"unable to enumerate tracked public web files: {exc}"
        ) from exc

    relative_paths = sorted(
        {
            line.strip().replace("\\", "/")
            for line in output.splitlines()
            if line.strip()
        }
    )
    if not relative_paths:
        raise ObservabilityError("tracked public web tree is empty")

    return {
        relative: _file_sha256(repo_root / relative)
        for relative in relative_paths
    }


def _validate_public_surface_base(
    repo_root: Path,
    anchor: dict[str, Any],
    path: Path,
    payload: dict[str, Any],
    *,
    exact_override_set: bool,
) -> dict[str, Any]:
    if payload.get("runtime_version") != RUNTIME_VERSION:
        return {
            "valid": False,
            "reason": "public_surface_runtime_version_mismatch",
        }
    if payload.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        return {
            "valid": False,
            "reason": "public_surface_decision_protocol_mismatch",
        }
    if payload.get("brand") != "VowSig":
        return {
            "valid": False,
            "reason": "public_surface_brand_mismatch",
        }
    if payload.get("canonical_domain") != "https://vowsig.com":
        return {
            "valid": False,
            "reason": "public_surface_canonical_domain_mismatch",
        }

    required_false = (
        "decision_artifacts_changed",
        "ledger_mutation_performed",
        "backfill_performed",
        "provider_call_made",
        "mt5_call_made",
        "broker_execution_enabled",
        "scheduler_changed",
    )
    for key in required_false:
        if payload.get(key) is not False:
            return {
                "valid": False,
                "reason": f"public_surface_{key}_must_be_false",
            }

    base_rel = payload.get("base_activation_anchor")
    base_sha = payload.get("base_activation_anchor_sha256")
    if not isinstance(base_rel, str) or not isinstance(base_sha, str):
        return {
            "valid": False,
            "reason": "public_surface_base_anchor_missing",
        }

    base_path = repo_root / base_rel
    try:
        base_payload = json.loads(base_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "valid": False,
            "reason": "public_surface_base_anchor_unreadable",
            "detail": str(exc)[:300],
        }
    if base_payload != anchor or _file_sha256(base_path) != base_sha:
        return {
            "valid": False,
            "reason": "public_surface_base_anchor_mismatch",
        }

    overrides = payload.get("artifact_hash_overrides")
    if not isinstance(overrides, dict) or not overrides:
        return {
            "valid": False,
            "reason": "public_surface_overrides_missing",
        }

    names = set(overrides)
    if exact_override_set:
        if names != set(PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS):
            return {
                "valid": False,
                "reason": "public_surface_v2_override_set_mismatch",
                "expected_artifacts": sorted(
                    PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS
                ),
                "actual_artifacts": sorted(names),
            }
    elif not names.issubset(PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS):
        return {
            "valid": False,
            "reason": "public_surface_override_outside_allowlist",
            "unexpected_artifacts": sorted(
                names - PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS
            ),
        }

    for name, value in overrides.items():
        if not _is_sha256(value):
            return {
                "valid": False,
                "reason": "public_surface_override_hash_invalid",
                "artifact": name,
            }

    upstream = verify_anchor_upstream_v1_1(repo_root, path)
    if upstream.get("valid") is not True:
        return {
            "valid": False,
            "reason": "public_surface_correction_not_upstream",
            "upstream": upstream,
        }

    return {
        "valid": True,
        "artifact_hash_overrides": dict(overrides),
        "upstream": upstream,
    }


def _validate_public_surface_v2(
    repo_root: Path,
    anchor: dict[str, Any],
    path: Path,
    payload: dict[str, Any],
    *,
    expected_sequence: int,
    predecessor_path: Path,
) -> dict[str, Any]:
    if payload.get("correction_schema_version") != PUBLIC_SURFACE_V2_SCHEMA_VERSION:
        return {
            "valid": False,
            "reason": "public_surface_v2_schema_version_mismatch",
        }
    if payload.get("sequence_number") != expected_sequence:
        return {
            "valid": False,
            "reason": "public_surface_v2_sequence_mismatch",
            "expected_sequence": expected_sequence,
            "actual_sequence": payload.get("sequence_number"),
        }

    expected_predecessor = predecessor_path.relative_to(repo_root).as_posix()
    if payload.get("supersedes_correction") != expected_predecessor:
        return {
            "valid": False,
            "reason": "public_surface_v2_predecessor_path_mismatch",
        }
    if payload.get("supersedes_correction_sha256") != _file_sha256(
        predecessor_path
    ):
        return {
            "valid": False,
            "reason": "public_surface_v2_predecessor_hash_mismatch",
        }

    base = _validate_public_surface_base(
        repo_root,
        anchor,
        path,
        payload,
        exact_override_set=True,
    )
    if base.get("valid") is not True:
        return base

    web_hashes = payload.get("tracked_web_artifact_hashes")
    if not isinstance(web_hashes, dict) or not web_hashes:
        return {
            "valid": False,
            "reason": "public_surface_v2_web_manifest_missing",
        }

    for relative, digest in web_hashes.items():
        if (
            not isinstance(relative, str)
            or not relative.startswith(f"{PUBLIC_SURFACE_WEB_ROOT}/")
            or relative.startswith("/")
            or ".." in Path(relative).parts
        ):
            return {
                "valid": False,
                "reason": "public_surface_v2_web_path_invalid",
                "path": str(relative),
            }
        if not _is_sha256(digest):
            return {
                "valid": False,
                "reason": "public_surface_v2_web_hash_invalid",
                "path": relative,
            }

    overrides = base["artifact_hash_overrides"]
    for artifact_name in ("ai_ui_index", "ai_ui_script"):
        relative = V11_ARTIFACT_PATHS[artifact_name]
        if web_hashes.get(relative) != overrides.get(artifact_name):
            return {
                "valid": False,
                "reason": "public_surface_v2_web_override_mismatch",
                "artifact": artifact_name,
                "path": relative,
            }

    return {
        "valid": True,
        "artifact_hash_overrides": overrides,
        "tracked_web_artifact_hashes": dict(web_hashes),
        "upstream": base["upstream"],
    }


def _public_surface_correction(
    repo_root: Path,
    anchor: dict[str, Any],
) -> dict[str, Any]:
    candidates = sorted(
        (repo_root / "research" / "forward").glob(
            PUBLIC_SURFACE_CORRECTION_GLOB
        )
    )
    if not candidates:
        return {
            "present": False,
            "valid": True,
            "artifact_hash_overrides": {},
            "tracked_web_artifact_hashes": None,
            "sequence_number": 0,
            "chain_paths": [],
        }

    loaded: dict[Path, dict[str, Any]] = {}
    for path in candidates:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            return {
                "present": True,
                "valid": False,
                "reason": "public_surface_correction_unreadable",
                "detail": str(exc)[:300],
                "artifact_hash_overrides": {},
            }
        if not isinstance(payload, dict):
            return {
                "present": True,
                "valid": False,
                "reason": "public_surface_correction_not_object",
                "artifact_hash_overrides": {},
            }
        loaded[path] = payload

    legacy_paths = [
        path
        for path, payload in loaded.items()
        if payload.get("correction_kind") == PUBLIC_SURFACE_CORRECTION_KIND
    ]
    v2_paths = [
        path
        for path, payload in loaded.items()
        if payload.get("correction_kind") == PUBLIC_SURFACE_CORRECTION_KIND_V2
    ]
    unexpected = sorted(
        str(path.relative_to(repo_root))
        for path, payload in loaded.items()
        if payload.get("correction_kind")
        not in {
            PUBLIC_SURFACE_CORRECTION_KIND,
            PUBLIC_SURFACE_CORRECTION_KIND_V2,
        }
    )
    if unexpected:
        return {
            "present": True,
            "valid": False,
            "reason": "unexpected_public_surface_correction_kind",
            "unexpected_files": unexpected,
            "artifact_hash_overrides": {},
        }
    if len(legacy_paths) != 1:
        return {
            "present": True,
            "valid": False,
            "reason": "expected_exactly_one_legacy_public_surface_correction",
            "count": len(legacy_paths),
            "artifact_hash_overrides": {},
        }

    legacy_path = legacy_paths[0]
    legacy_payload = loaded[legacy_path]
    legacy = _validate_public_surface_base(
        repo_root,
        anchor,
        legacy_path,
        legacy_payload,
        exact_override_set=False,
    )
    if legacy.get("valid") is not True:
        return {
            "present": True,
            "valid": False,
            "reason": legacy.get("reason"),
            "detail": legacy,
            "artifact_hash_overrides": {},
        }

    current_path = legacy_path
    current_payload = legacy_payload
    current = legacy
    current_sequence = 1
    chain_paths = [legacy_path.relative_to(repo_root).as_posix()]
    remaining = set(v2_paths)

    while remaining:
        current_rel = current_path.relative_to(repo_root).as_posix()
        successors = sorted(
            path
            for path in remaining
            if loaded[path].get("supersedes_correction") == current_rel
        )
        if not successors:
            return {
                "present": True,
                "valid": False,
                "reason": "public_surface_v2_orphaned_correction",
                "remaining_files": sorted(
                    path.relative_to(repo_root).as_posix()
                    for path in remaining
                ),
                "artifact_hash_overrides": {},
            }
        if len(successors) != 1:
            return {
                "present": True,
                "valid": False,
                "reason": "public_surface_v2_fork_detected",
                "predecessor": current_rel,
                "successors": [
                    path.relative_to(repo_root).as_posix()
                    for path in successors
                ],
                "artifact_hash_overrides": {},
            }

        successor = successors[0]
        successor_payload = loaded[successor]
        validated = _validate_public_surface_v2(
            repo_root,
            anchor,
            successor,
            successor_payload,
            expected_sequence=current_sequence + 1,
            predecessor_path=current_path,
        )
        if validated.get("valid") is not True:
            return {
                "present": True,
                "valid": False,
                "reason": validated.get("reason"),
                "detail": validated,
                "artifact_hash_overrides": {},
            }

        remaining.remove(successor)
        current_path = successor
        current_payload = successor_payload
        current = validated
        current_sequence += 1
        chain_paths.append(successor.relative_to(repo_root).as_posix())

    return {
        "present": True,
        "valid": True,
        "path": current_path.relative_to(repo_root).as_posix(),
        "correction_kind": current_payload.get("correction_kind"),
        "correction_schema_version": current_payload.get(
            "correction_schema_version"
        ),
        "sequence_number": current_sequence,
        "brand": current_payload.get("brand"),
        "canonical_domain": current_payload.get("canonical_domain"),
        "artifact_hash_overrides": dict(
            current["artifact_hash_overrides"]
        ),
        "tracked_web_artifact_hashes": current.get(
            "tracked_web_artifact_hashes"
        ),
        "chain_paths": chain_paths,
        "upstream": current["upstream"],
    }

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

    correction = _public_surface_correction(repo_root, anchor)
    if correction.get("valid") is not True:
        return {
            "valid": False,
            "checked": 0,
            "mismatches": {
                "public_surface_correction": {
                    "expected": "valid committed/upstream correction",
                    "actual": str(correction.get("reason")),
                }
            },
            "public_surface_correction": correction,
        }

    effective_expected = dict(expected)
    effective_expected.update(correction["artifact_hash_overrides"])

    mismatches: dict[str, dict[str, str | None]] = {}
    for name, relative in V11_ARTIFACT_PATHS.items():
        expected_hash = effective_expected.get(name)
        actual = _file_sha256(repo_root / relative)
        if actual != expected_hash:
            mismatches[name] = {
                "expected": str(expected_hash) if expected_hash else None,
                "actual": actual,
            }

    web_checked = 0
    expected_web = correction.get("tracked_web_artifact_hashes")
    if isinstance(expected_web, dict):
        try:
            actual_web = _tracked_web_hashes(repo_root)
        except ObservabilityError as exc:
            mismatches["public_web_tree"] = {
                "expected": "exact tracked web manifest",
                "actual": str(exc),
            }
        else:
            web_checked = len(expected_web)
            for relative in sorted(set(expected_web) | set(actual_web)):
                expected_hash = expected_web.get(relative)
                actual_hash = actual_web.get(relative)
                if expected_hash != actual_hash:
                    mismatches[f"public_web_tree::{relative}"] = {
                        "expected": expected_hash,
                        "actual": actual_hash,
                    }

    return {
        "valid": not mismatches,
        "checked": len(V11_ARTIFACT_PATHS),
        "public_web_tree_checked": web_checked,
        "mismatches": mismatches,
        "public_surface_correction": correction,
    }



def verify_frozen_decision_artifacts_v1_1(
    repo_root: Path,
    anchor: dict[str, Any],
) -> dict[str, Any]:
    expected = anchor.get("frozen_decision_artifact_hashes")
    if not isinstance(expected, dict):
        return {
            "valid": False,
            "checked": 0,
            "mismatches": {
                "frozen_decision_artifact_hashes": {"expected": "object"}
            },
        }

    mismatches: dict[str, dict[str, str | None]] = {}
    for name, relative in FROZEN_DECISION_ARTIFACT_PATHS.items():
        expected_hash = expected.get(name)
        actual = _file_sha256(repo_root / relative)
        if actual != expected_hash:
            mismatches[name] = {
                "expected": str(expected_hash) if expected_hash else None,
                "actual": actual,
            }

    extra = sorted(set(expected) - set(FROZEN_DECISION_ARTIFACT_PATHS))
    for name in extra:
        mismatches[name] = {
            "expected": str(expected[name]),
            "actual": None,
        }

    return {
        "valid": not mismatches,
        "checked": len(FROZEN_DECISION_ARTIFACT_PATHS),
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

    missed_reason_counts: dict[str, int] = {}
    sync_reasons: dict[str, int] = {}
    for row in records:
        reason = str(row["payload"].get("reason", "UNKNOWN"))
        if row["record_type"] == "MISSED_INFERENCE":
            missed_reason_counts[reason] = (
                missed_reason_counts.get(reason, 0) + 1
            )
        if row["record_type"] not in {"MISSED_INFERENCE", "SYNC_STATUS"}:
            continue
        if reason.startswith("rates_") or reason.startswith("no_current_"):
            sync_reasons[reason] = sync_reasons.get(reason, 0) + 1

    inferences = counts.get("INFERENCE", 0)
    errors = counts.get("ERROR", 0)
    missed = counts.get("MISSED_INFERENCE", 0)
    no_current_h1_tick = missed_reason_counts.get(
        "no_current_h1_tick",
        0,
    )
    processing_miss_count = missed - no_current_h1_tick
    processing_miss_denominator = (
        inferences + errors + processing_miss_count
    )
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
        "missed_reason_counts": dict(sorted(missed_reason_counts.items())),
        "no_current_h1_tick_count": no_current_h1_tick,
        "processing_miss_count": processing_miss_count,
        "processing_miss_denominator": processing_miss_denominator,
        "processing_miss_rate_excluding_no_current_h1_tick": (
            processing_miss_count / processing_miss_denominator
            if processing_miss_denominator
            else 0.0
        ),
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
    frozen_decision_artifacts = verify_frozen_decision_artifacts_v1_1(
        repo_root,
        anchor,
    )
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

    missed_reason_counts: dict[str, int] = {}
    for market in markets.values():
        for reason, count in market["missed_reason_counts"].items():
            missed_reason_counts[reason] = (
                missed_reason_counts.get(reason, 0) + int(count)
            )
    no_current_h1_tick = missed_reason_counts.get(
        "no_current_h1_tick",
        0,
    )
    processing_miss_count = missed - no_current_h1_tick
    processing_miss_denominator = (
        valid_inferences + errors + processing_miss_count
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
        and frozen_decision_artifacts["valid"]
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
            "frozen_artifacts_valid": (
                artifacts["valid"] and frozen_decision_artifacts["valid"]
            ),
            "v1_1_artifacts_valid": artifacts["valid"],
            "frozen_decision_artifacts_valid": (
                frozen_decision_artifacts["valid"]
            ),
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
            "frozen_decision_artifact_verification": (
                frozen_decision_artifacts
            ),
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
            "missed_reason_counts": dict(
                sorted(missed_reason_counts.items())
            ),
            "no_current_h1_tick_count": no_current_h1_tick,
            "processing_miss_count": processing_miss_count,
            "processing_miss_denominator": processing_miss_denominator,
            "processing_miss_rate_excluding_no_current_h1_tick": (
                processing_miss_count / processing_miss_denominator
                if processing_miss_denominator
                else 0.0
            ),
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
