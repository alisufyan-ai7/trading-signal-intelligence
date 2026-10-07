from __future__ import annotations

import hashlib
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1 import observability_v1_1 as obs
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



def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _false_boundary() -> dict[str, bool]:
    return {
        "decision_artifacts_changed": False,
        "ledger_mutation_performed": False,
        "backfill_performed": False,
        "provider_call_made": False,
        "mt5_call_made": False,
        "broker_execution_enabled": False,
        "scheduler_changed": False,
    }


def _write_v3_chain(tmp_path: Path) -> tuple[dict, Path, Path]:
    forward = tmp_path / "research" / "forward"
    forward.mkdir(parents=True)

    anchor = {
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "broker_execution_enabled": False,
    }
    activation_path = forward / "AI-v1.1-activation-test.json"
    activation_path.write_text(
        json.dumps(anchor, sort_keys=True),
        encoding="utf-8",
    )

    legacy_path = (
        forward / "AI-v1.1-public-surface-correction-2026-09-30T215809Z.json"
    )
    legacy_payload = {
        "correction_kind": obs.PUBLIC_SURFACE_CORRECTION_KIND,
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "base_activation_anchor": (
            "research/forward/AI-v1.1-activation-test.json"
        ),
        "base_activation_anchor_sha256": _sha(activation_path),
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "artifact_hash_overrides": {
            "ai_ui_index": "1" * 64,
            "ai_ui_script": "2" * 64,
        },
        **_false_boundary(),
    }
    legacy_path.write_text(
        json.dumps(legacy_payload, sort_keys=True),
        encoding="utf-8",
    )

    v2_overrides = {
        name: f"{index:x}" * 64
        for index, name in enumerate(
            sorted(obs.PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS),
            start=1,
        )
    }
    v2_web = {
        "web/app.js": v2_overrides["ai_ui_script"],
        "web/index.html": v2_overrides["ai_ui_index"],
        "web/styles.css": "a" * 64,
    }
    v2_path = (
        forward
        / "AI-v1.1-public-surface-correction-v0.2-2026-10-02T000000Z.json"
    )
    v2_payload = {
        "correction_kind": obs.PUBLIC_SURFACE_CORRECTION_KIND_V2,
        "correction_schema_version": obs.PUBLIC_SURFACE_V2_SCHEMA_VERSION,
        "sequence_number": 2,
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "base_activation_anchor": (
            "research/forward/AI-v1.1-activation-test.json"
        ),
        "base_activation_anchor_sha256": _sha(activation_path),
        "supersedes_correction": legacy_path.relative_to(tmp_path).as_posix(),
        "supersedes_correction_sha256": _sha(legacy_path),
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "artifact_hash_overrides": v2_overrides,
        "tracked_web_artifact_hashes": v2_web,
        **_false_boundary(),
    }
    v2_path.write_text(
        json.dumps(v2_payload, sort_keys=True),
        encoding="utf-8",
    )

    v3_overrides = {
        name: f"{index:x}" * 64
        for index, name in enumerate(
            sorted(obs.PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS),
            start=1,
        )
    }
    v3_web = {
        "web/app.js": v3_overrides["ai_ui_script"],
        "web/index.html": v3_overrides["ai_ui_index"],
        "web/styles.css": "b" * 64,
    }
    v3_path = (
        forward
        / "AI-v1.1-public-surface-correction-v0.3-2026-10-07T000000Z.json"
    )
    v3_payload = {
        "correction_kind": obs.PUBLIC_SURFACE_CORRECTION_KIND_V3,
        "correction_schema_version": obs.PUBLIC_SURFACE_V3_SCHEMA_VERSION,
        "sequence_number": 3,
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "base_activation_anchor": (
            "research/forward/AI-v1.1-activation-test.json"
        ),
        "base_activation_anchor_sha256": _sha(activation_path),
        "supersedes_correction": v2_path.relative_to(tmp_path).as_posix(),
        "supersedes_correction_sha256": _sha(v2_path),
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "artifact_hash_overrides": v3_overrides,
        "tracked_web_artifact_hashes": v3_web,
        **_false_boundary(),
    }
    v3_path.write_text(
        json.dumps(v3_payload, sort_keys=True),
        encoding="utf-8",
    )

    return anchor, v2_path, v3_path


def test_v3_correction_can_supersede_v2_without_rewriting_v2(
    monkeypatch,
    tmp_path: Path,
) -> None:
    anchor, _, v3_path = _write_v3_chain(tmp_path)
    monkeypatch.setattr(
        obs,
        "verify_anchor_upstream_v1_1",
        lambda repo_root, path: {
            "valid": True,
            "upstream_commit": "f" * 40,
        },
    )

    result = obs._public_surface_correction(tmp_path, anchor)

    assert result["valid"] is True
    assert result["correction_kind"] == obs.PUBLIC_SURFACE_CORRECTION_KIND_V3
    assert result["correction_schema_version"] == 3
    assert result["sequence_number"] == 3
    assert result["path"] == v3_path.relative_to(tmp_path).as_posix()
    assert len(result["chain_paths"]) == 3
    assert set(result["artifact_hash_overrides"]) == set(
        obs.PUBLIC_SURFACE_V3_CORRECTABLE_ARTIFACTS
    )


def test_v3_chain_rejects_schema_regression_to_v2(
    monkeypatch,
    tmp_path: Path,
) -> None:
    anchor, _, v3_path = _write_v3_chain(tmp_path)
    forward = tmp_path / "research" / "forward"
    regression_path = (
        forward
        / "AI-v1.1-public-surface-correction-v0.2-2026-10-07T000001Z.json"
    )

    v2_overrides = {
        name: f"{index:x}" * 64
        for index, name in enumerate(
            sorted(obs.PUBLIC_SURFACE_V2_CORRECTABLE_ARTIFACTS),
            start=1,
        )
    }
    regression = {
        "correction_kind": obs.PUBLIC_SURFACE_CORRECTION_KIND_V2,
        "correction_schema_version": obs.PUBLIC_SURFACE_V2_SCHEMA_VERSION,
        "sequence_number": 4,
        "runtime_version": "AI-v1.1",
        "decision_protocol_version": "AI-v1.0",
        "base_activation_anchor": (
            "research/forward/AI-v1.1-activation-test.json"
        ),
        "base_activation_anchor_sha256": _sha(
            forward / "AI-v1.1-activation-test.json"
        ),
        "supersedes_correction": v3_path.relative_to(tmp_path).as_posix(),
        "supersedes_correction_sha256": _sha(v3_path),
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "artifact_hash_overrides": v2_overrides,
        "tracked_web_artifact_hashes": {
            "web/app.js": v2_overrides["ai_ui_script"],
            "web/index.html": v2_overrides["ai_ui_index"],
        },
        **_false_boundary(),
    }
    regression_path.write_text(
        json.dumps(regression, sort_keys=True),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        obs,
        "verify_anchor_upstream_v1_1",
        lambda repo_root, path: {"valid": True},
    )

    result = obs._public_surface_correction(tmp_path, anchor)

    assert result["valid"] is False
    assert result["reason"] == "public_surface_schema_regression"
