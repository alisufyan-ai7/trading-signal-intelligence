from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.local_env import load_project_env
from trading_signal_intelligence.ai_v1.mt5_rates_adapter_v1_1 import (
    read_synchronized_market_bars,
)
from trading_signal_intelligence.ai_v1.openai_responses import (
    OpenAIResponsesAdapter,
)
from trading_signal_intelligence.ai_v1.runtime_verifier_v1_1 import (
    verify_active_runtime_v1_1,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    H1_BARS,
    H4_BARS,
    MARKETS,
    cycle_entity_id_v1_1,
    cycle_processed_v1_1,
    market_specs_v1_1,
    run_market_cycle_v1_1,
)
from trading_signal_intelligence.connectors.mt5 import MT5Connector


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> dict[str, Any]:
    payload = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be object: {path}")
    return payload


def _iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _append_sync_outcome(
    *,
    ledger: AILedger,
    symbol: str,
    scan_started_utc: datetime,
    observed_at_utc: datetime,
    synchronization,
) -> dict[str, Any]:
    boundary = scan_started_utc.astimezone(timezone.utc).replace(
        minute=0,
        second=0,
        microsecond=0,
    )
    final_state = synchronization.final_state
    payload = {
        "protocol_version": "AI-v1.0",
        "runtime_version": "AI-v1.1",
        "source_symbol": symbol,
        "scan_started_utc": scan_started_utc.isoformat(),
        "detected_at_utc": observed_at_utc.isoformat(),
        "sync_status": synchronization.status,
        "sync_attempts": synchronization.attempts,
        "sync_waited_seconds": synchronization.waited_seconds,
        "latest_tick_utc": (
            _iso_z(final_state.latest_tick_utc)
            if final_state.latest_tick_utc is not None
            else None
        ),
        "newest_h1_open_utc": (
            _iso_z(final_state.newest_h1_open_utc)
            if final_state.newest_h1_open_utc is not None
            else None
        ),
        "newest_h4_open_utc": (
            _iso_z(final_state.newest_h4_open_utc)
            if final_state.newest_h4_open_utc is not None
            else None
        ),
        "expected_h1_open_utc": (
            _iso_z(synchronization.expected_h1_open_utc)
            if synchronization.expected_h1_open_utc is not None
            else None
        ),
        "expected_h4_open_utc": (
            _iso_z(synchronization.expected_h4_open_utc)
            if synchronization.expected_h4_open_utc is not None
            else None
        ),
        "provider_call_made": False,
        "broker_execution_enabled": False,
    }

    if synchronization.status == "RATES_NOT_SYNCHRONIZED":
        entity_id = cycle_entity_id_v1_1(symbol, boundary)
        if cycle_processed_v1_1(ledger, entity_id):
            return {
                "record_type": "SKIPPED_ALREADY_PROCESSED",
                "entity_id": entity_id,
                "effective_at_utc": _iso_z(boundary),
                "reason": "rates_not_synchronized",
            }
        record = ledger.append(
            record_type="MISSED_INFERENCE",
            entity_id=entity_id,
            effective_at_utc=boundary,
            recorded_at_utc=observed_at_utc,
            payload={
                **payload,
                "source_bar_close_utc": _iso_z(boundary),
                "data_age_seconds": (
                    observed_at_utc.astimezone(timezone.utc) - boundary
                ).total_seconds(),
                "max_data_age_seconds": 300.0,
                "reason": "rates_not_synchronized",
            },
        )
        return {
            "record_type": record["record_type"],
            "entity_id": record["entity_id"],
            "record_hash": record["record_hash"],
            "effective_at_utc": record["effective_at_utc"],
            "reason": "rates_not_synchronized",
        }

    # A missing current-hour tick is a fail-closed missed opportunity, not a
    # new ledger record type. Reuse MISSED_INFERENCE so the frozen shared
    # AI-v1.0 ledger implementation remains unchanged and the cycle can never
    # be backfilled later if a tick appears afterward.
    entity_id = cycle_entity_id_v1_1(symbol, boundary)
    if cycle_processed_v1_1(ledger, entity_id):
        return {
            "record_type": "SKIPPED_ALREADY_PROCESSED",
            "entity_id": entity_id,
            "effective_at_utc": _iso_z(boundary),
            "reason": "no_current_h1_tick",
        }
    record = ledger.append(
        record_type="MISSED_INFERENCE",
        entity_id=entity_id,
        effective_at_utc=boundary,
        recorded_at_utc=observed_at_utc,
        payload={
            **payload,
            "source_bar_close_utc": _iso_z(boundary),
            "data_age_seconds": (
                observed_at_utc.astimezone(timezone.utc) - boundary
            ).total_seconds(),
            "max_data_age_seconds": 300.0,
            "reason": "no_current_h1_tick",
        },
    )
    return {
        "record_type": record["record_type"],
        "entity_id": record["entity_id"],
        "record_hash": record["record_hash"],
        "effective_at_utc": record["effective_at_utc"],
        "reason": "no_current_h1_tick",
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run one activated AI-v1.1 shadow scan across XAUUSD, USTEC and "
            "US30. Broker execution remains disabled."
        )
    )
    parser.add_argument("--terminal-path", default=None)
    args = parser.parse_args()

    # This verifies a committed v1.1 activation and all three ledgers before
    # any MT5/OpenAI object is created.
    readiness = verify_active_runtime_v1_1(
        ROOT,
        require_activation_only=False,
        include_scheduler=False,
        verify_upstream=True,
    )

    load_project_env(ROOT / ".env")

    provider_config = load_json("config/ai_v1_provider.json")
    provider_schema = load_json("config/ai_v1_openai_response_schema.json")
    decision_schema = load_json("config/ai_v1_decision_schema.json")
    guardrails = load_json("config/ai_v1_guardrails.json")
    policy_text = (ROOT / "config" / "ai_v1_policy.txt").read_text(
        encoding="utf-8"
    )

    if guardrails.get("broker_execution_enabled") is not False:
        raise RuntimeError("broker execution must remain disabled")

    adapter = OpenAIResponsesAdapter.from_environment(
        config=provider_config,
        provider_response_schema=provider_schema,
    )
    specs = market_specs_v1_1(ROOT)
    connector = MT5Connector(source_name="exness_mt5_demo")

    outputs: dict[str, Any] = {}
    failures: dict[str, str] = {}
    provider_error_seen = False

    connector.connect(args.terminal_path)
    try:
        for symbol in MARKETS:
            market = specs[symbol]
            ledger = AILedger(market.database_path)
            scan_started = datetime.now(timezone.utc)
            try:
                synchronized = read_synchronized_market_bars(
                    connector=connector,
                    source_symbol=market.source_symbol,
                    canonical_symbol=market.canonical_symbol,
                    scan_started_utc=scan_started,
                    h1_count=H1_BARS,
                    h4_count=H4_BARS,
                )

                if not synchronized.synchronization.ready:
                    observed = datetime.now(timezone.utc)
                    sync_action = _append_sync_outcome(
                        ledger=ledger,
                        symbol=symbol,
                        scan_started_utc=scan_started,
                        observed_at_utc=observed,
                        synchronization=synchronized.synchronization,
                    )
                    verification = ledger.verify()
                    if not verification["valid"]:
                        raise RuntimeError(
                            f"{symbol} ledger invalid after sync outcome"
                        )
                    outputs[symbol] = {
                        "runtime_version": "AI-v1.1",
                        "decision_protocol_version": "AI-v1.0",
                        "market": symbol,
                        "scanned_at_utc": observed.isoformat(),
                        "sync_status": synchronized.synchronization.status,
                        "sync_attempts": synchronized.synchronization.attempts,
                        "sync_waited_seconds": (
                            synchronized.synchronization.waited_seconds
                        ),
                        "actions": [sync_action],
                        "provider_error_seen": False,
                        "verification": verification,
                    }
                    continue

                now = datetime.now(timezone.utc)
                result = run_market_cycle_v1_1(
                    ledger=ledger,
                    market=market,
                    h1_all=synchronized.h1_all,
                    h4_all=synchronized.h4_all,
                    adapter=adapter,
                    policy_text=policy_text,
                    decision_schema=decision_schema,
                    guardrails=guardrails,
                    now_utc=now,
                )
                result["sync_status"] = synchronized.synchronization.status
                result["sync_attempts"] = synchronized.synchronization.attempts
                result["sync_waited_seconds"] = (
                    synchronized.synchronization.waited_seconds
                )
                outputs[symbol] = result
                provider_error_seen = (
                    provider_error_seen or bool(result["provider_error_seen"])
                )
            except Exception as exc:
                failures[symbol] = (
                    f"{type(exc).__name__}: {str(exc)[:1000]}"
                )
    finally:
        connector.disconnect()

    final_readiness = verify_active_runtime_v1_1(
        ROOT,
        require_activation_only=False,
        include_scheduler=False,
        verify_upstream=True,
    )

    summary = {
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "run_mode": "SHADOW_ONLY",
        "scanned_markets": list(MARKETS),
        "broker_execution_enabled": False,
        "activation_anchor": readiness["anchor_file"],
        "pre_run_verification": readiness,
        "market_results": outputs,
        "failures": failures,
        "post_run_verification": final_readiness,
    }
    print(json.dumps(summary, indent=2, default=str))

    if failures:
        raise SystemExit(2)
    if provider_error_seen:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
