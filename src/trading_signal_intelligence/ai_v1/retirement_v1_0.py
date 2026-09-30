from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS,
    MARKETS,
    build_report,
    read_records_read_only,
)


RETIREMENT_REASON = "prospective_mt5_rates_synchronization_correction"
RETIREMENT_METADATA_VERSION = "AI-v1.0-Retirement-v0.1"


class RetirementV10Error(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_v1_0_retirement_preview(
    repo_root: Path,
    *,
    retired_at_utc: datetime | None = None,
    include_scheduler: bool = True,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    root = repo_root.resolve()
    retired_at = (retired_at_utc or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    )

    report = build_report(
        root,
        include_scheduler=include_scheduler,
        verify_upstream=verify_upstream,
    )

    markets: dict[str, Any] = {}
    performance_bearing = False
    for symbol in MARKETS:
        path = root / DATABASE_PATHS[symbol]
        records = read_records_read_only(path)
        counts = report["markets"][symbol]["counts_by_type"]
        performance_bearing = performance_bearing or any(
            counts.get(record_type, 0) > 0
            for record_type in (
                "INFERENCE",
                "NO_TRADE",
                "REJECTED_INFERENCE",
                "SIGNAL",
                "PARTIAL_EXIT",
                "EXIT",
                "MISSED_INFERENCE",
                "ERROR",
            )
        )
        markets[symbol] = {
            "ledger_path": DATABASE_PATHS[symbol],
            "ledger_sha256": _sha256(path),
            "head_hash": records[-1]["record_hash"] if records else None,
            "records": len(records),
            "counts_by_type": counts,
            "valid_inferences": report["markets"][symbol]["valid_inferences"],
            "missed_inferences": report["markets"][symbol]["missed_inferences"],
            "errors": report["markets"][symbol]["errors"],
            "open_signal_entities": report["markets"][symbol][
                "open_signal_entities"
            ],
            "open_signals": report["markets"][symbol]["open_signals"],
            "completed_shadow_trades": report["markets"][symbol][
                "performance_observational_only"
            ]["completed_trades"],
            "ledger_valid": report["markets"][symbol][
                "ledger_verification"
            ]["valid"],
        }

    unresolved = sum(row["open_signals"] for row in markets.values())
    ledgers_valid = all(row["ledger_valid"] for row in markets.values())
    scheduler = report["scheduler"]

    return {
        "metadata_version": RETIREMENT_METADATA_VERSION,
        "runtime_version": "AI-v1.0",
        "decision_protocol_version": "AI-v1.0",
        "retired_at_utc": retired_at.isoformat(),
        "reason": RETIREMENT_REASON,
        "activation_anchor": report["activation"]["anchor_file"],
        "activation_utc": report["activation"]["activated_at_utc"],
        "performance_bearing_records_observed": performance_bearing,
        "ledgers_preserved": True,
        "ledger_mutation_performed": False,
        "backfilled_into_ai_v1_1": False,
        "provider_call_made": False,
        "mt5_call_made": False,
        "broker_execution_enabled": False,
        "markets": markets,
        "final_totals": {
            "valid_inferences": report["totals"]["valid_inferences"],
            "missed_inferences": report["totals"]["missed_inferences"],
            "errors": report["totals"]["errors"],
            "signals": report["totals"]["signals"],
            "completed_shadow_trades": report["totals"][
                "completed_shadow_trades"
            ],
            "open_shadow_signals": report["totals"][
                "open_shadow_signals"
            ],
            "performance_observational_only": report["totals"][
                "performance_observational_only"
            ],
        },
        "scheduler_before_disable": scheduler,
        "cutover_preconditions": {
            "ledgers_valid": ledgers_valid,
            "unresolved_signal_count": unresolved,
            "unresolved_signals_zero": unresolved == 0,
            "broker_execution_disabled": report["health"][
                "broker_execution_disabled"
            ],
            "ready_for_scheduler_cutover": (
                ledgers_valid
                and unresolved == 0
                and report["health"]["broker_execution_disabled"]
            ),
        },
        "metadata_write_performed": False,
    }



def _market_identity(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "ledger_path": row["ledger_path"],
        "ledger_sha256": row["ledger_sha256"],
        "head_hash": row["head_hash"],
        "records": row["records"],
        "counts_by_type": row["counts_by_type"],
        "valid_inferences": row["valid_inferences"],
        "missed_inferences": row["missed_inferences"],
        "errors": row["errors"],
        "open_signal_entities": row["open_signal_entities"],
        "open_signals": row["open_signals"],
        "completed_shadow_trades": row["completed_shadow_trades"],
        "ledger_valid": row["ledger_valid"],
    }


def validate_v1_0_retirement_preview(preview: dict[str, Any]) -> None:
    if preview.get("metadata_version") != RETIREMENT_METADATA_VERSION:
        raise RetirementV10Error("retirement metadata version mismatch")
    if preview.get("runtime_version") != "AI-v1.0":
        raise RetirementV10Error("retirement runtime version mismatch")
    if preview.get("decision_protocol_version") != "AI-v1.0":
        raise RetirementV10Error("retirement decision protocol mismatch")
    if preview.get("reason") != RETIREMENT_REASON:
        raise RetirementV10Error("retirement reason mismatch")
    if preview.get("performance_bearing_records_observed") is not True:
        raise RetirementV10Error(
            "AI-v1.0 retirement requires performance-bearing evidence"
        )
    if preview.get("ledgers_preserved") is not True:
        raise RetirementV10Error("AI-v1.0 ledgers must remain preserved")
    if preview.get("ledger_mutation_performed") is not False:
        raise RetirementV10Error("retirement preview must be read-only")
    if preview.get("backfilled_into_ai_v1_1") is not False:
        raise RetirementV10Error("AI-v1.0 evidence must not be backfilled")
    if preview.get("provider_call_made") is not False:
        raise RetirementV10Error("retirement must not call provider")
    if preview.get("mt5_call_made") is not False:
        raise RetirementV10Error("retirement must not call MT5")
    if preview.get("broker_execution_enabled") is not False:
        raise RetirementV10Error("broker execution must remain disabled")
    if preview.get("metadata_write_performed") is not False:
        raise RetirementV10Error("input must be a pre-write retirement preview")

    preconditions = preview.get("cutover_preconditions")
    if not isinstance(preconditions, dict):
        raise RetirementV10Error("retirement preconditions missing")
    if preconditions.get("ledgers_valid") is not True:
        raise RetirementV10Error("AI-v1.0 ledgers are not valid")
    if preconditions.get("unresolved_signal_count") != 0:
        raise RetirementV10Error("AI-v1.0 unresolved signals must be zero")
    if preconditions.get("unresolved_signals_zero") is not True:
        raise RetirementV10Error("AI-v1.0 unresolved signal gate failed")
    if preconditions.get("broker_execution_disabled") is not True:
        raise RetirementV10Error("broker execution boundary failed")
    if preconditions.get("ready_for_scheduler_cutover") is not True:
        raise RetirementV10Error("retirement preview is not cutover-ready")

    scheduler = preview.get("scheduler_before_disable")
    if not isinstance(scheduler, dict) or scheduler.get("available") is not True:
        raise RetirementV10Error("legacy scheduler evidence unavailable")
    if scheduler.get("state") != "Ready":
        raise RetirementV10Error(
            "legacy scheduler must be Ready, not Running/Disabled, in preview"
        )

    markets = preview.get("markets")
    if not isinstance(markets, dict) or set(markets) != set(MARKETS):
        raise RetirementV10Error("retirement market set mismatch")
    for symbol in MARKETS:
        row = markets[symbol]
        if not isinstance(row, dict):
            raise RetirementV10Error(f"{symbol} retirement market row invalid")
        if row.get("ledger_valid") is not True:
            raise RetirementV10Error(f"{symbol} ledger invalid")
        if int(row.get("open_signals", -1)) != 0:
            raise RetirementV10Error(f"{symbol} has unresolved signals")


def build_v1_0_retirement_document(
    repo_root: Path,
    *,
    preview: dict[str, Any],
    retired_at_utc: datetime | None = None,
    verify_upstream: bool = True,
) -> dict[str, Any]:
    """Finalize retirement metadata after the legacy scheduler is disabled.

    The pre-disable preview is authoritative for scheduler-before-disable
    evidence and final v1.0 ledger identities. This function re-reads the
    ledgers after disable and requires byte/head/count identity before building
    the committed metadata document.
    """
    validate_v1_0_retirement_preview(preview)
    retired_at = (retired_at_utc or datetime.now(timezone.utc)).astimezone(
        timezone.utc
    )

    current = build_v1_0_retirement_preview(
        repo_root,
        retired_at_utc=retired_at,
        include_scheduler=True,
        verify_upstream=verify_upstream,
    )

    current_scheduler = current["scheduler_before_disable"]
    if current_scheduler.get("available") is not True:
        raise RetirementV10Error("unable to verify legacy scheduler after disable")
    if current_scheduler.get("state") != "Disabled":
        raise RetirementV10Error(
            "legacy scheduler must be Disabled before retirement finalization"
        )

    if current["activation_anchor"] != preview["activation_anchor"]:
        raise RetirementV10Error("AI-v1.0 activation anchor changed")

    for symbol in MARKETS:
        expected = _market_identity(preview["markets"][symbol])
        observed = _market_identity(current["markets"][symbol])
        if observed != expected:
            raise RetirementV10Error(
                f"{symbol} ledger changed across scheduler-disable boundary"
            )

    preconditions = current["cutover_preconditions"]
    if preconditions.get("ledgers_valid") is not True:
        raise RetirementV10Error("AI-v1.0 ledgers invalid after scheduler disable")
    if preconditions.get("unresolved_signal_count") != 0:
        raise RetirementV10Error(
            "AI-v1.0 unresolved signals changed after scheduler disable"
        )
    if preconditions.get("broker_execution_disabled") is not True:
        raise RetirementV10Error("broker execution boundary failed after disable")

    document = dict(preview)
    document["retired_at_utc"] = retired_at.isoformat()
    document["scheduler_after_disable"] = current_scheduler
    document["metadata_write_performed"] = True
    return document
