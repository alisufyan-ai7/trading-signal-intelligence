from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

from trading_signal_intelligence.ai_v1.engine_v1_1 import (
    DECISION_PROTOCOL_VERSION,
    RUNTIME_VERSION,
    process_inference_cycle_v1_1,
)
from trading_signal_intelligence.ai_v1.features import build_feature_snapshot
from trading_signal_intelligence.ai_v1.inference import ReasoningModelAdapter
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.signals import (
    append_signal_from_approved_inference,
    evaluate_signal,
)
from trading_signal_intelligence.models import Candle


MARKETS = ("XAUUSD", "USTEC", "US30")
DATABASE_PATHS = {
    "XAUUSD": "data/ai_v1_1_xauusd.sqlite",
    "USTEC": "data/ai_v1_1_ustec.sqlite",
    "US30": "data/ai_v1_1_us30.sqlite",
}
SOURCE_NAME = "exness_mt5_demo"
H1_BARS = 500
H4_BARS = 200

PROCESSED_CYCLE_TYPES = (
    "INFERENCE",
    "NO_TRADE",
    "REJECTED_INFERENCE",
    "SIGNAL",
    "MISSED_INFERENCE",
    "ERROR",
)


class ShadowRuntimeV11Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MarketSpecV11:
    source_symbol: str
    canonical_symbol: str
    point_size: float
    database_path: Path


def _iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        raise ShadowRuntimeV11Error("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def market_specs_v1_1(repo_root: Path) -> dict[str, MarketSpecV11]:
    registry = json.loads(
        (repo_root / "config" / "instruments.json").read_text(encoding="utf-8")
    )
    by_symbol: dict[str, MarketSpecV11] = {}
    for instrument in registry["instruments"]:
        cfg = instrument.get("sources", {}).get(SOURCE_NAME)
        if not cfg:
            continue
        symbol = str(cfg.get("symbol"))
        if symbol not in MARKETS:
            continue
        digits = int(cfg["digits"])
        by_symbol[symbol] = MarketSpecV11(
            source_symbol=symbol,
            canonical_symbol=str(instrument["canonical"]),
            point_size=10.0 ** (-digits),
            database_path=repo_root / DATABASE_PATHS[symbol],
        )

    missing = [symbol for symbol in MARKETS if symbol not in by_symbol]
    if missing:
        raise ShadowRuntimeV11Error(f"missing registry entries: {missing}")
    return by_symbol


def cycle_entity_id_v1_1(
    source_symbol: str,
    source_bar_close_utc: datetime,
) -> str:
    return f"{RUNTIME_VERSION}:{source_symbol}:{_iso_z(source_bar_close_utc)}"


def cycle_processed_v1_1(ledger: AILedger, entity_id: str) -> bool:
    return any(
        ledger.has(record_type=record_type, entity_id=entity_id)
        for record_type in PROCESSED_CYCLE_TYPES
    )


def completed_opportunities_v1_1(
    closed_h1: Iterable[Candle],
    *,
    activated_at_utc: datetime,
    now_utc: datetime,
) -> list[tuple[Candle, datetime, float]]:
    if activated_at_utc.tzinfo is None or now_utc.tzinfo is None:
        raise ShadowRuntimeV11Error(
            "activation and current timestamps must be timezone-aware"
        )
    activated = activated_at_utc.astimezone(timezone.utc)
    now = now_utc.astimezone(timezone.utc)

    opportunities: list[tuple[Candle, datetime, float]] = []
    for candle in closed_h1:
        if not candle.is_closed or candle.timeframe.upper() != "H1":
            continue
        close_utc = candle.timestamp_utc + timedelta(hours=1)
        if close_utc <= activated or close_utc > now:
            continue
        age_seconds = (now - close_utc).total_seconds()
        opportunities.append((candle, close_utc, age_seconds))

    opportunities.sort(key=lambda row: row[1])
    return opportunities


def _require_v1_1_activation(ledger: AILedger) -> dict[str, Any]:
    rows = ledger.records(record_type="ACTIVATION")
    if len(rows) != 1:
        raise ShadowRuntimeV11Error(
            f"expected exactly one {RUNTIME_VERSION} activation record"
        )
    payload = rows[0]["payload"]
    if payload.get("runtime_version") != RUNTIME_VERSION:
        raise ShadowRuntimeV11Error("activation runtime_version mismatch")
    if payload.get("decision_protocol_version") != DECISION_PROTOCOL_VERSION:
        raise ShadowRuntimeV11Error("activation decision protocol mismatch")
    if payload.get("broker_execution_enabled") is not False:
        raise ShadowRuntimeV11Error("broker execution must remain disabled")
    return payload


def _summary_record(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload", {})
    result: dict[str, Any] = {
        "record_type": record["record_type"],
        "entity_id": record["entity_id"],
        "record_hash": record["record_hash"],
        "effective_at_utc": record["effective_at_utc"],
    }
    if "reason" in payload:
        result["reason"] = payload["reason"]
    if "decision" in payload:
        result["decision"] = payload["decision"]
    if "total_combined_signal_net_r" in payload:
        result["total_combined_signal_net_r"] = payload[
            "total_combined_signal_net_r"
        ]
    return result


def _append_missed_v1_1(
    *,
    ledger: AILedger,
    source_symbol: str,
    source_bar_close_utc: datetime,
    detected_at_utc: datetime,
    age_seconds: float,
    max_age_seconds: float,
    reason: str,
) -> dict[str, Any]:
    entity_id = cycle_entity_id_v1_1(source_symbol, source_bar_close_utc)
    return ledger.append(
        record_type="MISSED_INFERENCE",
        entity_id=entity_id,
        effective_at_utc=source_bar_close_utc,
        recorded_at_utc=detected_at_utc,
        payload={
            "protocol_version": DECISION_PROTOCOL_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "source_symbol": source_symbol,
            "source_bar_close_utc": _iso_z(source_bar_close_utc),
            "detected_at_utc": detected_at_utc.astimezone(timezone.utc).isoformat(),
            "data_age_seconds": float(age_seconds),
            "max_data_age_seconds": float(max_age_seconds),
            "reason": reason,
            "provider_call_made": False,
        },
    )


def _append_runtime_error_v1_1(
    *,
    ledger: AILedger,
    source_symbol: str,
    source_bar_close_utc: datetime,
    detected_at_utc: datetime,
    stage: str,
    error: Exception,
) -> dict[str, Any]:
    entity_id = cycle_entity_id_v1_1(source_symbol, source_bar_close_utc)
    return ledger.append(
        record_type="ERROR",
        entity_id=entity_id,
        effective_at_utc=source_bar_close_utc,
        recorded_at_utc=detected_at_utc,
        payload={
            "protocol_version": DECISION_PROTOCOL_VERSION,
            "runtime_version": RUNTIME_VERSION,
            "source_symbol": source_symbol,
            "source_bar_close_utc": _iso_z(source_bar_close_utc),
            "stage": stage,
            "error_class": type(error).__name__,
            "sanitized_message": str(error)[:500],
            "broker_execution_enabled": False,
        },
    )


def run_market_cycle_v1_1(
    *,
    ledger: AILedger,
    market: MarketSpecV11,
    h1_all: list[Candle],
    h4_all: list[Candle],
    adapter: ReasoningModelAdapter,
    policy_text: str,
    decision_schema: dict[str, Any],
    guardrails: dict[str, Any],
    now_utc: datetime,
) -> dict[str, Any]:
    closed_h1 = [bar for bar in h1_all if bar.is_closed]
    closed_h4 = [bar for bar in h4_all if bar.is_closed]
    if not closed_h1 or not closed_h4:
        raise ShadowRuntimeV11Error(
            f"{market.source_symbol} requires completed H1 and H4 history"
        )

    activation_payload = _require_v1_1_activation(ledger)
    activated_at = datetime.fromisoformat(
        str(activation_payload["activated_at_utc"]).replace("Z", "+00:00")
    )
    policy_sha256 = str(activation_payload["policy_sha256"])
    guardrails_sha256 = str(activation_payload["guardrails_sha256"])

    actions: list[dict[str, Any]] = []

    unresolved = ledger.unresolved_signal_entities()
    if len(unresolved) > 1:
        raise ShadowRuntimeV11Error(
            f"{market.source_symbol} has multiple unresolved signals: {unresolved}"
        )
    if unresolved:
        lifecycle = evaluate_signal(
            ledger=ledger,
            entity_id=unresolved[0],
            closed_h1=closed_h1,
            recorded_at_utc=now_utc,
        )
        actions.extend(_summary_record(row) for row in lifecycle)

    unresolved = ledger.unresolved_signal_entities()
    active_signal_exists = bool(unresolved)

    opportunities = completed_opportunities_v1_1(
        closed_h1,
        activated_at_utc=activated_at,
        now_utc=now_utc,
    )
    max_age = float(guardrails["max_data_age_seconds"])

    provider_error_seen = False
    for _, close_utc, age_seconds in opportunities:
        entity_id = cycle_entity_id_v1_1(market.source_symbol, close_utc)
        if cycle_processed_v1_1(ledger, entity_id):
            continue

        if age_seconds > max_age:
            missed = _append_missed_v1_1(
                ledger=ledger,
                source_symbol=market.source_symbol,
                source_bar_close_utc=close_utc,
                detected_at_utc=now_utc,
                age_seconds=age_seconds,
                max_age_seconds=max_age,
                reason="scheduler_gap_or_stale_at_discovery",
            )
            actions.append(_summary_record(missed))
            continue

        current_entry_bar = next(
            (
                bar
                for bar in h1_all
                if not bar.is_closed and bar.timestamp_utc == close_utc
            ),
            None,
        )
        if current_entry_bar is None:
            missed = _append_missed_v1_1(
                ledger=ledger,
                source_symbol=market.source_symbol,
                source_bar_close_utc=close_utc,
                detected_at_utc=now_utc,
                age_seconds=age_seconds,
                max_age_seconds=max_age,
                reason="next_h1_open_unavailable",
            )
            actions.append(_summary_record(missed))
            continue

        try:
            snapshot = build_feature_snapshot(
                h1_candles=h1_all,
                h4_candles=h4_all,
                point_size=market.point_size,
                inference_started_utc=now_utc,
                source_symbol=market.source_symbol,
                canonical_symbol=market.canonical_symbol,
            )
            snapshot_close = datetime.fromisoformat(
                str(snapshot.payload["source_bar_close_utc"]).replace("Z", "+00:00")
            )
            if snapshot_close != close_utc:
                raise ShadowRuntimeV11Error(
                    f"feature snapshot close {snapshot_close.isoformat()} does not "
                    f"match scheduled cycle {close_utc.isoformat()}"
                )
        except Exception as exc:
            error_record = _append_runtime_error_v1_1(
                ledger=ledger,
                source_symbol=market.source_symbol,
                source_bar_close_utc=close_utc,
                detected_at_utc=now_utc,
                stage="feature_snapshot",
                error=exc,
            )
            actions.append(_summary_record(error_record))
            continue

        result = process_inference_cycle_v1_1(
            ledger=ledger,
            adapter=adapter,
            feature_snapshot=snapshot,
            policy_text=policy_text,
            decision_schema=decision_schema,
            guardrails=guardrails,
            active_signal_exists=active_signal_exists,
            policy_sha256=policy_sha256,
            guardrails_sha256=guardrails_sha256,
            recorded_at_utc=now_utc,
        )

        if result.inference_record is not None:
            actions.append(_summary_record(result.inference_record))
        if result.terminal_record is not None:
            actions.append(_summary_record(result.terminal_record))

        if result.status == "ERROR":
            provider_error_seen = True
            continue

        if result.status == "APPROVED_PENDING_ENTRY":
            signal = append_signal_from_approved_inference(
                ledger=ledger,
                entity_id=result.entity_id,
                entry_bar=current_entry_bar,
                guardrails=guardrails,
                recorded_at_utc=now_utc,
            )
            actions.append(_summary_record(signal))
            active_signal_exists = True

    verification = ledger.verify()
    if not verification["valid"]:
        raise ShadowRuntimeV11Error(
            f"{market.source_symbol} ledger failed post-cycle verification"
        )

    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "market": market.source_symbol,
        "scanned_at_utc": now_utc.astimezone(timezone.utc).isoformat(),
        "actions": actions,
        "counts_by_type": ledger.counts_by_type(),
        "unresolved_signal_entities": ledger.unresolved_signal_entities(),
        "ledger_head_hash": ledger.head_hash(),
        "verification": verification,
        "provider_error_seen": provider_error_seen,
    }
