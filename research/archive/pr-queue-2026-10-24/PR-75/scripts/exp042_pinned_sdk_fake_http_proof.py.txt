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
from urllib.parse import urlsplit
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


def _safe_body_shape(body: Any, expected: bytes) -> dict[str, bool]:
    """Bounded fake-HTTP diagnostics; no raw body, type names or keys returned.

    A readable body is sampled ONLY if it is seekable and initially at 0.
    Always try to restore its exact cursor before subsequent B6 validation.
    This diagnostic does NOT authorize a new body representation in B6.
    """
    checks = {
        "body_is_bytes_type": type(body) is bytes,
        "body_bytes_match": type(body) is bytes and body == expected,
        "body_has_stream_methods": all(
            callable(getattr(body, name, None)) for name in
            ("read", "seek", "tell", "seekable")
        ),
        "body_stream_seekable": False,
        "body_stream_at_zero": False,
        "body_stream_full_payload_match": False,
        "body_stream_cursor_restored": False,
    }
    if not checks["body_has_stream_methods"]:
        return checks
    try:
        checks["body_stream_seekable"] = body.seekable() is True
        pos = body.tell()
        checks["body_stream_at_zero"] = type(pos) is int and pos == 0
        if not checks["body_stream_seekable"] or not checks["body_stream_at_zero"]:
            return checks
        # Limit read to exact ciphertext length + 1 to detect extra bytes.
        # Deny-transport context prevents any network submission.
        try:
            observed = body.read(len(expected) + 1)
            checks["body_stream_full_payload_match"] = (
                type(observed) is bytes and observed == expected
            )
        finally:
            body.seek(pos)
            checks["body_stream_cursor_restored"] = body.tell() == pos
    except Exception:
        # Fail closed: boolean-only diagnostic, no unsafe exceptions or data.
        return checks
    return checks


def _freeze_verified_fake_put_body(request: Any, envelope: bytes) -> None:
    """FAKE SDK ONLY: replace an identical rewindable stream with bytes.

    Runs after botocore signing but before the UNCHANGED B6 strict bytes check.
    Never wired to EXP040, a production client, or a real HTTP transport.
    Stream must be positioned at zero, readable only up to expected+1 bytes,
    match the entire authenticated ciphertext and restore its cursor.
    """
    if request.method != "PUT":
        return
    try:
        body = request.body
        if type(body) is bytes:
            if body != envelope:
                raise SDKOfflineRejected("fake SDK payload did not match")
            return
        checks = _safe_body_shape(body, envelope)
        if not all(checks[name] for name in (
            "body_has_stream_methods",
            "body_stream_seekable",
            "body_stream_at_zero",
            "body_stream_full_payload_match",
            "body_stream_cursor_restored",
        )):
            raise SDKOfflineRejected("fake SDK payload stream not admissible")
        # These are byte-for-byte the bytes that the existing B6 fence expects.
        # No SDK request is ever allowed to reach an HTTP transport in EXP042.
        request.body = envelope
        if type(request.body) is not bytes or request.body != envelope:
            raise SDKOfflineRejected("fake SDK body replacement rejected")
    except SDKOfflineRejected:
        raise
    except Exception:
        raise SDKOfflineRejected("fake SDK payload inspection failed") from None


class _SanitizedRequestProbe:
    """Only boolean shape evidence; NEVER retain raw HTTP request material."""

    def __init__(self, obj: Any) -> None:
        self._obj = obj
        self.seen = 0
        self.first_shape: dict[str, bool] = {}

    def make_handler(self, provider: b4.Provider, role: str):
        def record(request: Any, **kwargs: Any) -> None:
            self.seen += 1
            if self.seen != 1:
                return
            # Read-only inspection, no network, no body read, no secrets logged.
            try:
                parsed = urlsplit(request.url)
                fields = {
                    (key.decode("ascii").lower() if isinstance(key, bytes)
                     else str(key).lower()):
                    (value.decode("latin-1") if isinstance(value, bytes)
                     else str(value))
                    for key, value in request.headers.items()
                }
                body = request.body
                body_shape = _safe_body_shape(body, self._obj.envelope)
                self.first_shape = {
                    **body_shape,
                    "first_request_is_aws_writer": provider == b4.AWS and role == "writer",
                    "method_is_put": request.method == "PUT",
                    "scheme_is_https": parsed.scheme == "https",
                    "host_is_pinned": parsed.netloc == urlsplit(provider.endpoint).netloc,
                    "path_is_exact": parsed.path == f"/{provider.bucket}/{self._obj.object_key}",
                    "query_absent": parsed.query == "",
                    "body_exact_bytes": type(body) is bytes and body == self._obj.envelope,
                    "content_type_exact": fields.get("content-type") == "application/octet-stream",
                    "content_length_exact": fields.get("content-length") == str(len(self._obj.envelope)),
                    "atomic_put_condition": fields.get("if-none-match") == "*",
                    "sigv4_scheme": fields.get("authorization", "").startswith("AWS4-HMAC-SHA256 "),
                    "sigv4_region": f"/{provider.region}/s3/aws4_request" in fields.get("authorization", ""),
                    "has_transfer_encoding": "transfer-encoding" in fields,
                    "has_aws_session_token": "x-amz-security-token" in fields,
                }
            except Exception:
                self.first_shape = {"shape_inspection_succeeded": False}
        return record


class _SafeSDKPutParserProbe:
    """Fixed-schema after-call indicators only; no SDK objects stored.

    Botocore may reject a fake response before emitting after-call. An unseen
    event is a HOLD diagnostic, not evidence of a specific root cause.
    """

    def __init__(self) -> None:
        self.after_call_count = 0
        self.flags: dict[str, bool] = {
            "sdk_put_after_call_seen": False,
            "sdk_put_http_status_200": False,
            "sdk_put_parsed_is_dict": False,
            "sdk_put_parsed_version_exact": False,
            "sdk_put_parsed_metadata_status_200": False,
        }

    def observe(self, http_response: Any = None, parsed: Any = None,
                **kwargs: Any) -> None:
        self.after_call_count += 1
        self.flags["sdk_put_after_call_seen"] = True
        self.flags["sdk_put_http_status_200"] = (
            getattr(http_response, "status_code", None) == 200
        )
        self.flags["sdk_put_parsed_is_dict"] = type(parsed) is dict
        if type(parsed) is dict:
            self.flags["sdk_put_parsed_version_exact"] = (
                parsed.get("VersionId") == FAKE_VERSION
            )
            meta = parsed.get("ResponseMetadata")
            self.flags["sdk_put_parsed_metadata_status_200"] = (
                type(meta) is dict and meta.get("HTTPStatusCode") == 200
            )


class _InMemorySDKRawResponse(io.BytesIO):
    """FAKE HTTP ONLY: bounded urllib3-style raw stream for botocore.

    AWSResponse expects raw.stream() for ordinary non-streaming SDK payload
    parsing and raw.read() for streaming result shapes. No HTTP, sockets,
    providers, filesystem reads, or reloading of a completed response.
    """

    _MAX_FAKE_REPLY = b4.MAX_ENVELOPE_BYTES

    def __init__(self, payload: bytes) -> None:
        if type(payload) is not bytes or len(payload) > self._MAX_FAKE_REPLY:
            raise SDKOfflineRejected("invalid bounded fake SDK response")
        super().__init__(payload)

    def stream(self, amt: int | None = None,
               decode_content: bool = False):
        if decode_content is not False:
            raise SDKOfflineRejected("fake SDK raw decompression denied")
        if amt is not None and (
            type(amt) is not int or amt < 1 or amt > self._MAX_FAKE_REPLY
        ):
            raise SDKOfflineRejected("invalid fake SDK raw stream chunk budget")
        block_size = amt if amt is not None else 8192
        while True:
            chunk = self.read(block_size)
            if not chunk:
                return
            if type(chunk) is not bytes or len(chunk) > block_size:
                raise SDKOfflineRejected("invalid fake SDK raw stream bytes")
            yield chunk


class _MockSDKResponses:
    """Registered AFTER the B6 allowlist; supplies no-network AWSResponse."""

    def __init__(self, obj: Any, fence: b6.SyntheticWireFence, aws_response_type: Any) -> None:
        self.obj = obj
        self.fence = fence
        self.response_type = aws_response_type
        self.operations: list[str] = []
        self.aws_put_fake_response_constructed = False

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
                return self.response_type(request.url, 404, headers, _InMemorySDKRawResponse(payload))
            if verb == "PUT":
                headers = {"x-amz-version-id": FAKE_VERSION, "etag": '"exp042-fake"'}
                response = self.response_type(
                    request.url, 200, headers, _InMemorySDKRawResponse(b"")
                )
                if provider == b4.AWS and role == "writer":
                    self.aws_put_fake_response_constructed = True
                return response
            if verb == "GET":
                payload = self.obj.envelope
                headers = {
                    "x-amz-version-id": FAKE_VERSION,
                    "content-type": "application/octet-stream",
                    "content-length": str(len(payload)),
                }
                return self.response_type(request.url, 200, headers, _InMemorySDKRawResponse(payload))
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


def run_pinned_fake_sdk_proof(*, diagnostic: bool = False) -> dict:
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
            probe = _SanitizedRequestProbe(obj)
            for provider, role, client in (
                (b4.AWS, "writer", aw), (b4.AWS, "reader", ar),
                (b4.B2, "writer", bw), (b4.B2, "reader", br),
            ):
                # Register before B6 so a denied request still leaves only
                # boolean shape evidence; never store URLs/headers/body.
                client.meta.events.register(
                    "before-send.s3", probe.make_handler(provider, role)
                )
            # Offline fake-SDK compatibility only: normalize an already
            # proven byte-identical SDK body BEFORE the original B6 hook.
            # This does not change B6 and cannot contact a real HTTP server.
            for client in (aw, bw):
                def normalize_fake_put(request: Any, **kwargs: Any) -> None:
                    _freeze_verified_fake_put_body(request, obj.envelope)
                client.meta.events.register(
                    "before-send.s3", normalize_fake_put
                )
            fence.attach(aw, ar, bw, br)
            responses = _MockSDKResponses(obj, fence, AWSResponse)
            for provider, role, client in (
                (b4.AWS, "writer", aw), (b4.AWS, "reader", ar),
                (b4.B2, "writer", bw), (b4.B2, "reader", br),
            ):
                client.meta.events.register(
                    "before-send.s3", responses.make_handler(provider, role)
                )
            parser_probe = _SafeSDKPutParserProbe()
            aw.meta.events.register(
                "after-call.s3.PutObject", parser_probe.observe
            )
            # Observes only fixed booleans after SDK response parsing.
            # Not part of actual HTTP, B5, B6 or production operation.
            # Actual SDK operation serialization/signing/parsing, but no HTTP.
            try:
                result = b4.run_two_provider_pilot(
                    fixture_root=root, captured_source=copied, obj=obj, key=key,
                    aws_writer=gaw, aws_reader=gar, b2_writer=gbw, b2_reader=gbr,
                    network_approved=True, approval_phrase=b4.APPROVAL_PHRASE,
                )
            except Exception:
                if diagnostic:
                    return {
                        "status": "EXP042_FAKE_HTTP_DIAGNOSTIC_HOLD",
                        "boto3_pin": PIN_BOTO3,
                        "botocore_pin": PIN_BOTOCORE,
                        "sdk_before_send_observed": probe.seen,
                        "b6_accepted_pre_send_events": fence.attempted_sends,
                        "mock_response_events": len(responses.operations),
                        "denied_transport_send_attempts": sum(
                            x.unsolicited_send_calls for x in transports),
                        "first_request_shape_checks": {
                            **probe.first_shape,
                            "aws_put_mock_response_constructed":
                                responses.aws_put_fake_response_constructed,
                            **parser_probe.flags,
                        },
                        "real_provider_requests": 0,
                        "real_credentials": False,
                        "cloud_mode_enabled": False,
                    }
                raise
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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument(OFFLINE_MODE, action="store_true")
    mode.add_argument("--diagnostic-only", action="store_true")
    args = parser.parse_args(argv)
    output = run_pinned_fake_sdk_proof(diagnostic=args.diagnostic_only)
    print(json.dumps(output, sort_keys=True, separators=(",", ":")))
    return 0 if output["status"] == "EXP042_PINNED_SDK_FAKE_TRANSPORT_PASS" else 2


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
