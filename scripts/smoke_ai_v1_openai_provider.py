from __future__ import annotations

import json
from pathlib import Path

from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.inference import run_inference
from trading_signal_intelligence.ai_v1.local_env import load_project_env
from trading_signal_intelligence.ai_v1.openai_responses import OpenAIResponsesAdapter


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def main() -> None:
    load_project_env(ROOT / ".env")
    config = load_json("config/ai_v1_provider.json")
    provider_schema = load_json("config/ai_v1_openai_response_schema.json")
    decision_schema = load_json("config/ai_v1_decision_schema.json")
    policy = (ROOT / "config" / "ai_v1_policy.txt").read_text(encoding="utf-8")

    # Synthetic fixture only: deliberately not a real market-state snapshot and
    # never written to an AI-v1 performance ledger.
    synthetic = FeatureSnapshot(
        payload={
            "feature_schema_version": "AI-v1.0",
            "source_symbol": "XAUUSD",
            "canonical_symbol": "XAU/USD",
            "source_bar_open_utc": "2000-01-01T00:00:00Z",
            "source_bar_close_utc": "2000-01-01T01:00:00Z",
            "inference_started_utc": "2000-01-01T01:01:00Z",
            "data_age_seconds": 60.0,
            "close_h1": 100.0,
            "ret_1": 0.0,
            "ret_4": 0.0,
            "ret_12": 0.0,
            "ret_24": 0.0,
            "atr_14": 1.0,
            "atr_percentile_252": 0.5,
            "price_vs_ema20_h1_atr": 0.0,
            "price_vs_ema50_h1_atr": 0.0,
            "ema20_slope_h1": 0.0,
            "ema50_slope_h1": 0.0,
            "price_vs_ema20_h4_atr": 0.0,
            "price_vs_ema50_h4_atr": 0.0,
            "ema20_slope_h4": 0.0,
            "ema50_slope_h4": 0.0,
            "rsi_14": 50.0,
            "range_position_20": 0.5,
            "distance_prior20_high_atr": 1.0,
            "distance_prior20_low_atr": 1.0,
            "distance_previous_day_high_atr": 1.0,
            "distance_previous_day_low_atr": 1.0,
            "previous_day_utc": "1999-12-31",
            "tr_expansion_ratio": 1.0,
            "volume_z_20": 0.0,
            "return_sign_agreement": "MIXED",
            "volatility_regime": "NORMAL",
            "trend_regime": "RANGE",
            "session_bucket": "ASIA",
            "utc_hour": 1,
            "utc_day_of_week": 5,
            "spread_price": 0.1,
            "spread_atr_fraction": 0.1,
            "quality_flags": ["SYNTHETIC_PROVIDER_SMOKE"],
        },
        sha256="synthetic-provider-smoke-not-performance-evidence",
    )

    adapter = OpenAIResponsesAdapter.from_environment(
        config=config,
        provider_response_schema=provider_schema,
    )
    result = run_inference(
        adapter=adapter,
        feature_snapshot=synthetic,
        policy_text=policy,
        decision_schema=decision_schema,
    )

    print(
        json.dumps(
            {
                "provider_smoke": "PASS",
                "synthetic_nonperformance_input": True,
                "performance_ledger_write": False,
                "provider": result.provider,
                "model_id": result.model_id,
                "model_parameter_fingerprint": result.model_parameter_fingerprint,
                "decision_contract_valid": True,
                "decision": result.decision,
                "metadata": result.metadata,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
