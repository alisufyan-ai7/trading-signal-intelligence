"""EXP049 P7 — synthetic exclusive escrow/read-only cold recovery ONLY."""
from __future__ import annotations

import ast
import hashlib
import inspect

import pytest

from trading_signal_intelligence.recovery import offline_immutable_receipt_escrow_v0_1 as p7
from trading_signal_intelligence.recovery import offline_private_receipt_handoff_v0_1 as p6
from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as p2
from test_live_sqlite_envelope_v0_1 import sealed_fixture
from test_live_dual_provider_transport_v0_1 import clients, permit
from test_private_versioned_restore_manifest_v0_1 import (
    sample_verified, create_manifest, MANIFEST_KEY, FAKE_AWS_VERSION,
)

W = "a" * 64
R = "b" * 64
C = "c" * 64


class MemoryOnlyVault:
    """Deliberately not durable; fake independent read/write operation objects."""

    def __init__(self):
        self.objects = {}
        self.writes = []
        self.reads = []

    def write_once(self, key, ciphertext, digest):
        self.writes.append(key)
        if key in self.objects:
            raise RuntimeError("FAKE_ALREADY_EXISTS secret-never-log")
        self.objects[key] = ciphertext
        return {"status": "CREATED_EXCLUSIVELY", "key": key, "sha256": digest}

    def read_exact(self, key):
        self.reads.append(key)
        return self.objects[key]


def escrow(vault, *, writer=None, reader=None):
    return p7.OfflineImmutableReceiptEscrow(
        write_once=writer or vault.write_once,
        read_exact=reader or vault.read_exact,
        writer_scope_ref_sha256=W,
        reader_scope_ref_sha256=R,
        owner_recovery_custody_ref_sha256=C,
    )


def fixture(tmp_path):
    obj, safe, data_key = sample_verified(tmp_path)
    sealed = create_manifest(obj, safe, data_key)
    return obj, data_key, sealed


def test_p7_integrates_p6_exact_opaque_versions_and_cold_restart(tmp_path):
    _, scratch, _, _, data_key, obj = sealed_fixture(tmp_path)
    aws_writer, aws_reader, b2_writer, b2_reader = clients(obj)
    vault = MemoryOnlyVault()
    sink = p6.OfflinePrivateReceiptSink(
        data_key=data_key, manifest_key=MANIFEST_KEY,
        key_custody_ref_sha256=C, commit_and_readback=escrow(vault),
    )
    safe = p2.replicate_approved_s02(
        obj=obj, key=data_key, authorization=permit(obj),
        aws_writer=aws_writer, aws_reader=aws_reader,
        b2_writer=b2_writer, b2_reader=b2_reader,
        recovery_scratch=scratch, require_private_receipt=True,
        private_receipt_sink=sink,
    )
    assert safe["status"] == "LIVE_S02_TWO_PROVIDER_VERIFIED_LOCAL_RECEIPT_ONLY"
    assert safe["offhost_persistence_verified"] is False
    assert safe["real_provider_operation_authorized"] is False
    sha = safe["private_manifest_sha256"]
    expected = p7._identity(obj.run_id, sha)
    assert vault.writes == [expected]
    assert vault.reads == [expected]
    assert FAKE_AWS_VERSION.encode() not in vault.objects[expected]
    assert obj.object_key.encode() not in vault.objects[expected]
    assert FAKE_AWS_VERSION not in str(safe)
    # Simulated new recovery context: ONLY read-only vault and separately
    # supplied key + public run/digest. No source, writer, or old sink state.
    cold = p7.open_from_independent_escrow(
        read_exact=vault.read_exact, run_id=obj.run_id,
        manifest_sha256=sha, manifest_key=MANIFEST_KEY,
    )
    assert cold.aws_version_id == FAKE_AWS_VERSION
    assert cold.b2_version_id == FAKE_AWS_VERSION
    assert cold.object_key == obj.object_key
    assert vault.reads == [expected, expected]


def test_write_once_duplicate_is_hard_hold_with_no_read_or_retry(tmp_path):
    obj, _, sealed = fixture(tmp_path)
    vault = MemoryOnlyVault()
    escrow(vault)(sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id)
    second = escrow(vault)
    with pytest.raises(p7.ReceiptEscrowRejected, match="no retry"):
        second(sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id)
    assert len(vault.writes) == 2
    assert len(vault.reads) == 1
    assert len(vault.objects) == 1
    with pytest.raises(p7.ReceiptEscrowRejected, match="already attempted"):
        second(sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id)
    assert len(vault.writes) == 2


@pytest.mark.parametrize("fault", ["wrong_ack", "bad_bytes", "missing", "exception"])
def test_untrusted_callback_outcomes_fail_closed_and_redact(tmp_path, fault):
    obj, _, sealed = fixture(tmp_path)
    vault = MemoryOnlyVault()
    events = []
    def writer(key, blob, digest):
        events.append("write")
        if fault == "exception":
            raise RuntimeError("FAKE_SECRET_UNSAFE_TO_LOG")
        vault.objects[key] = blob
        if fault == "wrong_ack":
            return {"status": "OVERWROTE", "key": key, "sha256": digest}
        return {"status": "CREATED_EXCLUSIVELY", "key": key, "sha256": digest}
    def reader(key):
        events.append("read")
        if fault == "missing":
            return None
        if fault == "bad_bytes":
            return vault.objects[key][:-1] + b"!"
        return vault.objects[key]
    adapter = escrow(vault, writer=writer, reader=reader)
    with pytest.raises(p7.ReceiptEscrowRejected) as exc:
        adapter(sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id)
    assert "FAKE_SECRET" not in str(exc.value)
    assert events.count("write") == 1
    assert events.count("read") == (0 if fault in ("wrong_ack", "exception") else 1)
    with pytest.raises(p7.ReceiptEscrowRejected, match="already attempted"):
        adapter(sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id)
    assert events.count("write") == 1


@pytest.mark.parametrize("alter", ["digest", "run_id", "not_bytes", "oversize"])
def test_invalid_write_preflight_has_zero_external_callbacks(tmp_path, alter):
    obj, _, sealed = fixture(tmp_path)
    vault = MemoryOnlyVault()
    payload, sha, run = sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id
    if alter == "digest":
        sha = "0" * 64
    if alter == "run_id":
        run = "../unsafe"
    if alter == "not_bytes":
        payload = bytearray(payload)
    if alter == "oversize":
        payload = sealed.sealed_bytes + b"z" * (p7.MAX_SEALED_BYTES + 1)
    with pytest.raises(p7.ReceiptEscrowRejected):
        escrow(vault)(payload, sha, run)
    assert vault.writes == vault.reads == []


@pytest.mark.parametrize("fault", ["bad_key", "bad_sha", "bad_read", "no_reader"])
def test_cold_restore_fails_closed_without_original_writer(tmp_path, fault):
    obj, _, sealed = fixture(tmp_path)
    vault = MemoryOnlyVault()
    escrow(vault)(sealed.sealed_bytes, sealed.sealed_sha256, obj.run_id)
    key = MANIFEST_KEY
    sha = sealed.sealed_sha256
    reader = vault.read_exact
    if fault == "bad_key":
        key = b"x" * 32
    if fault == "bad_sha":
        sha = "0" * 64
    if fault == "bad_read":
        reader = lambda _: b"private not a manifest"
    if fault == "no_reader":
        reader = None
    with pytest.raises(p7.ReceiptEscrowRejected):
        p7.open_from_independent_escrow(
            read_exact=reader, run_id=obj.run_id,
            manifest_sha256=sha, manifest_key=key,
        )


def test_escrow_configuration_fails_on_shared_or_fake_custody():
    writer = lambda a, b, c: {"status": "CREATED_EXCLUSIVELY", "key": a, "sha256": c}
    reader = lambda a: b""
    for options in (
        {"writer_scope_ref_sha256": "BAD"},
        {"reader_scope_ref_sha256": W},
        {"owner_recovery_custody_ref_sha256": R},
        {"read_exact": writer},
    ):
        config = dict(
            write_once=writer, read_exact=reader,
            writer_scope_ref_sha256=W, reader_scope_ref_sha256=R,
            owner_recovery_custody_ref_sha256=C,
        )
        config.update(options)
        with pytest.raises(p7.ReceiptEscrowRejected):
            p7.OfflineImmutableReceiptEscrow(**config)


def test_p7_cold_reader_never_imports_sdk_cli_network_or_credentials():
    parsed = ast.parse(inspect.getsource(p7))
    imports = set()
    for node in ast.walk(parsed):
        if isinstance(node, ast.Import):
            imports.update(x.name.split(".")[0] for x in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not imports.intersection({
        "boto3", "botocore", "socket", "requests", "urllib",
        "subprocess", "sqlite3",
    })
    source = inspect.getsource(p7)
    assert "os.environ" not in source
    assert 'if __name__ == "__main__"' not in source
    assert "offhost_persistence_verified=True" not in source
    assert "FAKE_AWS_SECRET" not in source
