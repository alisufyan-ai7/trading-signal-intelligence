"""EXP037 offline S3-compatible transport regression: synthetic-only, zero network."""
from __future__ import annotations

import hashlib
import io
import json
import sqlite3
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from trading_signal_intelligence.recovery import b1b2_synthetic_v0_1 as b1
from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4

TEST_KEY = bytes(range(32))  # Deterministic TEST ONLY; never production key.
UTC = "2026-10-22T00:00:00+00:00"


def synthetic_fixture(tmp_path: Path):
    root = tmp_path / "vowsig-b1b2-fixture-b4test"
    root.mkdir()
    (root / b1.FIXTURE_FILE).write_text(b1.FIXTURE_MARKER, encoding="utf-8")
    source = root / "forward.sqlite"
    with sqlite3.connect(source) as con:
        con.execute("CREATE TABLE vowsig_synthetic_fixture_only (synthetic_token TEXT NOT NULL)")
        con.execute("INSERT INTO vowsig_synthetic_fixture_only VALUES (?)", (b1.FIXTURE_MARKER.strip(),))
        con.execute("CREATE TABLE forward_records (sequence INTEGER PRIMARY KEY, record_id TEXT, record_type TEXT, entity_id TEXT, recorded_at_utc TEXT, effective_at_utc TEXT, payload_json TEXT, previous_hash TEXT, record_hash TEXT)")
        previous = None
        for i in range(1, 3):
            record = {
                "record_id": f"b4synthetic-{i}", "record_type": "ACTIVATION" if i == 1 else "NO_TRADE",
                "entity_id": f"synthetic-{i}", "recorded_at_utc": UTC,
                "effective_at_utc": UTC, "payload_json": json.dumps({"synthetic": i}, separators=(",", ":")),
                "previous_hash": previous,
            }
            digest = hashlib.sha256(b1.canonical_bytes(record)).hexdigest()
            con.execute("INSERT INTO forward_records VALUES (?,?,?,?,?,?,?,?,?)",
                        (i, *record.values(), digest))
            previous = digest
    b1.capture_synthetic_set(root, [b1.SyntheticSpec("fakes02", "forward.sqlite", "S02")], set_id="setb4")
    copied = root / "captured" / "setb4" / "forward.sqlite"
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="syntheticb4", key=TEST_KEY)
    return root, copied, obj


class FakeS3NotFound(Exception):
    response = {
        "Error": {"Code": "404"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }


class FakeS3Denied(Exception):
    response = {
        "Error": {"Code": "AccessDenied"},
        "ResponseMetadata": {"HTTPStatusCode": 403},
    }


class FakeBackend:
    def __init__(self, provider):
        self.provider = provider
        self.objects = {}
        self.operations = []
        self.deny_head = False
        self.fail_put = False
        self.bad_content = False
        self.omit_version = False
        self.already_exists = False


class FakeClient:
    def __init__(self, backend: FakeBackend, role: str):
        self.backend, self.role = backend, role
        provider = backend.provider
        self.meta = SimpleNamespace(
            endpoint_url=provider.endpoint,
            region_name=provider.region,
            config=SimpleNamespace(
                retries={"total_max_attempts": 1},
                signature_version="s3v4",
                connect_timeout=5, read_timeout=10,
            ),
        )

    def head_object(self, **kwargs):
        assert self.role == "reader", "writer must not perform reads"
        assert kwargs["Bucket"] == self.backend.provider.bucket
        self.backend.operations.append(("head", self.role))
        if self.backend.deny_head:
            raise FakeS3Denied()
        if self.backend.already_exists or kwargs["Key"] in self.backend.objects:
            return {"ResponseMetadata": {"HTTPStatusCode": 200}}
        raise FakeS3NotFound()

    def put_object(self, **kwargs):
        assert self.role == "writer", "readback must not upload"
        assert kwargs["Bucket"] == self.backend.provider.bucket
        assert isinstance(kwargs["Body"], bytes)
        assert kwargs["ContentLength"] == len(kwargs["Body"])
        assert (kwargs.get("IfNoneMatch") == "*") == (self.backend.provider == b4.AWS)
        self.backend.operations.append(("put", self.role))
        if self.backend.fail_put:
            raise RuntimeError("provider fake simulated ambiguous upload")
        version = "test-v1"
        self.backend.objects[kwargs["Key"]] = (kwargs["Body"], version)
        return {} if self.backend.omit_version else {"VersionId": version}

    def get_object(self, **kwargs):
        assert self.role == "reader"
        assert kwargs["Bucket"] == self.backend.provider.bucket
        self.backend.operations.append(("get", self.role))
        data, version = self.backend.objects[kwargs["Key"]]
        assert kwargs["VersionId"] == version
        if self.backend.bad_content:
            data = b"X" + data[1:]
        return {"VersionId": version, "ContentLength": len(data), "Body": io.BytesIO(data)}


def pairs():
    aws = FakeBackend(b4.AWS)
    b2 = FakeBackend(b4.B2)
    return aws, b2, FakeClient(aws, "writer"), FakeClient(aws, "reader"), FakeClient(b2, "writer"), FakeClient(b2, "reader")


def invoke(root, copied, obj, clients, *, approved=True, approval_phrase=b4.APPROVAL_PHRASE,
           key=TEST_KEY):
    aws, b2, aw, ar, bw, br = clients
    return b4.run_two_provider_pilot(
        fixture_root=root, captured_source=copied, obj=obj, key=key,
        aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
        network_approved=approved, approval_phrase=approval_phrase,
    )


def test_default_deny_zero_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    with pytest.raises(b4.SyntheticS3PilotRejected, match="not authorized"):
        invoke(root, copied, obj, clients, approved=False)
    assert not clients[0].operations and not clients[1].operations


def test_wrong_phrase_zero_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    with pytest.raises(b4.SyntheticS3PilotRejected, match="not authorized"):
        invoke(root, copied, obj, clients, approval_phrase="yes")
    assert not clients[0].operations and not clients[1].operations


def test_two_providers_two_independent_restores(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    source_digest = hashlib.sha256(copied.read_bytes()).hexdigest()
    report = invoke(root, copied, obj, clients)
    assert report["status"] == "SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES"
    assert report["actual_attempted_requests"] == report["max_requests"] == 6
    assert report["object_size_bytes"] <= b4.MAX_ENVELOPE_BYTES
    assert [r["provider"] for r in report["receipts"]] == ["AWS_S3", "BACKBLAZE_B2"]
    assert [name for name, _ in clients[0].operations] == ["head", "put", "get"]
    assert [name for name, _ in clients[1].operations] == ["head", "put", "get"]
    assert clients[0].objects is not clients[1].objects
    for place in ("awsrestore", "b2restore"):
        restored = root / "restored" / place / "forward.sqlite"
        assert restored.is_file()
        assert hashlib.sha256(restored.read_bytes()).hexdigest() == source_digest
    assert copied.read_bytes() == (root / "restored" / "awsrestore" / "forward.sqlite").read_bytes()


def test_writer_and_reader_roles_never_interchanged(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    report = invoke(root, copied, obj, clients)
    assert report["actual_attempted_requests"] == 6
    for backend in clients[:2]:
        assert all((act == "put") == (role == "writer") for act, role in backend.operations)


def test_unapproved_live_source_path_rejected_before_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    with pytest.raises(b4.SyntheticS3PilotRejected):
        invoke(root, root / "forward.sqlite", obj, clients)
    assert not clients[0].operations and not clients[1].operations


def test_source_attestation_mismatch_before_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    fake = replace(obj, plaintext_sha256="0" * 64)
    with pytest.raises(b4.SyntheticS3PilotRejected):
        invoke(root, copied, fake, clients)
    assert not clients[0].operations


def test_wrong_key_before_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    with pytest.raises(b4.SyntheticS3PilotRejected):
        invoke(root, copied, obj, clients, key=bytes(reversed(range(32))))
    assert not clients[0].operations and not clients[1].operations


def test_wrong_endpoint_or_retry_config_rejected_before_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    clients[3].meta.endpoint_url = "http://example.com"
    with pytest.raises(b4.SyntheticS3PilotRejected):
        invoke(root, copied, obj, clients)
    assert not clients[0].operations and not clients[1].operations


def test_unsafe_shared_writer_reader_rejected(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = list(pairs())
    clients[3] = clients[2]
    with pytest.raises(b4.SyntheticS3PilotRejected):
        invoke(root, copied, obj, clients)
    assert not clients[0].operations and not clients[1].operations


def test_existing_key_denied_no_put(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    clients[0].already_exists = True
    with pytest.raises(b4.SyntheticS3PilotRejected, match="already exists"):
        invoke(root, copied, obj, clients)
    assert [name for name, _ in clients[0].operations] == ["head"]
    assert not clients[1].operations


def test_permission_denied_head_fails_closed(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    clients[0].deny_head = True
    with pytest.raises(b4.SyntheticS3PilotRejected, match="inconclusive"):
        invoke(root, copied, obj, clients)
    assert [name for name, _ in clients[0].operations] == ["head"]


def test_ambiguous_put_never_retries(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    clients[0].fail_put = True
    with pytest.raises(b4.SyntheticS3PilotRejected, match="do not retry"):
        invoke(root, copied, obj, clients)
    assert [name for name, _ in clients[0].operations] == ["head", "put"]
    assert not clients[1].operations


def test_missing_version_no_get_and_no_second_provider(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    clients[0].omit_version = True
    with pytest.raises(b4.SyntheticS3PilotRejected, match="versioned"):
        invoke(root, copied, obj, clients)
    assert [name for name, _ in clients[0].operations] == ["head", "put"]
    assert not clients[1].operations


def test_b2_corrupted_readback_fails_no_all_clear(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    clients[1].bad_content = True
    with pytest.raises(b4.SyntheticS3PilotRejected, match="mismatch"):
        invoke(root, copied, obj, clients)
    assert [name for name, _ in clients[0].operations] == ["head", "put", "get"]
    assert [name for name, _ in clients[1].operations] == ["head", "put", "get"]
    assert not (root / "restored" / "b2restore").exists()


def test_oversize_envelope_rejected_without_calls(tmp_path):
    root, copied, obj = synthetic_fixture(tmp_path)
    clients = pairs()
    bad = replace(obj, envelope=b"x" * (b4.MAX_ENVELOPE_BYTES + 1))
    with pytest.raises(b4.SyntheticS3PilotRejected):
        invoke(root, copied, bad, clients)
    assert not clients[0].operations and not clients[1].operations
