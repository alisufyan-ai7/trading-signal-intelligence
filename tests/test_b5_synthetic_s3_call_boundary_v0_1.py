"""EXP039 offline-only method/ordering guard tests; all provider clients are fake."""
from __future__ import annotations

import hashlib
import io
from dataclasses import replace

import pytest

from scripts import exp038_offline_synthetic_pilot as offline
from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4
from trading_signal_intelligence.recovery import b5_synthetic_s3_call_boundary_v0_1 as b5

FAKE_KEY = bytes(range(32))


def fixture(tmp_path):
    root = tmp_path / "vowsig-b1b2-fixture-exp039"
    root.mkdir()
    copied = offline._create_disposable_synthetic_fixture(root)
    obj = b3.seal_captured_synthetic_s02(root, copied, artifact_id="exp039", key=FAKE_KEY)
    return root, copied, obj


def clients(obj):
    aws = offline._MemoryStore(b4.AWS)
    b2 = offline._MemoryStore(b4.B2)
    aw, ar, ag = b5.guard_pair(
        b4.AWS,
        offline._MemoryClient(aws, role="writer"),
        offline._MemoryClient(aws, role="reader"), obj)
    bw, br, bg = b5.guard_pair(
        b4.B2,
        offline._MemoryClient(b2, role="writer"),
        offline._MemoryClient(b2, role="reader"), obj)
    return aws, b2, aw, ar, ag, bw, br, bg


def put_args(obj, *, aws=True):
    arguments = {
        "Bucket": b4.AWS.bucket if aws else b4.B2.bucket,
        "Key": obj.object_key,
        "Body": obj.envelope,
        "ContentLength": len(obj.envelope),
        "ContentType": "application/octet-stream",
    }
    if aws:
        arguments["IfNoneMatch"] = "*"
    return arguments


def test_constructor_does_not_call_provider(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws, b2, _, _, ag, _, _, bg = clients(obj)
    assert not aws.calls and not b2.calls
    assert ag.calls == [] and bg.calls == []


def test_full_b4_two_provider_independent_restores_via_b5_guard(tmp_path):
    root, copied, obj = fixture(tmp_path)
    aws, b2, aw, ar, ag, bw, br, bg = clients(obj)
    result = b4.run_two_provider_pilot(
        fixture_root=root, captured_source=copied, obj=obj, key=FAKE_KEY,
        aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
        network_approved=True, approval_phrase=b4.APPROVAL_PHRASE,
    )
    assert result["actual_attempted_requests"] == 5
    assert result["protection_class"] == "SYNTHETIC_ONLY_NOT_REAL_APPLICATION_BACKUP"
    assert ag.calls == aws.calls == ["PUT", "GET"]
    assert bg.calls == b2.calls == ["HEAD", "PUT", "GET"]
    assert ag.next_step == bg.next_step == "DONE"
    assert ag.poisoned and bg.poisoned
    original_hash = hashlib.sha256(copied.read_bytes()).hexdigest()
    for name in ("awsrestore", "b2restore"):
        restored = root / "restored" / name / "forward.sqlite"
        assert restored.exists()
        assert hashlib.sha256(restored.read_bytes()).hexdigest() == original_hash
    # These are IN-PROCESS fake clients only; no network transport exists.
    assert len(aws.objects) == len(b2.objects) == 1


def test_guard_blocks_out_of_order_aws_get_and_any_aws_head(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws, _, aw, ar, ag, _, _, _ = clients(obj)
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        ar.get_object(Bucket=b4.AWS.bucket, Key=obj.object_key, VersionId="test")
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        ar.head_object(Bucket=b4.AWS.bucket, Key=obj.object_key)
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        aw.get_object(Bucket=b4.AWS.bucket, Key=obj.object_key, VersionId="test")
    assert not aws.calls and ag.calls == []


def test_guard_denies_role_swaps_and_unapproved_client_methods(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws, _, aw, ar, _, _, _, _ = clients(obj)
    assert not hasattr(aw, "delete_object")
    assert not hasattr(ar, "list_objects")
    assert not hasattr(aw, "create_bucket")
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        ar.put_object(**put_args(obj))
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        aw.head_object(Bucket=b4.AWS.bucket, Key=obj.object_key)
    assert aws.calls == []


def test_guard_denies_wrong_bucket_key_payload_and_optional_headers(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws, _, aw, _, _, _, _, _ = clients(obj)
    tampered_requests = (
        {**put_args(obj), "Bucket": "unrelated-bucket"},
        {**put_args(obj), "Key": "pilot/wrong"},
        {**put_args(obj), "Body": b"not-the-envelope", "ContentLength": 16},
        {**put_args(obj), "ACL": "public-read"},
        {**put_args(obj), "IfNoneMatch": "bad"},
    )
    for args in tampered_requests:
        with pytest.raises(b5.SyntheticS3BoundaryRejected):
            aw.put_object(**args)
    assert aws.calls == []


def test_guard_denies_second_put_after_first_success(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws, _, aw, _, ag, _, _, _ = clients(obj)
    assert aw.put_object(**put_args(obj))["VersionId"] == "synthetic-offline-v1"
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        aw.put_object(**put_args(obj))
    assert aws.calls == ag.calls == ["PUT"]


def test_guard_poisoned_after_missing_put_version_no_retry(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws, _, aw, _, ag, _, _, _ = clients(obj)
    # Fake 'unverified version': underlying writes but returns no valid receipt.
    def ambiguous_put(**args):
        aws.calls.append("PUT")
        return {}
    aw._underlying.put_object = ambiguous_put
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        aw.put_object(**put_args(obj))
    assert ag.poisoned
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        aw.put_object(**put_args(obj))
    assert aws.calls == ["PUT"]


def test_b2_head_403_poisoned_cannot_upload(tmp_path):
    _, _, obj = fixture(tmp_path)
    _, b2, _, _, _, bw, br, bg = clients(obj)
    def denied_head(**kwargs):
        b2.calls.append("HEAD")
        class Forbidden(Exception):
            response = {
                "Error": {"Code": "AccessDenied"},
                "ResponseMetadata": {"HTTPStatusCode": 403},
            }
        raise Forbidden("SECRET SHOULD NOT LEAK")
    br._underlying.head_object = denied_head
    with pytest.raises(b5.SyntheticS3BoundaryRejected, match="inconclusive") as err:
        br.head_object(Bucket=b4.B2.bucket, Key=obj.object_key)
    assert "SECRET" not in str(err.value)
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        bw.put_object(**put_args(obj, aws=False))
    assert bg.poisoned and b2.calls == ["HEAD"]


def test_b2_404_allows_one_write_and_one_get(tmp_path):
    _, _, obj = fixture(tmp_path)
    _, b2, _, _, _, bw, br, bg = clients(obj)
    with pytest.raises(Exception) as notfound:
        br.head_object(Bucket=b4.B2.bucket, Key=obj.object_key)
    response = getattr(notfound.value, "response", None)
    assert response["Error"]["Code"] == "404"
    assert bg.next_step == "PUT" and not bg.poisoned
    assert bw.put_object(**put_args(obj, aws=False))["VersionId"] == "synthetic-offline-v1"
    assert br.get_object(
        Bucket=b4.B2.bucket, Key=obj.object_key, VersionId="synthetic-offline-v1"
    )["VersionId"] == "synthetic-offline-v1"
    assert bg.poisoned
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        br.get_object(
            Bucket=b4.B2.bucket, Key=obj.object_key, VersionId="synthetic-offline-v1"
        )
    assert b2.calls == ["HEAD", "PUT", "GET"]


def test_guard_rejects_invalid_client_config_and_wrong_manifest(tmp_path):
    _, _, obj = fixture(tmp_path)
    aws = offline._MemoryStore(b4.AWS)
    writer = offline._MemoryClient(aws, role="writer")
    reader = offline._MemoryClient(aws, role="reader")
    writer.meta.endpoint_url = "https://example.invalid"
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        b5.guard_pair(b4.AWS, writer, reader, obj)
    assert not aws.calls
    writer.meta.endpoint_url = b4.AWS.endpoint
    forged = replace(obj, envelope_sha256="0" * 64)
    with pytest.raises(b5.SyntheticS3BoundaryRejected):
        b5.guard_pair(b4.AWS, writer, reader, forged)
    assert not aws.calls


def test_source_does_not_construct_live_network_clients():
    import inspect
    text = inspect.getsource(b5)
    assert "import boto3" not in text
    assert "import botocore" not in text
    assert "import requests" not in text
    assert "import socket" not in text
    assert "os.environ" not in text
    assert "os.getenv" not in text
    assert "subprocess" not in text
    assert "if __name__" not in text
