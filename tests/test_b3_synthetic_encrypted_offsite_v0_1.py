"""B3 AES-GCM synthetic in-memory two-provider backup/restore, never cloud/VPS."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from trading_signal_intelligence.recovery import b1b2_synthetic_v0_1 as b1
from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3

KEY = bytes(range(32))  # Test-only key, NEVER production key material.
BAD_KEY = bytes(reversed(range(32)))
UTC = "2026-10-22T00:00:00+00:00"


def fixture(tmp_path: Path):
    root = tmp_path / "vowsig-b1b2-fixture-b3test"
    root.mkdir()
    (root / b1.FIXTURE_FILE).write_text(b1.FIXTURE_MARKER, encoding="utf-8")
    source = root / "forward.sqlite"
    with sqlite3.connect(source) as conn:
        conn.execute("CREATE TABLE vowsig_synthetic_fixture_only (synthetic_token TEXT NOT NULL)")
        conn.execute("INSERT INTO vowsig_synthetic_fixture_only VALUES (?)", (b1.FIXTURE_MARKER.strip(),))
        conn.execute("CREATE TABLE forward_records (sequence INTEGER PRIMARY KEY, record_id TEXT, record_type TEXT, entity_id TEXT, recorded_at_utc TEXT, effective_at_utc TEXT, payload_json TEXT, previous_hash TEXT, record_hash TEXT)")
        prev = None
        for i in range(1, 3):
            payload = json.dumps({"fake_count": i}, sort_keys=True, separators=(",", ":"))
            fields = dict(record_id=f"b3-synthetic-{i}", record_type="ACTIVATION" if i == 1 else "NO_TRADE",
                          entity_id=f"fake-{i}", recorded_at_utc=UTC, effective_at_utc=UTC,
                          payload_json=payload, previous_hash=prev)
            digest = hashlib.sha256(b1.canonical_bytes(fields)).hexdigest()
            conn.execute("INSERT INTO forward_records VALUES (?,?,?,?,?,?,?,?,?)",
                         (i, *fields.values(), digest))
            prev = digest
    manifest = b1.capture_synthetic_set(root, [b1.SyntheticSpec("fake_s02", "forward.sqlite", "S02")], set_id="setb3")
    assert manifest["database_objects"][0]["records"] == 2
    copy = root / "captured" / "setb3" / "forward.sqlite"
    return root, copy


def test_roundtrip_both_providers_and_portable_restore_without_local_seal(tmp_path):
    root, source = fixture(tmp_path)
    sealed = b3.seal_captured_synthetic_s02(root, source, artifact_id="a1", key=KEY)
    assert source.read_bytes() not in sealed.envelope
    a, b = b3.MemoryBucket("aws-s3-synthetic"), b3.MemoryBucket("b2-synthetic")
    outcome = b3.replicate_and_readback(sealed, a, b)
    assert outcome["status"] == "SYNTHETIC_ONLY_TWO_MEMORY_READBACKS_VERIFIED"
    assert outcome["cloud_uploads"] == 0 and outcome["billable_requests"] == 0
    for provider, ident in ((a, "awsrestore"), (b, "b2restore")):
        # Only downloaded bytes and separately held key are needed for recovery.
        report = b3.restore_synthetic_s02(root, bytes(provider.get(sealed.object_key)),
                                          key=KEY, restore_id=ident)
        assert report["records"] == 2 and report["sha256"] == sealed.plaintext_sha256
    assert a._objects is not b._objects


def test_tampered_ciphertext_denied_before_restore(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="t1", key=KEY)
    corrupt = bytearray(obj.envelope)
    corrupt[-1] ^= 1
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.restore_synthetic_s02(root, bytes(corrupt), key=KEY, restore_id="bad")
    assert not (root / "restored").exists()


def test_wrong_key_denied_before_plaintext_written(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="t2", key=KEY)
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.restore_synthetic_s02(root, obj.envelope, key=BAD_KEY, restore_id="wrong")
    assert not (root / "restored").exists()


def test_altered_authenticated_manifest_denied(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="t3", key=KEY)
    altered = bytearray(obj.envelope)
    pos = obj.envelope.index(b"SYNTHETIC_ONLY_NEVER_PRODUCTION")
    altered[pos] ^= 1
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.restore_synthetic_s02(root, bytes(altered), key=KEY, restore_id="altered")
    assert not (root / "restored").exists()


def test_duplicate_object_fails_closed(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="dup", key=KEY)
    a = b3.MemoryBucket("aws-s3-synthetic")
    a.put_new(obj)
    with pytest.raises(b3.SyntheticOffsiteRejected, match="duplicate"):
        a.put_new(obj)
    assert len(a._objects) == 1


def test_partial_provider_failure_not_promoted(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="partial", key=KEY)
    a = b3.MemoryBucket("aws-s3-synthetic")
    b = b3.MemoryBucket("b2-synthetic")
    b.put_new(obj)  # simulate pre-existing version/no overwrite on second provider
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.replicate_and_readback(obj, a, b)
    assert a.get(obj.object_key) == obj.envelope
    assert b.get(obj.object_key) == obj.envelope


def test_live_or_unmarked_copy_rejected(tmp_path):
    root, copied = fixture(tmp_path)
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.seal_captured_synthetic_s02(root, root / "forward.sqlite", artifact_id="live", key=KEY)
    (root / b1.FIXTURE_FILE).unlink()
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.seal_captured_synthetic_s02(root, copied, artifact_id="unmarked", key=KEY)


def test_file_limits_key_lengths_and_ids_rejected(tmp_path):
    root, copied = fixture(tmp_path)
    for key in (b"x", b"", None):
        with pytest.raises(b3.SyntheticOffsiteRejected):
            b3.seal_captured_synthetic_s02(root, copied, artifact_id="test", key=key)
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.seal_captured_synthetic_s02(root, copied, artifact_id="../untrusted", key=KEY)
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.restore_synthetic_s02(root, b"", key=KEY, restore_id="../bad")
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.MemoryBucket("actual-s3-bucket")


def test_nonce_random_and_ciphertext_distinct(tmp_path):
    root, copied = fixture(tmp_path)
    one = b3.seal_captured_synthetic_s02(root, copied, artifact_id="nonce", key=KEY)
    two = b3.seal_captured_synthetic_s02(root, copied, artifact_id="nonce", key=KEY)
    assert one.envelope != two.envelope
    assert one.plaintext_sha256 == two.plaintext_sha256


def test_wrong_provider_pair_and_payload_budget_denied(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="t5", key=KEY)
    a = b3.MemoryBucket("aws-s3-synthetic")
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.replicate_and_readback(obj, a, a)
    altered = replace(obj, envelope=b"x" * (b3.MAX_OBJECT_BYTES + 1))
    with pytest.raises(b3.SyntheticOffsiteRejected):
        a.put_new(altered)


def test_corrupted_portable_header_fails_closed(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="header", key=KEY)
    magic = len(b3.MAGIC)
    bad_objects = (
        b"bad" + obj.envelope[3:],
        obj.envelope[:magic] + b"\xff\xff" + obj.envelope[magic + 2:],
        obj.envelope[:magic + 4],
    )
    for corrupted in bad_objects:
        with pytest.raises(b3.SyntheticOffsiteRejected):
            b3.restore_synthetic_s02(root, corrupted, key=KEY, restore_id="badheader")
    assert not (root / "restored").exists()


def test_tampered_portable_nonce_fails_closed(tmp_path):
    root, copied = fixture(tmp_path)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="noncebad", key=KEY)
    corrupted = bytearray(obj.envelope)
    corrupted[len(b3.MAGIC) + 2] ^= 1
    with pytest.raises(b3.SyntheticOffsiteRejected):
        b3.restore_synthetic_s02(root, bytes(corrupted), key=KEY, restore_id="badnonce")
    assert not (root / "restored").exists()
