"""Prospective real-data core: synthetic SQLite fixtures ONLY; no cloud/keys."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

import pytest

from trading_signal_intelligence.recovery import live_sqlite_envelope_v0_1 as live


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def fixture_s02(tmp_path):
    repo = tmp_path / "repo"
    data = repo / "data"
    data.mkdir(parents=True)
    scratch = tmp_path / "private-scratch"
    scratch.mkdir()
    database = data / "forward.sqlite"
    with sqlite3.connect(database) as con:
        con.execute("""CREATE TABLE forward_records (
            sequence INTEGER, record_id TEXT, record_type TEXT, entity_id TEXT,
            recorded_at_utc TEXT, effective_at_utc TEXT, payload_json TEXT,
            previous_hash TEXT, record_hash TEXT)""")
        con.execute("""CREATE TRIGGER forward_records_no_update
                    BEFORE UPDATE ON forward_records
                    BEGIN SELECT RAISE(ABORT,'no'); END""")
        con.execute("""CREATE TRIGGER forward_records_no_delete
                    BEFORE DELETE ON forward_records
                    BEGIN SELECT RAISE(ABORT,'no'); END""")
        prev = None
        for i in range(1, 4):
            material = {
                "record_id": f"fake-{i}", "record_type": "INFERENCE",
                "entity_id": "S02",
                "recorded_at_utc": "2026-10-23T00:00:00+00:00",
                "effective_at_utc": "2026-10-23T00:00:00+00:00",
                "payload_json": canonical({"v": i}).decode(), "previous_hash": prev,
            }
            digest = hashlib.sha256(canonical(material)).hexdigest()
            con.execute(
                "INSERT INTO forward_records VALUES(?,?,?,?,?,?,?,?,?)",
                (i, *material.values(), digest),
            )
            prev = digest
        con.commit()
    permit = live.SourceAuthorization(
        "data/forward.sqlite", "S02", "a" * 64, "b" * 64,
        ("us-east-1", "us-east-005"),
    )
    return repo, scratch, permit


def sealed_fixture(tmp_path):
    repo, scratch, permit = fixture_s02(tmp_path)
    copied = live.capture_approved_s02(
        repo_root=repo, scratch_parent=scratch, run_id="release-test-0001",
        authorization=permit,
    )
    key = b"k" * 32
    sealed = live.seal_verified_copy(
        copied=copied, run_id="release-test-0001", key=key,
        authorization=permit,
    )
    return repo, scratch, permit, copied, key, sealed


def test_snapshot_encrypt_and_independent_authenticated_restore(tmp_path):
    _, scratch, permit, copied, key, sealed = sealed_fixture(tmp_path)
    assert copied.exists()
    assert sealed.record_count == 3
    assert sealed.object_key.startswith("vowsig/approved-s02/v1/release-test-0001/")
    assert not sealed.envelope.startswith(b"SQLite format 3")
    recovered = live.restore_verified_envelope(
        envelope=sealed.envelope, key=key, scratch_parent=scratch,
        restore_id="restore-test-0001", expected_sha256=sealed.envelope_sha256,
    )
    assert recovered["status"] == "LIVE_S02_AUTHENTICATED_RESTORE_VERIFIED"
    assert recovered["record_count"] == 3
    assert recovered["plaintext_sha256"] == sealed.plaintext_sha256
    assert (scratch / "restore-test-0001" / "forward.sqlite").exists()


def test_default_source_and_rights_are_not_inferred(tmp_path):
    repo, scratch, permit = fixture_s02(tmp_path)
    with pytest.raises(live.LiveBackupRejected):
        live.capture_approved_s02(
            repo_root=repo, scratch_parent=scratch, run_id="short",
            authorization=permit,
        )
    disallowed = live.SourceAuthorization(
        "data/research.sqlite", "S02", "a" * 64, "b" * 64,
        ("us-east-1", "us-east-005"),
    )
    with pytest.raises(live.LiveBackupRejected):
        live.capture_approved_s02(
            repo_root=repo, scratch_parent=scratch, run_id="release-test-0002",
            authorization=disallowed,
        )
    malformed = live.SourceAuthorization(
        "data/forward.sqlite", "S02", "BAD", "b" * 64,
        ("us-east-1", "us-east-005"),
    )
    with pytest.raises(live.LiveBackupRejected):
        malformed.validate()


def test_capture_no_overwrite_and_never_inside_repo(tmp_path):
    repo, scratch, permit = fixture_s02(tmp_path)
    live.capture_approved_s02(
        repo_root=repo, scratch_parent=scratch, run_id="release-test-0001",
        authorization=permit,
    )
    with pytest.raises(live.LiveBackupRejected):
        live.capture_approved_s02(
            repo_root=repo, scratch_parent=scratch, run_id="release-test-0001",
            authorization=permit,
        )
    with pytest.raises(live.LiveBackupRejected):
        live.capture_approved_s02(
            repo_root=repo, scratch_parent=repo / "data",
            run_id="release-test-0002", authorization=permit,
        )


def test_bad_key_ciphertext_and_digest_rejected(tmp_path):
    _, scratch, _, _, key, sealed = sealed_fixture(tmp_path)
    tampered = sealed.envelope[:-1] + bytes([sealed.envelope[-1] ^ 1])
    for payload, provided_key in (
        (sealed.envelope, b"z" * 32),
        (tampered, key),
        (sealed.envelope[:-3], key),
    ):
        with pytest.raises(live.LiveBackupRejected):
            live.restore_verified_envelope(
                envelope=payload, key=provided_key, scratch_parent=scratch,
                restore_id="restore-test-0002",
            )
    assert not (scratch / "restore-test-0002").exists()
    with pytest.raises(live.LiveBackupRejected):
        live.restore_verified_envelope(
            envelope=sealed.envelope, key=key, scratch_parent=scratch,
            restore_id="restore-test-0003", expected_sha256="0" * 64,
        )


def test_reject_symlink_or_path_escape(tmp_path):
    repo, scratch, permit = fixture_s02(tmp_path)
    database = repo / "data" / "forward.sqlite"
    database.unlink()
    external = tmp_path / "outside.sqlite"
    external.write_bytes(b"SQLite format 3\x00")
    try:
        database.symlink_to(external)
    except OSError:
        pytest.skip("symlinks unavailable on test host")
    with pytest.raises(live.LiveBackupRejected):
        live.capture_approved_s02(
            repo_root=repo, scratch_parent=scratch, run_id="release-test-0004",
            authorization=permit,
        )


def test_reject_tampered_s02_hash_chain(tmp_path):
    repo, scratch, permit = fixture_s02(tmp_path)
    with sqlite3.connect(repo / "data" / "forward.sqlite") as con:
        con.execute("DROP TRIGGER forward_records_no_update")
        con.execute("UPDATE forward_records SET record_hash=? WHERE sequence=2",
                    ("0" * 64,))
        con.commit()
    with pytest.raises(live.LiveBackupRejected):
        live.capture_approved_s02(
            repo_root=repo, scratch_parent=scratch, run_id="release-test-0005",
            authorization=permit,
        )


def test_no_real_provider_sdk_network_or_runtime_entrypoint():
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(live))
    names = {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    assert names.isdisjoint({"boto3", "botocore", "requests", "socket", "urllib"})
    assert live.MAX_SOURCE_BYTES <= 16 * 1024 * 1024
