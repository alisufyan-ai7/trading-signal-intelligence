from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.activation_v1_2 import (
    ActivationV12Error,
    DECISION_PROTOCOL_VERSION,
    EXPANSION_ARTIFACT_PATHS,
    PARALLEL_RUNTIME_ANCHOR,
    RUNTIME_VERSION,
    build_activation_anchor_document_v1_2,
    build_activation_anchor_preview_v1_2,
    build_activation_payload_v1_2,
    preactivation_report_v1_2,
    validate_activation_anchor_document_v1_2,
    validate_activation_payload_v1_2,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_2 import (
    DATABASE_PATHS,
    MARKETS,
)


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def test_v1_2_preactivation_report_passes_without_live_expansion_state() -> None:
    before = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }
    report = preactivation_report_v1_2(ROOT)
    after = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }

    assert before == after
    assert report["preactivation_check"] == "PASS"
    assert report["runtime_version"] == "AI-v1.2"
    assert report["decision_protocol_version"] == "AI-v1.0"
    assert report["parallel_to_runtime_version"] == "AI-v1.1"
    assert report["parallel_runtime_anchor"] == PARALLEL_RUNTIME_ANCHOR
    assert report["frozen_decision_artifacts_match_upstream"] is True
    assert report["feature_schema_compatibility"][
        "equivalent_except_schema_metadata_and_source_symbol_allowlist"
    ] is True
    assert report["guardrails_compatibility"][
        "equivalent_except_status_and_shadow_market_allowlist"
    ] is True
    assert report["review_gates"]["valid"] is True
    assert not any(report["expansion_ledger_paths_exist"].values())
    assert report["expansion_activation_anchors"] == []
    assert report["provider_call_made"] is False
    assert report["mt5_call_made"] is False
    assert report["ledger_write_performed"] is False
    assert report["activation_performed"] is False
    assert report["scheduler_changed"] is False
    assert report["public_exposure_changed"] is False
    assert report["broker_execution_enabled"] is False


def test_v1_2_activation_payload_is_parallel_and_restarts_evidence() -> None:
    payload = build_activation_payload_v1_2(
        repo_root=ROOT,
        market="EURUSD",
        activated_at_utc=datetime(2026, 10, 7, 0, 0, tzinfo=UTC),
    )

    assert payload["runtime_version"] == RUNTIME_VERSION
    assert payload["decision_protocol_version"] == DECISION_PROTOCOL_VERSION
    assert payload["parallel_to_runtime_version"] == "AI-v1.1"
    assert payload["parallel_runtime_anchor"] == PARALLEL_RUNTIME_ANCHOR
    assert payload["gate_counts_carry_forward"] is False
    assert payload["backfill_prior_missed"] is False
    assert payload["provider"] == "openai"
    assert payload["model_id"] == "gpt-5.4-2026-03-05"
    assert payload["sync_max_wait_seconds"] == 30.0
    assert payload["sync_poll_interval_seconds"] == 1.0
    assert payload["public_exposure_enabled"] is False
    assert payload["broker_execution_enabled"] is False
    assert len(payload["activation_bundle_sha256"]) == 64


def test_v1_2_activation_validation_rejects_boundary_changes() -> None:
    payload = build_activation_payload_v1_2(
        repo_root=ROOT,
        market="XAGUSD",
        activated_at_utc=datetime(2026, 10, 7, 0, 0, tzinfo=UTC),
    )

    carry = dict(payload)
    carry["gate_counts_carry_forward"] = True
    with pytest.raises(ActivationV12Error):
        validate_activation_payload_v1_2(carry)

    backfill = dict(payload)
    backfill["backfill_prior_missed"] = True
    with pytest.raises(ActivationV12Error):
        validate_activation_payload_v1_2(backfill)

    public = dict(payload)
    public["public_exposure_enabled"] = True
    with pytest.raises(ActivationV12Error):
        validate_activation_payload_v1_2(public)

    broker = dict(payload)
    broker["broker_execution_enabled"] = True
    with pytest.raises(ActivationV12Error):
        validate_activation_payload_v1_2(broker)


def test_v1_2_artifact_bundle_is_complete() -> None:
    required = {
        "preregistration_exp_2026_015",
        "compatibility_plan_v0_1",
        "activation_plan_v0_1",
        "instrument_registry",
        "activation_schema_v1_2",
        "activation_anchor_schema_v1_2",
        "expansion_config",
        "expansion_feature_schema",
        "expansion_guardrails",
        "review_gates",
        "expansion_compatibility_source",
        "readiness_source",
        "engine_source_v1_2",
        "shadow_runtime_source_v1_2",
        "activation_builder_source_v1_2",
        "observability_source_v1_2",
        "runtime_verifier_source_v1_2",
        "preactivation_verifier_script_v1_2",
        "activation_readiness_verifier_script_v1_2",
        "progress_report_script_v1_2",
        "readiness_probe_script_v1_2",
        "activation_preview_script_v1_2",
        "activation_execution_script_v1_2",
        "live_runner_script_v1_2",
        "runtime_verifier_script_v1_2",
        "task_runner_script_v1_2",
        "task_installer_script_v1_2",
        "rates_sync_source_v1_1",
        "mt5_rates_adapter_source_v1_1",
        "mt5_connector_source",
    }
    assert set(EXPANSION_ARTIFACT_PATHS) == required
    for relative in EXPANSION_ARTIFACT_PATHS.values():
        assert (ROOT / relative).is_file()


def test_v1_2_activation_preview_is_side_effect_free() -> None:
    before = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }
    preview = build_activation_anchor_preview_v1_2(
        repo_root=ROOT,
        activated_at_utc=datetime(2026, 10, 7, 0, 0, tzinfo=UTC),
    )
    after = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }

    assert before == after
    assert preview["anchor_preview_only"] is True
    assert preview["runtime_version"] == "AI-v1.2"
    assert preview["decision_protocol_version"] == "AI-v1.0"
    assert preview["parallel_to_runtime_version"] == "AI-v1.1"
    assert preview["gate_counts_carry_forward"] is False
    assert preview["backfill_prior_missed"] is False
    assert preview["provider_call_made"] is False
    assert preview["public_exposure_enabled"] is False
    assert preview["broker_execution_enabled"] is False
    assert preview["ledger_records_created"] == 0
    assert preview["activation_anchor_written"] is False
    assert preview["scheduler_changed"] is False
    assert set(preview["market_payloads"]) == set(MARKETS)


def test_v1_2_aggregate_anchor_builder_is_pure_and_valid() -> None:
    activated = datetime(2026, 10, 7, 0, 0, tzinfo=UTC)
    payloads = {
        market: build_activation_payload_v1_2(
            repo_root=ROOT,
            market=market,
            activated_at_utc=activated,
        )
        for market in MARKETS
    }
    records = {
        market: {
            "record_type": "ACTIVATION",
            "record_hash": (str(index) * 64)[:64],
            "payload": payload,
        }
        for index, (market, payload) in enumerate(payloads.items(), start=1)
    }

    before = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }
    anchor = build_activation_anchor_document_v1_2(
        repo_root=ROOT,
        activated_at_utc=activated,
        activation_records=records,
    )
    after = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }

    assert before == after
    assert anchor["status"] == "ACTIVE_PARALLEL_SHADOW"
    assert anchor["runtime_version"] == "AI-v1.2"
    assert anchor["decision_protocol_version"] == "AI-v1.0"
    assert anchor["parallel_to_runtime_version"] == "AI-v1.1"
    assert anchor["gate_counts_carry_forward"] is False
    assert anchor["backfill_prior_missed"] is False
    assert anchor["provider_call_made"] is False
    assert anchor["public_exposure_enabled"] is False
    assert anchor["broker_execution_enabled"] is False
    assert set(anchor["markets"]) == set(MARKETS)
    validate_activation_anchor_document_v1_2(anchor)


def test_live_runner_verifies_activation_before_side_effects() -> None:
    text = (ROOT / "scripts" / "run_ai_v1_2_live.py").read_text(
        encoding="utf-8"
    )
    verify_pos = text.index("verify_active_runtime_v1_2(")
    env_pos = text.index("load_project_env(")
    provider_pos = text.index("OpenAIResponsesAdapter.from_environment(")
    connector_pos = text.index("MT5Connector(")
    assert verify_pos < env_pos < provider_pos < connector_pos


def test_task_installer_preserves_parallel_runtime_and_minute_three() -> None:
    text = (
        ROOT / "scripts" / "install_ai_v1_2_shadow_task.ps1"
    ).read_text(encoding="utf-8")

    assert "VowSig AI-v1.2 Expansion Shadow Scan" in text
    assert "SignalProof AI-v1.1 Shadow Scan" in text
    assert "AddMinutes(3)" in text
    assert "ScheduledMinute = 3" in text
    assert "ConfirmActivatedRuntime" in text
    assert "Register-ScheduledTask" in text


def test_review_gates_are_frozen_before_activation() -> None:
    payload = json.loads(
        (ROOT / "config" / "ai_v1_2_review_gates.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["status"] == "frozen_pre_activation"
    assert payload["markets"] == ["EURUSD", "XAGUSD", "USOIL"]
    assert payload["gates"]["X1"] == {
        "purpose": "operational_audit_only",
        "valid_inferences": 100,
        "completed_shadow_trades": 20,
        "minimum_calendar_days": 0,
    }
    assert payload["gates"]["X2"] == {
        "purpose": "interim_expansion_economic_review",
        "valid_inferences": 500,
        "completed_shadow_trades": 50,
        "minimum_calendar_days": 60,
    }
    assert payload["gates"]["X3"] == {
        "purpose": "first_expansion_publishability_graduation_decision",
        "valid_inferences": 1000,
        "completed_shadow_trades": 100,
        "minimum_calendar_days": 120,
    }
