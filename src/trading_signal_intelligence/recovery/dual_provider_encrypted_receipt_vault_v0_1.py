"""Fixed-target encrypted dual-provider S3 receipt escrow -- NOT LIVE.

This module prepares a real boto3-client-compatible protocol for encrypted
P5/P7 VersionId receipts. Four independent *extra client instances* are
required because P2's per-client signed wire hooks remain registered after data
upload. The SAME four off-VPS credential identities may construct them later,
subject to IAM and separate release approval. No SDK factory or ambient secrets.

B2's HEAD404 + PUT is NOT atomic exclusive-create; therefore even when the
code is separately enabled and fake tests pass, it cannot independently prove
the P7 atomic exclusive-create contract or offhost persistence. A future
release must provide a stronger immutability design and external evidence.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit
from typing import Any

from . import live_dual_provider_transport_v0_1 as transport
from . import offline_immutable_receipt_escrow_v0_1 as p7
from . import private_versioned_restore_manifest_v0_1 as p5

# Must be changed only in a separately reviewed exact release commit.
REAL_ESCROW_REQUESTS_ENABLED = False
# B2 HEAD404+PUT is not an atomic exclusive create; never bypass by boolean attestation.
B2_EXCLUSIVE_CREATE_PROTOCOL_AVAILABLE = False
MAX_WIRE_ATTEMPTS = 5
MAX_ENCRYPTED_RECEIPT_BYTES = p7.MAX_SEALED_BYTES


class CloudEscrowRejected(RuntimeError):
    """No raw SDK exceptions, credentials, bucket paths or version IDs."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _opaque_version(response: Any) -> str:
    value = response.get("VersionId") if type(response) is dict else None
    if (type(value) is not str or not 0 < len(value) <= 512
            or not all(32 < ord(char) < 127 for char in value)):
        raise CloudEscrowRejected("encrypted receipt cloud version missing")
    return value


class _ReceiptSignedFence:
    """Signed SDK request observer, fails closed on unexpected/retried calls."""

    def __init__(self):
        self.expected = None
        self.attempts = 0
        self.seen = 0

    def before(self, provider, role, verb, key, version=None, payload=None):
        if self.expected is not None or self.attempts >= MAX_WIRE_ATTEMPTS:
            raise CloudEscrowRejected("signed encrypted receipt request budget exhausted")
        self.expected = (provider, role, verb, key, version, payload)
        self.seen = 0

    def hook(self, request: Any, **kwargs: Any) -> None:
        if self.expected is None or self.seen != 0:
            raise CloudEscrowRejected("unexpected or retried signed receipt request")
        provider, role, verb, key, version, payload = self.expected
        try:
            uri = urlsplit(request.url)
            headers = transport._signed_http_headers(request.headers)
            auth = headers.get("authorization", "")
            if (request.method != verb or uri.scheme != "https"
                    or uri.netloc != urlsplit(provider.endpoint).netloc
                    or unquote(uri.path) != f"/{provider.bucket}/{key}"
                    or not auth.startswith("AWS4-HMAC-SHA256 ")
                    or f"/{provider.region}/s3/aws4_request" not in auth
                    or "transfer-encoding" in headers):
                raise CloudEscrowRejected("receipt signed target mismatch")
            query = parse_qs(uri.query, keep_blank_values=True)
            if verb == "GET":
                if query != {"versionId": [version]}:
                    raise CloudEscrowRejected("receipt exact version query mismatch")
            elif query:
                raise CloudEscrowRejected("unexpected receipt SDK query")
            if verb == "PUT":
                if (role != "writer" or type(payload) is not bytes
                        or not transport._body_matches(request.body, payload)
                        or headers.get("content-length") != str(len(payload))
                        or headers.get("content-type") != "application/octet-stream"
                        or (provider == transport.AWS and
                            headers.get("if-none-match") != "*")
                        or (provider == transport.B2 and
                            "if-none-match" in headers)):
                    raise CloudEscrowRejected("encrypted receipt signed body mismatch")
            elif role != "reader":
                raise CloudEscrowRejected("receipt reader role mismatch")
            self.attempts += 1
            self.seen = 1
        except CloudEscrowRejected:
            raise
        except Exception:
            raise CloudEscrowRejected("unverifiable signed receipt wire event") from None

    def after(self):
        if self.seen != 1:
            raise CloudEscrowRejected("receipt SDK signed operation missing")
        self.expected = None


class PreparedDualProviderEncryptedReceiptVault:
    """Prepared P7 write/read callbacks. No network while compiled OFF.

    Four clients must be distinct instances NOT previously used by the P2
    transport signed fence; otherwise the original hooks deliberately reject.
    This class does not construct or discover credentials. After a future
    reviewed release, it still cannot prove durable off-VPS escrow without
    independent provider retention/rights/cost/restore evidence.
    """

    def __init__(self, *, aws_writer: Any, aws_reader: Any,
                 b2_writer: Any, b2_reader: Any) -> None:
        self._clients = (aws_writer, aws_reader, b2_writer, b2_reader)
        self._fence = _ReceiptSignedFence()
        self._invoked = False
        self._key = None
        self._sha = None
        self._versions = None

    def __repr__(self):
        return "<PreparedDualProviderEncryptedReceiptVault versions=REDACTED live=False>"

    def _preflight(self):
        if not REAL_ESCROW_REQUESTS_ENABLED:
            raise CloudEscrowRejected("encrypted receipt cloud I/O compiled OFF")
        if not B2_EXCLUSIVE_CREATE_PROTOCOL_AVAILABLE:
            raise CloudEscrowRejected("B2 atomic no-overwrite not established; no requests")
        if len({id(x) for x in self._clients}) != 4:
            raise CloudEscrowRejected("independent receipt SDK clients missing")
        for client, provider in zip(
            self._clients,
            (transport.AWS, transport.AWS, transport.B2, transport.B2)
        ):
            transport._client_checked(client, provider)
        if self._fence.attempts:
            raise CloudEscrowRejected("receipt vault already used")

    def _invoke(self, client, provider, role, verb, key,
                version=None, payload=None):
        self._fence.before(provider, role, verb, key, version, payload)
        args = {"Bucket": provider.bucket, "Key": key}
        if verb == "PUT":
            args.update({
                "Body": payload, "ContentLength": len(payload),
                "ContentType": "application/octet-stream",
            })
            if provider == transport.AWS:
                args["IfNoneMatch"] = "*"
            method = client.put_object
        elif verb == "GET":
            args["VersionId"] = version
            method = client.get_object
        else:
            method = client.head_object
        try:
            response = method(**args)
            self._fence.after()
            return response
        except Exception:
            # SDK failures can be ambiguous even if a remote PUT succeeded.
            raise CloudEscrowRejected(
                "encrypted receipt SDK operation ambiguous; no retry"
            ) from None

    def _b2_head_missing(self, key):
        provider = transport.B2
        self._fence.before(provider, "reader", "HEAD", key)
        try:
            self._clients[3].head_object(Bucket=provider.bucket, Key=key)
        except Exception as exc:
            response = getattr(exc, "response", None)
            error = response.get("Error", {}) if type(response) is dict else {}
            meta = response.get("ResponseMetadata", {}) if type(response) is dict else {}
            if (error.get("Code") not in ("404", "NoSuchKey", "NotFound")
                    or meta.get("HTTPStatusCode") != 404):
                raise CloudEscrowRejected("B2 receipt existence uncertain") from None
        else:
            raise CloudEscrowRejected("B2 encrypted receipt already exists")
        self._fence.after()

    def write_once(self, key: str, payload: bytes, sha256: str) -> dict:
        """At most AWS PUT + B2 signed HEAD + B2 PUT; no cleanup/retry."""
        self._preflight()
        if self._invoked:
            raise CloudEscrowRejected("encrypted receipt already attempted")
        self._invoked = True
        if (type(key) is not str
                or not key.startswith(p7.ESCROW_PREFIX + "/")
                or type(sha256) is not str
                or not p7.core.HEX64.fullmatch(sha256)):
            raise CloudEscrowRejected("encrypted receipt key identity rejected")
        try:
            expected_key = p7._identity(
                key[len(p7.ESCROW_PREFIX) + 1:].split("/", 1)[0], sha256
            )
            if expected_key != key:
                raise CloudEscrowRejected("receipt key does not bind digest")
            p7._sealed_bytes(payload, sha256)
            for client, provider in zip(
                self._clients,
                (transport.AWS, transport.AWS, transport.B2, transport.B2)
            ):
                transport._client_checked(client, provider)
                client.meta.events.register("before-send.s3", self._fence.hook)
            aws_receipt = self._invoke(
                self._clients[0], transport.AWS, "writer", "PUT", key,
                payload=payload
            )
            aws_version = _opaque_version(aws_receipt)
            self._b2_head_missing(key)
            b2_receipt = self._invoke(
                self._clients[2], transport.B2, "writer", "PUT", key,
                payload=payload
            )
            b2_version = _opaque_version(b2_receipt)
            self._key = key
            self._sha = sha256
            self._versions = (aws_version, b2_version)
            if self._fence.attempts != 3:
                raise CloudEscrowRejected("receipt write sequence incomplete")
            return {"status": "CREATED_EXCLUSIVELY",
                    "key": key, "sha256": sha256}
        except Exception:
            raise CloudEscrowRejected(
                "encrypted receipt write uncertain; no retry or deletion"
            ) from None

    def read_exact(self, key: str) -> bytes:
        """Independent exact-version readback for *both* prior receipt PUTs."""
        if (not REAL_ESCROW_REQUESTS_ENABLED
                or type(key) is not str or key != self._key
                or self._sha is None or self._versions is None
                or self._fence.attempts != 3):
            raise CloudEscrowRejected("verified receipt readback not configured")
        copies = []
        for client, provider, version in (
            (self._clients[1], transport.AWS, self._versions[0]),
            (self._clients[3], transport.B2, self._versions[1]),
        ):
            try:
                response = self._invoke(
                    client, provider, "reader", "GET", key, version=version
                )
                if (type(response) is not dict
                        or response.get("VersionId") != version
                        or type(response.get("ContentLength")) is not int
                        or not 0 < response["ContentLength"] <= MAX_ENCRYPTED_RECEIPT_BYTES):
                    raise CloudEscrowRejected("remote receipt version invalid")
                stream = response.get("Body")
                try:
                    data = stream.read(MAX_ENCRYPTED_RECEIPT_BYTES + 1)
                finally:
                    stream.close()
                p7._sealed_bytes(data, self._sha)
                if len(data) != response["ContentLength"]:
                    raise CloudEscrowRejected("remote receipt length mismatch")
                copies.append(data)
            except Exception:
                raise CloudEscrowRejected(
                    "encrypted receipt exact-version readback failed"
                ) from None
        if (len(copies) != 2 or copies[0] != copies[1]
                or self._fence.attempts != MAX_WIRE_ATTEMPTS):
            raise CloudEscrowRejected("dual receipt readback mismatch")
        return copies[0]
