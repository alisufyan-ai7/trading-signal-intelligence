"""No-network Git-only tests for active frozen-dependency change-impact gate."""
from __future__ import annotations

import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "impact_guard_under_test", ROOT / "scripts/check_frozen_dependency_impact.py"
)
assert spec and spec.loader
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


def cmd(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=root, text=True).strip()


def commit(root: Path, message: str) -> str:
    cmd(root, "add", "-A")
    cmd(root, "-c", "user.email=test@example.invalid",
        "-c", "user.name=Offline Fixture", "commit", "-qm", message)
    return cmd(root, "rev-parse", "HEAD")


@pytest.fixture
def fixture(tmp_path, monkeypatch):
    repo = tmp_path / "repo"
    repo.mkdir()
    cmd(repo, "init", "-q")
    anchor = "research/forward/AI-v1.1-activation-test.json"
    source = "src/activation.py"
    pinned = "config/instruments.json"
    (repo / "research/forward").mkdir(parents=True)
    (repo / "src").mkdir()
    (repo / "config").mkdir()
    (repo / "docs").mkdir()

    (repo / source).write_text(
        'V11_ARTIFACT_PATHS = {"instrument_registry": "config/instruments.json"}\n',
        encoding="utf-8"
    )
    (repo / pinned).write_text('{"instruments": []}\n', encoding="utf-8")
    (repo / anchor).write_text(json.dumps({
        "runtime_version": "AI-v1.1",
        "status": "ACTIVE",
        "artifact_hashes": {"instrument_registry": "f" * 64},
    }) + "\n", encoding="utf-8")
    (repo / "docs/info.md").write_text("hello\n", encoding="utf-8")
    first = commit(repo, "Base")
    cmd(repo, "checkout", "-qb", "test-change")
    monkeypatch.setattr(gate, "LINEAGES", (
        ("AI-v1.1", anchor, source,
         (("V11_ARTIFACT_PATHS", "artifact_hashes"),), None),
    ))
    return repo, first, anchor, source, pinned


def test_new_unpinned_file_is_not_blocked(fixture):
    repo, first, *_ = fixture
    (repo / "docs/new.md").write_text("new\n", encoding="utf-8")
    updated = commit(repo, "Unpinned documentation")
    result = gate.check(repo, first, updated)
    assert result["blocked"] == []
    assert result["coverage"] == {"AI-v1.1": 1}
    assert result["protected"] >= 5


@pytest.mark.parametrize("changed", ["registry", "map", "anchor", "guard", "workflow"])
def test_freeze_change_blocks_even_if_diff_is_additive(fixture, changed):
    repo, first, anchor, source, registry = fixture
    targets = {
        "registry": registry,
        "map": source,
        "anchor": anchor,
        "guard": "scripts/check_frozen_dependency_impact.py",
        "workflow": ".github/workflows/frozen-dependency-change-impact.yml",
    }
    file = targets[changed]
    target = repo / file
    target.parent.mkdir(parents=True, exist_ok=True)
    if changed == "registry":
        # Reproduces 2026-10-08 failure: harmless looking additive content
        # still invalidates whole historical activation digest.
        target.write_text(target.read_text(encoding="utf-8") + "ETHUSDT\n")
    else:
        target.write_text("changed\n", encoding="utf-8")
    updated = commit(repo, "Change frozen artifact/policy")
    assert file in gate.check(repo, first, updated)["blocked"]


def test_rename_and_delete_pinned_file_also_block(fixture):
    repo, first, _, _, registry = fixture
    newname = "config/renamed-registry.json"
    (repo / registry).rename(repo / newname)
    updated = commit(repo, "Rename protected")
    assert registry in gate.check(repo, first, updated)["blocked"]


def test_future_activation_anchor_creation_requires_governance(fixture):
    repo, first, *_ = fixture
    target = repo / "research/forward/AI-v1.4-crypto-expansion-activation-new.json"
    target.write_text('{"future": true}\n', encoding="utf-8")
    updated = commit(repo, "New anchor")
    assert target.relative_to(repo).as_posix() in gate.check(repo, first, updated)["blocked"]


def test_future_correction_evidence_creation_requires_governance(fixture):
    repo, first, *_ = fixture
    target = repo / "research/forward/AI-v1.1-public-surface-correction-v0.4.json"
    target.write_text('{"future": true}\n', encoding="utf-8")
    updated = commit(repo, "New correction")
    assert target.relative_to(repo).as_posix() in gate.check(repo, first, updated)["blocked"]


def test_immutable_base_maps_cannot_be_reassigned(fixture):
    repo, first, anchor, source, registry = fixture
    (repo / source).write_text(
        'V11_ARTIFACT_PATHS = {"instrument_registry": "config/instruments.json"}\n'
        'V11_ARTIFACT_PATHS = {"instrument_registry": "config/other.json"}\n'
    )
    replacement = commit(repo, "Mutate map")
    with pytest.raises(gate.GateViolation, match="reassigned"):
        gate.baseline_protected(repo, replacement)


def test_manifest_missing_anchor_hashes_fails_closed(fixture):
    repo, first, anchor, source, registry = fixture
    data = json.loads((repo / anchor).read_text())
    data["artifact_hashes"] = {}
    (repo / anchor).write_text(json.dumps(data), encoding="utf-8")
    replacement = commit(repo, "Drop frozen hashes")
    with pytest.raises(gate.GateViolation, match="do not match"):
        gate.baseline_protected(repo, replacement)


@pytest.mark.parametrize("path", ["/config/secret.json", "../secret.json", "config//bad.json",
                                  "config\\instruments.json", ".github/evil.yml"])
def test_unsafe_manifest_paths_rejected(path):
    with pytest.raises(gate.GateViolation):
        gate.canonical_path(path)


def test_no_runtime_module_import_side_effects(fixture):
    repo, first, anchor, source, registry = fixture
    (repo / source).write_text(
        "raise RuntimeError('MUST NOT EXECUTE')\n"
        'V11_ARTIFACT_PATHS = {"instrument_registry": "config/instruments.json"}\n'
    )
    altered = commit(repo, "Static source with dangerous top-level code")
    protected, coverage = gate.baseline_protected(repo, altered)
    assert registry in protected
    assert coverage["AI-v1.1"] == 1


def test_known_real_active_manifests_have_matching_keys_and_broad_coverage():
    # On an exact-SHA review checkout, this reads only its own Git objects;
    # never executes scanner/provider/broker code or accesses real ledgers.
    head = cmd(ROOT, "rev-parse", "HEAD")
    protected, coverage = gate.baseline_protected(ROOT, head)
    assert coverage["AI-v1.1"] >= 45
    assert coverage["AI-v1.2.1"] == 34
    assert coverage["AI-v1.3"] >= 30
    assert "config/instruments.json" in protected
    assert "src/trading_signal_intelligence/ai_v1/crypto_runtime_v1_3.py" in protected
    assert "src/trading_signal_intelligence/product/ai_insights.py" in protected
    assert gate.GOVERNANCE_FILES.issubset(protected)


def test_historical_hash_mismatch_does_not_whitelist_new_edits(fixture):
    repo, first, _, _, registry = fixture
    # The existing fixture's hash is intentionally already different from
    # frozen anchor SHA, yet unchanged docs remain allowed and new registry
    # edits still block. A historical FAIL must never grant future bypass.
    (repo / "docs/info.md").write_text("updated docs\n")
    docs_head = commit(repo, "Docs changed")
    assert gate.check(repo, first, docs_head)["blocked"] == []
    (repo / registry).write_text('{"instruments":["ETHUSDT"]}\n')
    bad_head = commit(repo, "New drift")
    assert registry in gate.check(repo, first, bad_head)["blocked"]


def test_missing_trusted_base_fails_closed(fixture):
    repo, _, *_ = fixture
    head = cmd(repo, "rev-parse", "HEAD")
    with pytest.raises(gate.GateViolation):
        gate.check(repo, "0" * 40, head)
