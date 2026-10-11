"""Synthetic fixture tests for a prospective one-ledger S02 recovery prototype.

These tests create mock source repositories under pytest tmp_path, never use VPS
data/research.sqlite or real data/forward.sqlite, and have no network calls.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pytest

from trading_signal_intelligence.forward.ledger import ForwardLedger
from trading_signal_intelligence.recovery import b1b2_single_s02_local_trial_v0_1 as trial

FAKE_REVISION = "a" * 40
NOW = datetime(2026, 10, 11, tzinfo=timezone.utc)


def fixture(tmp_path: Path, count: int = 2):
    root = tmp_path / "mock_repository"
    (root / "data").mkdir(parents=True)
    scratch = tmp_path / "vowsig-b1b2-synthetic-output"
    scratch.mkdir()
    source = root / "data" / "forward.sqlite"
    ledger = ForwardLedger(source)  # Creates only the synthetic fixture.
    for i in range(count):
        ledger.append(
            record_type="SIGNAL" if i == 0 else "EXIT",
            entity_id=f"synthetic-{i}",
            effective_at_utc=NOW,
            recorded_at_utc=NOW,
            payload={"synthetic": i, "nested": {"market": "test"}},
            record_id=f"mock-{i:03d}",
        )
    return root, scratch, source


def capture(root, scratch, name="trial-001"):
    return trial.capture_single_s02_trial(
        repo_root=root,
        output_parent=scratch,
        trial_id=name,
        source_revision=FAKE_REVISION,
        real_source_access_explicitly_approved=True,  # mock DBs only
    )


def test_requires_explicit_external_authorization_before_source_read(tmp_path):
    root, scratch, source = fixture(tmp_path)
    hash_before = trial._sha256(source)
    with pytest.raises(trial.TrialRejected, match="authorization"):
        trial.capture_single_s02_trial(
            repo_root=root, output_parent=scratch,
            trial_id="trial-001", source_revision=FAKE_REVISION,
        )
    assert list(scratch.iterdir()) == []
    assert trial._sha256(source) == hash_before


def test_single_s02_copy_chain_manifest_and_no_overwrite(tmp_path):
    root, scratch, source = fixture(tmp_path)
    original_sha = trial._sha256(source)
    expected_head = ForwardLedger(source).head_hash()
    report = capture(root, scratch)
    assert report["classification"] == "PRIVATE_LOCAL_EXPERIMENTAL_COPY_ONLY"
    assert report["record_count"] == 2
    assert report["counts_by_type"] == {"EXIT": 1, "SIGNAL": 1}
    assert report["head_hash"] == expected_head
    assert report["s02_chain_valid"] is True
    assert report["integrity_check"] == "ok"
    assert report["offsite_copy_verified"] is False
    assert report["independent_restore_verified"] is False
    assert report["cross_database_atomic"] is False
    assert report["publisher_cutover_authorized"] is False
    assert report["source_git_revision"] == FAKE_REVISION
    assert report["source_relative_path"] == "data/forward.sqlite"
    copy = scratch / "trial-001" / "forward.sqlite"
    assert report["copy_sha256"] == trial._sha256(copy)
    assert trial._sha256(source) == original_sha
    saved = json.loads((scratch / "trial-001" / "local-trial-manifest.json").read_text())
    digest = saved.pop("manifest_sha256")
    assert hashlib.sha256(trial._canonical(saved)).hexdigest() == digest
    with pytest.raises(trial.TrialRejected, match="no-overwrite"):
        capture(root, scratch)


def test_copy_verification_does_not_initialize_schema(tmp_path):
    db = tmp_path / "alien.sqlite"
    with sqlite3.connect(db) as con:
        con.execute("CREATE TABLE irrelevant(message TEXT)")
    before = trial._sha256(db)
    with pytest.raises(trial.TrialRejected, match="triggers"):
        trial.verify_sealed_s02_copy(db)
    assert trial._sha256(db) == before
    with sqlite3.connect(db) as con:
        tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    assert "forward_records" not in tables


def test_synthetic_payload_tampering_not_promoted(tmp_path):
    root, scratch, source = fixture(tmp_path)
    with sqlite3.connect(source) as con:
        con.execute("DROP TRIGGER forward_records_no_update")
        con.execute("UPDATE forward_records SET payload_json=? WHERE sequence=1", ('{"bad":true}',))
        con.executescript("""
        CREATE TRIGGER forward_records_no_update BEFORE UPDATE ON forward_records
        BEGIN SELECT RAISE(ABORT, 'forbidden'); END;
        """)
    with pytest.raises(trial.TrialRejected, match="canonical record hash"):
        capture(root, scratch)
    assert not (scratch / "trial-001" / "local-trial-manifest.json").exists()
    assert (scratch / "trial-001" / "forward.sqlite").exists()


def test_missing_append_only_trigger_rejected(tmp_path):
    root, scratch, source = fixture(tmp_path)
    with sqlite3.connect(source) as con:
        con.execute("DROP TRIGGER forward_records_no_delete")
    with pytest.raises(trial.TrialRejected, match="append-only triggers"):
        capture(root, scratch)
    assert not (scratch / "trial-001" / "local-trial-manifest.json").exists()


def test_wal_source_blocked_before_sqlite_connection(tmp_path):
    root, scratch, source = fixture(tmp_path)
    with sqlite3.connect(source) as con:
        assert con.execute("PRAGMA journal_mode=WAL").fetchone()[0] == "wal"
    with pytest.raises(trial.TrialRejected, match="WAL or unsupported|sidecar"):
        capture(root, scratch)
    assert list(scratch.iterdir()) == []


def test_source_sidecar_held_before_capture(tmp_path):
    root, scratch, source = fixture(tmp_path)
    Path(str(source) + "-journal").write_bytes(b"synthetic pending writer")
    with pytest.raises(trial.TrialRejected, match="sidecar"):
        capture(root, scratch)
    assert list(scratch.iterdir()) == []


def test_research_sqlite_not_in_allowed_capture_scope(tmp_path):
    root, scratch, _ = fixture(tmp_path)
    (root / "data" / "forward.sqlite").rename(root / "data" / "research.sqlite")
    with pytest.raises(trial.TrialRejected, match="missing"):
        capture(root, scratch)
    assert list(scratch.iterdir()) == []


def test_output_inside_repository_rejected(tmp_path):
    root, _, _ = fixture(tmp_path)
    unsafe = root / "vowsig-b1b2-synthetic"
    unsafe.mkdir()
    with pytest.raises(trial.TrialRejected, match="outside the repository"):
        capture(root, unsafe)


def test_source_size_budget_rejected_before_capture(tmp_path):
    root, scratch, source = fixture(tmp_path)
    with source.open("ab") as handle:
        handle.truncate(trial.MAX_TRIAL_BYTES + 1)
    with pytest.raises(trial.TrialRejected, match="10 MiB"):
        capture(root, scratch)
    assert list(scratch.iterdir()) == []


def test_bad_revision_and_collision_rejected(tmp_path):
    root, scratch, _ = fixture(tmp_path)
    with pytest.raises(trial.TrialRejected, match="revision"):
        trial.capture_single_s02_trial(
            repo_root=root, output_parent=scratch, trial_id="trial-001",
            source_revision="main", real_source_access_explicitly_approved=True,
        )
    with pytest.raises(trial.TrialRejected, match="trial ID"):
        capture(root, scratch, name="../escape")
    assert list(scratch.iterdir()) == []


def test_empty_real_schema_fixture_cannot_be_promoted(tmp_path):
    root, scratch, source = fixture(tmp_path, count=0)
    with pytest.raises(trial.TrialRejected, match="no S02 records"):
        capture(root, scratch)
    assert not (scratch / "trial-001" / "local-trial-manifest.json").exists()


def test_modified_copy_has_failing_integrity(tmp_path):
    root, scratch, _ = fixture(tmp_path)
    capture(root, scratch)
    sealed = scratch / "trial-001" / "forward.sqlite"
    with sealed.open("r+b") as handle:
        handle.write(b"definitely-not-sqlite")
    with pytest.raises((trial.TrialRejected, sqlite3.DatabaseError)):
        trial.verify_sealed_s02_copy(sealed)


def test_source_drift_during_copy_verification_prevents_manifest(tmp_path, monkeypatch):
    root, scratch, source = fixture(tmp_path)
    original_verify = trial.verify_sealed_s02_copy

    def add_synthetic_source_bytes(copy_path):
        verified = original_verify(copy_path)
        with source.open("ab") as stream:
            stream.write(b"synthetic concurrent source change")
        return verified

    monkeypatch.setattr(trial, "verify_sealed_s02_copy", add_synthetic_source_bytes)
    with pytest.raises(trial.TrialRejected, match="source metadata changed"):
        capture(root, scratch)
    assert not (scratch / "trial-001" / "local-trial-manifest.json").exists()
