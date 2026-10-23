"""EXP042: real SDK serialization/signing with FAKE in-process S3 HTTP replies.

VPS-only, OFFLINE-ONLY. Refuses to execute with any missing/unpinned SDK.
No cloud keys, no credential lookup, no actual HTTPS call, no SDK install.
This proof DOES NOT activate the EXP040 operator's cloud mode.

Security layers: explicit nonfunctional fake credentials; pinned SDK versions;
global fail-closed socket connect blocker; deny-all endpoint HTTP transport;
B6 before-send signed request gate; mock in-process AWSResponse objects;
B1/B3/B4/B5/B6 independent synthetic restore verification.

Never run this module with provider-issued credentials.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import importlib.metadata
import io
import json
import os
from pathlib import Path
import socket
import tempfile
from typing import Any

from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4
from trading_signal_intelligence.recovery import b6_synthetic_s3_wire_fence_v0_1 as b6

if __package__:
    from scripts import exp040_vps_one_shot_synthetic_cloud_operator as exp040
else:
    import exp040_vps_one_shot_synthetic_cloud_operator as exp040

PIN_BOTO3 = "1.43.114"
PIN_BOTOCORE = "1.43.114"
OFFLINE_MODE = "--offline-only"
FAKE_ACCESS = "EXP042_FAKE_NEVER_VALID_ACCESS_ID"
FAKE_SECRET = "EXP042_FAKE_NEVER_VALID_SECRET_KEY_UNUSABLE"
FAKE_VERSION = "exp042-synthetic-version"
PROVIDER_CALLS_ALLOWED = False


class SDKOfflineRejected(RuntimeError):
    """Fixed safe errors; never embed URLs, credentials or provider exceptions."""


class _QuietParser(argparse.ArgumentParser):
    def error(self, message: str) -> None:
        raise SDKOfflineRejected("unapproved command-line argument")


def sdk_pin_status() -> str:
    """Reads local package metadata only; no network, no package installation."""
    versions = []
    for name in ("boto3", "botocore"):
        try:
            versions.append(importlib.metadata.version(name))
        except importlib.metadata.PackageNotFoundError:
            return "PINNED_SDK_NOT_INSTALLED"
    if tuple(versions) != (PIN_BOTO3, PIN_BOTOCORE):
        return "PINNED_SDK_VERSION_MISMATCH"
    return "PINNED_SDK_AVAILABLE"


@contextmanager
def _block_external_socket_connections():
    """Block actual TCP connects regardless of accidental SDK fallback."""
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create_connection = socket.create_connection

    def deny(*args: Any, **kwargs: Any) -> Any:
        raise SDKOfflineRejected("external network blocked in synthetic SDK proof")

    socket.socket.connect = deny
    socket.socket.connect_ex = deny
    socket.create_connection = deny
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create_connection


class _DenyHTTPTransport:
    """Never forward any SDK attempt to a network implementation."""

    def __init__(self) -> None:
        self.unsolicited_send_calls = 0

    def send(self, request: Any) -> Any:
        self.unsolicited_send_calls += 1
        raise SDKOfflineRejected("unauthorized SDK HTTP transport invocation")

    def close(self) -> None:
        return None


class _MockSDKResponses:
    """Registered AFTER the B6 allowlist; supplies no-network AWSResponse."""

    def __init__(self, obj: Any, fence: b6.SyntheticWireFence, aws_response_type: Any) -> None:
        self.obj = obj
        self.fence = fence
        self.response_type = aws_response_type
        self.operations: list[str] = []

    def make_handler(self, provider: b4.Provider, role: str):
        def respond(request: Any, **kwargs: Any) -> Any:
            # Fail closed if B6 hook did NOT inspect this exact event first.
            ix = len(self.operations)
            if (ix >= len(b6.PLAN)
                    or self.fence.attempted_sends != ix + 1
                    or b6.PLAN[ix].provider != provider
                    or b6.PLAN[ix].role != role
                    or request.method != b6.PLAN[ix].verb):
                raise SDKOfflineRejected("SDK request fence did not precede mock response")
            verb = request.method
            self.operations.append(f"{provider.name}_{verb}")
            if verb == "HEAD":
                payload = b"<Error><Code>NoSuchKey</Code><Message>Not Found</Message></Error>"
                headers = {"content-type": "application/xml",
                           "content-length": str(len(payload))}
                return self.response_type(request.url, 404, headers, io.BytesIO(payload))
            if verb == "PUT":
                headers = {"x-amz-version-id": FAKE_VERSION, "etag": '"exp042-fake"'}
                return self.response_type(request.url, 200, headers, io.BytesIO(b""))
            if verb == "GET":
                payload = self.obj.envelope
                headers = {
                    "x-amz-version-id": FAKE_VERSION,
                    "content-type": "application/octet-stream",
                    "content-length": str(len(payload)),
                }
                return self.response_type(request.url, 200, headers, io.BytesIO(payload))
            raise SDKOfflineRejected("unexpected synthetic operation")
        return respond


def _new_client(boto3: Any, Config: Any, provider: b4.Provider) -> Any:
    """Only made under global socket deny, with NEVER-valid fake credentials."""
    conf = Config(
        region_name=provider.region, signature_version="s3v4",
        retries={"mode": "standard", "total_max_attempts": 1},
        s3={"addressing_style": "path", "payload_signing_enabled": True},
        request_checksum_calculation="when_required",
        response_checksum_validation="when_required",
        connect_timeout=5, read_timeout=10, max_pool_connections=1,
        proxies={},
    )
    session = boto3.session.Session(
        aws_access_key_id=FAKE_ACCESS, aws_secret_access_key=FAKE_SECRET,
        region_name=provider.region,
    )
    client = session.client(
        "s3", endpoint_url=provider.endpoint, region_name=provider.region,
        aws_access_key_id=FAKE_ACCESS, aws_secret_access_key=FAKE_SECRET,
        config=conf, verify=True,
    )
    b4._check_client(client, provider)
    return client


def run_pinned_fake_sdk_proof() -> dict:
    if PROVIDER_CALLS_ALLOWED is not False:
        raise SDKOfflineRejected("EXP042 network permission invariant violated")
    if exp040.REAL_PROVIDER_REQUESTS_ENABLED is not False:
        raise SDKOfflineRejected("EXP040 real cloud operator must remain disabled")
    if os.name != "nt":
        raise SDKOfflineRejected("native Windows VPS required")
    status = sdk_pin_status()
    if status != "PINNED_SDK_AVAILABLE":
        raise SDKOfflineRejected(status)

    with _block_external_socket_connections():
        # Import SDK only after pin verification and socket blocking.
        try:
            import boto3
            import botocore
            from botocore.config import Config
            from botocore.awsrequest import AWSResponse
            if (boto3.__version__ != PIN_BOTO3
                    or botocore.__version__ != PIN_BOTOCORE):
                raise SDKOfflineRejected("SDK runtime version drift")
        except SDKOfflineRejected:
            raise
        except Exception:
            raise SDKOfflineRejected("pinned SDK import failed") from None

        with tempfile.TemporaryDirectory(prefix="vowsig-b1b2-fixture-exp042-") as folder:
            root = Path(folder)
            copied, obj, key = exp040._synthetic_inputs(root)
            aw = _new_client(boto3, Config, b4.AWS)
            ar = _new_client(boto3, Config, b4.AWS)
            bw = _new_client(boto3, Config, b4.B2)
            br = _new_client(boto3, Config, b4.B2)
            transports = [_DenyHTTPTransport() for _ in range(4)]
            # Replace every HTTP session BEFORE ANY SDK API method.
            for client, transport in zip((aw, ar, bw, br), transports):
                client._endpoint.http_session = transport

            from trading_signal_intelligence.recovery import (
                b5_synthetic_s3_call_boundary_v0_1 as b5
            )
            gaw, gar, ga = b5.guard_pair(b4.AWS, aw, ar, obj)
            gbw, gbr, gb = b5.guard_pair(b4.B2, bw, br, obj)
            fence = b6.SyntheticWireFence(obj, ga, gb)
            fence.attach(aw, ar, bw, br)
            responses = _MockSDKResponses(obj, fence, AWSResponse)
            for provider, role, client in (
                (b4.AWS, "writer", aw), (b4.AWS, "reader", ar),
                (b4.B2, "writer", bw), (b4.B2, "reader", br),
            ):
                client.meta.events.register(
                    "before-send.s3", responses.make_handler(provider, role)
                )
            # Actual SDK operation serialization/signing/parsing, but no HTTP.
            result = b4.run_two_provider_pilot(
                fixture_root=root, captured_source=copied, obj=obj, key=key,
                aws_writer=gaw, aws_reader=gar, b2_writer=gbw, b2_reader=gbr,
                network_approved=True, approval_phrase=b4.APPROVAL_PHRASE,
            )
            fence_status = fence.assert_complete()
            expected = [
                "AWS_S3_PUT", "AWS_S3_GET",
                "BACKBLAZE_B2_HEAD", "BACKBLAZE_B2_PUT", "BACKBLAZE_B2_GET"
            ]
            if (responses.operations != expected
                    or fence_status["validated_pre_send_events"] != 5
                    or result.get("actual_attempted_requests") != 5
                    or any(x.unsolicited_send_calls for x in transports)
                    or len(result.get("receipts", [])) != 2):
                raise SDKOfflineRejected("fake SDK transport proof invariant failed")
            return {
                "status": "EXP042_PINNED_SDK_FAKE_TRANSPORT_PASS",
                "boto3_pin": PIN_BOTO3, "botocore_pin": PIN_BOTOCORE,
                "sdk_serialized_and_signed_pre_send_events": 5,
                "synthetic_independent_restores": 2,
                "http_transport_send_invocations": 0,
                "real_provider_requests": 0,
                "real_credentials": False,
                "production_modified": False,
                "live_cloud_mode_enabled": False,
            }


def main(argv: list[str] | None = None) -> int:
    parser = _QuietParser(description="EXP042 VPS-only PINNED SDK FAKE HTTP proof")
    parser.add_argument(OFFLINE_MODE, action="store_true", required=True)
    args = parser.parse_args(argv)
    if not args.offline_only:
        raise SDKOfflineRejected("offline mode required")
    print(json.dumps(run_pinned_fake_sdk_proof(), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SDKOfflineRejected as exc:
        # These are fixed known labels only; no provider/SDK traceback.
        label = str(exc)
        safe = {
            "PINNED_SDK_NOT_INSTALLED", "PINNED_SDK_VERSION_MISMATCH",
            "native Windows VPS required",
        }
        reason = label if label in safe else "OFFLINE_SDK_PROOF_INCOMPLETE"
        print(f"EXP042_FINAL=HOLD; REASON={reason}; CLOUD_MODE=DISABLED")
        raise SystemExit(2) from None
