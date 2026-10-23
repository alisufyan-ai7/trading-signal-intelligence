"""EXP041 offline fake S3 before-send hook safety and B4/B5 integration tests."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from urllib.parse import quote
import hashlib

import pytest

from scripts import exp038_offline_synthetic_pilot as offline
from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4
from trading_signal_intelligence.recovery import b5_synthetic_s3_call_boundary_v0_1 as b5
from trading_signal_intelligence.recovery import b6_synthetic_s3_wire_fence_v0_1 as b6

FAKE_KEY = bytes(range(32))


class OfflineEvents:
    """Offline event emitter; makes no SDK or network request."""
    def __init__(self):
        self.hooks = []

    def register(self, name, fn):
        self.hooks.append((name, fn))

    def emit(self, request):
        for name, fn in self.hooks:
            if name == "before-send.s3":
                fn(request=request, event_name="before-send.s3.PutObject")


def synthetic(tmp_path):
    root = tmp_path / "vowsig-b1b2-fixture-exp041"
    root.mkdir()
    copied = offline._create_disposable_synthetic_fixture(root)
    obj = b3.seal_captured_synthetic_s02(
        root, copied, artifact_id="exp041", key=FAKE_KEY)
    return root, copied, obj


def request_for(provider, obj, verb, *, version=None, **overrides):
    url = f"{provider.endpoint}/{provider.bucket}/{obj.object_key}"
    if verb == "GET":
        if version is None:
            version = "synthetic-offline-v1"
        url += "?versionId=" + quote(version, safe="")
    headers = {
        "Host": provider.endpoint.split("//")[1],
        "Authorization": (
            "AWS4-HMAC-SHA256 Credential=TESTONLY/20261023/"
            + provider.region + "/s3/aws4_request, SignedHeaders=host, Signature=FAKE"
        ),
    }
    if verb == "PUT":
        headers["Content-Type"] = "application/octet-stream"
        headers["Content-Length"] = str(len(obj.envelope))
        if provider == b4.AWS:
            headers["If-None-Match"] = "*"
    return SimpleNamespace(
        method=overrides.get("method", verb),
        url=overrides.get("url", url),
        headers=overrides.get("headers", headers),
        body=overrides.get("body", obj.envelope if verb == "PUT" else None),
    )


class EmittingClient(offline._MemoryClient):
    def __init__(self, store, role, obj):
        super().__init__(store, role=role)
        self.obj = obj
        self.meta.events = OfflineEvents()

    def _emit(self, verb, args):
        self.meta.events.emit(request_for(
            self.store.provider, self.obj, verb, version=args.get("VersionId")))

    def head_object(self, **kwargs):
        self._emit("HEAD", kwargs)
        return super().head_object(**kwargs)

    def put_object(self, **kwargs):
        self._emit("PUT", kwargs)
        return super().put_object(**kwargs)

    def get_object(self, **kwargs):
        self._emit("GET", kwargs)
        return super().get_object(**kwargs)


def pair(obj):
    aws, b2 = offline._MemoryStore(b4.AWS), offline._MemoryStore(b4.B2)
    aws_writer = EmittingClient(aws, "writer", obj)
    aws_reader = EmittingClient(aws, "reader", obj)
    b2_writer = EmittingClient(b2, "writer", obj)
    b2_reader = EmittingClient(b2, "reader", obj)
    aw, ar, ag = b5.guard_pair(b4.AWS, aws_writer, aws_reader, obj)
    bw, br, bg = b5.guard_pair(b4.B2, b2_writer, b2_reader, obj)
    fence = b6.SyntheticWireFence(obj, ag, bg)
    return (aws, b2), (aw, ar, bw, br), fence, (aws_writer, aws_reader, b2_writer, b2_reader)


def test_full_disposable_two_provider_fake_signed_http_and_sqlite_restores(tmp_path):
    root, copied, obj = synthetic(tmp_path)
    stores, guarded, fence, underlying = pair(obj)
    fence.attach(*underlying)
    result = b4.run_two_provider_pilot(
        fixture_root=root, captured_source=copied, obj=obj, key=FAKE_KEY,
        aws_writer=guarded[0], aws_reader=guarded[1],
        b2_writer=guarded[2], b2_reader=guarded[3],
        network_approved=True, approval_phrase=b4.APPROVAL_PHRASE,
    )
    assert result["actual_attempted_requests"] == 5
    assert fence.assert_complete() == {
        "status": "EXP041_FAKE_HTTP_BOUNDARY_COMPLETE",
        "validated_pre_send_events": 5,
        "max_encrypted_object_bytes": 131072,
        "real_provider_requests_observed": False,
        "cloud_mode_enabled": False,
    }
    assert [x.calls for x in stores] == [["PUT", "GET"], ["HEAD", "PUT", "GET"]]
    original_digest = hashlib.sha256(copied.read_bytes()).hexdigest()
    for which in ("awsrestore", "b2restore"):
        downloaded = root / "restored" / which / "forward.sqlite"
        assert downloaded.is_file()
        assert hashlib.sha256(downloaded.read_bytes()).hexdigest() == original_digest


def test_attach_no_sdk_requests_and_four_distinct_clients(tmp_path):
    _, _, obj = synthetic(tmp_path)
    stores, _, fence, clients = pair(obj)
    assert fence.attempted_sends == 0
    fence.attach(*clients)
    assert all(len(client.meta.events.hooks) == 1 for client in clients)
    assert not stores[0].calls and not stores[1].calls
    with pytest.raises(b6.SyntheticWireRejected):
        fence.attach(*clients)


def test_attach_rejects_reused_client(tmp_path):
    _, _, obj = synthetic(tmp_path)
    _, _, fence, clients = pair(obj)
    with pytest.raises(b6.SyntheticWireRejected):
        fence.attach(clients[0], clients[0], clients[2], clients[3])


def setup_aws_put(tmp_path):
    _, _, obj = synthetic(tmp_path)
    stores, guarded, fence, clients = pair(obj)
    ag = guarded[0]._gate
    arguments = {
        "Bucket": b4.AWS.bucket,
        "Key": obj.object_key,
        "Body": obj.envelope,
        "ContentLength": len(obj.envelope),
        "ContentType": "application/octet-stream",
        "IfNoneMatch": "*",
    }
    ag.enter("PUT", "writer", arguments, set(arguments))
    return obj, fence, ag


@pytest.mark.parametrize("mutator", [
    lambda req: setattr(req, "method", "DELETE"),
    lambda req: setattr(req, "url", req.url.replace("https://", "http://")),
    lambda req: setattr(req, "url", req.url.replace("s3.us-east-1.amazonaws.com", "example.org")),
    lambda req: setattr(req, "url", req.url + "?delete=true"),
    lambda req: setattr(req, "url", req.url.replace("/pilot/", "/real/")),
    lambda req: req.headers.update({"X-Amz-ACL": "public-read"}),
    lambda req: req.headers.update({"X-Amz-Tagging": "category=other"}),
    lambda req: req.headers.update({"X-Amz-Meta-Sample": "private"}),
    lambda req: req.headers.update({"X-Amz-Security-Token": "should-not-work"}),
    lambda req: req.headers.update({"Transfer-Encoding": "chunked"}),
    lambda req: req.headers.update({"If-None-Match": "wrong"}),
    lambda req: req.headers.update({"Content-Length": "123"}),
    lambda req: req.headers.update({"Authorization": "Basic invalid"}),
    lambda req: setattr(req, "body", b"not-authenticated"),
])
def test_aws_put_rejects_mutated_or_unsafe_http_send(tmp_path, mutator):
    obj, fence, _ = setup_aws_put(tmp_path)
    req = request_for(b4.AWS, obj, "PUT")
    mutator(req)
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.AWS, "writer", req)
    assert fence.attempted_sends == 0
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.AWS, "writer", request_for(b4.AWS, obj, "PUT"))


def test_unplanned_provider_or_role_denied_before_send(tmp_path):
    obj, fence, _ = setup_aws_put(tmp_path)
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.B2, "writer", request_for(b4.B2, obj, "PUT"))
    assert fence.attempted_sends == 0


def test_accept_once_then_deny_repeated_put_before_send(tmp_path):
    obj, fence, _ = setup_aws_put(tmp_path)
    req = request_for(b4.AWS, obj, "PUT")
    fence.observe(b4.AWS, "writer", req)
    assert fence.attempted_sends == 1
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.AWS, "writer", req)
    assert fence.attempted_sends == 1


def test_aws_get_rejects_wrong_or_duplicate_version_query(tmp_path):
    obj, fence, ag = setup_aws_put(tmp_path)
    fence.observe(b4.AWS, "writer", request_for(b4.AWS, obj, "PUT"))
    ag.finish("GET", version="synthetic-offline-v1")
    args = {
        "Bucket": b4.AWS.bucket, "Key": obj.object_key,
        "VersionId": "synthetic-offline-v1",
    }
    ag.enter("GET", "reader", args, set(args))
    req = request_for(b4.AWS, obj, "GET", version="wrong-version")
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.AWS, "reader", req)


def test_aws_get_rejects_duplicate_query_params(tmp_path):
    obj, fence, ag = setup_aws_put(tmp_path)
    fence.observe(b4.AWS, "writer", request_for(b4.AWS, obj, "PUT"))
    ag.finish("GET", version="synthetic-offline-v1")
    args = {
        "Bucket": b4.AWS.bucket, "Key": obj.object_key,
        "VersionId": "synthetic-offline-v1",
    }
    ag.enter("GET", "reader", args, set(args))
    req = request_for(b4.AWS, obj, "GET")
    req.url += "&versionId=synthetic-offline-v1"
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.AWS, "reader", req)


def test_requires_b5_enter_before_accepting_http_event(tmp_path):
    _, _, obj = synthetic(tmp_path)
    _, _, fence, _ = pair(obj)
    with pytest.raises(b6.SyntheticWireRejected):
        fence.observe(b4.AWS, "writer", request_for(b4.AWS, obj, "PUT"))
    assert fence.attempted_sends == 0


def test_incomplete_and_poisoned_request_sequence_denied(tmp_path):
    obj, fence, _ = setup_aws_put(tmp_path)
    fence.observe(b4.AWS, "writer", request_for(b4.AWS, obj, "PUT"))
    with pytest.raises(b6.SyntheticWireRejected):
        fence.assert_complete()


def test_source_no_sdk_credentials_or_cloud_activation():
    import inspect
    source = inspect.getsource(b6)
    assert "import boto3" not in source
    assert "import botocore" not in source
    assert "import requests" not in source
    assert "import socket" not in source
    assert "os.environ" not in source
    assert "getpass" not in source
    assert "if __name__" not in source
    assert "before-send.s3" in source
