from __future__ import annotations

import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable

from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
    DATABASE_PATHS,
    DECISION_PROTOCOL_VERSION,
    MARKETS,
    RUNTIME_VERSION,
    CryptoPackageV13Error,
    validate_activation_payload_v1_3,
)
from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    CryptoExecutionContext,
)
from trading_signal_intelligence.ai_v1.crypto_engine_v1_3 import (
    process_crypto_inference_cycle,
)
from trading_signal_intelligence.ai_v1.crypto_signals_v1_3 import (
    append_crypto_signal_from_approved_inference,
)
from trading_signal_intelligence.ai_v1.features import (
    FeatureSnapshot,
    build_feature_snapshot,
    snapshot_sha256,
)
from trading_signal_intelligence.ai_v1.inference import ReasoningModelAdapter
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.signals import evaluate_signal
from trading_signal_intelligence.models import Candle


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


class CryptoRuntimeV13Error(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CryptoMarketRuntimeSpec:
    source_symbol: str
    canonical_symbol: str
    database_path: Path


def _iso_z(value: datetime) -> str:
    if value.tzinfo is None:
        raise CryptoRuntimeV13Error("timestamp must be timezone-aware")
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def market_specs_v1_3(repo_root: Path) -> dict[str, CryptoMarketRuntimeSpec]:
    from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
        crypto_market_specs,
    )

    specs = crypto_market_specs(repo_root)
    return {
        symbol: CryptoMarketRuntimeSpec(
            source_symbol=spec.source_symbol,
            canonical_symbol=spec.canonical_symbol,
            database_path=spec.database_path,
        )
        for symbol, spec in specs.items()
    }


def cycle_entity_id_v1_3(
    source_symbol: str,
    source_bar_close_utc: datetime,
) -> str:
    return f"{RUNTIME_VERSION}:{source_symbol}:{_iso_z(source_bar_close_utc)}"


def cycle_processed_v1_3(ledger: AILedger, entity_id: str) -> bool:
    return any(
        ledger.has(record_type=record_type, entity_id=entity_id)
        for record_type in PROCESSED_CYCLE_TYPES
    )


def completed_opportunities_v1_3(
    closed_h1: Iterable[Candle],
    *,
    activated_at_utc: datetime,
    now_utc: datetime,
) -> list[tuple[Candle, datetime, float]]:
    if activated_at_utc.tzinfo is None or now_utc.tzinfo is None:
        raise CryptoRuntimeV13Error(
            "activation and current timestamps must be timezone-aware"
        )
    activated = activated_at_utc.astimezone(UTC)
    now = now_utc.astimezone(UTC)
    opportunities: list[tuple[Candle, datetime, float]] = []
    for candle in closed_h1:
        if not candle.is_closed or candle.timeframe.upper() != "H1":
            continue
        close_utc = candle.timestamp_utc.astimezone(UTC) + timedelta(hours=1)
        if close_utc <= activated or close_utc > now:
            continue
        opportunities.append(
            (candle, close_utc, (now - close_utc).total_seconds())
        )
    opportunities.sort(key=lambda row: row[1])
    return opportunities


def _activation_payload(ledger: AILedger, symbol: str) -> dict[str, Any]:
    rows = ledger.records(record_type="ACTIVATION")
    if len(rows) != 1:
        raise CryptoRuntimeV13Error(
            f"{symbol} expected exactly one AI-v1.3 ACTIVATION"
        )
    records = ledger.records()
    if not records or records[0]["record_hash"] != rows[0]["record_hash"]:
        raise CryptoRuntimeV13Error(f"{symbol} ACTIVATION is not first")
    payload = rows[0]["payload"]
    try:
        validate_activation_payload_v1_3(payload)
    except CryptoPackageV13Error as exc:
        raise CryptoRuntimeV13Error(
            f"{symbol} activation payload invalid: {exc}"
        ) from exc
    if payload["market"] != symbol:
        raise CryptoRuntimeV13Error(f"{symbol} activation market mismatch")
    return payload


def build_crypto_feature_snapshot_v1_3(
    *,
    h1_all: list[Candle],
    h4_all: list[Candle],
    execution_context: CryptoExecutionContext,
    inference_started_utc: datetime,
    source_symbol: str,
    canonical_symbol: str,
) -> FeatureSnapshot:
    if execution_context.source_symbol != source_symbol:
        raise CryptoRuntimeV13Error("execution context symbol mismatch")
    if not h1_all:
        raise CryptoRuntimeV13Error("H1 history required")

    completed = [
        candle
        for candle in h1_all
        if candle.is_closed and candle.timeframe.upper() == "H1"
    ]
    if not completed:
        raise CryptoRuntimeV13Error("completed H1 history required")

    latest_completed = max(completed, key=lambda candle: candle.timestamp_utc)
    adapted_h1 = list(h1_all)
    for idx, candle in enumerate(adapted_h1):
        if (
            candle.timeframe.upper() == "H1"
            and candle.timestamp_utc == latest_completed.timestamp_utc
        ):
            adapted_h1[idx] = replace(
                candle,
                spread=execution_context.spread_price,
            )
            break
    else:
        raise CryptoRuntimeV13Error("latest completed H1 bar not found")

    base = build_feature_snapshot(
        h1_candles=adapted_h1,
        h4_candles=h4_all,
        point_size=1.0,
        inference_started_utc=inference_started_utc,
        source_symbol=source_symbol,
        canonical_symbol=canonical_symbol,
    )
    payload = dict(base.payload)
    payload["feature_schema_version"] = "AI-crypto-v1.0"
    return FeatureSnapshot(
        payload=payload,
        sha256=snapshot_sha256(payload),
    )


def _summary_record(record: dict[str, Any]) -> dict[str, Any]:
    payload = record.get("payload", {})
    result: dict[str, Any] = {
        "record_type": record["record_type"],
        "entity_id": record["entity_id"],
        "record_hash": record["record_hash"],
        "effective_at_utc": record["effective_at_utc"],
    }
    for key in (
        "reason",
        "decision",
        "total_combined_signal_net_r",
        "estimated_cost_r",
    ):
        if key in payload:
            result[key] = payload[key]
    return result


def _append_missed(
    *,
    ledger: AILedger,
    source_symbol: str,
    source_bar_close_utc: datetime,
    detected_at_utc: datetime,
    age_seconds: float,
    max_age_seconds: float,
    reason: str,
) -> dict[str, Any]:
    entity_id = cycle_entity_id_v1_3(source_symbol, source_bar_close_utc)
    return ledger.append(
        record_type="MISSED_INFERENCE",
        entity_id=entity_id,
        effective_at_utc=source_bar_close_utc,
        recorded_at_utc=detected_at_utc,
        payload={
            "runtime_version": RUNTIME_VERSION,
            "protocol_version": DECISION_PROTOCOL_VERSION,
            "source_symbol": source_symbol,
            "source_bar_close_utc": _iso_z(source_bar_close_utc),
            "detected_at_utc": detected_at_utc.astimezone(UTC).isoformat(),
            "data_age_seconds": float(age_seconds),
            "max_data_age_seconds": float(max_age_seconds),
            "reason": reason,
            "provider_call_made": False,
            "public_signal_exposure_enabled": False,
            "broker_execution_enabled": False,
        },
    )


def run_market_cycle_v1_3(
    *,
    ledger: AILedger,
    market: CryptoMarketRuntimeSpec,
    h1_all: list[Candle],
    h4_all: list[Candle],
    execution_context: CryptoExecutionContext,
    adapter: ReasoningModelAdapter,
    policy_text: str,
    decision_schema: dict[str, Any],
    guardrails: dict[str, Any],
    cost_policy: dict[str, Any],
    now_utc: datetime,
) -> dict[str, Any]:
    closed_h1 = [bar for bar in h1_all if bar.is_closed]
    closed_h4 = [bar for bar in h4_all if bar.is_closed]
    if not closed_h1 or not closed_h4:
        raise CryptoRuntimeV13Error(
            f"{market.source_symbol} requires completed H1/H4 history"
        )

    activation = _activation_payload(ledger, market.source_symbol)
    activated_at = datetime.fromisoformat(
        str(activation["activated_at_utc"])
    ).astimezone(UTC)

    actions: list[dict[str, Any]] = []

    unresolved = ledger.unresolved_signal_entities()
    if len(unresolved) > 1:
        raise CryptoRuntimeV13Error(
            f"{market.source_symbol} has multiple unresolved signals"
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
    if len(unresolved) > 1:
        raise CryptoRuntimeV13Error(
            f"{market.source_symbol} has multiple unresolved signals after lifecycle"
        )
    active_signal_exists = bool(unresolved)

    opportunities = completed_opportunities_v1_3(
        closed_h1,
        activated_at_utc=activated_at,
        now_utc=now_utc,
    )
    max_age = float(guardrails["max_data_age_seconds"])
    provider_error_seen = False

    for _, close_utc, age_seconds in opportunities:
        entity_id = cycle_entity_id_v1_3(market.source_symbol, close_utc)
        if cycle_processed_v1_3(ledger, entity_id):
            continue

        if age_seconds > max_age:
            missed = _append_missed(
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
                if not bar.is_closed
                and bar.timeframe.upper() == "H1"
                and bar.timestamp_utc.astimezone(UTC) == close_utc
            ),
            None,
        )
        if current_entry_bar is None:
            missed = _append_missed(
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

        snapshot = build_crypto_feature_snapshot_v1_3(
            h1_all=h1_all,
            h4_all=h4_all,
            execution_context=execution_context,
            inference_started_utc=now_utc,
            source_symbol=market.source_symbol,
            canonical_symbol=market.canonical_symbol,
        )
        snapshot_close = datetime.fromisoformat(
            str(snapshot.payload["source_bar_close_utc"])
        ).astimezone(UTC)
        if snapshot_close != close_utc:
            raise CryptoRuntimeV13Error(
                f"feature snapshot close {snapshot_close.isoformat()} does not "
                f"match cycle {close_utc.isoformat()}"
            )

        result = process_crypto_inference_cycle(
            ledger=ledger,
            adapter=adapter,
            feature_snapshot=snapshot,
            execution_context=execution_context,
            cost_policy=cost_policy,
            policy_text=policy_text,
            decision_schema=decision_schema,
            guardrails=guardrails,
            active_signal_exists=active_signal_exists,
            policy_sha256=str(activation["policy_sha256"]),
            guardrails_sha256=str(activation["guardrails_sha256"]),
            cost_policy_sha256=str(activation["cost_policy_sha256"]),
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
            signal = append_crypto_signal_from_approved_inference(
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
        raise CryptoRuntimeV13Error(
            f"{market.source_symbol} ledger failed post-cycle verification"
        )

    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "market": market.source_symbol,
        "scanned_at_utc": now_utc.astimezone(UTC).isoformat(),
        "actions": actions,
        "provider_error_seen": provider_error_seen,
        "verification": verification,
    }
