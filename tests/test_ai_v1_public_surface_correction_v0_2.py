from __future__ import annotations

import hashlib
import json
from pathlib import Path

from trading_signal_intelligence.ai_v1 import observability_v1_1 as obs


ROOT = Path(__file__).resolve().parents[1]


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


def _write_chain(
    tmp_path: Path,
    *,
    bad_predecessor_hash: bool = False,
    add_fork: bool = False,
) -> tuple[dict, Path, Path]:
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
            sorted(obs.PUBLIC_SURFACE_CORRECTABLE_ARTIFACTS),
            start=1,
        )
    }
    # The generated one-character hex strings above are repeated 64 times.
    # Force the UI values into the tracked-web manifest for cross-checking.
    web_hashes = {
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
        "supersedes_correction_sha256": (
            "0" * 64 if bad_predecessor_hash else _sha(legacy_path)
        ),
        "brand": "VowSig",
        "canonical_domain": "https://vowsig.com",
        "artifact_hash_overrides": v2_overrides,
        "tracked_web_artifact_hashes": web_hashes,
        **_false_boundary(),
    }
    v2_path.write_text(
        json.dumps(v2_payload, sort_keys=True),
        encoding="utf-8",
    )

    if add_fork:
        fork_path = (
            forward
            / "AI-v1.1-public-surface-correction-v0.2-2026-10-02T000001Z.json"
        )
        fork_payload = dict(v2_payload)
        fork_payload["created_at_utc"] = "2026-10-02T00:00:01+00:00"
        fork_path.write_text(
            json.dumps(fork_payload, sort_keys=True),
            encoding="utf-8",
        )

    return anchor, legacy_path, v2_path


def test_v2_correction_chain_selects_unique_tip(
    monkeypatch,
    tmp_path: Path,
) -> None:
    anchor, _, v2_path = _write_chain(tmp_path)
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
    assert result["correction_kind"] == obs.PUBLIC_SURFACE_CORRECTION_KIND_V2
    assert result["sequence_number"] == 2
    assert result["path"] == v2_path.relative_to(tmp_path).as_posix()
    assert len(result["chain_paths"]) == 2
    assert result["tracked_web_artifact_hashes"]["web/styles.css"] == "a" * 64


def test_v2_correction_chain_fails_closed_on_fork(
    monkeypatch,
    tmp_path: Path,
) -> None:
    anchor, _, _ = _write_chain(tmp_path, add_fork=True)
    monkeypatch.setattr(
        obs,
        "verify_anchor_upstream_v1_1",
        lambda repo_root, path: {"valid": True},
    )

    result = obs._public_surface_correction(tmp_path, anchor)

    assert result["valid"] is False
    assert result["reason"] == "public_surface_v2_fork_detected"


def test_v2_correction_chain_fails_closed_on_bad_predecessor_hash(
    monkeypatch,
    tmp_path: Path,
) -> None:
    anchor, _, _ = _write_chain(tmp_path, bad_predecessor_hash=True)
    monkeypatch.setattr(
        obs,
        "verify_anchor_upstream_v1_1",
        lambda repo_root, path: {"valid": True},
    )

    result = obs._public_surface_correction(tmp_path, anchor)

    assert result["valid"] is False
    assert result["reason"] == "public_surface_v2_predecessor_hash_mismatch"


def test_artifact_verifier_checks_exact_tracked_web_manifest(
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
            "tracked_web_artifact_hashes": {
                "web/index.html": "new-ui",
                "web/styles.css": "styles",
            },
        },
    )

    def fake_hash(path: Path) -> str:
        return {
            "index.html": "new-ui",
            "engine.py": "engine",
        }[path.name]

    monkeypatch.setattr(obs, "_file_sha256", fake_hash)
    monkeypatch.setattr(
        obs,
        "_tracked_web_hashes",
        lambda repo_root: {
            "web/index.html": "new-ui",
            "web/styles.css": "changed-styles",
        },
    )

    result = obs.verify_v1_1_artifacts(
        tmp_path,
        {
            "artifact_hashes": {
                "ai_ui_index": "old-ui",
                "engine_source_v1_1": "engine",
            }
        },
    )

    assert result["valid"] is False
    assert result["public_web_tree_checked"] == 2
    assert "public_web_tree::web/styles.css" in result["mismatches"]


def test_v2_builder_is_confirmation_gated_and_non_trading() -> None:
    text = (
        ROOT / "scripts" / "create_vowsig_public_surface_correction_v0_2.py"
    ).read_text(encoding="utf-8")

    assert "CREATE-VOWSIG-PUBLIC-SURFACE-CORRECTION-V0.2" in text
    assert '"decision_artifacts_changed": False' in text
    assert '"ledger_mutation_performed": False' in text
    assert '"provider_call_made": False' in text
    assert '"mt5_call_made": False' in text
    assert '"broker_execution_enabled": False' in text
    assert '"scheduler_changed": False' in text
    assert '"tracked_web_tree_mode": "git_tracked_exact"' in text
    assert '"change_scope": "VowSig missed-inference public observability correction v0.1"' in text
    assert "supersedes_correction" in text

    assert "OpenAIResponsesAdapter" not in text
    assert "MT5Connector" not in text
    assert "AILedger" not in text
    assert "Register-ScheduledTask" not in text
