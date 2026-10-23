"""EXP041 synthetic S3 HTTP-before-send allowlist. OFFLINE PREPARATION ONLY.

NO network/SDK/credential imports, CLI or provider client creation. The frozen
EXP040 operator still has REAL_PROVIDER_REQUESTS_ENABLED=False. A separately
approved code change must integrate and validate this hook with a PINNED
botocore version before any actual provider request.

This is a fail-closed Python event observer, NOT a firewall, a cost cap, a
guarantee of HTTP-request counts, or authorization for an actual S3 operation.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from urllib.parse import parse_qsl, urlsplit
from typing import Any

from . import b3_synthetic_encrypted_offsite_v0_1 as b3
from . import b4_synthetic_s3_pilot_v0_1 as b4
from . import b5_synthetic_s3_call_boundary_v0_1 as b5


class SyntheticWireRejected(RuntimeError):
    """Sanitized fail-closed error; never includes URL or authentication fields."""


@dataclass(frozen=True)
class ExpectedSend:
    provider: b4.Provider
    role: str
    verb: str


PLAN = (
    ExpectedSend(b4.AWS, "writer", "PUT"),
    ExpectedSend(b4.AWS, "reader", "GET"),
    ExpectedSend(b4.B2, "reader", "HEAD"),
    ExpectedSend(b4.B2, "writer", "PUT"),
    ExpectedSend(b4.B2, "reader", "GET"),
)

# Deny all S3 request metadata that could alter ACL, object management,
# retention, replication, tagging, storage class or encoding without review.
BANNED_HEADERS = (
    "x-amz-acl", "x-amz-tagging", "x-amz-storage-class",
    "x-amz-server-side-encryption", "x-amz-website-redirect-location",
    "x-amz-object-lock-", "x-amz-meta-", "x-amz-copy-source",
    "x-amz-grant-", "x-amz-request-payer", "x-amz-security-token",
    "x-amz-bucket-", "x-amz-restore", "x-amz-delete-marker",
    "transfer-encoding",
)


class SyntheticWireFence:
    """Validate all five expected pre-send events in a single exact order."""

    def __init__(
        self, obj: b3.SealedSynthetic, aws_gate: b5._Gate, b2_gate: b5._Gate
    ) -> None:
        if (not isinstance(obj, b3.SealedSynthetic)
                or type(obj.envelope) is not bytes
                or not 0 < len(obj.envelope) <= b4.MAX_ENVELOPE_BYTES
                or not b4.KEY_RE.fullmatch(obj.object_key)
                or hashlib.sha256(obj.envelope).hexdigest() != obj.envelope_sha256):
            raise SyntheticWireRejected("invalid synthetic encrypted object")
        for provider, gate in ((b4.AWS, aws_gate), (b4.B2, b2_gate)):
            if (not isinstance(gate, b5._Gate)
                    or gate.provider != provider
                    or gate.object_key != obj.object_key
                    or gate.sha256 != obj.envelope_sha256
                    or gate.envelope != obj.envelope
                    or gate.calls or gate.version is not None
                    or gate.poisoned):
                raise SyntheticWireRejected("invalid initial B5 operation gate")
        self._obj = obj
        self._gates = {b4.AWS.name: aws_gate, b4.B2.name: b2_gate}
        self._count = 0
        self._poisoned = False
        self._attached = False

    @property
    def attempted_sends(self) -> int:
        return self._count

    def _deny(self) -> None:
        self._poisoned = True
        raise SyntheticWireRejected("synthetic S3 HTTP request denied") from None

    def observe(self, provider: b4.Provider, role: str, request: Any) -> None:
        """Called synchronously by a future before-send observer, not a sender.

        Every accepted event consumes its one attempt *before* the SDK sends.
        If a send later fails, repeating the event is denied; never retry.
        """
        if self._poisoned or self._count >= len(PLAN):
            self._deny()
        expected = PLAN[self._count]
        if provider != expected.provider or role != expected.role:
            self._deny()
        try:
            method = request.method
            raw_url = request.url
            headers = request.headers
            body = request.body
            if not isinstance(method, str) or method != expected.verb:
                self._deny()
            if not isinstance(raw_url, str) or not hasattr(headers, "items"):
                self._deny()
            parsed = urlsplit(raw_url)
            target = urlsplit(provider.endpoint)
            if (parsed.scheme != "https"
                    or parsed.netloc != target.netloc
                    or parsed.username is not None
                    or parsed.password is not None
                    or parsed.fragment != ""
                    or parsed.path != f"/{provider.bucket}/{self._obj.object_key}"):
                self._deny()
            gate = self._gates[provider.name]
            if (not gate.poisoned or not gate.calls
                    or gate.calls[-1] != expected.verb):
                # B5 must have authorized this precise SDK method first.
                self._deny()
            if expected.verb == "GET":
                params = parse_qsl(
                    parsed.query, keep_blank_values=True, strict_parsing=True,
                )
                if (len(params) != 1 or params[0][0] != "versionId"
                        or not b5._is_version(gate.version)
                        or params[0][1] != gate.version):
                    self._deny()
            elif parsed.query:
                self._deny()
            h = {}
            for k, v in headers.items():
                label = k.decode("ascii") if isinstance(k, bytes) else k
                value = v.decode("latin-1") if isinstance(v, bytes) else v
                if not isinstance(label, str) or not isinstance(value, str):
                    self._deny()
                label = label.lower()
                if (label in h or any(
                    label == blocked or (
                        blocked.endswith("-") and label.startswith(blocked)
                    ) for blocked in BANNED_HEADERS)):
                    self._deny()
                h[label] = value
            if h.get("host", target.netloc) != target.netloc:
                self._deny()
            auth = h.get("authorization", "")
            # Check the signing *scheme and scope*, never inspect/print keys.
            if (not auth.startswith("AWS4-HMAC-SHA256 ")
                    or f"/{provider.region}/s3/aws4_request" not in auth):
                self._deny()
            if expected.verb == "PUT":
                if (not isinstance(body, bytes)
                        or body != self._obj.envelope
                        or hashlib.sha256(body).hexdigest() != self._obj.envelope_sha256
                        or h.get("content-type") != "application/octet-stream"
                        or h.get("content-length") != str(len(body))):
                    self._deny()
                if provider == b4.AWS:
                    if h.get("if-none-match") != "*":
                        self._deny()
                elif "if-none-match" in h:
                    self._deny()
            elif body not in (None, b""):
                self._deny()
        except SyntheticWireRejected:
            raise
        except Exception:
            self._deny()
        self._count += 1

    def attach(self, aws_writer: Any, aws_reader: Any, b2_writer: Any, b2_reader: Any) -> None:
        """Register only; NO network request. SDK hook behavior NOT yet verified.

        This proposed event hook is not wired into EXP040. Do not activate it
        against real clients before a botocore-version-pinned integration test.
        """
        if self._attached or self._count or self._poisoned:
            self._deny()
        placements = (
            (b4.AWS, "writer", aws_writer),
            (b4.AWS, "reader", aws_reader),
            (b4.B2, "writer", b2_writer),
            (b4.B2, "reader", b2_reader),
        )
        if len({id(item[2]) for item in placements}) != 4:
            self._deny()
        for provider, _, client in placements:
            try:
                b4._check_client(client, provider)
                if not callable(client.meta.events.register):
                    self._deny()
            except Exception:
                self._deny()
        # Prefix-scoped event dispatch behavior requires future SDK validation.
        for provider, role, client in placements:
            def on_before_send(request: Any, *, _p=provider, _role=role, **kwargs: Any) -> None:
                self.observe(_p, _role, request)
            try:
                client.meta.events.register("before-send.s3", on_before_send)
            except Exception:
                self._deny()
        self._attached = True

    def assert_complete(self) -> dict:
        if (self._poisoned or self._count != len(PLAN)
                or any(self._gates[p.name].next_step != "DONE"
                       for p in (b4.AWS, b4.B2))):
            raise SyntheticWireRejected("synthetic S3 request sequence incomplete")
        return {
            "status": "EXP041_FAKE_HTTP_BOUNDARY_COMPLETE",
            "validated_pre_send_events": self._count,
            "max_encrypted_object_bytes": b4.MAX_ENVELOPE_BYTES,
            "real_provider_requests_observed": False,
            "cloud_mode_enabled": False,
        }
