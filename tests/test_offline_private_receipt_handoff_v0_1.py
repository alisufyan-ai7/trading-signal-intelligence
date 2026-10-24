"""EXP048 P6 — synthetic S02, fake AWS/B2 clients, memory-only manifests."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as p2
from trading_signal_intelligence.recovery import offline_private_receipt_handoff_v0_1 as p6
from trading_signal_intelligence.recovery import private_versioned_restore_manifest_v0_1 as p5

from test_live_sqlite_envelope_v0_1 import sealed_fixture
from test_live_dual_provider_transport_v0_1 import clients, permit

MKEY = b"m" * 32
CUSTODY = "f" * 64
VERSION = "fake-version-0001"


def fake_sink(data_key, *, commit=None, manifest_key=MKEY):
    vault = {}
    def write_once_and_read(blob, digest, run_id):
        assert run_id not in vault, "no overwrite allowed"
        vault[run_id] = blob
        return vault[run_id]
    sink = p6.OfflinePrivateReceiptSink(
        data_key=data_key, manifest_key=manifest_key,
        key_custody_ref_sha256=CUSTODY,
        commit_and_readback=commit or write_once_and_read,
    )
    return sink, vault


def execute(tmp_path, *, sink=None, require=True, aws=None, b2=None):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    if aws == "missing_version":
        aw.no_version = True
    if b2 == "missing_version":
        bw.no_version = True
    if b2 == "corrupt_read":
        br.corrupt = True
    selected = sink(key) if callable(sink) else sink
    result = p2.replicate_approved_s02(
        obj=obj, key=key, authorization=permit(obj),
        aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
        recovery_scratch=scratch,
        require_private_receipt=require, private_receipt_sink=selected,
    )
    return result, (aw, ar, bw, br), obj, scratch, key


def test_raw_exact_versions_handoff_sealed_once_no_public_leak(tmp_path):
    stored = {}
    def committed(blob, digest, run_id):
        if run_id in stored:
            raise AssertionError("duplicate receipt")
        stored[run_id] = blob
        return stored[run_id]
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    sink, _ = fake_sink(key, commit=committed)
    result = p2.replicate_approved_s02(
        obj=obj, key=key, authorization=permit(obj), aws_writer=aw,
        aws_reader=ar, b2_writer=bw, b2_reader=br, recovery_scratch=scratch,
        require_private_receipt=True, private_receipt_sink=sink,
    )
    assert result["status"] == "LIVE_S02_TWO_PROVIDER_VERIFIED_LOCAL_RECEIPT_ONLY"
    assert result["attempted_signed_requests"] == 5
    assert result["offhost_persistence_verified"] is False
    assert result["real_provider_operation_authorized"] is False
    assert len(result["private_manifest_sha256"]) == 64
    assert set(stored) == {obj.run_id}
    sealed = stored[obj.run_id]
    assert VERSION.encode() not in sealed
    assert obj.object_key.encode() not in sealed
    assert VERSION not in str(result)
    assert obj.object_key not in str(result)
    opened = p5.open_private_recovery_manifest(
        sealed=sealed, manifest_key=MKEY,
        expected_sha256=result["private_manifest_sha256"],
    )
    assert opened.aws_version_id == VERSION
    assert opened.b2_version_id == VERSION
    assert opened.object_key == obj.object_key
    assert opened.record_count == obj.record_count
    assert all([aw.called == ["PUT"], ar.called == ["GET"],
                bw.called == ["PUT"], br.called == ["HEAD", "GET"]])
    assert sink._invoked is True
    assert VERSION not in repr(sink)
    assert MKEY.decode() not in repr(sink)


def test_missing_private_receipt_sink_stops_before_any_cloud_call(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    with pytest.raises(p2.LiveTransportRejected, match="not configured"):
        p2.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj),
            aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
            recovery_scratch=scratch, require_private_receipt=True,
        )
    assert all(not x.called for x in (aw, ar, bw, br))


def test_sink_without_explicit_mode_is_rejected_pre_request(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    sink, _ = fake_sink(key)
    with pytest.raises(p2.LiveTransportRejected, match="not configured"):
        p2.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj),
            aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
            recovery_scratch=scratch, private_receipt_sink=sink,
        )
    assert all(not x.called for x in (aw, ar, bw, br))


@pytest.mark.parametrize("error_case", [
    "no_readback", "mismatch_readback", "exception", "bad_ack",
])
def test_failed_private_receipt_commits_never_claim_success_or_retry(tmp_path, error_case):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    calls = []
    def commit(blob, digest, run_id):
        calls.append(run_id)
        if error_case == "exception":
            raise RuntimeError("fake secret should never be logged")
        if error_case == "no_readback":
            return None
        return blob[:-1] + bytes([blob[-1] ^ 1])
    if error_case == "bad_ack":
        def callback(o, public, versions):
            calls.append(o.run_id)
            return {"status": "FAKE_OK", "access_key": "never-log"}
        sink = callback
    else:
        sink, _ = fake_sink(key, commit=commit)
    with pytest.raises(p2.LiveTransportRejected,
                       match="private recovery manifest handoff failed"):
        p2.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj), aws_writer=aw,
            aws_reader=ar, b2_writer=bw, b2_reader=br, recovery_scratch=scratch,
            require_private_receipt=True, private_receipt_sink=sink,
        )
    assert calls == [obj.run_id]  # exactly once, no retries
    assert aw.called == ["PUT"] and bw.called == ["PUT"]
    assert ar.called == ["GET"] and br.called == ["HEAD", "GET"]


@pytest.mark.parametrize("bad", ["aws_version", "b2_version", "b2_corrupt"])
def test_incomplete_provider_chain_never_calls_private_version_sink(tmp_path, bad):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    if bad == "aws_version":
        aw.no_version = True
    elif bad == "b2_version":
        bw.no_version = True
    elif bad == "b2_corrupt":
        br.corrupt = True
    calls = []
    def no_sink_call(*args):
        calls.append(1)
        raise RuntimeError("should never invoke")
    with pytest.raises(p2.LiveTransportRejected):
        p2.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj), aws_writer=aw,
            aws_reader=ar, b2_writer=bw, b2_reader=br, recovery_scratch=scratch,
            require_private_receipt=True, private_receipt_sink=no_sink_call,
        )
    assert not calls


def test_private_sink_one_shot_never_replays_after_commit_error(tmp_path):
    _, _, _, _, key, obj = sealed_fixture(tmp_path)
    called = []
    def broken_readback(blob, digest, run_id):
        called.append(1)
        raise RuntimeError("do not leak")
    sink, _ = fake_sink(key, commit=broken_readback)
    safe = {"status": "NOT_A_VERIFIED_RECEIPT"}
    for attempt in range(2):
        with pytest.raises(p6.ReceiptHandoffRejected):
            sink(obj, safe, (VERSION, VERSION))
    assert called == []  # sealing refuses unverified receipt before commit
    assert sink._invoked is True


def test_private_sink_configuration_rejects_shared_keys_or_bad_custody():
    for kwargs in (
        {"data_key": MKEY, "manifest_key": MKEY},
        {"data_key": b"x" * 31, "manifest_key": MKEY},
        {"data_key": b"k" * 32, "manifest_key": MKEY,
         "key_custody_ref_sha256": "BAD"},
    ):
        opts = {"data_key": b"k" * 32, "manifest_key": MKEY,
                "key_custody_ref_sha256": CUSTODY,
                "commit_and_readback": lambda data, sha, run: data}
        opts.update(kwargs)
        with pytest.raises(p6.ReceiptHandoffRejected):
            p6.OfflinePrivateReceiptSink(**opts)


def test_private_sink_imports_no_real_cloud_client_socket_or_entrypoint():
    parsed = ast.parse(inspect.getsource(p6))
    imports = set()
    for node in parsed.body:
        if isinstance(node, ast.Import):
            imports.update(e.name.split(".")[0] for e in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not imports.intersection({
        "boto3", "botocore", "requests", "socket", "urllib", "sqlite3", "subprocess",
    })
    assert "os.environ" not in inspect.getsource(p6)
    assert 'if __name__ == "__main__"' not in inspect.getsource(p6)
