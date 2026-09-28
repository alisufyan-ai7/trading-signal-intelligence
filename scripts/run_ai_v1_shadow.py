from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.local_env import load_project_env
from trading_signal_intelligence.ai_v1.openai_responses import OpenAIResponsesAdapter
from trading_signal_intelligence.ai_v1.shadow_runtime import (
    H1_BARS,
    H4_BARS,
    MARKETS,
    market_specs,
    run_market_cycle,
    verify_active_runtime,
)
from trading_signal_intelligence.connectors.mt5 import MT5Connector


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> dict[str, Any]:
    payload = json.loads((ROOT / path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"JSON root must be object: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Run one activated AI-v1 shadow scan across XAUUSD, USTEC and US30. "
            "No broker execution is performed."
        )
    )
    parser.add_argument("--terminal-path", default=None)
    args = parser.parse_args()

    load_project_env(ROOT / ".env")

    readiness = verify_active_runtime(ROOT, require_activation_only=False)

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

    specs = market_specs(ROOT)
    connector = MT5Connector(source_name="exness_mt5_demo")

    outputs: dict[str, Any] = {}
    failures: dict[str, str] = {}
    provider_error_seen = False

    connector.connect(args.terminal_path)
    try:
        for symbol in MARKETS:
            market = specs[symbol]
            try:
                h1_all = connector.bars_from_pos(
                    market.source_symbol,
                    market.canonical_symbol,
                    "H1",
                    0,
                    H1_BARS,
                    current_bar_is_closed=False,
                )
                h4_all = connector.bars_from_pos(
                    market.source_symbol,
                    market.canonical_symbol,
                    "H4",
                    0,
                    H4_BARS,
                    current_bar_is_closed=False,
                )
                now = datetime.now(timezone.utc)
                ledger = AILedger(market.database_path)
                result = run_market_cycle(
                    ledger=ledger,
                    market=market,
                    h1_all=h1_all,
                    h4_all=h4_all,
                    adapter=adapter,
                    policy_text=policy_text,
                    decision_schema=decision_schema,
                    guardrails=guardrails,
                    now_utc=now,
                )
                outputs[symbol] = result
                provider_error_seen = (
                    provider_error_seen or bool(result["provider_error_seen"])
                )
            except Exception as exc:
                failures[symbol] = f"{type(exc).__name__}: {str(exc)[:1000]}"
    finally:
        connector.disconnect()

    final_readiness = verify_active_runtime(ROOT, require_activation_only=False)

    summary = {
        "protocol_version": "AI-v1.0",
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
