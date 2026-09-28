from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

from trading_signal_intelligence.ai_v1.activation import artifact_hashes
from trading_signal_intelligence.ai_v1.features import FeatureSnapshot, build_feature_snapshot
from trading_signal_intelligence.ai_v1.inference import ReasoningModelAdapter
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.engine import process_inference_cycle
from trading_signal_intelligence.ai_v1.signals import (
    append_signal_from_approved_inference,
    evaluate_signal,
)
from trading_signal_intelligence.models import Candle


MARKETS = ("XAUUSD", "USTEC", "US30")
DATABASE_PATHS = {
    "XAUUSD": "data/ai_v1_xauusd.sqlite",
    "USTEC": "data/ai_v1_ustec.sqlite",
    "US30": "data/ai_v1_us30.sqlite",
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


class ShadowRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class MarketSpec:
    source_symbol: str
    canonical_symbol: str
    point_size: float
    database_path: Path


def _iso_z(value: datetime | pd.Timestamp) -> str:
    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise ShadowRuntimeError("timestamp must be timezone-aware")
    return ts.tz_convert("UTC").isoformat().replace("+00:00", "Z")


def market_specs(repo_root: Path) -> dict[str, MarketSpec]:
    registry = json.loads(
        (repo_root / "config" / "instruments.json").read_text(encoding="utf-8")
    )
    by_symbol: dict[str, MarketSpec] = {}
    for instrument in registry["instruments"]:
        cfg = instrument.get("sources", {}).get(SOURCE_NAME)
        if not cfg:
            continue
        symbol = str(cfg.get("symbol"))
        if symbol not in MARKETS:
            continue
        digits = int(cfg["digits"])
        by_symbol[symbol] = MarketSpec(
            source_symbol=symbol,
            canonical_symbol=str(instrument["canonical"]),
            point_size=10.0 ** (-digits),
            database_path=repo_root / DATABASE_PATHS[symbol],
        )

    missing = [symbol for symbol in MARKETS if symbol not in by_symbol]
    if missing:
        raise ShadowRuntimeError(f"missing registry entries: {missing}")
    return by_symbol


def cycle_entity_id(source_symbol: str, source_bar_close_utc: datetime) -> str:
    return f"AI-v1.0:{source_symbol}:{_iso_z(source_bar_close_utc)}"


def cycle_processed(ledger: AILedger, entity_id: str) -> bool:
    return any(
        ledger.has(record_type=record_type, entity_id=entity_id)
        for record_type in PROCESSED_CYCLE_TYPES
    )


def completed_opportunities(
    closed_h1: Iterable[Candle],
    *,
    activated_at_utc: datetime,
    now_utc: datetime,
) -> list[tuple[Candle, datetime, float]]:
    if activated_at_utc.tzinfo is None or now_utc.tzinfo is None:
        raise ShadowRuntimeError("activation and current timestamps must be timezone-aware")
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


def _load_anchor(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("protocol_version") != "AI-v1.0":
        raise ShadowRuntimeError(f"unexpected protocol in anchor: {path}")
    if payload.get("broker_execution_enabled") is not False:
        raise ShadowRuntimeError(f"broker execution not disabled in anchor: {path}")
    return payload


def discover_active_anchor(repo_root: Path) -> tuple[Path, dict[str, Any]]:
    candidates = sorted(
        (
            path
            for path in (repo_root / "research" / "forward").glob(
                "AI-v1-activation-*.json"
            )
            if "SUPERSEDED" not in path.name.upper()
        ),
        reverse=True,
    )
    if not candidates:
        raise ShadowRuntimeError("no AI-v1 activation anchor found")

    specs = market_specs(repo_root)
    for path in candidates:
        try:
            anchor = _load_anchor(path)
        except Exception:
            continue

        markets = anchor.get("markets")
        if not isinstance(markets, dict):
            continue

        matched = True
        for symbol in MARKETS:
            db_path = specs[symbol].database_path
            if not db_path.exists() or symbol not in markets:
                matched = False
                break
            ledger = AILedger(db_path)
            activations = ledger.records(record_type="ACTIVATION")
            if len(activations) != 1:
                matched = False
                break
            if activations[0]["record_hash"] != markets[symbol].get("record_hash"):
                matched = False
                break

        if matched:
            return path, anchor

    raise ShadowRuntimeError(
        "no committed AI-v1 activation anchor matches the local active ledgers"
    )


def _require_anchor_in_upstream(repo_root: Path, anchor_path: Path) -> str:
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
        raise ShadowRuntimeError(
            "activation anchor is not verifiably present in the configured upstream branch"
        ) from exc

    local_bytes = anchor_path.read_bytes()
    if hashlib.sha256(local_bytes).digest() != hashlib.sha256(upstream_bytes).digest():
        raise ShadowRuntimeError(
            "local activation anchor differs from the copy in the upstream branch"
        )
    return upstream


def verify_active_runtime(
    repo_root: Path,
    *,
    require_activation_only: bool = False,
) -> dict[str, Any]:
    anchor_path, anchor = discover_active_anchor(repo_root)
    upstream_commit = _require_anchor_in_upstream(repo_root, anchor_path)

    frozen_now = artifact_hashes(repo_root)
    anchored_hashes = anchor.get("artifact_hashes", {})
    hash_mismatches: dict[str, dict[str, str | None]] = {}
    for name, expected in anchored_hashes.items():
        actual = frozen_now.get(name)
        if actual != expected:
            hash_mismatches[name] = {"expected": expected, "actual": actual}
    if hash_mismatches:
        raise ShadowRuntimeError(
            f"frozen runtime artifact mismatch: {hash_mismatches}"
        )

    specs = market_specs(repo_root)
    markets_summary: dict[str, Any] = {}
    for symbol in MARKETS:
        ledger = AILedger(specs[symbol].database_path)
        verification = ledger.verify()
        if not verification["valid"]:
            raise ShadowRuntimeError(
                f"{symbol} ledger verification failed: {verification}"
            )

        records = ledger.records()
        activations = [
            row for row in records if row["record_type"] == "ACTIVATION"
        ]
        if len(activations) != 1:
            raise ShadowRuntimeError(
                f"{symbol} expected exactly one ACTIVATION; found {len(activations)}"
            )
        activation = activations[0]
        anchored = anchor["markets"][symbol]
        if activation["record_hash"] != anchored["record_hash"]:
            raise ShadowRuntimeError(f"{symbol} activation record hash mismatch")
        if activation["payload"] != anchored["payload"]:
            raise ShadowRuntimeError(f"{symbol} activation payload mismatch")
        if records[0]["record_hash"] != activation["record_hash"]:
            raise ShadowRuntimeError(f"{symbol} ACTIVATION is not first ledger record")
        if require_activation_only and len(records) != 1:
            raise ShadowRuntimeError(
                f"{symbol} has {len(records)} records before first scheduler run"
            )

        markets_summary[symbol] = {
            "records": len(records),
            "activation_record_hash": activation["record_hash"],
            "current_head_hash": ledger.head_hash(),
            "verification": verification,
        }

    return {
        "valid": True,
        "anchor_file": str(anchor_path.relative_to(repo_root)),
        "anchor_upstream_commit": upstream_commit,
        "activated_at_utc": anchor["activated_at_utc"],
        "provider_call_made_at_activation": anchor["provider_call_made"],
        "broker_execution_enabled": anchor["broker_execution_enabled"],
        "markets": markets_summary,
    }


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
    entity_id = cycle_entity_id(source_symbol, source_bar_close_utc)
    return ledger.append(
        record_type="MISSED_INFERENCE",
        entity_id=entity_id,
        effective_at_utc=source_bar_close_utc,
        recorded_at_utc=detected_at_utc,
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": source_symbol,
            "source_bar_close_utc": _iso_z(source_bar_close_utc),
            "detected_at_utc": detected_at_utc.astimezone(timezone.utc).isoformat(),
            "data_age_seconds": float(age_seconds),
            "max_data_age_seconds": float(max_age_seconds),
            "reason": reason,
            "provider_call_made": False,
        },
    )


def _append_runtime_error(
    *,
    ledger: AILedger,
    source_symbol: str,
    source_bar_close_utc: datetime,
    detected_at_utc: datetime,
    stage: str,
    error: Exception,
) -> dict[str, Any]:
    entity_id = cycle_entity_id(source_symbol, source_bar_close_utc)
    return ledger.append(
        record_type="ERROR",
        entity_id=entity_id,
        effective_at_utc=source_bar_close_utc,
        recorded_at_utc=detected_at_utc,
        payload={
            "protocol_version": "AI-v1.0",
            "source_symbol": source_symbol,
            "source_bar_close_utc": _iso_z(source_bar_close_utc),
            "stage": stage,
            "error_class": type(error).__name__,
            "sanitized_message": str(error)[:500],
            "broker_execution_enabled": False,
        },
    )


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


def run_market_cycle(
    *,
    ledger: AILedger,
    market: MarketSpec,
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
        raise ShadowRuntimeError(
            f"{market.source_symbol} requires completed H1 and H4 history"
        )

    activation_rows = ledger.records(record_type="ACTIVATION")
    if len(activation_rows) != 1:
        raise ShadowRuntimeError(
            f"{market.source_symbol} expected one activation record"
        )
    activation_payload = activation_rows[0]["payload"]
    activated_at = datetime.fromisoformat(
        str(activation_payload["activated_at_utc"]).replace("Z", "+00:00")
    )
    policy_sha256 = str(activation_payload["policy_sha256"])
    guardrails_sha256 = str(activation_payload["guardrails_sha256"])

    actions: list[dict[str, Any]] = []

    unresolved = ledger.unresolved_signal_entities()
    if len(unresolved) > 1:
        raise ShadowRuntimeError(
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
    if len(unresolved) > 1:
        raise ShadowRuntimeError(
            f"{market.source_symbol} has multiple unresolved signals after evaluation"
        )
    active_signal_exists = bool(unresolved)

    opportunities = completed_opportunities(
        closed_h1,
        activated_at_utc=activated_at,
        now_utc=now_utc,
    )
    max_age = float(guardrails["max_data_age_seconds"])

    provider_error_seen = False
    for _, close_utc, age_seconds in opportunities:
        entity_id = cycle_entity_id(market.source_symbol, close_utc)
        if cycle_processed(ledger, entity_id):
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
                if not bar.is_closed and bar.timestamp_utc == close_utc
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
                raise ShadowRuntimeError(
                    f"feature snapshot close {snapshot_close.isoformat()} does not "
                    f"match scheduled cycle {close_utc.isoformat()}"
                )
        except Exception as exc:
            error_record = _append_runtime_error(
                ledger=ledger,
                source_symbol=market.source_symbol,
                source_bar_close_utc=close_utc,
                detected_at_utc=now_utc,
                stage="feature_snapshot",
                error=exc,
            )
            actions.append(_summary_record(error_record))
            continue

        result = process_inference_cycle(
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
        raise ShadowRuntimeError(
            f"{market.source_symbol} ledger failed post-cycle verification"
        )

    return {
        "market": market.source_symbol,
        "scanned_at_utc": now_utc.astimezone(timezone.utc).isoformat(),
        "actions": actions,
        "counts_by_type": ledger.counts_by_type(),
        "unresolved_signal_entities": ledger.unresolved_signal_entities(),
        "ledger_head_hash": ledger.head_hash(),
        "verification": verification,
        "provider_error_seen": provider_error_seen,
    }
