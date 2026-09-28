from __future__ import annotations

import json
from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.activation import (
    ARTIFACT_PATHS,
    ActivationError,
    validate_activation_payload,
)
from trading_signal_intelligence.ai_v1.features import canonical_json
from trading_signal_intelligence.ai_v1.inference import parameter_fingerprint
from trading_signal_intelligence.ai_v1.openai_responses import OpenAIResponsesAdapter


ROOT = Path(__file__).resolve().parents[1]


def load_json(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def test_frozen_provider_config_uses_exact_snapshot() -> None:
    config = load_json("config/ai_v1_provider.json")
    schema = load_json("config/ai_v1_openai_response_schema.json")
    adapter = OpenAIResponsesAdapter(
        config=config,
        provider_response_schema=schema,
        api_key="not-used",
    )

    assert adapter.provider == "openai"
    assert adapter.model_id == "gpt-5.4-2026-03-05"
    assert config["reasoning_effort"] == "medium"
    assert config["service_tier"] == "default"
    assert config["store"] is False
    assert config["truncation"] == "disabled"
    assert config["max_output_tokens"] == 8192
    assert config["tools"] == []
    assert config["temperature"] is None
    assert config["top_p"] is None

    fingerprint = parameter_fingerprint(
        provider=adapter.provider,
        model_id=adapter.model_id,
        parameters=adapter.parameters,
    )
    assert len(fingerprint) == 64


def test_openai_provider_schema_has_no_unsupported_composition() -> None:
    schema = load_json("config/ai_v1_openai_response_schema.json")
    serialized = canonical_json(schema)

    for keyword in ('"allOf"', '"if"', '"then"', '"else"'):
        assert keyword not in serialized
    assert schema["additionalProperties"] is False
    assert set(schema["required"]) == set(schema["properties"])


def activation_payload() -> dict:
    digest = "a" * 64
    return {
        "protocol_version": "AI-v1.0",
        "market": "XAUUSD",
        "activated_at_utc": "2026-09-28T10:00:00+00:00",
        "repository_commit_sha": "b" * 40,
        "activation_bundle_sha256": digest,
        "provider": "openai",
        "model_id": "gpt-5.4-2026-03-05",
        "model_parameter_fingerprint": digest,
        "policy_sha256": digest,
        "feature_definitions_sha256": digest,
        "feature_schema_sha256": digest,
        "decision_schema_sha256": digest,
        "guardrails_sha256": digest,
        "feature_builder_source_sha256": digest,
        "inference_adapter_source_sha256": digest,
        "ai_ledger_source_sha256": digest,
        "lifecycle_evaluator_source_sha256": digest,
        "cost_policy_fingerprint": digest,
        "broker_execution_enabled": False,
    }


def test_activation_contract_rejects_wrong_model_or_execution() -> None:
    payload = activation_payload()
    validate_activation_payload(payload)

    wrong_model = dict(payload)
    wrong_model["model_id"] = "moving-alias"
    with pytest.raises(ActivationError):
        validate_activation_payload(wrong_model)

    execution = dict(payload)
    execution["broker_execution_enabled"] = True
    with pytest.raises(ActivationError):
        validate_activation_payload(execution)


def test_activation_bundle_binds_shadow_runtime_and_task_files() -> None:
    assert ARTIFACT_PATHS["shadow_runtime_source"].endswith("shadow_runtime.py")
    assert ARTIFACT_PATHS["shadow_runner_script"].endswith("run_ai_v1_shadow.py")
    assert ARTIFACT_PATHS["shadow_task_runner_script"].endswith(
        "run_ai_v1_shadow_task.cmd"
    )
    assert ARTIFACT_PATHS["shadow_task_installer_script"].endswith(
        "install_ai_v1_shadow_task.ps1"
    )
    for relative in (
        ARTIFACT_PATHS["shadow_runtime_source"],
        ARTIFACT_PATHS["shadow_runner_script"],
        ARTIFACT_PATHS["shadow_task_runner_script"],
        ARTIFACT_PATHS["shadow_task_installer_script"],
    ):
        assert (ROOT / relative).is_file()
