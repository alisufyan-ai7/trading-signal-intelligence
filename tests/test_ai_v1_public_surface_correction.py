from __future__ import annotations

from pathlib import Path

from trading_signal_intelligence.ai_v1 import observability_v1_1 as obs


ROOT = Path(__file__).resolve().parents[1]


def test_public_surface_correction_allowlist_is_narrow() -> None:
    assert obs.PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS == frozenset(
        {
            "observability_source_v1_1",
            "product_publish_task_runner_script",
            "cloud_app_source",
            "cloud_snapshot_verifier_script",
            "ai_ui_script",
            "ai_ui_index",
        }
    )
    assert not (
        set(obs.PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS)
        & set(obs.FROZEN_DECISION_ARTIFACT_PATHS)
    )


def test_artifact_verifier_accepts_only_effective_corrected_hashes(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        obs,
        "V11_ARTIFACT_PATHS",
        {
            "ai_ui_index": "web/index.html",
            "engine_source_v1_1": "engine.py",
        },
    )
    monkeypatch.setattr(
        obs,
        "_public_surface_correction",
        lambda repo_root, anchor: {
            "present": True,
            "valid": True,
            "artifact_hash_overrides": {"ai_ui_index": "new-ui"},
        },
    )

    def fake_hash(path: Path) -> str:
        return {
            "index.html": "new-ui",
            "engine.py": "engine",
        }[path.name]

    monkeypatch.setattr(obs, "_file_sha256", fake_hash)

    result = obs.verify_v1_1_artifacts(
        tmp_path,
        {
            "artifact_hashes": {
                "ai_ui_index": "old-ui",
                "engine_source_v1_1": "engine",
            }
        },
    )

    assert result["valid"] is True
    assert result["mismatches"] == {}


def test_artifact_verifier_fails_closed_on_invalid_correction(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(
        obs,
        "_public_surface_correction",
        lambda repo_root, anchor: {
            "present": True,
            "valid": False,
            "reason": "public_surface_override_outside_allowlist",
            "artifact_hash_overrides": {},
        },
    )

    result = obs.verify_v1_1_artifacts(
        tmp_path,
        {"artifact_hashes": {}},
    )

    assert result["valid"] is False
    assert "public_surface_correction" in result["mismatches"]


def test_vowsig_correction_builder_is_confirmation_gated_and_non_trading() -> None:
    text = (
        ROOT / "scripts" / "create_vowsig_public_surface_correction.py"
    ).read_text(encoding="utf-8")

    assert "CREATE-VOWSIG-PUBLIC-SURFACE-CORRECTION" in text
    assert '"decision_artifacts_changed": False' in text
    assert '"ledger_mutation_performed": False' in text
    assert '"provider_call_made": False' in text
    assert '"mt5_call_made": False' in text
    assert '"broker_execution_enabled": False' in text
    assert '"scheduler_changed": False' in text

    assert "OpenAIResponsesAdapter" not in text
    assert "MT5Connector" not in text
    assert "AILedger" not in text
    assert "Register-ScheduledTask" not in text


def test_vowsig_correction_anchor_preserves_committed_bytes() -> None:
    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert (
        "research/forward/AI-v1.1-public-surface-correction-*.json -text"
        in attributes
    )
