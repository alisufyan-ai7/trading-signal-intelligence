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
        "metadata_version": "AI-v1.0-Retirement-v0.1",
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
