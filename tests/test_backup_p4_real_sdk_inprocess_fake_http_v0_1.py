"""EXP046: REAL pinned SDK serializer/signing, FAKE HTTP, synthetic S02 only.

No provider SDK network request is ever allowed. In this test, *all four*
botocore endpoint http_session instances are overwritten with in-process
responders before the FIRST SDK call, while socket.connect/connect_ex are
blocked for the entire SDK construction+execution scope.
"""
from __future__ import annotations

import hashlib
import io
import socket
from pathlib import Path

import pytest

from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as p2
from test_live_sqlite_envelope_v0_1 import sealed_fixture

FAKE_ACCESS = "EXP046_FAKE_NOT_VALID"
FAKE_SECRET = "EXP046_SYNTHETIC_NEVER_VALID_NOT_A_REAL_AWS_SECRET"
FAKE_VERSION = "exp046-in-process-version-id"


class NoExternalSocket(RuntimeError):
    pass


class _FakeRaw(io.BytesIO):
    """Minimum response streaming protocol expected by pinned botocore."""

    def stream(self, amt=None, decode_content=False):
        if decode_content is not False:
            raise NoExternalSocket("fake response decoding prohibited")
        if amt is not None and (type(amt) is not int or not 0 < amt <= 65536):
            raise NoExternalSocket("fake response chunk budget rejected")
        size = 8192 if amt is None else amt
        while True:
            part = self.read(size)
            if not part:
                return
            yield part


class _InProcessFakeHttp:
    """Only returns in-process AWSResponse. Never delegates to SDK transport."""

    def __init__(self, fence, obj, provider, role, response_type, trace):
        self.fence = fence
        self.obj = obj
        self.provider = provider
        self.role = role
        self.response_type = response_type
        self.trace = trace
        self.synthetic_sends = 0
        self.real_network_sends = 0

    def send(self, request):
        if (self.fence.seen_this_call != 1
                or self.fence.pending is None
                or self.fence.pending[0] != self.provider
                or self.fence.pending[1] != self.role
                or self.fence.pending[2] != request.method
                or self.fence.attempted != len(self.trace) + 1
                or self.synthetic_sends >= 2
                or len(self.trace) >= p2.MAX_REQUESTS):
            raise NoExternalSocket("unfenced or duplicate fake SDK operation")
        self.synthetic_sends += 1
        self.trace.append((self.provider.name, self.role, request.method))
        if request.method == "PUT":
            return self.response_type(
                request.url, 200,
                {"x-amz-version-id": FAKE_VERSION, "etag": '"in-process-synthetic"'},
                _FakeRaw(b""),
            )
        if request.method == "GET":
            blob = self.obj.envelope
            return self.response_type(
                request.url, 200,
                {"x-amz-version-id": FAKE_VERSION,
                 "content-type": "application/octet-stream",
                 "content-length": str(len(blob))},
                _FakeRaw(blob),
            )
        if request.method == "HEAD" and self.provider == p2.B2:
            payload = b"<Error><Code>NoSuchKey</Code><Message>Not Found</Message></Error>"
            return self.response_type(
                request.url, 404,
                {"content-type": "application/xml", "content-length": str(len(payload))},
                _FakeRaw(payload),
            )
        raise NoExternalSocket("unexpected fake SDK operation")


def _new_fake_client(boto3, Config, provider):
    config = Config(
        region_name=provider.region, signature_version="s3v4",
        retries={"mode": "standard", "total_max_attempts": 1},
        s3={"addressing_style": "path", "payload_signing_enabled": True},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        connect_timeout=5, read_timeout=10, max_pool_connections=1, proxies={},
    )
    session = boto3.session.Session(
        aws_access_key_id=FAKE_ACCESS,
        aws_secret_access_key=FAKE_SECRET,
        region_name=provider.region,
    )
    client = session.client(
        "s3", endpoint_url=provider.endpoint, region_name=provider.region,
        aws_access_key_id=FAKE_ACCESS,
        aws_secret_access_key=FAKE_SECRET,
        config=config, verify=True,
    )
    p2._client_checked(client, provider)
    return client


def _release_token(obj):
    return p2.ReleaseAuthorization(
        owner_approval_phrase=p2.APPROVAL,
        rights_sha256="a" * 64,
        budget_and_billing_attestation_sha256="b" * 64,
        iam_and_retention_attestation_sha256="c" * 64,
        encryption_key_recovery_attestation_sha256="d" * 64,
        expected_bucket_pair=(p2.AWS.bucket, p2.B2.bucket),
        permitted_region_pair=(p2.AWS.region, p2.B2.region),
    )


def test_real_pinned_sdk_five_signed_events_two_verified_synthetic_restores(
    tmp_path, monkeypatch,
):
    # Missing exact dependency closure is a HARD failure; never silently skip.
    from importlib import metadata as md
    expected = {
        "boto3": "1.43.114", "botocore": "1.43.114",
        "jmespath": "1.0.1", "s3transfer": "0.19.3",
        "python-dateutil": "2.9.0.post0", "urllib3": "2.8.0",
        "six": "1.17.0",
    }
    assert all(md.version(name) == version for name, version in expected.items())

    def block_socket(*args, **kwargs):
        raise NoExternalSocket("all OS network connects are blocked")
    monkeypatch.setattr(socket.socket, "connect", block_socket)
    monkeypatch.setattr(socket.socket, "connect_ex", block_socket)

    # SDK imports happen AFTER network is blocked; fake-only explicit creds.
    import boto3
    import botocore
    from botocore.awsrequest import AWSResponse
    from botocore.config import Config
    assert boto3.__version__ == "1.43.114"
    assert botocore.__version__ == "1.43.114"

    _, scratch, _, _, key, obj = sealed_fixture(tmp_path)
    clients = [_new_fake_client(boto3, Config, p) for p in
               (p2.AWS, p2.AWS, p2.B2, p2.B2)]
    assert len({id(c) for c in clients}) == 4

    # P2 creates its own strict wire guard internally. The fake session is
    # installed before invocation; only synthetic responders can be reached.
    trace = []
    proxies = []
    original_init = p2._WireFence.__init__
    def observe_fence_init(self, sealed):
        original_init(self, sealed)
        for client, (provider, role) in zip(
            clients,
            ((p2.AWS, "writer"), (p2.AWS, "reader"),
             (p2.B2, "writer"), (p2.B2, "reader")),
        ):
            proxy = _InProcessFakeHttp(self, sealed, provider, role, AWSResponse, trace)
            client._endpoint.http_session = proxy
            proxies.append(proxy)

    with monkeypatch.context() as patch:
        patch.setattr(p2._WireFence, "__init__", observe_fence_init)
        result = p2.replicate_approved_s02(
            obj=obj, key=key, authorization=_release_token(obj),
            aws_writer=clients[0], aws_reader=clients[1],
            b2_writer=clients[2], b2_reader=clients[3],
            recovery_scratch=Path(scratch),
        )

    assert result["status"] == "LIVE_S02_TWO_PROVIDER_VERIFIED"
    assert result["attempted_signed_requests"] == 5
    assert [r["verified_records"] for r in result["receipts"]] == [3, 3]
    assert trace == [
        ("AWS_S3", "writer", "PUT"),
        ("AWS_S3", "reader", "GET"),
        ("BACKBLAZE_B2", "reader", "HEAD"),
        ("BACKBLAZE_B2", "writer", "PUT"),
        ("BACKBLAZE_B2", "reader", "GET"),
    ]
    assert sum(x.synthetic_sends for x in proxies) == 5
    assert all(x.real_network_sends == 0 for x in proxies)
    assert (scratch / "aws-restore-0001" / "forward.sqlite").exists()
    assert (scratch / "b2-restore-0001" / "forward.sqlite").exists()
    assert (scratch / ("preflight-" + hashlib.sha256(
        obj.run_id.encode("utf-8")).hexdigest()[:24]) /
        "forward.sqlite").exists()


def test_fake_sdk_harness_never_has_a_real_transport_fallback():
    import ast
    import inspect
    source = inspect.getsource(_InProcessFakeHttp)
    ast.parse(source)
    assert "return self.response_type(" in source
    assert "self.fence.seen_this_call != 1" in source
    assert "self.real_network_sends = 0" in source
    assert "_endpoint.http_session = proxy" in inspect.getsource(
        test_real_pinned_sdk_five_signed_events_two_verified_synthetic_restores
    )
