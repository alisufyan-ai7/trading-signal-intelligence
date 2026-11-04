"""P2 reproducible normalized-R metrics from verified, complete research facts.

NOT a live trading P&L calculator. Input is a separately rights-reviewed,
source-sha-verified fact projection, NEVER the 20-row public snapshot preview.
No broker balances, dollar equity, customer trades or success predictions.
"""
from __future__ import annotations

import math
import re
import statistics
from datetime import datetime, timezone
from typing import Any

METRIC_VERSION = "research-net-r-v1"
_HASH = re.compile(r"^[0-9a-f]{64}$")


class MetricContractError(ValueError):
    pass


def utc_time(value: Any) -> datetime:
    if not isinstance(value, str):
        raise MetricContractError("UTC timestamp missing")
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MetricContractError("Invalid UTC timestamp") from exc
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise MetricContractError("UTC timezone required")
    return result.astimezone(timezone.utc)


def complete_performance(
    facts: list[dict[str, Any]],
    *,
    program_id: str,
    model_version: str,
    cohort: str,
    window_start_utc: str,
    window_end_utc: str,
    as_of_utc: str,
    source_snapshot_sha256: str,
    cost_model_version: str,
) -> dict[str, Any]:
    """Require pre-reconciled, source-anchored, entire-period outcomes.

    All closed records require exact after-cost combined net R. NO_TRADE,
    errors, blocked and open cases remain visible with separate denominators.
    """
    if not isinstance(facts, list):
        raise MetricContractError("Fact population must be an explicit list")
    if not all(isinstance(x, str) and x.strip() for x in
               (program_id, model_version, cohort, cost_model_version)):
        raise MetricContractError("Missing source/model/cohort/cost definition")
    if not _HASH.fullmatch(source_snapshot_sha256):
        raise MetricContractError("Verified 64-hex source snapshot hash required")
    start, end, asof = map(utc_time, (window_start_utc, window_end_utc, as_of_utc))
    if not start < end <= asof:
        raise MetricContractError("Invalid or future source window")
    seen: set[str] = set()
    completed: list[tuple[datetime, str, float]] = []
    counts = {"open": 0, "no_trade": 0, "rejected": 0, "error": 0}
    for record in facts:
        if not isinstance(record, dict):
            raise MetricContractError("Non-object outcome record")
        entity_id = record.get("entity_id")
        if not isinstance(entity_id, str) or not entity_id or entity_id in seen:
            raise MetricContractError("Duplicate/missing immutable entity identity")
        seen.add(entity_id)
        if (record.get("program_id") != program_id or
            record.get("model_version") != model_version or
            record.get("cohort") != cohort):
            raise MetricContractError("Population mixes source/model/cohort")
        if not _HASH.fullmatch(str(record.get("source_record_sha256", ""))):
            raise MetricContractError("Unverified source record anchor")
        state = record.get("state")
        if state == "closed":
            if record.get("after_costs_verified") is not True:
                raise MetricContractError("Completed outcome cost status unverified")
            if record.get("cost_model_version") != cost_model_version:
                raise MetricContractError("Cost methodology mismatch")
            net = record.get("combined_net_r")
            if type(net) not in (float, int) or not math.isfinite(net):
                raise MetricContractError("Completed net R missing/nonfinite; never default to 0")
            close = utc_time(record.get("exit_at_utc"))
            if not start <= close <= end:
                raise MetricContractError("Completed outcome outside exact cohort window")
            completed.append((close, entity_id, float(net)))
        elif state in counts:
            if record.get("combined_net_r") is not None:
                raise MetricContractError("Non-completed event cannot claim realized R")
            counts[state] += 1
        else:
            raise MetricContractError("Unknown/restricted lifecycle state")

    completed.sort(key=lambda row: (row[0], row[1]))
    vals = [r for _, _, r in completed]
    wins = sum(n > 0 for n in vals)
    losses = sum(n < 0 for n in vals)
    even = sum(n == 0 for n in vals)
    closed = len(vals)
    positive = sum(n for n in vals if n > 0)
    negative = sum(n for n in vals if n < 0)
    equity, high, max_drawdown, loss_streak, longest_loss_streak = 0., 0., 0., 0, 0
    for number in vals:
        equity += number
        high = max(high, equity)
        max_drawdown = max(max_drawdown, high-equity)
        loss_streak = loss_streak + 1 if number < 0 else 0
        longest_loss_streak = max(longest_loss_streak, loss_streak)
    return {
        "metric_version": METRIC_VERSION, "source_program_id": program_id,
        "model_version": model_version, "cohort": cohort,
        "window_start_utc": window_start_utc, "window_end_utc": window_end_utc,
        "as_of_utc": as_of_utc, "source_snapshot_sha256": source_snapshot_sha256,
        "cost_model_version": cost_model_version,
        "sample_complete": True, "research_only": True,
        "real_execution_pnl_available": False,
        "total_outcomes": len(facts), "completed_count": closed,
        "open_count": counts["open"], "no_trade_count": counts["no_trade"],
        "rejected_count": counts["rejected"], "error_count": counts["error"],
        "win_count": wins, "loss_count": losses, "breakeven_count": even,
        "win_rate": wins / closed if closed else None,
        "expectancy_net_r": statistics.mean(vals) if vals else None,
        "median_net_r": statistics.median(vals) if vals else None,
        "sum_completed_net_r": sum(vals) if vals else None,
        "profit_factor": positive / abs(negative) if negative < 0 else None,
        "max_normalized_r_drawdown": max_drawdown if vals else None,
        "longest_loss_streak": longest_loss_streak if vals else None,
        "sample_warning": "small_forward_sample" if closed < 30 else None,
        "drawdown_notice": "Cumulative completed R, not actual cash equity.",
        "cost_notice": "Source-verified combined net R; partial TP1 counted once.",
    }


def admin_snapshot_diagnostics(snapshot: dict[str, Any] | None) -> dict[str, Any]:
    """Truthful summary of bounded public snapshot. NOT real VPS health."""
    from trading_signal_intelligence.product.accounts.policy import (
        CATALOG, market_directory,
    )
    directory = market_directory(snapshot)
    programs = snapshot.get("validation_programs") if isinstance(snapshot, dict) else None
    health = snapshot.get("health") if isinstance(snapshot, dict) else None
    result = []
    if isinstance(programs, list):
        allowed = frozenset(row[3] for row in CATALOG)
        for p in programs:
            if not isinstance(p, dict) or p.get("program_id") not in allowed:
                continue
            totals = p.get("totals")
            h = p.get("health")
            result.append({
                "program_id": p["program_id"],
                "mode": p.get("mode"),
                "public_signal_exposure": p.get("public_signal_exposure") is True,
                "reported_healthy": h.get("healthy") if isinstance(h, dict) else None,
                "reported_scheduler_healthy": (
                    h.get("scheduler_healthy") if isinstance(h, dict) else None
                ),
                "valid_inferences": (
                    totals.get("valid_inferences") if isinstance(totals, dict) else None
                ),
                "errors": totals.get("errors") if isinstance(totals, dict) else None,
                "completed_shadow_trades": (
                    totals.get("completed_shadow_trades") if isinstance(totals, dict) else None
                ),
            })
    return {
        "source": "public_snapshot_only",
        "as_of_utc": directory["snapshot_generated_at_utc"],
        "snapshot_fresh": all(m["snapshot_fresh"] for m in directory["markets"]),
        "public_health_reported": health.get("ok") if isinstance(health, dict) else None,
        "programs": result,
        "verified_full_history": False,
        "performance_metrics_available": False,
        "independent_vps_runtime_health_verified": False,
        "backup_restore_proven": False,
        "broker_execution_enabled": False,
    }
