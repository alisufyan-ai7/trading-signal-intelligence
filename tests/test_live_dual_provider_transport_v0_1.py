"""No provider networking: fake boto3 clients exercise all five signed call gates."""
from __future__ import annotations

import ast
import io
import inspect
from types import SimpleNamespace

import pytest

from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as cloud
from test_live_sqlite_envelope_v0_1 import sealed_fixture


class FakeNoSuchKey(Exception):
    response = {
        "Error": {"Code": "404"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }


class FakeEvents:
    def __init__(self):
        self.hooks = []
    def register(self, event, callback):
        assert event == "before-send.s3"
        self.hooks.append(callback)
    def fire(self, request):
        for callback in self.hooks:
            callback(request)


class FakeS3:
    def __init__(self, provider, *, corrupt=False, bad_sig=False, no_version=False):
        self.provider = provider
        self.corrupt = corrupt
        self.bad_sig = bad_sig
        self.no_version = no_version
        self.events = FakeEvents()
        self.called = []
        cfg = SimpleNamespace(
            retries={"total_max_attempts": 1}, signature_version="s3v4",
            connect_timeout=5, read_timeout=15,
        )
        self.meta = SimpleNamespace(
            endpoint_url=provider.endpoint, region_name=provider.region,
            config=cfg, events=self.events,
        )
        self.stored = None

    def _emit(self, method, kwargs):
        self.called.append(method)
        headers = {
            "authorization": "AWS4-HMAC-SHA256 Credential=FAKE/"
                             f"20261023/{self.provider.region}/s3/aws4_request",
        }
        if method == "PUT":
            headers["content-length"] = str(kwargs["ContentLength"])
            headers["content-type"] = kwargs["ContentType"]
            if "IfNoneMatch" in kwargs:
                headers["if-none-match"] = kwargs["IfNoneMatch"]
        query = "?versionId=fake-version-0001" if method == "GET" else ""
        request = SimpleNamespace(
            method=method,
            url=(self.provider.endpoint + "/" + self.provider.bucket + "/" +
                 kwargs["Key"] + query),
            headers=headers,
            body=io.BytesIO(kwargs["Body"]) if method == "PUT" else b"",
        )
        if self.bad_sig:
            request.headers["authorization"] = "Not-a-SigV4"
        self.events.fire(request)

    def put_object(self, **kwargs):
        self._emit("PUT", kwargs)
        self.stored = kwargs["Body"]
        return {} if self.no_version else {"VersionId": "fake-version-0001"}

    def get_object(self, **kwargs):
        self._emit("GET", kwargs)
        # Another stub client may have handled PUT. The expected authenticated
        # object is injected into readers by the test; never external data.
        body = self.stored if not self.corrupt else (
            self.stored[:-1] + bytes([self.stored[-1] ^ 1])
        )
        return {"VersionId": "fake-version-0001", "ContentLength": len(body),
                "Body": io.BytesIO(body)}

    def head_object(self, **kwargs):
        self._emit("HEAD", kwargs)
        raise FakeNoSuchKey()


def permit(sealed, *, token=cloud.APPROVAL):
    return cloud.ReleaseAuthorization(
        token, "a" * 64, "b" * 64, "c" * 64, "d" * 64,
        (cloud.AWS.bucket, cloud.B2.bucket),
        (cloud.AWS.region, cloud.B2.region),
    )


def clients(sealed, *, corrupt=False, bad_sig=False, no_version=False):
    aw = FakeS3(cloud.AWS, bad_sig=bad_sig, no_version=no_version)
    ar = FakeS3(cloud.AWS, corrupt=corrupt)
    bw = FakeS3(cloud.B2)
    br = FakeS3(cloud.B2)
    # Mock writer's remote object, not real account data.
    ar.stored = sealed.envelope
    br.stored = sealed.envelope
    return aw, ar, bw, br


def test_two_provider_five_signed_operations_and_restored_ledgers(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    result = cloud.replicate_approved_s02(
        obj=obj, key=key, authorization=permit(obj),
        aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
        recovery_scratch=scratch,
    )
    assert result["status"] == "LIVE_S02_TWO_PROVIDER_VERIFIED"
    assert result["attempted_signed_requests"] == 5
    assert [x["verified_records"] for x in result["receipts"]] == [3, 3]
    assert aw.called == ["PUT"]
    assert ar.called == ["GET"]
    assert bw.called == ["PUT"]
    assert br.called == ["HEAD", "GET"]


def test_no_release_permission_no_sdk_request(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aws_writer, aws_reader, b2_writer, b2_reader = clients(obj)
    with pytest.raises(cloud.LiveTransportRejected):
        cloud.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj, token="NOT_APPROVED"),
            aws_writer=aws_writer, aws_reader=aws_reader,
            b2_writer=b2_writer, b2_reader=b2_reader,
            recovery_scratch=scratch,
        )
    assert all(not c.called for c in (aws_writer, aws_reader, b2_writer, b2_reader))


def test_invalid_client_config_blocks_all_requests(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    bw.meta.config.retries["total_max_attempts"] = 3
    with pytest.raises(cloud.LiveTransportRejected):
        cloud.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj),
            aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
            recovery_scratch=scratch,
        )
    assert not aw.called


@pytest.mark.parametrize("bad_case", ["bad_signature", "bad_version", "corrupt_read"])
def test_first_provider_ambiguity_fail_closed_no_b2_attempt(tmp_path, bad_case):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(
        obj, corrupt=bad_case == "corrupt_read",
        bad_sig=bad_case == "bad_signature",
        no_version=bad_case == "bad_version",
    )
    with pytest.raises(cloud.LiveTransportRejected):
        cloud.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj),
            aws_writer=aw, aws_reader=ar, b2_writer=bw, b2_reader=br,
            recovery_scratch=scratch,
        )
    assert not bw.called and not br.called


def test_duplicate_before_send_denied_without_retry(tmp_path):
    _, _, _, _, _, obj = sealed_fixture(tmp_path)
    wire = cloud._WireFence(obj)
    wire.before_call(cloud.AWS, "writer", "PUT", None)
    client = FakeS3(cloud.AWS)
    client.events.register("before-send.s3", wire.hook)
    request = {
        "Body": obj.envelope, "ContentLength": len(obj.envelope),
        "ContentType": "application/octet-stream",
        "IfNoneMatch": "*", "Key": obj.object_key,
    }
    client._emit("PUT", request)
    with pytest.raises(cloud.LiveTransportRejected, match="duplicate"):
        client._emit("PUT", request)


def test_source_has_no_ambient_credential_or_client_construction():
    tree = ast.parse(inspect.getsource(cloud))
    names = {x.id for x in ast.walk(tree) if isinstance(x, ast.Name)}
    assert names.isdisjoint({"boto3", "botocore", "getpass", "os", "socket"})
    assert cloud.MAX_REQUESTS == 5
    assert cloud.AWS.bucket != cloud.B2.bucket



def test_invalid_aead_key_stops_before_any_provider_call(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    with pytest.raises(cloud.LiveTransportRejected, match="pre-transfer"):
        cloud.replicate_approved_s02(
            obj=obj, key=b"wrong-encryption-key-wrong-encry"[:32],
            authorization=permit(obj), aws_writer=aw, aws_reader=ar,
            b2_writer=bw, b2_reader=br, recovery_scratch=scratch,
        )
    assert not any(c.called for c in (aw, ar, bw, br))


def test_preflight_rollback_is_never_overwritten(tmp_path):
    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    aw, ar, bw, br = clients(obj)
    cloud.replicate_approved_s02(
        obj=obj, key=key, authorization=permit(obj), aws_writer=aw,
        aws_reader=ar, b2_writer=bw, b2_reader=br, recovery_scratch=scratch,
    )
    newer = clients(obj)
    with pytest.raises(cloud.LiveTransportRejected, match="pre-transfer"):
        cloud.replicate_approved_s02(
            obj=obj, key=key, authorization=permit(obj),
            aws_writer=newer[0], aws_reader=newer[1],
            b2_writer=newer[2], b2_reader=newer[3],
            recovery_scratch=scratch,
        )
    assert all(not c.called for c in newer)
