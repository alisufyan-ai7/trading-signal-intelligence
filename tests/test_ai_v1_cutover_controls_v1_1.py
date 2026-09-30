from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_legacy_disable_script_is_confirmation_gated_and_non_destructive() -> None:
    text = (
        ROOT / "scripts" / "disable_ai_v1_shadow_task_for_v1_1.ps1"
    ).read_text(encoding="utf-8")

    assert "ConfirmCutover" in text
    assert "AI-v1.0 task is Running" in text
    assert "AI-v1.0 task must be Ready" in text
    assert "Disable-ScheduledTask" in text
    assert "Unregister-ScheduledTask" not in text
    assert "after_state" in text
    assert "Disabled" in text


def test_retirement_finalizer_is_confirmation_gated_and_read_only_to_ledgers() -> None:
    text = (
        ROOT / "scripts" / "finalize_ai_v1_0_retirement.py"
    ).read_text(encoding="utf-8")

    assert "WRITE-AI-V1.0-RETIREMENT-METADATA" in text
    assert "build_v1_0_retirement_document" in text
    assert "AI-v1.0-retired-" in text
    assert "AILedger" not in text
    assert "MT5Connector" not in text
    assert "OpenAIResponsesAdapter" not in text
    assert '"ledger_mutation_performed": False' in text
    assert '"provider_call_made": False' in text
    assert '"mt5_call_made": False' in text


def test_v1_1_activation_writer_requires_retirement_and_disabled_legacy_task() -> None:
    text = (ROOT / "scripts" / "activate_ai_v1_1.py").read_text(
        encoding="utf-8"
    )

    assert "ACTIVATE-AI-V1.1-LEDGERS" in text
    assert "preactivation_report_v1_1" in text
    assert "probe_windows_scheduler" in text
    assert "Legacy AI-v1.0 scheduler must be Disabled" in text
    assert "_require_committed_retirement" in text
    assert "verify_anchor_upstream" in text
    assert "build_activation_anchor_document_v1_1" in text
    assert "AILedger" in text
    assert "OpenAIResponsesAdapter" not in text
    assert "MT5Connector" not in text
    assert "Register-ScheduledTask" not in text
    assert '"scheduler_installed": False' in text
    assert '"backfill_performed": False' in text


def test_v1_1_live_no_current_tick_uses_frozen_allowed_record_type() -> None:
    text = (ROOT / "scripts" / "run_ai_v1_1_live.py").read_text(
        encoding="utf-8"
    )

    assert 'record_type="SYNC_STATUS"' not in text
    assert 'record_type="MISSED_INFERENCE"' in text
    assert '"reason": "no_current_h1_tick"' in text
    assert "cycle_processed_v1_1(ledger, entity_id)" in text



def test_activation_only_v1_1_public_snapshot_is_frozen_until_first_cycle() -> None:
    text = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "product"
        / "ai_insights.py"
    ).read_text(encoding="utf-8")

    assert "activation_only_pre_first_cycle" in text
    assert "unhealthy_v1_1" in text
    assert "v1_1_publish_blocked" in text
    assert '"publish_allowed": not v1_1_publish_blocked' in text
    assert '"transition_blocked": v1_1_publish_blocked' in text
    assert 'int(totals["valid_inferences"])' in text
    assert 'int(totals["missed_inferences"])' in text
    assert 'int(totals["errors"])' in text

def test_v1_1_activation_anchor_has_explicit_lf_normalization() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert (
        "research/forward/AI-v1.1-activation-*.json text eol=lf"
        in attributes
    )

