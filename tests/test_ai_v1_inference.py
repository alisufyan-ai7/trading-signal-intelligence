from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.inference import run_inference


@dataclass
class FakeAdapter:
    provider: str = "test-provider"
    model_id: str = "test-model"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"temperature": 0}

    def infer(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
        decision_schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        assert policy_text
        assert feature_snapshot["feature_schema_version"] == "AI-v1.0"
        assert decision_schema["title"]
        return (
            {
                "protocol_version": "AI-v1.0",
                "decision": "NO_TRADE",
                "raw_confidence": 40,
                "regime": "MIXED",
                "stop_atr": None,
                "tp1_r": None,
                "tp2_r": None,
                "rationale": "Evidence is mixed.",
                "supporting_factors": [],
                "risk_factors": ["mixed_regime"],
            },
            {
                "request_id": "req-test",
                "api_key": "must-not-be-retained",
                "usage": {"input_tokens": 10, "output_tokens": 10},
            },
        )


def test_provider_neutral_inference_sanitizes_metadata() -> None:
    result = run_inference(
        adapter=FakeAdapter(),
        feature_snapshot=FeatureSnapshot(
            payload={"feature_schema_version": "AI-v1.0"},
            sha256="a" * 64,
        ),
        policy_text="policy",
        decision_schema={"title": "schema"},
    )

    assert result.decision["decision"] == "NO_TRADE"
    assert result.provider == "test-provider"
    assert result.model_parameter_fingerprint
    assert result.metadata["request_id"] == "req-test"
    assert "api_key" not in result.metadata
