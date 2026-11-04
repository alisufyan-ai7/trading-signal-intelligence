"""Owner-only, source-bounded diagnostics for all nine catalog markets.

Public snapshot != independently verified VPS task status, original ledger
source, historical after-cost performance, or executable trading signal.
Build only strict allowlisted aggregates; never echo raw market/signal data.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trading_signal_intelligence.product.accounts.policy import (
    CATALOG, FRESH_SECONDS, market_directory,
)

_PROGRAM_IDS = frozenset(row[3] for row in CATALOG)
_MAX_COUNT = 2**53 - 1
_TOTAL_KEYS = (
    "valid_inferences", "completed_shadow_trades", "open_shadow_signals",
    "signals", "no_trade", "rejected_inferences", "missed_inferences",
    "errors", "no_current_h1_tick_count", "processing_miss_count",
    "processing_miss_denominator",
)
_MARKET_KEYS = (
    "valid_inferences", "completed_shadow_trades", "open_signals",
    "signals", "no_trade", "rejected_inferences", "missed_inferences", "errors",
)
_ALLOWED_MARKET_LOOKUP = {row[0]: row[3] for row in CATALOG}


def _count(value: Any) -> int | None:
    """Missing, negative, bool and nonintegral values are UNKNOWN, never zero."""
    return value if type(value) is int and 0 <= value <= _MAX_COUNT else None


def _flag(value: Any) -> bool | None:
    return value if type(value) is bool else None


def _age(raw: Any, now: datetime) -> int | None:
    if not isinstance(raw, str) or not isinstance(now, datetime) or now.tzinfo is None:
        return None
    try:
        stamp = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return None
        seconds = (now.astimezone(timezone.utc)-stamp.astimezone(timezone.utc)).total_seconds()
    except (TypeError, ValueError, OverflowError):
        return None
    return int(seconds) if 0 <= seconds < 10**12 else None


def _program_rows(snapshot: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("validation_programs"), list):
        return {}
    groups: dict[str, list[dict[str, Any]]] = {}
    for p in snapshot["validation_programs"]:
        if isinstance(p, dict) and p.get("program_id") in _PROGRAM_IDS:
            groups.setdefault(p["program_id"], []).append(p)
    # Duplicate programs are ambiguous, so do not display either as observed.
    return {key: values[0] for key,values in groups.items() if len(values)==1}


def _market_rows(program: dict[str, Any]) -> dict[str, dict[str, Any]]:
    data = program.get("markets")
    if not isinstance(data, list) or len(data) > 100:
        return {}
    markets: dict[str,list[dict[str,Any]]] = {}
    for row in data:
        if isinstance(row, dict) and isinstance(row.get("source_symbol"),str):
            markets.setdefault(row["source_symbol"], []).append(row)
    return {key:rows[0] for key,rows in markets.items() if len(rows)==1}


def owner_operational_diagnostics(
    snapshot: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    payload = snapshot if isinstance(snapshot,dict) else None
    timestamp = payload.get("generated_at_utc") if payload else None
    age = _age(timestamp, now)
    fresh = age is not None and age < FRESH_SECONDS
    programs = _program_rows(payload)
    entries = []
    for program_id in sorted(_PROGRAM_IDS):
        p = programs.get(program_id)
        health = p.get("health") if p and isinstance(p.get("health"), dict) else {}
        totals = p.get("totals") if p and isinstance(p.get("totals"),dict) else {}
        raw_missed = _count(totals.get("missed_inferences"))
        no_tick = _count(totals.get("no_current_h1_tick_count"))
        processing = _count(totals.get("processing_miss_count"))
        # Missing split is UNKNOWN: raw MISSED_INFERENCE cannot be called
        # a missed trading opportunity. No-tick cycles are non-trading.
        split_valid = (
            raw_missed is not None and no_tick is not None
            and processing is not None and raw_missed == no_tick+processing
        )
        counters = {k:_count(totals.get(k)) for k in _TOTAL_KEYS}
        if not split_valid:
            counters["no_current_h1_tick_count"]=None
            counters["processing_miss_count"]=None
            counters["processing_miss_denominator"]=None
        else:
            valid = counters["valid_inferences"]
            errors = counters["errors"]
            den = counters["processing_miss_denominator"]
            if (valid is None or errors is None or den is None
                    or den != valid+errors+processing):
                counters["processing_miss_denominator"]=None
        boundaries = {
            "broker_execution_disabled_reported":_flag(health.get("broker_execution_disabled")),
            "public_signal_exposure_reported":_flag(p.get("public_signal_exposure")) if p else None,
            "shadow_only_reported":p.get("mode")=="SHADOW_ONLY" if p else None,
        }
        boundary_violation = (
            boundaries["broker_execution_disabled_reported"] is not True
            or boundaries["shadow_only_reported"] is not True
            or (program_id != "core-ai-shadow"
                and boundaries["public_signal_exposure_reported"] is not False)
        ) if p else None
        entries.append({
            "program_id":program_id,
            "runtime_version": (
                p.get("runtime_version") if p and
                isinstance(p.get("runtime_version"),str) and
                len(p["runtime_version"]) <= 128 else None
            ),
            "status":"snapshot_missing" if not p else (
                "snapshot_delayed" if not fresh else
                "reported_boundary_violation" if boundary_violation else
                "snapshot_reported_only"
            ),
            "snapshot_observation_current":fresh and p is not None,
            "reported_healthy":_flag(health.get("healthy")),
            "reported_scheduler_healthy":_flag(health.get("scheduler_healthy")),
            "reported_ledgers_valid":_flag(health.get("ledgers_valid")),
            "boundary_violation_reported":boundary_violation,
            **boundaries,
            "totals":counters,
            "processing_miss_rate":(
                processing/counters["processing_miss_denominator"]
                if split_valid and counters["processing_miss_denominator"] else None
            ),
            "independent_scheduler_probe":False,
            "independent_ledger_audit":False,
            "source":"published_validation_snapshot",
        })
    return {
        "source":"public_snapshot_only",
        "snapshot_generated_at_utc":timestamp if isinstance(timestamp,str) else None,
        "snapshot_age_seconds":age,
        "snapshot_fresh":fresh,
        "snapshot_expected_max_age_seconds":FRESH_SECONDS,
        "publisher_last_success_independently_verified":False,
        "vps_schedulers_independently_verified":False,
        "broker_execution_independently_verified":False,
        "backup_restore_proven":False,
        "programs":entries,
        "risk_flags":(
            (["SNAPSHOT_MISSING_OR_DELAYED"] if not fresh else [])
            + (["SHADOW_BOUNDARY_REPORTED_VIOLATION"] if any(
                x["boundary_violation_reported"] is True for x in entries
            ) else [])
            + ["VPS_RUNTIME_NOT_INDEPENDENTLY_OBSERVED",
               "POSTGRES_RECOVERY_UNVERIFIED"]
        ),
        "metric_notice":(
            "Published counters describe an observed snapshot, not current "
            "Windows Task Scheduler or independent ledger proof. Missing "
            "no-tick splits cannot be reinterpreted as missed trades."
        ),
    }


def owner_market_reliability(
    snapshot: dict[str, Any] | None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    operations = owner_operational_diagnostics(snapshot,now=now)
    program_rows = _program_rows(snapshot)
    catalog = market_directory(snapshot,now=now)["markets"]
    result = []
    for market in catalog:
        symbol = market["symbol"]
        program_id = _ALLOWED_MARKET_LOOKUP[symbol]
        p = program_rows.get(program_id)
        observed = _market_rows(p).get(symbol) if p else None
        metrics = {
            k:_count(observed.get(k)) if observed is not None else None
            for k in _MARKET_KEYS
        }
        if p and isinstance(p.get("markets"),list):
            # Only exact symbol in its configured program may supply counters.
            metrics = {
                k:_count(observed.get(k)) if (
                    observed is not None and
                    program_id == _ALLOWED_MARKET_LOOKUP[symbol]
                ) else None for k in _MARKET_KEYS
            }
        result.append({
            "symbol":symbol,
            "program_id":program_id,
            "snapshot_fresh":operations["snapshot_fresh"],
            "catalog_research_status":market["research_status"],
            "reported_ledger_valid":_flag(observed.get("ledger_valid")) if observed else None,
            "reported_activation_anchor_match":(
                _flag(observed.get("activation_anchor_match")) if observed else None
            ),
            "source_metrics_present":observed is not None,
            "reported_counts":metrics,
            "processing_miss_count":None,
            "processing_miss_rate":None,
            "after_costs_per_market_verified":False,
            "independent_ledger_audit":False,
            "research_only":True,
            "no_signal_detail_access_granted_by_diagnostics":True,
            "source":"published_market_snapshot",
        })
    return {
        "source":"public_snapshot_only",
        "as_of_utc":operations["snapshot_generated_at_utc"],
        "snapshot_fresh":operations["snapshot_fresh"],
        "markets":result,
        "market_count":len(result),
        "all_market_performance_verified":False,
        "per_market_processing_miss_breakdown_available":False,
        "notice":(
            "Per-market raw MISSED_INFERENCE counts are not missed trade "
            "opportunities; no-tick processing split is unavailable at "
            "market level. Neither market source counters nor any "
            "after-cost market returns are independently authenticated."
        ),
    }
