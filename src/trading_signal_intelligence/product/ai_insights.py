from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.active_observability import (
    active_database_paths,
    build_active_report,
    build_legacy_v1_0_summary,
)
from trading_signal_intelligence.ai_v1.observability import (
    MARKETS,
    ObservabilityError,
    read_records_read_only,
)


def _trim_hash(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:12] + "…" + value[-8:] if len(value) > 24 else value


def _records_by_type(
    records: list[dict[str, Any]],
    record_type: str,
) -> list[dict[str, Any]]:
    return [row for row in records if row["record_type"] == record_type]


def _decision_status(
    entity_id: str,
    by_type: dict[str, list[dict[str, Any]]],
) -> str:
    for record_type, status in (
        ("EXIT", "COMPLETED"),
        ("SIGNAL", "SHADOW_SIGNAL"),
        ("REJECTED_INFERENCE", "REJECTED"),
        ("NO_TRADE", "NO_TRADE"),
        ("ERROR", "ERROR"),
        ("MISSED_INFERENCE", "MISSED"),
    ):
        if any(row["entity_id"] == entity_id for row in by_type.get(record_type, [])):
            return status
    return "PENDING_ENTRY"


def _public_decision(
    inference: dict[str, Any],
    by_type: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    payload = inference["payload"]
    decision = payload.get("normalized_decision") or {}
    return {
        "entity_id": inference["entity_id"],
        "source_symbol": payload.get("source_symbol"),
        "source_bar_close_utc": payload.get("source_bar_close_utc"),
        "recorded_at_utc": inference["recorded_at_utc"],
        "decision": decision.get("decision"),
        "raw_confidence": decision.get("raw_confidence"),
        "confidence_label": "uncalibrated_model_score",
        "regime": decision.get("regime"),
        "rationale": decision.get("rationale"),
        "supporting_factors": list(decision.get("supporting_factors") or []),
        "risk_factors": list(decision.get("risk_factors") or []),
        "guard_publishable": bool(payload.get("guard_publishable")),
        "guard_reasons": list(payload.get("guard_reasons") or []),
        "estimated_cost_r": payload.get("estimated_cost_r"),
        "status": _decision_status(inference["entity_id"], by_type),
        "record_hash": _trim_hash(inference.get("record_hash")),
    }


def _public_signal(
    signal: dict[str, Any],
    *,
    inference_by_entity: dict[str, dict[str, Any]],
    partial_by_entity: dict[str, dict[str, Any]],
    exit_by_entity: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    payload = signal["payload"]
    entity_id = signal["entity_id"]
    inference = inference_by_entity.get(entity_id)
    decision = (
        (inference or {}).get("payload", {}).get("normalized_decision", {})
        if inference
        else {}
    )
    partial = partial_by_entity.get(entity_id)
    exit_row = exit_by_entity.get(entity_id)
    exit_payload = exit_row["payload"] if exit_row else {}
    partial_payload = partial["payload"] if partial else {}

    return {
        "entity_id": entity_id,
        "source_symbol": payload.get("source_symbol"),
        "status": "closed" if exit_row else "active",
        "direction": payload.get("direction"),
        "issued_at_utc": signal["recorded_at_utc"],
        "entry_at_utc": payload.get("entry_timestamp_utc"),
        "entry": payload.get("entry"),
        "stop": payload.get("stop"),
        "tp1": payload.get("tp1"),
        "tp2": payload.get("tp2"),
        "max_hold_h1_bars": payload.get("max_hold_h1_bars"),
        "raw_confidence": decision.get("raw_confidence"),
        "regime": decision.get("regime"),
        "rationale": decision.get("rationale"),
        "supporting_factors": list(decision.get("supporting_factors") or []),
        "risk_factors": list(decision.get("risk_factors") or []),
        "tp1_partial": bool(partial),
        "tp1_partial_net_r": (
            partial_payload.get("net_contribution_r") if partial else None
        ),
        "exit_at_utc": (
            exit_payload.get("exit_bar_timestamp_utc") if exit_row else None
        ),
        "exit_price": exit_payload.get("exit_price") if exit_row else None,
        "exit_reason": exit_payload.get("reason") if exit_row else None,
        "net_r": (
            exit_payload.get("total_combined_signal_net_r") if exit_row else None
        ),
        "record_hash": _trim_hash(signal.get("record_hash")),
        "exit_record_hash": (
            _trim_hash(exit_row.get("record_hash")) if exit_row else None
        ),
    }


def build_public_ai_insights(
    repo_root: Path,
    *,
    include_scheduler: bool = True,
    verify_upstream: bool = True,
    decision_limit: int = 12,
    signal_limit: int = 20,
) -> dict[str, Any]:
    """Build a sanitized, read-only AI-v1 product payload.

    This consumes only the verified observability/read-only ledger layer.
    It excludes raw feature snapshots, provider request metadata, full ledger
    payloads and hidden reasoning.
    """

    repo_root = repo_root.resolve()
    report = build_active_report(
        repo_root,
        include_scheduler=include_scheduler,
        verify_upstream=verify_upstream,
    )
    runtime_version = str(report["runtime_version"])
    database_paths = active_database_paths(repo_root)

    market_records: dict[str, list[dict[str, Any]]] = {
        symbol: read_records_read_only(repo_root / database_paths[symbol])
        for symbol in MARKETS
    }

    for symbol in MARKETS:
        records = market_records[symbol]
        observed_head = records[-1]["record_hash"] if records else None
        reported_head = report["markets"][symbol]["current_head_hash"]
        if observed_head != reported_head:
            raise ObservabilityError(
                f"{symbol} ledger changed while AI Insights snapshot was being built"
            )

    decisions: list[dict[str, Any]] = []
    signals: list[dict[str, Any]] = []
    market_rows: list[dict[str, Any]] = []

    for symbol in MARKETS:
        records = market_records[symbol]
        by_type = {
            record_type: _records_by_type(records, record_type)
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
        }
        inference_by_entity = {
            row["entity_id"]: row for row in by_type["INFERENCE"]
        }
        partial_by_entity = {
            row["entity_id"]: row for row in by_type["PARTIAL_EXIT"]
        }
        exit_by_entity = {
            row["entity_id"]: row for row in by_type["EXIT"]
        }

        decisions.extend(
            _public_decision(row, by_type) for row in by_type["INFERENCE"]
        )
        signals.extend(
            _public_signal(
                row,
                inference_by_entity=inference_by_entity,
                partial_by_entity=partial_by_entity,
                exit_by_entity=exit_by_entity,
            )
            for row in by_type["SIGNAL"]
        )

        market = report["markets"][symbol]
        counts = market["counts_by_type"]
        market_rows.append(
            {
                "source_symbol": symbol,
                "ledger_valid": market["ledger_verification"]["valid"],
                "activation_anchor_match": market["activation_anchor_match"],
                "valid_inferences": market["valid_inferences"],
                "signals": counts.get("SIGNAL", 0),
                "open_signals": market["open_signals"],
                "completed_trades": market[
                    "performance_observational_only"
                ]["completed_trades"],
                "no_trade": counts.get("NO_TRADE", 0),
                "rejected_inferences": counts.get("REJECTED_INFERENCE", 0),
                "missed_inferences": market["missed_inferences"],
                "errors": market["errors"],
                "missed_rate": market[
                    "missed_rate_of_processed_opportunities"
                ],
                "latest_recorded_at_utc": market["latest_recorded_at_utc"],
            }
        )

    decisions.sort(
        key=lambda row: (
            str(row.get("source_bar_close_utc")),
            str(row.get("recorded_at_utc")),
        ),
        reverse=True,
    )
    signals.sort(key=lambda row: str(row.get("issued_at_utc")), reverse=True)

    gates = {
        name: {
            "eligible": gate["eligible"],
            "valid_inferences": gate["valid_inferences"],
            "completed_shadow_trades": gate["completed_shadow_trades"],
            "minimum_calendar_days": gate["minimum_calendar_days"],
            "calendar_eligible_at_utc": gate["calendar_eligible_at_utc"],
            "calendar_requirement_met": gate["calendar_requirement_met"],
            "calendar_days_remaining": gate["calendar_days_remaining"],
        }
        for name, gate in report["gates"].items()
    }

    totals = report["totals"]
    performance_bearing_records = (
        int(totals["valid_inferences"])
        + int(totals["missed_inferences"])
        + int(totals["errors"])
    )
    activation_only_v1_1 = (
        runtime_version == "AI-v1.1"
        and performance_bearing_records == 0
    )
    unhealthy_v1_1 = (
        runtime_version == "AI-v1.1"
        and report["health"]["healthy"] is not True
    )
    v1_1_publish_blocked = activation_only_v1_1 or unhealthy_v1_1
    legacy_lineage = (
        build_legacy_v1_0_summary(repo_root)
        if runtime_version == "AI-v1.1"
        else None
    )
    return {
        "schema_version": 1,
        "runtime_version": runtime_version,
        "decision_protocol_version": report["decision_protocol_version"],
        "protocol_version": report["protocol_version"],
        "generated_at_utc": report["generated_at_utc"],
        "mode": "SHADOW_ONLY",
        "status": (
            "activation_only_pre_first_cycle"
            if activation_only_v1_1
            else (
                "runtime_attention_required"
                if unhealthy_v1_1
                else "forward_validation_in_progress"
            )
        ),
        "publish_allowed": not v1_1_publish_blocked,
        "transition_blocked": v1_1_publish_blocked,
        "customer_notice": (
            f"{runtime_version} is running in shadow mode. Signals are research "
            "outputs, not broker executions or personalized investment advice."
        ),
        "lineage_notice": (
            "AI-v1.1 gate progress starts from zero at its own activation. "
            "AI-v1.0 evidence remains a separate legacy lineage."
            if runtime_version == "AI-v1.1"
            else "AI-v1.0 is the active shadow evidence lineage."
        ),
        "legacy_lineage": legacy_lineage,
        "confidence_notice": (
            "Raw confidence is an uncalibrated model score, not a probability "
            "of profit or success."
        ),
        "health": {
            "healthy": report["health"]["healthy"],
            "ledgers_valid": report["health"]["ledgers_valid"],
            "frozen_artifacts_valid": report["health"][
                "frozen_artifacts_valid"
            ],
            "scheduler_healthy": report["health"]["scheduler_healthy"],
            "broker_execution_disabled": report["health"][
                "broker_execution_disabled"
            ],
        },
        "totals": {
            "valid_inferences": totals["valid_inferences"],
            "completed_shadow_trades": totals[
                "completed_shadow_trades"
            ],
            "open_shadow_signals": totals["open_shadow_signals"],
            "signals": totals["signals"],
            "no_trade": totals["no_trade"],
            "rejected_inferences": totals["rejected_inferences"],
            "missed_inferences": totals["missed_inferences"],
            "errors": totals["errors"],
            "error_rate": totals["error_rate_of_attempted_cycles"],
            "missed_rate": totals[
                "missed_rate_of_processed_opportunities"
            ],
            "lifecycle": totals["lifecycle"],
            "performance_observational_only": totals[
                "performance_observational_only"
            ],
            "sync_operational_counts": totals.get(
                "sync_operational_counts", {}
            ),
        },
        "gates": gates,
        "markets": market_rows,
        "recent_decisions": decisions[:decision_limit],
        "shadow_signals": signals[:signal_limit],
        "raw_market_data_included": False,
        "raw_feature_snapshots_included": False,
        "provider_request_metadata_included": False,
        "hidden_reasoning_included": False,
    }
