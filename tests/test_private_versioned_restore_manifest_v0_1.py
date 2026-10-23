"""EXP047 P5 synthetic SQLite and fake provider receipts ONLY; no cloud access."""
from __future__ import annotations

import ast
import hashlib
import inspect

import pytest

from trading_signal_intelligence.recovery import private_versioned_restore_manifest_v0_1 as vault
from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as p2
from test_live_sqlite_envelope_v0_1 import sealed_fixture
from test_live_dual_provider_transport_v0_1 import clients, permit


MANIFEST_KEY = b"m" * 32
SOURCE_KEY = b"k" * 32
FAKE_AWS_VERSION = "fake-version-0001"
FAKE_B2_VERSION = "fake-version-0001"
CUSTODY_REF = "f" * 64


def sample_verified(tmp_path):
    _, scratch, _, _, data_key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    result = p2.replicate_approved_s02(
        obj=obj, key=data_key, authorization=permit(obj),
        aws_writer=aw, aws_reader=ar,
        b2_writer=bw, b2_reader=br, recovery_scratch=scratch,
    )
    assert result["status"] == "LIVE_S02_TWO_PROVIDER_VERIFIED"
    assert result["attempted_signed_requests"] == 5
    return obj, result, data_key


def create_manifest(obj, result, data_key, *, manifest_key=MANIFEST_KEY,
                    versions=(FAKE_AWS_VERSION, FAKE_B2_VERSION)):
    return vault.seal_private_recovery_manifest(
        obj=obj,
        verified_result=result,
        version_ids=versions,
        manifest_key=manifest_key,
        data_key=data_key,
        offhost_key_custody_reference_sha256=CUSTODY_REF,
    )


def test_immutable_two_provider_receipts_roundtrip_only_in_encrypted_envelope(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    sealed = create_manifest(obj, result, key)
    assert sealed.sealed_bytes.startswith(vault.MAGIC)
    assert FAKE_AWS_VERSION.encode() not in sealed.sealed_bytes
    assert obj.object_key.encode() not in sealed.sealed_bytes
    assert obj.envelope not in sealed.sealed_bytes
    restored = vault.open_private_recovery_manifest(
        sealed=sealed.sealed_bytes,
        manifest_key=MANIFEST_KEY,
        expected_sha256=sealed.sealed_sha256,
    )
    assert restored.object_key == obj.object_key
    assert restored.aws_version_id == FAKE_AWS_VERSION
    assert restored.b2_version_id == FAKE_B2_VERSION
    assert restored.plaintext_sha256 == obj.plaintext_sha256
    assert restored.record_count == 3
    assert restored.key_custody_reference_sha256 == CUSTODY_REF
    safe = vault.public_receipt_summary(sealed)
    assert safe["real_provider_operation_authorized"] is False
    assert safe["offhost_persistence_verified"] is False
    assert set(safe) == {
        "status", "manifest_sha256", "run_id",
        "real_provider_operation_authorized", "offhost_persistence_verified",
    }
    assert FAKE_AWS_VERSION not in str(safe)
    assert obj.object_key not in str(safe)


def test_ciphertext_corruption_wrong_key_and_wrong_digest_are_rejected(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    sealed = create_manifest(obj, result, key)
    bad = sealed.sealed_bytes[:-1] + bytes([sealed.sealed_bytes[-1] ^ 1])
    for envelope, secret, expected in (
        (bad, MANIFEST_KEY, hashlib.sha256(bad).hexdigest()),
        (sealed.sealed_bytes, b"w" * 32, sealed.sealed_sha256),
        (sealed.sealed_bytes, MANIFEST_KEY, "0" * 64),
        (sealed.sealed_bytes[:-7], MANIFEST_KEY, "0" * 64),
    ):
        with pytest.raises(vault.PrivateManifestRejected):
            vault.open_private_recovery_manifest(
                sealed=envelope, manifest_key=secret, expected_sha256=expected,
            )


def test_manifest_and_backup_data_keys_must_be_distinct(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    with pytest.raises(vault.PrivateManifestRejected, match="independent"):
        create_manifest(obj, result, key, manifest_key=key)


@pytest.mark.parametrize("tamper", [
    lambda r: r.update({"status": "LIVE_S02_PARTIAL_ONLY"}),
    lambda r: r.update({"attempted_signed_requests": 4}),
    lambda r: r.update({"attempted_signed_requests": True}),
    lambda r: r.update({"receipts": r["receipts"][:1]}),
    lambda r: r["receipts"].reverse(),
    lambda r: r["receipts"][0].update({"verified_records": 1}),
    lambda r: r["receipts"][0].update({"version_sha256": "0" * 64}),
    lambda r: r["receipts"][1].update({"object_sha256": "0" * 64}),
    lambda r: r["receipts"][1].update({"region": "us-west-2"}),
    lambda r: r["receipts"][1].update({"provider": "AWS_S3"}),
    lambda r: r["receipts"][0].update({"surprise_access_key": "DO_NOT_LOG"}),
    lambda r: r.update({"data_rights_ref_sha256": "BAD"}),
    lambda r: r.update({"extra_evidence": "DO_NOT_LOG"}),
])
def test_incomplete_or_forged_software_receipt_is_rejected(tmp_path, tamper):
    obj, result, key = sample_verified(tmp_path)
    tamper(result)
    with pytest.raises(vault.PrivateManifestRejected):
        create_manifest(obj, result, key)


@pytest.mark.parametrize("ids", [
    ("other-version", FAKE_B2_VERSION),
    (FAKE_AWS_VERSION, "other-version"),
    ("", FAKE_B2_VERSION),
    ("a" * 513, FAKE_B2_VERSION),
    ("with\nnewline", FAKE_B2_VERSION),
    (FAKE_AWS_VERSION, "with\x00control"),
    (FAKE_AWS_VERSION, 123),
    (FAKE_AWS_VERSION, "unicode-λ"),
])
def test_unmatched_or_nonportable_exact_version_ids_fail_closed(tmp_path, ids):
    obj, result, key = sample_verified(tmp_path)
    with pytest.raises(vault.PrivateManifestRejected):
        create_manifest(obj, result, key, versions=ids)


def test_manifest_requires_existing_two_independently_authenticated_restores(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    for idx in (0, 1):
        mutated = {
            **result,
            "receipts": [dict(entry) for entry in result["receipts"]],
        }
        mutated["receipts"][idx]["verified_records"] = 0
        with pytest.raises(vault.PrivateManifestRejected):
            create_manifest(obj, mutated, key)


def test_random_nonce_makes_two_seals_unique_without_exposing_metadata(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    first = create_manifest(obj, result, key)
    second = create_manifest(obj, result, key)
    assert first.sealed_sha256 != second.sealed_sha256
    assert first.sealed_bytes != second.sealed_bytes
    assert vault.open_private_recovery_manifest(
        sealed=second.sealed_bytes,
        manifest_key=MANIFEST_KEY,
        expected_sha256=second.sealed_sha256,
    ).object_sha256 == obj.envelope_sha256


def test_no_sdk_network_filesystem_or_ambient_credential_io():
    src = inspect.getsource(vault)
    tree = ast.parse(src)
    imports = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            imports.update(item.name.split(".")[0] for item in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint({
        "boto3", "botocore", "requests", "socket", "urllib", "subprocess",
        "sqlite3", "pathlib",
    })
    assert 'if __name__ == "__main__"' not in src
    assert "os.environ" not in src
    assert "offhost_persistence_verified" in src


def test_public_summary_rejects_corrupted_ciphertext_object(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    sealed = create_manifest(obj, result, key)
    broken = vault.SealedRecoveryManifest(
        sealed_bytes=b"corrupted" + sealed.sealed_bytes[9:],
        sealed_sha256=sealed.sealed_sha256,
        run_id=sealed.run_id,
    )
    with pytest.raises(vault.PrivateManifestRejected):
        vault.public_receipt_summary(broken)



def test_dataclass_repr_must_not_expose_private_versions_or_ciphertext(tmp_path):
    obj, result, key = sample_verified(tmp_path)
    sealed = create_manifest(obj, result, key)
    opened = vault.open_private_recovery_manifest(
        sealed=sealed.sealed_bytes, manifest_key=MANIFEST_KEY,
        expected_sha256=sealed.sealed_sha256,
    )
    assert "sealed_bytes=" not in repr(sealed)
    assert "object_key=" not in repr(opened)
    assert "aws_version_id=" not in repr(opened)
    assert "b2_version_id=" not in repr(opened)
    assert FAKE_AWS_VERSION not in repr(opened)
    assert obj.object_key not in repr(opened)
