from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
    COST_POLICY,
    GUARDRAILS,
    MARKETS,
)
from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    CryptoExecutionContext,
    load_crypto_cost_policy,
)
from trading_signal_intelligence.ai_v1.crypto_runtime_v1_3 import (
    H1_BARS,
    H4_BARS,
    market_specs_v1_3,
    run_market_cycle_v1_3,
    validate_batch_freeze_v1_3,
)
from trading_signal_intelligence.ai_v1.crypto_runtime_verifier_v1_3 import (
    verify_active_runtime_v1_3,
)
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.local_env import load_project_env
from trading_signal_intelligence.ai_v1.openai_responses import (
    OpenAIResponsesAdapter,
)
from trading_signal_intelligence.connectors.binance import BinanceSpotConnector


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> dict[str, Any]:
    payload = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be object: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run one activated AI-v1.3 BTC/ETH/SOL crypto shadow scan. "
            "All Binance snapshots are frozen before the first provider call. "
            "Public signal exposure and broker/exchange execution remain disabled."
        )
    )
    parser.parse_args()

    pre_run = verify_active_runtime_v1_3(
        ROOT,
        require_activation_only=False,
        include_scheduler=False,
        verify_upstream=True,
    )

    guardrails = load_json(GUARDRAILS)
    cost_policy = load_crypto_cost_policy(ROOT / COST_POLICY)
    decision_schema = load_json("config/ai_v1_decision_schema.json")
    provider_config = load_json("config/ai_v1_provider.json")
    provider_schema = load_json("config/ai_v1_openai_response_schema.json")
    policy_text = (ROOT / "config" / "ai_v1_policy.txt").read_text(
        encoding="utf-8"
    )

    if guardrails.get("broker_execution_enabled") is not False:
        raise RuntimeError("AI-v1.3 broker execution must remain disabled")
    if guardrails.get("public_signal_exposure_enabled") is not False:
        raise RuntimeError("AI-v1.3 public signal exposure must remain disabled")

    specs = market_specs_v1_3(ROOT)
    connector = BinanceSpotConnector()

    batch_inputs: dict[
        str,
        tuple[list, list, CryptoExecutionContext],
    ] = {}
    collection_errors: dict[str, str] = {}

    # K4/K5 runtime invariant: collect every market snapshot and quote before
    # any OpenAI adapter is instantiated or provider call can occur.
    for symbol in MARKETS:
        spec = specs[symbol]
        try:
            h1_all = connector.klines(
                spec.source_symbol,
                spec.canonical_symbol,
                "H1",
                limit=H1_BARS + 1,
            )
            h4_all = connector.klines(
                spec.source_symbol,
                spec.canonical_symbol,
                "H4",
                limit=H4_BARS + 1,
            )
            quote = connector.book_ticker(
                spec.source_symbol,
                spec.canonical_symbol,
            )
            if quote.bid is None or quote.ask is None:
                raise RuntimeError(f"{symbol} Binance quote lacks bid/ask")
            context = CryptoExecutionContext(
                source=quote.source,
                source_symbol=quote.source_symbol,
                observed_at_utc=quote.timestamp_utc,
                best_bid=quote.bid,
                best_ask=quote.ask,
            )
            batch_inputs[symbol] = (h1_all, h4_all, context)
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            collection_errors[symbol] = f"{type(exc).__name__}: {str(exc)[:1000]}"

    if collection_errors:
        print(
            json.dumps(
                {
                    "runtime_version": "AI-v1.3",
                    "run_mode": "PARALLEL_SHADOW_ONLY",
                    "batch_collection": "FAIL_CLOSED_BEFORE_PROVIDER",
                    "collection_errors": collection_errors,
                    "provider_call_made": False,
                    "ledger_write_performed": False,
                    "public_signal_exposure_enabled": False,
                    "broker_execution_enabled": False,
                },
                indent=2,
                allow_nan=False,
            )
        )
        raise SystemExit(2)

    batch_frozen_at = datetime.now(UTC)
    batch_report = validate_batch_freeze_v1_3(
        batch_inputs,
        batch_frozen_at_utc=batch_frozen_at,
        max_data_age_seconds=float(guardrails["max_data_age_seconds"]),
    )

    load_project_env(ROOT / ".env")
    adapter = OpenAIResponsesAdapter.from_environment(
        config=provider_config,
        provider_response_schema=provider_schema,
    )

    outputs: dict[str, Any] = {}
    failures: dict[str, str] = {}
    provider_error_seen = False

    for symbol in MARKETS:
        spec = specs[symbol]
        h1_all, h4_all, context = batch_inputs[symbol]
        ledger = AILedger(spec.database_path)
        try:
            result = run_market_cycle_v1_3(
                ledger=ledger,
                market=spec,
                h1_all=h1_all,
                h4_all=h4_all,
                execution_context=context,
                adapter=adapter,
                policy_text=policy_text,
                decision_schema=decision_schema,
                guardrails=guardrails,
                cost_policy=cost_policy,
                now_utc=datetime.now(UTC),
            )
            outputs[symbol] = result
            provider_error_seen = (
                provider_error_seen or bool(result["provider_error_seen"])
            )
        except Exception as exc:  # noqa: BLE001
            failures[symbol] = f"{type(exc).__name__}: {str(exc)[:1000]}"

    post_run = verify_active_runtime_v1_3(
        ROOT,
        require_activation_only=False,
        include_scheduler=False,
        verify_upstream=True,
    )

    summary = {
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "program_id": "crypto-expansion-1",
        "run_mode": "PARALLEL_SHADOW_ONLY",
        "batch_frozen_before_provider_calls": True,
        "batch_readiness": batch_report,
        "scanned_markets": list(MARKETS),
        "public_signal_exposure_enabled": False,
        "broker_execution_enabled": False,
        "pre_run_verification": pre_run,
        "market_results": outputs,
        "failures": failures,
        "post_run_verification": post_run,
    }
    print(json.dumps(summary, indent=2, default=str, allow_nan=False))

    if failures:
        raise SystemExit(2)
    if provider_error_seen:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
