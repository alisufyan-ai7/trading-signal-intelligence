"""Prospective dual-provider real-S02 transport LIBRARY; no live entrypoint.

Never constructs SDK clients, reads credentials or creates schedules. Direct call
could make real provider requests: ONLY a separately approved operator with a
verified scoped authorization may call it. No auto retry/delete/overwrite.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, parse_qs, unquote
from typing import Any

from . import live_sqlite_envelope_v0_1 as core

MAX_REQUESTS = 5
MAX_BYTES = core.MAX_ENVELOPE_BYTES
APPROVAL = "OWNER_APPROVED_REAL_S02_ENCRYPTED_AWS_B2_FIRST_TRANSFER"
KEY_RX = re.compile(r"^vowsig/approved-s02/v1/[a-z][a-z0-9-]{7,55}/[0-9a-f]{64}\.aesgcm$")


class LiveTransportRejected(RuntimeError):
    """Fixed, sanitized failure; never include an SDK exception or secret."""


@dataclass(frozen=True)
class Provider:
    name: str
    bucket: str
    region: str
    endpoint: str


# Source-grounded existing owner-selected names from the B4 readiness plan.
AWS = Provider("AWS_S3", "vowsig-backup-s3-2026", "us-east-1",
               "https://s3.us-east-1.amazonaws.com")
B2 = Provider("BACKBLAZE_B2", "vowsig-backup-b2-2026", "us-east-005",
              "https://s3.us-east-005.backblazeb2.com")


@dataclass(frozen=True)
class ReleaseAuthorization:
    """Owner assertions, NOT independently validated legal/billing permissions."""
    owner_approval_phrase: str
    rights_sha256: str
    budget_and_billing_attestation_sha256: str
    iam_and_retention_attestation_sha256: str
    encryption_key_recovery_attestation_sha256: str
    expected_bucket_pair: tuple[str, str]
    permitted_region_pair: tuple[str, str]
    max_attempted_requests: int = MAX_REQUESTS

    def validate(self, obj: core.SealedLiveCopy) -> None:
        if (self.owner_approval_phrase != APPROVAL
                or not isinstance(obj, core.SealedLiveCopy)
                or self.rights_sha256 != _metadata_rights(obj.envelope)
                or any(not core.HEX64.fullmatch(v) for v in (
                    self.rights_sha256, self.budget_and_billing_attestation_sha256,
                    self.iam_and_retention_attestation_sha256,
                    self.encryption_key_recovery_attestation_sha256,
                ))
                or self.expected_bucket_pair != (AWS.bucket, B2.bucket)
                or self.permitted_region_pair != (AWS.region, B2.region)
                or type(self.max_attempted_requests) is not int
                or self.max_attempted_requests != MAX_REQUESTS):
            raise LiveTransportRejected("live transfer authorization not established")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _metadata_rights(envelope: bytes) -> str:
    if not isinstance(envelope, bytes) or not envelope.startswith(core.MAGIC):
        raise LiveTransportRejected("encrypted object missing authenticated schema")
    start = len(core.MAGIC)
    length = int.from_bytes(envelope[start:start + 2], "big")
    if not 0 < length <= 2048 or start + 14 + length >= len(envelope):
        raise LiveTransportRejected("encrypted rights metadata invalid")
    import json
    try:
        meta = json.loads(envelope[start + 14:start + 14 + length])
        right = meta["rights_ref_sha256"]
        if not isinstance(right, str) or not core.HEX64.fullmatch(right):
            raise ValueError
        return right
    except (ValueError, KeyError, TypeError):
        raise LiveTransportRejected("rights reference cannot be parsed") from None


def _client_checked(client: Any, provider: Provider) -> None:
    try:
        cfg = client.meta.config
        retries = cfg.retries
        if (client.meta.endpoint_url != provider.endpoint
                or client.meta.region_name != provider.region
                or cfg.signature_version != "s3v4"
                or not isinstance(retries, dict)
                or retries.get("total_max_attempts") != 1
                or int(cfg.connect_timeout) > 5
                or int(cfg.read_timeout) > 15
                or not callable(client.meta.events.register)
                or not all(callable(getattr(client, x, None))
                           for x in ("put_object", "get_object", "head_object"))):
            raise LiveTransportRejected("incompatible pinned SDK client")
    except (AttributeError, TypeError, ValueError):
        raise LiveTransportRejected("unknown SDK endpoint or request policy") from None


def _body_matches(body: Any, expected: bytes) -> bool:
    if type(body) is bytes:
        return body == expected
    if not all(callable(getattr(body, x, None))
               for x in ("read", "seek", "tell", "seekable")):
        return False
    try:
        if body.seekable() is not True or body.tell() != 0:
            return False
        try:
            sampled = body.read(len(expected) + 1)
        finally:
            body.seek(0)
        return type(sampled) is bytes and sampled == expected and body.tell() == 0
    except Exception:
        return False


class _WireFence:
    """One selected SDK method = at most one actual signed before-send event."""

    def __init__(self, obj: core.SealedLiveCopy) -> None:
        self.obj = obj
        self.attempted = 0
        self.pending: tuple[Provider, str, str, str | None] | None = None
        self.seen_this_call = 0

    def before_call(self, provider: Provider, role: str, verb: str,
                    version: str | None) -> None:
        if self.pending is not None or self.attempted >= MAX_REQUESTS:
            raise LiveTransportRejected("on-wire request quota exhausted")
        self.pending = provider, role, verb, version
        self.seen_this_call = 0

    def hook(self, request: Any, **kwargs: Any) -> None:
        if self.pending is None or self.seen_this_call != 0:
            raise LiveTransportRejected("duplicate or unexpected signed SDK attempt")
        provider, role, verb, version = self.pending
        try:
            uri = urlsplit(request.url)
            headers = {str(k).lower(): str(v) for k, v in request.headers.items()}
            authorization = headers.get("authorization", "")
            if (request.method != verb or uri.scheme != "https"
                    or uri.netloc != urlsplit(provider.endpoint).netloc
                    or unquote(uri.path) != f"/{provider.bucket}/{self.obj.object_key}"
                    or not authorization.startswith("AWS4-HMAC-SHA256 ")
                    or f"/{provider.region}/s3/aws4_request" not in authorization
                    or "transfer-encoding" in headers):
                raise LiveTransportRejected("signed request identity rejected")
            query = parse_qs(uri.query, keep_blank_values=True)
            if verb == "GET":
                if query != {"versionId": [version]}:
                    raise LiveTransportRejected("versioned read identity rejected")
            elif query:
                raise LiveTransportRejected("unexpected signed request query")
            if verb == "PUT":
                if (role != "writer" or not _body_matches(request.body, self.obj.envelope)
                        or headers.get("content-length") != str(len(self.obj.envelope))
                        or headers.get("content-type") != "application/octet-stream"
                        or (provider == AWS and headers.get("if-none-match") != "*")
                        or (provider == B2 and "if-none-match" in headers)):
                    raise LiveTransportRejected("signed encrypted payload rejected")
            elif role != "reader":
                raise LiveTransportRejected("read method on writer credentials")
            self.seen_this_call = 1
            self.attempted += 1
        except LiveTransportRejected:
            raise
        except Exception:
            raise LiveTransportRejected("unverifiable signed provider request") from None

    def after_call(self) -> None:
        if self.seen_this_call != 1:
            raise LiveTransportRejected("missing signed on-wire request")
        self.pending = None


def _invoke(client: Any, wire: _WireFence, provider: Provider, role: str,
            verb: str, version: str | None = None) -> Any:
    wire.before_call(provider, role, verb, version)
    args = {"Bucket": provider.bucket, "Key": wire.obj.object_key}
    if verb == "PUT":
        args.update({"Body": wire.obj.envelope,
                     "ContentLength": len(wire.obj.envelope),
                     "ContentType": "application/octet-stream"})
        if provider == AWS:
            args["IfNoneMatch"] = "*"
        action = client.put_object
    elif verb == "HEAD":
        action = client.head_object
    elif verb == "GET":
        args["VersionId"] = version
        action = client.get_object
    else:
        raise LiveTransportRejected("unsupported SDK method")
    # Register a per-client callback before the first SDK method is ever used.
    # Duplicate callbacks/SDK retries are rejected by wire.seen_this_call.
    try:
        response = action(**args)
        wire.after_call()
        return response
    except Exception:
        if wire.seen_this_call != 1:
            raise LiveTransportRejected("SDK request did not pass signed fence") from None
        # On ambiguous SDK status, caller cannot issue another write.
        raise LiveTransportRejected("SDK request failed or ambiguous; no retry") from None


def _read_ciphertext(response: Any, version: str, expected_sha: str) -> bytes:
    if (not isinstance(response, dict)
            or response.get("VersionId") != version
            or type(response.get("ContentLength")) is not int
            or not 0 < response["ContentLength"] <= MAX_BYTES):
        raise LiveTransportRejected("versioned ciphertext receipt invalid")
    stream = response.get("Body")
    try:
        ciphertext = stream.read(MAX_BYTES + 1)
    except Exception:
        raise LiveTransportRejected("ciphertext readback failed") from None
    finally:
        try:
            stream.close()
        except Exception:
            pass
    if (type(ciphertext) is not bytes
            or len(ciphertext) != response["ContentLength"]
            or _sha(ciphertext) != expected_sha):
        raise LiveTransportRejected("remote ciphertext digest mismatch")
    return ciphertext


def _version(receipt: Any) -> str:
    value = receipt.get("VersionId") if isinstance(receipt, dict) else None
    if (not isinstance(value, str) or not 0 < len(value) <= 512
            or any(c in value for c in "\r\n")):
        raise LiveTransportRejected("versioned immutable upload receipt missing")
    return value


def _one_provider(provider: Provider, writer: Any, reader: Any, wire: _WireFence,
                  key: bytes, recovery_scratch: Path, restore_id: str) -> dict:
    if provider == B2:
        # Must observe exactly one signed preflight HEAD returning authentic 404.
        wire.before_call(provider, "reader", "HEAD", None)
        try:
            response = reader.head_object(Bucket=provider.bucket, Key=wire.obj.object_key)
        except Exception as exc:
            detail = getattr(exc, "response", None)
            error = detail.get("Error", {}) if isinstance(detail, dict) else {}
            meta = detail.get("ResponseMetadata", {}) if isinstance(detail, dict) else {}
            if (error.get("Code") not in ("404", "NoSuchKey", "NotFound")
                    or meta.get("HTTPStatusCode") != 404):
                raise LiveTransportRejected("B2 existence or access uncertain") from None
        else:
            raise LiveTransportRejected("B2 object already exists; no overwrite")
        wire.after_call()
    receipt = _invoke(writer, wire, provider, "writer", "PUT")
    version = _version(receipt)
    response = _invoke(reader, wire, provider, "reader", "GET", version)
    ciphertext = _read_ciphertext(response, version, wire.obj.envelope_sha256)
    restored = core.restore_verified_envelope(
        envelope=ciphertext, key=key, scratch_parent=recovery_scratch,
        restore_id=restore_id, expected_sha256=wire.obj.envelope_sha256,
    )
    if (restored["status"] != "LIVE_S02_AUTHENTICATED_RESTORE_VERIFIED"
            or restored["record_count"] != wire.obj.record_count
            or restored["plaintext_sha256"] != wire.obj.plaintext_sha256):
        raise LiveTransportRejected("independent provider restore inconsistent")
    return {"provider": provider.name, "region": provider.region,
            "object_sha256": wire.obj.envelope_sha256,
            "version_sha256": _sha(version.encode("utf-8")),
            "verified_records": restored["record_count"]}


def replicate_approved_s02(*, obj: core.SealedLiveCopy, key: bytes,
                           authorization: ReleaseAuthorization,
                           aws_writer: Any, aws_reader: Any,
                           b2_writer: Any, b2_reader: Any,
                           recovery_scratch: Path) -> dict:
    """Five request maximum. May use REAL cloud if explicitly invoked; NOT wired.

    No API is ever called by importing this module. Retention and billing
    attestations must be independently substantiated before invoking.
    """
    authorization.validate(obj)
    if (type(key) is not bytes or len(key) != 32
            or len({id(x) for x in (aws_writer, aws_reader, b2_writer, b2_reader)}) != 4
            or not KEY_RX.fullmatch(obj.object_key)
            or type(obj.envelope) is not bytes
            or not 0 < len(obj.envelope) <= MAX_BYTES
            or _sha(obj.envelope) != obj.envelope_sha256):
        raise LiveTransportRejected("invalid sealed source or independent client boundaries")
    core._safe_directory(Path(recovery_scratch))
    # Independent offline AEAD and full SQLite-chain verification MUST finish
    # before the first provider request; never send an unauthenticated envelope.
    try:
        preflight = core.restore_verified_envelope(
            envelope=obj.envelope, key=key, scratch_parent=Path(recovery_scratch),
            restore_id="preflight-" + _sha(obj.run_id.encode("utf-8"))[:24],
            expected_sha256=obj.envelope_sha256,
        )
        if (preflight["record_count"] != obj.record_count
                or preflight["plaintext_sha256"] != obj.plaintext_sha256):
            raise LiveTransportRejected("pre-transfer authenticated source mismatch")
    except LiveTransportRejected:
        raise
    except Exception:
        raise LiveTransportRejected("pre-transfer AEAD and ledger proof rejected") from None
    # Fail before network if any of the four pinned clients is misconfigured.
    for client, provider in (
        (aws_writer, AWS), (aws_reader, AWS),
        (b2_writer, B2), (b2_reader, B2),
    ):
        _client_checked(client, provider)
    wire = _WireFence(obj)
    for client in (aws_writer, aws_reader, b2_writer, b2_reader):
        client.meta.events.register("before-send.s3", wire.hook)
    # Strict order: AWS PUT+versioned GET, then B2 HEAD404+PUT+versioned GET.
    first = _one_provider(
        AWS, aws_writer, aws_reader, wire, key, Path(recovery_scratch),
        "aws-restore-0001",
    )
    second = _one_provider(
        B2, b2_writer, b2_reader, wire, key, Path(recovery_scratch),
        "b2-restore-0001",
    )
    if wire.pending is not None or wire.attempted != MAX_REQUESTS:
        raise LiveTransportRejected("request/receipt sequence incomplete")
    return {"status": "LIVE_S02_TWO_PROVIDER_VERIFIED",
            "attempted_signed_requests": wire.attempted, "receipts": [first, second],
            "data_rights_ref_sha256": authorization.rights_sha256}
