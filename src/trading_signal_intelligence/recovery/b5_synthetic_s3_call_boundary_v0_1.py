"""EXP039: fail-closed synthetic-only S3 SDK call boundary, NOT a cloud driver.

Wrap caller-provided boto3-style clients (or fake clients) to constrain allowed
methods, object key, kwargs, and call ordering per provider. No SDK imports,
credentials, session/client creation, CLI, network, or automatic invocation.

IMPORTANT: The guard restricts Python *method invocations*, not on-wire HTTP
requests and is not a security sandbox. Any future real pilot must separately
pin explicit credentials, disable credential discovery and SDK retries, validate
a real request trace and receive fresh owner authorization. $0 is not guaranteed.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any

from . import b3_synthetic_encrypted_offsite_v0_1 as b3
from . import b4_synthetic_s3_pilot_v0_1 as b4


class SyntheticS3BoundaryRejected(RuntimeError):
    """Keep SDK exceptions and credential material out of operator output."""


def _is_version(value: Any) -> bool:
    return (isinstance(value, str) and 0 < len(value) <= 512
            and not any(c in value for c in "\r\n"))


@dataclass
class _Gate:
    provider: b4.Provider
    object_key: str
    envelope: bytes
    sha256: str
    next_step: str = field(init=False)
    version: str | None = None
    calls: list[str] = field(default_factory=list)
    poisoned: bool = False

    def __post_init__(self) -> None:
        self.next_step = "PUT" if self.provider == b4.AWS else "HEAD"

    def enter(self, action: str, role: str, kwargs: dict, exact: set[str]) -> None:
        if (self.poisoned or action != self.next_step
                or not isinstance(kwargs, dict)
                or set(kwargs) != exact
                or kwargs.get("Bucket") != self.provider.bucket
                or kwargs.get("Key") != self.object_key):
            raise SyntheticS3BoundaryRejected("synthetic S3 call denied")
        expected_role = "writer" if action == "PUT" else "reader"
        if role != expected_role:
            raise SyntheticS3BoundaryRejected("synthetic S3 role denied")
        if action == "PUT":
            if (type(kwargs.get("Body")) is not bytes
                    or kwargs["Body"] != self.envelope
                    or type(kwargs.get("ContentLength")) is not int
                    or kwargs["ContentLength"] != len(self.envelope)
                    or kwargs.get("ContentType") != "application/octet-stream"
                    or (self.provider == b4.AWS
                        and kwargs.get("IfNoneMatch") != "*")):
                raise SyntheticS3BoundaryRejected("synthetic upload arguments denied")
        if action == "GET" and (
            not _is_version(self.version)
            or kwargs.get("VersionId") != self.version
        ):
            raise SyntheticS3BoundaryRejected("synthetic version selection denied")
        self.calls.append(action)
        # A write or read may succeed remotely even if the SDK later throws;
        # fail closed and never issue a second attempt through this gate.
        self.poisoned = True

    def finish(self, next_step: str, *, version: str | None = None) -> None:
        if version is not None:
            if not _is_version(version):
                raise SyntheticS3BoundaryRejected("synthetic version receipt denied")
            self.version = version
        self.next_step = next_step
        self.poisoned = False


class _Client:
    """Exposes ONLY methods B4 requires; no arbitrary SDK method forwarding."""

    def __init__(self, underlying: Any, role: str, gate: _Gate) -> None:
        if role not in ("reader", "writer"):
            raise SyntheticS3BoundaryRejected("synthetic client role denied")
        self._underlying = underlying
        self._role = role
        self._gate = gate
        self.meta = underlying.meta

    def head_object(self, **kwargs: Any) -> Any:
        gate = self._gate
        if gate.provider != b4.B2:
            raise SyntheticS3BoundaryRejected("AWS synthetic HEAD denied")
        gate.enter("HEAD", self._role, kwargs, {"Bucket", "Key"})
        try:
            response = self._underlying.head_object(**kwargs)
        except Exception as exc:
            details = getattr(exc, "response", None)
            error = details.get("Error", {}) if isinstance(details, dict) else {}
            meta = details.get("ResponseMetadata", {}) if isinstance(details, dict) else {}
            if (error.get("Code") in ("404", "NoSuchKey", "NotFound")
                    and meta.get("HTTPStatusCode") == 404):
                gate.finish("PUT")
            # Preserve a *structured* error signal to B4 but never propagate
            # the original SDK exception, which may contain credential fields.
            class _NotFound(Exception):
                response = {
                    "Error": {"Code": "404"},
                    "ResponseMetadata": {"HTTPStatusCode": 404},
                }
            if gate.next_step == "PUT" and not gate.poisoned:
                raise _NotFound() from None
            raise SyntheticS3BoundaryRejected("synthetic object HEAD inconclusive") from None
        # A 200 (existing key) is a terminal refusal, not permission to upload.
        raise SyntheticS3BoundaryRejected("synthetic object key already exists")

    def put_object(self, **kwargs: Any) -> Any:
        gate = self._gate
        fields = {"Bucket", "Key", "Body", "ContentLength", "ContentType"}
        if gate.provider == b4.AWS:
            fields.add("IfNoneMatch")
        gate.enter("PUT", self._role, kwargs, fields)
        try:
            response = self._underlying.put_object(**kwargs)
            if not isinstance(response, dict) or not _is_version(response.get("VersionId")):
                raise SyntheticS3BoundaryRejected("no usable synthetic version receipt")
        except Exception:
            raise SyntheticS3BoundaryRejected("synthetic PUT failed or ambiguous") from None
        gate.finish("GET", version=response["VersionId"])
        return response

    def get_object(self, **kwargs: Any) -> Any:
        gate = self._gate
        gate.enter("GET", self._role, kwargs, {"Bucket", "Key", "VersionId"})
        # A successful response is NOT a verified restore; B4 authenticates
        # full downloaded bytes, the AEAD tag and SQLite record chain afterward.
        try:
            result = self._underlying.get_object(**kwargs)
            if (not isinstance(result, dict)
                    or result.get("VersionId") != gate.version):
                raise SyntheticS3BoundaryRejected("unverified synthetic GET response")
        except Exception:
            raise SyntheticS3BoundaryRejected("synthetic GET failed or ambiguous") from None
        gate.next_step = "DONE"
        # Stay poisoned: repeated GET or other calls can never execute.
        return result


def guard_pair(
    provider: b4.Provider, writer: Any, reader: Any, obj: b3.SealedSynthetic
) -> tuple[_Client, _Client, _Gate]:
    """Construct guards; no provider method or request is invoked here."""
    if provider not in (b4.AWS, b4.B2):
        raise SyntheticS3BoundaryRejected("unapproved provider")
    if writer is reader:
        raise SyntheticS3BoundaryRejected("shared read/write client denied")
    if (not isinstance(obj, b3.SealedSynthetic)
            or not isinstance(obj.envelope, bytes)
            or not 0 < len(obj.envelope) <= b4.MAX_ENVELOPE_BYTES
            or not b4.KEY_RE.fullmatch(obj.object_key)
            or hashlib.sha256(obj.envelope).hexdigest() != obj.envelope_sha256
            or not obj.object_key.endswith(f"/{obj.envelope_sha256}.aesgcm")):
        raise SyntheticS3BoundaryRejected("invalid synthetic encrypted envelope")
    try:
        b4._check_client(writer, provider)
        b4._check_client(reader, provider)
        gate = _Gate(provider, obj.object_key, obj.envelope, obj.envelope_sha256)
        return _Client(writer, "writer", gate), _Client(reader, "reader", gate), gate
    except SyntheticS3BoundaryRejected:
        raise
    except Exception:
        raise SyntheticS3BoundaryRejected("unverified synthetic SDK client") from None
