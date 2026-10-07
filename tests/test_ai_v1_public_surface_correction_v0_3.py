from __future__ import annotations

from pathlib import Path

from trading_signal_intelligence.ai_v1.observability_v1_1 import (
    PUBLIC_SURFACE_CORRECTION_KIND_V3,
    PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS,
    PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS,
    PUBLIC_SURFACE_V3_SCHEMA_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v3_public_surface_schema_expands_without_rewriting_v2() -> None:
    assert PUBLIC_SURFACE_CORRECTION_KIND_V3 == "AI-v1.1-public-surface-v0.3"
    assert PUBLIC_SURFACE_V3_SCHEMA_VERSION == 3
    assert PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS < (
        PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS
    )
    assert (
        PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS
        - PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS
    ) == {
        "ai_insights_source",
        "public_snapshot_export_script",
        "public_snapshot_push_script",
    }


def test_v3_builder_is_confirmation_gated_and_non_trading() -> None:
    text = (
        ROOT / "scripts" / "create_vowsig_public_surface_correction_v0_3.py"
    ).read_text(encoding="utf-8")

    assert "CREATE-VOWSIG-PUBLIC-SURFACE-CORRECTION-V0.3" in text
    assert "--change-scope" in text
    assert "PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS" in text
    assert '"decision_artifacts_changed": False' in text
    assert '"ledger_mutation_performed": False' in text
    assert '"provider_call_made": False' in text
    assert '"mt5_call_made": False' in text
    assert '"broker_execution_enabled": False' in text
    assert '"scheduler_changed": False' in text
    assert '"tracked_web_tree_mode": "git_tracked_exact"' in text

    assert "OpenAIResponsesAdapter" not in text
    assert "MT5Connector" not in text
    assert "AILedger" not in text
    assert "Register-ScheduledTask" not in text
