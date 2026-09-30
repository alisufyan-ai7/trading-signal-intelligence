from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    ActivationV11Error,
    RUNTIME_VERSION,
    DECISION_PROTOCOL_VERSION,
    V11_ARTIFACT_PATHS,
    build_activation_anchor_preview_v1_1,
    build_activation_payload_v1_1,
    preactivation_report_v1_1,
    validate_activation_payload_v1_1,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import DATABASE_PATHS


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def test_preactivation_report_passes_without_creating_v1_1_state() -> None:
    before = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }
    assert not any(before.values())

    report = preactivation_report_v1_1(ROOT)

    assert report["preactivation_check"] == "PASS"
    assert report["runtime_version"] == "AI-v1.1"
    assert report["decision_protocol_version"] == "AI-v1.0"
    assert report["frozen_decision_artifacts_match_upstream"] is True
    assert report["v1_1_activation_anchors"] == []
    assert not any(report["v1_1_ledger_paths_exist"].values())
    assert report["provider_call_made"] is False
    assert report["mt5_call_made"] is False
    assert report["activation_performed"] is False
    assert report["scheduler_changed"] is False

    after = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }
    assert after == before


def test_activation_preview_binds_upstream_and_restarts_evidence() -> None:
    payload = build_activation_payload_v1_1(
        repo_root=ROOT,
        market="USTEC",
        activated_at_utc=datetime(2026, 9, 30, 8, 0, tzinfo=UTC),
    )

    assert payload["runtime_version"] == RUNTIME_VERSION
    assert payload["decision_protocol_version"] == DECISION_PROTOCOL_VERSION
    assert payload["supersedes_runtime_version"] == "AI-v1.0"
    assert payload["gate_counts_carry_forward"] is False
    assert payload["backfill_prior_missed"] is False
    assert payload["provider"] == "openai"
    assert payload["model_id"] == "gpt-5.4-2026-03-05"
    assert payload["model_parameter_fingerprint"] == (
        "ed5069535190cb33771ff8efe1c4389e09abaddea933143c0c839c6dc87d3e9b"
    )
    assert payload["sync_max_wait_seconds"] == 30.0
    assert payload["sync_poll_interval_seconds"] == 1.0
    assert payload["broker_execution_enabled"] is False
    assert len(payload["activation_bundle_sha256"]) == 64

    assert not any(
        (ROOT / relative).exists()
        for relative in DATABASE_PATHS.values()
    )


def test_activation_validation_rejects_carry_forward_or_backfill() -> None:
    payload = build_activation_payload_v1_1(
        repo_root=ROOT,
        market="XAUUSD",
        activated_at_utc=datetime(2026, 9, 30, 8, 0, tzinfo=UTC),
    )

    carry = dict(payload)
    carry["gate_counts_carry_forward"] = True
    with pytest.raises(ActivationV11Error):
        validate_activation_payload_v1_1(carry)

    backfill = dict(payload)
    backfill["backfill_prior_missed"] = True
    with pytest.raises(ActivationV11Error):
        validate_activation_payload_v1_1(backfill)


def test_v1_1_activation_bundle_includes_versioned_runtime_artifacts() -> None:
    required = {
        "activation_schema_v1_1",
        "rates_sync_source_v1_1",
        "mt5_rates_adapter_source_v1_1",
        "engine_source_v1_1",
        "shadow_runtime_source_v1_1",
        "activation_builder_source_v1_1",
        "preactivation_runner_script_v1_1",
        "preactivation_verifier_script_v1_1",
        "activation_preview_script_v1_1",
        "live_runner_script_v1_1",
        "runtime_verifier_source_v1_1",
        "runtime_verifier_script_v1_1",
        "task_runner_script_v1_1",
        "task_installer_script_v1_1",
        "observability_source_v1_1",
        "active_observability_source",
        "ai_insights_source",
        "public_snapshot_export_script",
        "retirement_builder_source_v1_0",
        "retirement_preview_script_v1_0",
        "mt5_connector_source",
    }
    assert set(V11_ARTIFACT_PATHS) == required
    for relative in V11_ARTIFACT_PATHS.values():
        assert (ROOT / relative).is_file()


def test_preactivation_runner_cannot_execute_live_path() -> None:
    text = (ROOT / "scripts" / "run_ai_v1_1_shadow.py").read_text(
        encoding="utf-8"
    )
    assert "AI-v1.1 live execution is not activated or authorized" in text
    assert "MT5Connector" not in text
    assert "OpenAIResponsesAdapter" not in text
    assert "AILedger" not in text


def test_v1_1_activation_schema_freezes_sync_and_execution() -> None:
    schema = json.loads(
        (ROOT / "config" / "ai_v1_1_activation_schema.json").read_text(
            encoding="utf-8"
        )
    )
    props = schema["properties"]
    assert props["runtime_version"]["const"] == "AI-v1.1"
    assert props["decision_protocol_version"]["const"] == "AI-v1.0"
    assert props["sync_max_wait_seconds"]["const"] == 30.0
    assert props["sync_poll_interval_seconds"]["const"] == 1.0
    assert props["gate_counts_carry_forward"]["const"] is False
    assert props["backfill_prior_missed"]["const"] is False
    assert props["broker_execution_enabled"]["const"] is False



def test_activation_anchor_preview_is_side_effect_free() -> None:
    before = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }
    preview = build_activation_anchor_preview_v1_1(
        repo_root=ROOT,
        activated_at_utc=datetime(2026, 9, 30, 12, 0, tzinfo=UTC),
    )
    after = {
        market: (ROOT / relative).exists()
        for market, relative in DATABASE_PATHS.items()
    }

    assert before == after
    assert preview["anchor_preview_only"] is True
    assert preview["runtime_version"] == "AI-v1.1"
    assert preview["decision_protocol_version"] == "AI-v1.0"
    assert preview["gate_counts_carry_forward"] is False
    assert preview["backfill_prior_missed"] is False
    assert preview["provider_call_made"] is False
    assert preview["broker_execution_enabled"] is False
    assert preview["ledger_records_created"] == 0
    assert preview["activation_anchor_written"] is False
    assert preview["scheduler_changed"] is False
    assert set(preview["market_payloads"]) == {"XAUUSD", "USTEC", "US30"}


def test_live_runner_verifies_activation_before_runtime_side_effects() -> None:
    text = (ROOT / "scripts" / "run_ai_v1_1_live.py").read_text(
        encoding="utf-8"
    )
    verify_pos = text.index("verify_active_runtime_v1_1(")
    env_pos = text.index("load_project_env(")
    provider_pos = text.index("OpenAIResponsesAdapter.from_environment(")
    connector_pos = text.index("MT5Connector(")
    assert verify_pos < env_pos < provider_pos < connector_pos


def test_task_installer_requires_disabled_legacy_task() -> None:
    text = (
        ROOT / "scripts" / "install_ai_v1_1_shadow_task.ps1"
    ).read_text(encoding="utf-8")
    assert "Legacy AI-v1.0 task is still Running" in text
    assert "Legacy AI-v1.0 task must be Disabled" in text
    assert "-ConfirmActivatedRuntime" in text or "ConfirmActivatedRuntime" in text
    assert "Register-ScheduledTask" in text
