from __future__ import annotations

import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS,
    MARKETS,
    ObservabilityError,
    read_records_read_only,
)


INDEX_MARKETS = ("USTEC", "US30")
FRESHNESS_SECONDS = 300.0


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ObservabilityError(f"timestamp is not timezone-aware: {value}")
    return parsed.astimezone(timezone.utc)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _delay_bucket(seconds: float) -> str:
    if seconds <= FRESHNESS_SECONDS:
        return "fresh_le_300s"
    if seconds < 1800:
        return "late_5_to_30m"
    if seconds < 3300:
        return "late_30_to_55m"
    if seconds <= 4500:
        return "late_about_1h"
    if seconds < 9000:
        return "late_75_to_150m"
    return "late_over_150m"


def _cycle_close(row: dict[str, Any]) -> str | None:
    payload = row.get("payload") or {}
    value = payload.get("source_bar_close_utc")
    if value:
        return str(value).replace("+00:00", "Z")
    effective = row.get("effective_at_utc")
    return str(effective).replace("+00:00", "Z") if effective else None


def _inference_delay(row: dict[str, Any]) -> float | None:
    close = _cycle_close(row)
    if not close:
        return None
    return (_parse_utc(str(row["recorded_at_utc"])) - _parse_utc(close)).total_seconds()


def _missed_delay(row: dict[str, Any]) -> float:
    payload = row.get("payload") or {}
    if payload.get("data_age_seconds") is not None:
        return float(payload["data_age_seconds"])
    close = _cycle_close(row)
    detected = payload.get("detected_at_utc") or row.get("recorded_at_utc")
    if not close or not detected:
        raise ObservabilityError(
            f"MISSED_INFERENCE missing timing fields: {row.get('entity_id')}"
        )
    return (_parse_utc(str(detected)) - _parse_utc(close)).total_seconds()


def _market_cycle_map(records: list[dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in records:
        record_type = row["record_type"]
        if record_type not in {"INFERENCE", "MISSED_INFERENCE", "ERROR"}:
            continue
        close = _cycle_close(row)
        if close is None:
            continue
        if record_type == "INFERENCE":
            result[close] = "INFERENCE"
        elif close not in result:
            result[close] = record_type
    return result


def _same_close_comparison(
    records_by_market: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    cycle_maps = {
        symbol: _market_cycle_map(records_by_market[symbol]) for symbol in MARKETS
    }
    rows: list[dict[str, Any]] = []
    for symbol in INDEX_MARKETS:
        for close, outcome in sorted(cycle_maps[symbol].items()):
            if outcome != "MISSED_INFERENCE":
                continue
            xau_outcome = cycle_maps["XAUUSD"].get(close, "NO_RECORD")
            rows.append(
                {
                    "index_symbol": symbol,
                    "source_bar_close_utc": close,
                    "index_outcome": outcome,
                    "xauusd_outcome_same_close": xau_outcome,
                }
            )
    xau_fresh = sum(
        1 for row in rows if row["xauusd_outcome_same_close"] == "INFERENCE"
    )
    return {
        "rows": rows,
        "index_missed_cycles": len(rows),
        "xauusd_inference_same_close_count": xau_fresh,
        "xauusd_inference_same_close_fraction": (
            xau_fresh / len(rows) if rows else None
        ),
    }


def _market_summary(symbol: str, records: list[dict[str, Any]]) -> dict[str, Any]:
    missed = [row for row in records if row["record_type"] == "MISSED_INFERENCE"]
    inferences = [row for row in records if row["record_type"] == "INFERENCE"]

    missed_rows: list[dict[str, Any]] = []
    reason_counts: Counter[str] = Counter()
    delay_counts: Counter[str] = Counter()
    utc_hour_counts: Counter[str] = Counter()

    for row in missed:
        payload = row.get("payload") or {}
        delay = _missed_delay(row)
        reason = str(payload.get("reason") or "UNKNOWN")
        close = _cycle_close(row)
        close_dt = _parse_utc(close) if close else None
        bucket = _delay_bucket(delay)
        reason_counts[reason] += 1
        delay_counts[bucket] += 1
        if close_dt:
            utc_hour_counts[f"{close_dt.hour:02d}:00"] += 1
        missed_rows.append(
            {
                "entity_id": row["entity_id"],
                "source_bar_close_utc": close,
                "detected_at_utc": payload.get("detected_at_utc")
                or row["recorded_at_utc"],
                "data_age_seconds": delay,
                "delay_bucket": bucket,
                "reason": reason,
            }
        )

    inference_delays: list[float] = []
    inference_delay_counts: Counter[str] = Counter()
    for row in inferences:
        delay = _inference_delay(row)
        if delay is None:
            continue
        inference_delays.append(delay)
        inference_delay_counts[_delay_bucket(delay)] += 1

    one_hour_late = delay_counts.get("late_about_1h", 0)
    stale_reason = reason_counts.get("scheduler_gap_or_stale_at_discovery", 0)
    return {
        "symbol": symbol,
        "valid_inferences": len(inferences),
        "missed_inferences": len(missed),
        "missed_rate": (
            len(missed) / (len(inferences) + len(missed))
            if (len(inferences) + len(missed))
            else 0.0
        ),
        "missed_reason_counts": dict(sorted(reason_counts.items())),
        "missed_delay_bucket_counts": dict(sorted(delay_counts.items())),
        "missed_source_close_utc_hour_counts": dict(sorted(utc_hour_counts.items())),
        "missed_about_one_hour_late_fraction": (
            one_hour_late / len(missed) if missed else None
        ),
        "stale_discovery_reason_fraction": (
            stale_reason / len(missed) if missed else None
        ),
        "inference_delay_bucket_counts": dict(sorted(inference_delay_counts.items())),
        "inference_delay_seconds": {
            "minimum": min(inference_delays) if inference_delays else None,
            "maximum": max(inference_delays) if inference_delays else None,
            "average": (
                sum(inference_delays) / len(inference_delays)
                if inference_delays
                else None
            ),
        },
        "missed_rows": missed_rows,
    }


def _diagnosis(
    market_summaries: dict[str, dict[str, Any]],
    synchronized: dict[str, Any],
) -> dict[str, Any]:
    index_missed = sum(
        int(market_summaries[symbol]["missed_inferences"])
        for symbol in INDEX_MARKETS
    )
    stale = sum(
        int(
            market_summaries[symbol]["missed_reason_counts"].get(
                "scheduler_gap_or_stale_at_discovery", 0
            )
        )
        for symbol in INDEX_MARKETS
    )
    one_hour = sum(
        int(
            market_summaries[symbol]["missed_delay_bucket_counts"].get(
                "late_about_1h", 0
            )
        )
        for symbol in INDEX_MARKETS
    )
    next_open = sum(
        int(
            market_summaries[symbol]["missed_reason_counts"].get(
                "next_h1_open_unavailable", 0
            )
        )
        for symbol in INDEX_MARKETS
    )
    stale_fraction = stale / index_missed if index_missed else 0.0
    one_hour_fraction = one_hour / index_missed if index_missed else 0.0
    same_close_fraction = synchronized.get("xauusd_inference_same_close_fraction")
    same_close_fraction = (
        float(same_close_fraction) if same_close_fraction is not None else 0.0
    )

    if (
        index_missed >= 5
        and stale_fraction >= 0.70
        and one_hour_fraction >= 0.50
        and same_close_fraction >= 0.30
    ):
        classification = "CONSISTENT_WITH_LATE_INDEX_BAR_DISCOVERY"
        confidence = "strong_pattern_not_causal_proof"
    elif index_missed >= 5 and next_open / index_missed >= 0.50:
        classification = "NEXT_H1_OPEN_UNAVAILABLE_DOMINANT"
        confidence = "strong_pattern"
    elif index_missed:
        classification = "MIXED_OR_UNRESOLVED"
        confidence = "insufficient_for_single_mechanism"
    else:
        classification = "NO_INDEX_MISSES"
        confidence = "not_applicable"

    return {
        "classification": classification,
        "confidence": confidence,
        "index_missed_inferences": index_missed,
        "scheduler_gap_or_stale_at_discovery_count": stale,
        "scheduler_gap_or_stale_fraction": stale_fraction,
        "late_about_one_hour_count": one_hour,
        "late_about_one_hour_fraction": one_hour_fraction,
        "next_h1_open_unavailable_count": next_open,
        "xauusd_inference_on_same_missed_index_close_fraction": same_close_fraction,
        "connector_hypothesis": (
            "The generic MT5 connector marks the newest returned bar incomplete. "
            "If no new index H1 row exists by the :02 scan, the just-finished bar "
            "can remain hidden until a later scan and then exceed the frozen "
            "300-second freshness limit."
        ),
        "causal_limit": (
            "Historical ledger records do not preserve the raw newest MT5 H1 row "
            "timestamp observed at each original scan, so this report can establish "
            "a timing pattern but cannot by itself prove the connector hypothesis."
        ),
        "decision_affecting_change_made": False,
    }


def build_missed_inference_diagnostic(repo_root: Path) -> dict[str, Any]:
    root = repo_root.resolve()
    db_paths = {
        symbol: root / DATABASE_PATHS[symbol]
        for symbol in MARKETS
    }
    missing = [str(path) for path in db_paths.values() if not path.is_file()]
    if missing:
        raise ObservabilityError(f"AI-v1 ledger files missing: {missing}")

    before = {symbol: _sha256(path) for symbol, path in db_paths.items()}
    records_by_market = {
        symbol: read_records_read_only(path)
        for symbol, path in db_paths.items()
    }

    summaries = {
        symbol: _market_summary(symbol, records_by_market[symbol])
        for symbol in MARKETS
    }
    synchronized = _same_close_comparison(records_by_market)
    diagnosis = _diagnosis(summaries, synchronized)

    after = {symbol: _sha256(path) for symbol, path in db_paths.items()}
    unchanged = before == after
    if not unchanged:
        raise ObservabilityError("AI-v1 ledger bytes changed during read-only diagnostic")

    return {
        "diagnostic_version": "AI-v1-Index-Missed-Inference-Diagnostic-v0.1",
        "mode": "READ_ONLY",
        "markets": summaries,
        "synchronized_cross_market_comparison": synchronized,
        "diagnosis": diagnosis,
        "mutation_safety": {
            "database_sha256_before": before,
            "database_sha256_after": after,
            "byte_identical": unchanged,
        },
        "provider_call_made": False,
        "mt5_call_made": False,
        "broker_execution_enabled": False,
    }


def format_diagnostic_text(report: dict[str, Any]) -> str:
    lines = [
        "SignalProof AI-v1 Index Missed-Inference Diagnostic v0.1",
        "Mode: READ_ONLY",
        f"Database byte-identical: {report['mutation_safety']['byte_identical']}",
        "",
        "Market coverage",
    ]
    for symbol in MARKETS:
        market = report["markets"][symbol]
        lines.append(
            f"  {symbol}: valid={market['valid_inferences']} "
            f"missed={market['missed_inferences']} "
            f"missed_rate={market['missed_rate']:.3f}"
        )
        lines.append(
            f"    reasons={market['missed_reason_counts']}"
        )
        lines.append(
            f"    delay_buckets={market['missed_delay_bucket_counts']}"
        )

    sync = report["synchronized_cross_market_comparison"]
    lines += [
        "",
        "Cross-market comparison",
        f"  Index missed cycles: {sync['index_missed_cycles']}",
        "  XAUUSD had an inference on the same close: "
        f"{sync['xauusd_inference_same_close_count']}",
        "  Same-close fraction: "
        f"{sync['xauusd_inference_same_close_fraction']}",
        "",
        "Diagnosis",
        f"  Classification: {report['diagnosis']['classification']}",
        f"  Confidence: {report['diagnosis']['confidence']}",
        "  Decision-affecting change made: False",
        "",
        "Causal limitation",
        f"  {report['diagnosis']['causal_limit']}",
    ]
    return "\n".join(lines)
