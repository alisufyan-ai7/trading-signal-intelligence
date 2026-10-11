"""Offline synthetic-only B1/B2: no repository/VPS databases or external services."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from trading_signal_intelligence.recovery import b1b2_synthetic_v0_1 as p

UTC = "2026-10-11T00:00:00+00:00"


def fixture_root(tmp_path: Path) -> Path:
    root = tmp_path / "vowsig-b1b2-fixture-test"
    root.mkdir()
    (root / p.FIXTURE_FILE).write_text(p.FIXTURE_MARKER, encoding="utf-8")
    return root


def create_fixture(root: Path, filename="ai_fake.sqlite", kind="AI", count=2) -> Path:
    table = p.ALLOWED_KINDS[kind]
    db = root / filename
    with sqlite3.connect(db) as con:
        con.execute(f"CREATE TABLE {table} (sequence INTEGER PRIMARY KEY, record_id TEXT, record_type TEXT, entity_id TEXT, recorded_at_utc TEXT, effective_at_utc TEXT, payload_json TEXT, previous_hash TEXT, record_hash TEXT)")
        con.execute(f"CREATE TABLE {p.SYNTHETIC_TABLE} (synthetic_token TEXT NOT NULL)")
        con.execute(f"INSERT INTO {p.SYNTHETIC_TABLE} VALUES (?)", (p.FIXTURE_MARKER.strip(),))
        prev = None
        for i in range(1, count + 1):
            record = {
                "record_id": f"fixture-id-{i}",
                "record_type": "ACTIVATION" if i == 1 else "NO_TRADE",
                "entity_id": f"synthetic-{i}",
                "recorded_at_utc": UTC,
                "effective_at_utc": UTC,
                "payload_json": p.canonical_bytes({"synthetic": i}).decode("utf-8"),
                "previous_hash": prev,
            }
            record_hash = hashlib.sha256(p.canonical_bytes(record)).hexdigest()
            con.execute(f"INSERT INTO {table} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                        (i, record["record_id"], record["record_type"],
                         record["entity_id"], UTC, UTC, record["payload_json"], prev, record_hash))
            prev = record_hash
    return db


def test_both_kinds_online_backup_manifest_and_copy_bytes_unchanged(tmp_path):
    root = fixture_root(tmp_path)
    first = create_fixture(root)
    other = create_fixture(root, "s02_fake.sqlite", "S02")
    originals = [p.sha256_file(first), p.sha256_file(other)]
    report = p.capture_synthetic_set(root, [
        p.SyntheticSpec("s02-example", other.name, "S02"),
        p.SyntheticSpec("ai-example", first.name, "AI"),
    ], set_id="testbatch-001")
    assert report["status"] == "VERIFIED_SYNTHETIC_COPY"
    assert report["cross_database_atomic"] is False
    assert report["external_backup_verified"] is False
    assert report["independent_restore_verified"] is False
    assert [o["object_id"] for o in report["database_objects"]] == ["ai-example", "s02-example"]
    assert all(o["ledger_chain_valid"] and o["integrity_check"] == "ok" and o["records"] == 2 for o in report["database_objects"])
    assert [p.sha256_file(first), p.sha256_file(other)] == originals
    manifest = json.loads((root / "captured/testbatch-001/synthetic-manifest.json").read_text())
    digest = manifest.pop("manifest_sha256")
    assert hashlib.sha256(p.canonical_bytes(manifest)).hexdigest() == digest
    assert report["manifest_sha256"] == digest
    with pytest.raises(p.SyntheticGateRejected, match="collision"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai-example", first.name, "AI")], set_id="testbatch-001")


def test_missing_marker_and_real_looking_path_rejected_before_writes(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    (root / p.FIXTURE_FILE).unlink()
    with pytest.raises(p.SyntheticGateRejected):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI")], set_id="safe-01")
    assert not (root / "captured").exists()


def test_unmarked_sqlite_rejected_before_copies(tmp_path):
    root = fixture_root(tmp_path)
    with sqlite3.connect(root / "unmarked.sqlite") as con:
        con.execute("CREATE TABLE unrelated(x INTEGER)")
    with pytest.raises(p.SyntheticGateRejected, match="synthetic-only marker"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("foo", "unmarked.sqlite", "AI")], set_id="safe-01")
    assert not (root / "captured").exists()


@pytest.mark.parametrize("specs", [
    [p.SyntheticSpec("same", "ai_fake.sqlite", "AI"), p.SyntheticSpec("same", "other.sqlite", "S02")],
    [p.SyntheticSpec("first", "ai_fake.sqlite", "AI"), p.SyntheticSpec("other", "AI_FAKE.sqlite", "AI")],
    [p.SyntheticSpec("foo", "ai_fake.sqlite", "AI", rights="UNKNOWN_RIGHTS")],
    [p.SyntheticSpec("foo", "../ai_fake.sqlite", "AI")],
    [p.SyntheticSpec("foo", "ai_fake.sqlite", "UNKNOWN")],
])
def test_bad_scope_or_rights_fail_closed(tmp_path, specs):
    root = fixture_root(tmp_path)
    create_fixture(root)
    create_fixture(root, "other.sqlite", "S02")
    with pytest.raises(p.SyntheticGateRejected):
        p.capture_synthetic_set(root, specs, set_id="safe-01")
    assert not (root / "captured").exists()


def test_reject_budget_before_destination(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    with pytest.raises(p.SyntheticGateRejected, match="budget"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI")], set_id="safe-01", max_source_bytes=1)
    assert not (root / "captured").exists()


def test_record_chain_tamper_detected_on_copy(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    # Synthetic fixture has no update trigger: tamper affects only mock data.
    with sqlite3.connect(db) as con:
        con.execute("UPDATE ai_records SET payload_json = ? WHERE sequence = 2", ('{"synthetic":999}',))
    with pytest.raises(p.SyntheticGateRejected, match="chain hash"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI")], set_id="tamper-01")
    assert (root / "captured/tamper-01/ai_fake.sqlite").exists()
    assert not (root / "captured/tamper-01/synthetic-manifest.json").exists()


def test_corrupted_copy_rejected_even_if_source_is_synthetic(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    with db.open("r+b") as f:
        f.write(b"not-a-sqlite-db")
    with pytest.raises((p.SyntheticGateRejected, sqlite3.DatabaseError)):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI")], set_id="bad-01")


def test_anchor_must_be_in_chain(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    with pytest.raises(p.SyntheticGateRejected, match="anchor"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI", anchor_hash="0" * 64)], set_id="anchor-01")


def test_wal_uncommitted_writer_not_in_snapshot(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    writer = sqlite3.connect(db)
    try:
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("CREATE TABLE never_committed_by_writer(x INTEGER)")
        report = p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI")], set_id="wal-01")
        assert report["database_objects"][0]["records"] == 2
        with sqlite3.connect(root / "captured/wal-01/ai_fake.sqlite") as captured:
            tables = {r[0] for r in captured.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert "never_committed_by_writer" not in tables
    finally:
        writer.rollback()
        writer.close()


def test_interrupted_progress_cannot_promote_manifest(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    def fail(_status, _remaining, _total):
        raise RuntimeError("synthetic-injected-cancel")
    with pytest.raises(RuntimeError, match="synthetic-injected-cancel"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("ai", db.name, "AI")], set_id="cancel-01", progress=fail)
    assert not (root / "captured/cancel-01/synthetic-manifest.json").exists()


def test_symlink_source_disallowed(tmp_path):
    root = fixture_root(tmp_path)
    db = create_fixture(root)
    link = root / "linked.sqlite"
    try:
        link.symlink_to(db)
    except (OSError, NotImplementedError):
        pytest.skip("symlink permission unavailable on this host")
    with pytest.raises(p.SyntheticGateRejected, match="unsafe"):
        p.capture_synthetic_set(root, [p.SyntheticSpec("link", link.name, "AI")], set_id="link-01")
    assert not (root / "captured").exists()
