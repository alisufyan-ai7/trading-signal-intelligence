"""EXP050 P8: no-network cold recovery + partial-provider failure fixtures."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as p2
from trading_signal_intelligence.recovery import offline_private_receipt_handoff_v0_1 as p6
from trading_signal_intelligence.recovery import offline_synthetic_cold_disaster_drill_v0_1 as p8
from test_live_sqlite_envelope_v0_1 import sealed_fixture
from test_live_dual_provider_transport_v0_1 import clients, permit
from test_offline_immutable_receipt_escrow_v0_1 import MemoryOnlyVault, escrow, C
from test_private_versioned_restore_manifest_v0_1 import MANIFEST_KEY, FAKE_AWS_VERSION


def fixture(tmp_path):
    # Setup uses only a three-record SQLite SYNTHETIC source.
    _, scratch, _, _, data_key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    vault = MemoryOnlyVault()
    sink = p6.OfflinePrivateReceiptSink(
        data_key=data_key, manifest_key=MANIFEST_KEY,
        key_custody_ref_sha256=C,
        commit_and_readback=escrow(vault),
    )
    summary = p2.replicate_approved_s02(
        obj=obj, key=data_key, authorization=permit(obj),
        aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
        recovery_scratch=scratch, require_private_receipt=True,
        private_receipt_sink=sink,
    )
    assert summary["status"] == "LIVE_S02_TWO_PROVIDER_VERIFIED_LOCAL_RECEIPT_ONLY"
    assert summary["offhost_persistence_verified"] is False
    digest = summary["private_manifest_sha256"]
    receipt_key = next(iter(vault.objects))
    assert receipt_key.endswith(digest + ".aesgcm")
    ciphertext_receipt = vault.objects[receipt_key]
    # Completely separate fake recovery reader, without retaining vault writer
    # or sink in the recovery object.
    receipt_reader = p8.SyntheticMemoryEscrowReader(
        run_id=obj.run_id, manifest_sha256=digest,
        ciphertext=ciphertext_receipt,
    )
    aws_reader = p8.SyntheticMemoryVersionReader(
        provider=p2.AWS.name, object_key=obj.object_key,
        version_id=FAKE_AWS_VERSION, envelope=obj.envelope,
    )
    b2_reader = p8.SyntheticMemoryVersionReader(
        provider=p2.B2.name, object_key=obj.object_key,
        version_id=FAKE_AWS_VERSION, envelope=obj.envelope,
    )
    cold_scratch = tmp_path / "isolated-p8-cold-recovery"
    cold_scratch.mkdir()
    return {
        "escrow_reader": receipt_reader, "aws_reader": aws_reader,
        "b2_reader": b2_reader, "run_id": obj.run_id,
        "manifest_sha256": digest, "manifest_key": MANIFEST_KEY,
        "data_key": data_key, "scratch_parent": cold_scratch,
    }, obj, vault, sink


def test_two_independent_synthetic_versioned_restores_from_cold_receipt(tmp_path):
    args, obj, old_vault, old_sink = fixture(tmp_path)
    # old state references are not passed to recovery; only unrelated cold
    # reader, AES keys and two memory-only provider readers.
    result = p8.run_synthetic_cold_disaster_drill(**args)
    assert result["status"] == "SYNTHETIC_DUAL_PROVIDER_RESTORED"
    assert result["aws_restore"] == "VERIFIED"
    assert result["b2_restore"] == "VERIFIED"
    assert result["verified_provider_count"] == 2
    assert result["verified_record_count"] == 3
    assert result["independent_escrow_used"] is True
    assert result["real_offhost_restore_proven"] is False
    assert result["live_provider_requests_authorized"] is False
    assert result["production_resume_authorized"] is False
    assert result["operator_action"] == "NO_LIVE_ACTION"
    assert args["escrow_reader"].read_calls == 1
    assert args["aws_reader"].read_calls == 1
    assert args["b2_reader"].read_calls == 1
    assert (args["scratch_parent"] / "p8-aws-restore-0001" / "forward.sqlite").is_file()
    assert (args["scratch_parent"] / "p8-b2-restore-0001" / "forward.sqlite").is_file()
    assert obj.object_key not in str(result)
    assert FAKE_AWS_VERSION not in str(result)
    assert "REDAC" in repr(args["escrow_reader"])
    assert "REDAC" in repr(args["aws_reader"])


@pytest.mark.parametrize("failed_provider", ["aws", "b2"])
@pytest.mark.parametrize("failure", ["offline", "missing", "corrupt"])
def test_one_provider_down_returns_degraded_hold_no_retry(tmp_path, failed_provider, failure):
    args, obj, _, _ = fixture(tmp_path)
    key = failed_provider + "_reader"
    args[key]._fault = failure
    result = p8.run_synthetic_cold_disaster_drill(**args)
    assert result["status"] == "SYNTHETIC_ONE_PROVIDER_RESTORED_DEGRADED"
    assert result["verified_provider_count"] == 1
    assert result[failed_provider + "_restore"] == "HOLD"
    assert result[("b2" if failed_provider == "aws" else "aws") + "_restore"] == "VERIFIED"
    assert result["operator_action"] == "HOLD_AND_INVESTIGATE"
    assert result["production_resume_authorized"] is False
    assert args["aws_reader"].read_calls == args["b2_reader"].read_calls == 1
    assert args["escrow_reader"].read_calls == 1
    assert obj.object_key not in str(result)


def test_both_providers_unavailable_hard_stop_with_one_attempt_each(tmp_path):
    args, _, _, _ = fixture(tmp_path)
    args["aws_reader"]._fault = "offline"
    args["b2_reader"]._fault = "missing"
    with pytest.raises(p8.OfflineColdDrillRejected, match="no retry"):
        p8.run_synthetic_cold_disaster_drill(**args)
    assert args["aws_reader"].read_calls == 1
    assert args["b2_reader"].read_calls == 1
    assert args["escrow_reader"].read_calls == 1


@pytest.mark.parametrize("fault", ["bad_data_key", "bad_manifest_key", "bad_manifest_hash", "bad_receipt"])
def test_wrong_keys_or_cold_receipt_digest_fail_closed(tmp_path, fault):
    args, _, _, _ = fixture(tmp_path)
    if fault == "bad_data_key":
        args["data_key"] = b"w" * 32
    if fault == "bad_manifest_key":
        args["manifest_key"] = b"w" * 32
    if fault == "bad_manifest_hash":
        args["manifest_sha256"] = "0" * 64
    if fault == "bad_receipt":
        args["escrow_reader"]._bytes = args["escrow_reader"]._bytes[:-1] + b"Z"
    if fault == "bad_data_key":
        with pytest.raises(p8.OfflineColdDrillRejected, match="no retry"):
            p8.run_synthetic_cold_disaster_drill(**args)
        assert args["aws_reader"].read_calls == args["b2_reader"].read_calls == 1
    else:
        with pytest.raises(p8.OfflineColdDrillRejected, match="escrow preflight"):
            p8.run_synthetic_cold_disaster_drill(**args)
        assert args["aws_reader"].read_calls == args["b2_reader"].read_calls == 0


def test_untrusted_wrong_exact_version_cannot_be_substituted(tmp_path):
    args, _, _, _ = fixture(tmp_path)
    args["aws_reader"]._version = "fake-wrong-version"
    result = p8.run_synthetic_cold_disaster_drill(**args)
    assert result["aws_restore"] == "HOLD"
    assert result["b2_restore"] == "VERIFIED"
    assert result["production_resume_authorized"] is False


def test_wrong_provider_reader_order_fails_before_any_escrow_or_sdk(tmp_path):
    args, _, _, _ = fixture(tmp_path)
    args["aws_reader"], args["b2_reader"] = args["b2_reader"], args["aws_reader"]
    with pytest.raises(p8.OfflineColdDrillRejected, match="preflight"):
        p8.run_synthetic_cold_disaster_drill(**args)
    assert args["escrow_reader"].read_calls == 0
    assert args["aws_reader"].read_calls == args["b2_reader"].read_calls == 0


def test_real_network_capable_reader_objects_rejected_before_any_call(tmp_path):
    args, _, _, _ = fixture(tmp_path)
    invoked = []
    def malicious_external_reader(*a, **kw):
        invoked.append(1)
        raise RuntimeError("fake-callback-contacted")
    args["aws_reader"] = malicious_external_reader
    with pytest.raises(p8.OfflineColdDrillRejected, match="preflight"):
        p8.run_synthetic_cold_disaster_drill(**args)
    args, _, _, _ = fixture(tmp_path / "another")
    # Other injection attempt: a callable masquerading as receipt reader.
    args["escrow_reader"] = malicious_external_reader
    with pytest.raises(p8.OfflineColdDrillRejected, match="preflight"):
        p8.run_synthetic_cold_disaster_drill(**args)
    assert invoked == []


def test_source_imports_are_sdk_network_cli_and_environment_free():
    source = inspect.getsource(p8)
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(x.name.split(".")[0] for x in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not imports.intersection({
        "boto3", "botocore", "socket", "requests", "urllib", "subprocess",
        "sqlite3", "http", "asyncio", "multiprocessing",
    })
    assert "os.environ" not in source
    assert 'if __name__ == "__main__"' not in source
    assert "real_offhost_restore_proven=True" not in source
    assert "production_resume_authorized=True" not in source
