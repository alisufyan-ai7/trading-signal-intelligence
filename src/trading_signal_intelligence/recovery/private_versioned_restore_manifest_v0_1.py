"""EXP047 P5: OFFLINE private exact-version disaster recovery manifest.

Contains real S3/B2 VersionIds only INSIDE AES-256-GCM ciphertext.
No external clients, account operations, ambient secret discovery or live DB.
An authentic encrypted manifest cannot by itself prove a remote object survives.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import live_sqlite_envelope_v0_1 as core
from . import live_dual_provider_transport_v0_1 as transport

SCHEMA = "vowsig-private-exact-version-manifest-v0.1"
MAGIC = b"VOWSIG_PRIVATE_VERSION_RECEIPT_V1\x00"
MAX_MANIFEST_BYTES = 8192
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class PrivateManifestRejected(RuntimeError):
    """Fixed message categories; never print exact versions or keys."""


@dataclass(frozen=True)
class SealedRecoveryManifest:
    """Object holding only encrypted recoverability references."""
    sealed_bytes: bytes
    sealed_sha256: str
    run_id: str


@dataclass(frozen=True)
class VerifiedRecoveryTargets:
    """Private recoverability references; NEVER log or send to GitHub."""
    object_key: str
    object_sha256: str
    plaintext_sha256: str
    record_count: int
    aws_version_id: str
    b2_version_id: str
    run_id: str
    key_custody_reference_sha256: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(payload: Mapping[str, Any]) -> bytes:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        allow_nan=False, ensure_ascii=False,
    ).encode("utf-8")


def _version_id(value: Any) -> str:
    # S3 version IDs are opaque. Preserve EXACT bytes in UTF-8 encoding,
    # rejecting controls rather than stripping or URL-decoding anything.
    if (type(value) is not str or not 0 < len(value) <= 512
            or not all(32 < ord(c) < 127 for c in value)):
        raise PrivateManifestRejected("unusable exact provider version")
    return value


def _require_key(key: Any) -> None:
    if type(key) is not bytes or len(key) != 32:
        raise PrivateManifestRejected("separately held manifest key required")


def _require_sha(value: Any) -> str:
    if type(value) is not str or not HEX64.fullmatch(value):
        raise PrivateManifestRejected("invalid immutable digest")
    return value


def _receipt_pair(result: Any, obj: core.SealedLiveCopy,
                  version_ids: Sequence[str]) -> tuple[str, str]:
    if (type(result) is not dict
            or set(result) != {"status", "attempted_signed_requests",
                               "receipts", "data_rights_ref_sha256"}
            or result["status"] != "LIVE_S02_TWO_PROVIDER_VERIFIED"
            or type(result["attempted_signed_requests"]) is not int
            or result["attempted_signed_requests"] != transport.MAX_REQUESTS
            or type(result["receipts"]) is not list
            or len(result["receipts"]) != 2
            or not isinstance(version_ids, (tuple, list))
            or len(version_ids) != 2
            or not isinstance(obj, core.SealedLiveCopy)):
        raise PrivateManifestRejected("incomplete dual-provider verification")
    a, b = (_version_id(version_ids[0]), _version_id(version_ids[1]))
    for receipt, provider, version in zip(
        result["receipts"], (transport.AWS, transport.B2), (a, b),
    ):
        if (type(receipt) is not dict
                or set(receipt) != {"provider", "region", "object_sha256",
                                   "version_sha256", "verified_records"}
                or receipt["provider"] != provider.name
                or receipt["region"] != provider.region
                or receipt["object_sha256"] != obj.envelope_sha256
                or receipt["version_sha256"] != _sha(version.encode("utf-8"))
                or type(receipt["verified_records"]) is not int
                or receipt["verified_records"] != obj.record_count):
            raise PrivateManifestRejected("provider receipt and version mismatch")
    _require_sha(result["data_rights_ref_sha256"])
    return a, b


def seal_private_recovery_manifest(
    *, obj: core.SealedLiveCopy, verified_result: Mapping[str, Any],
    version_ids: tuple[str, str],
    manifest_key: bytes, data_key: bytes,
    offhost_key_custody_reference_sha256: str,
) -> SealedRecoveryManifest:
    """After TWO verified remote restores, seal the exact version pointers.

    This method does not store or upload the receipt; future runtime must
    durably persist it in owner-controlled private off-host storage.
    """
    _require_key(manifest_key)
    _require_key(data_key)
    if manifest_key == data_key:
        raise PrivateManifestRejected("manifest and data keys must be independent")
    ref = _require_sha(offhost_key_custody_reference_sha256)
    if (not isinstance(obj, core.SealedLiveCopy)
            or type(obj.envelope) is not bytes
            or not core.RUN_ID.fullmatch(obj.run_id)
            or not transport.KEY_RX.fullmatch(obj.object_key)
            or not core.HEX64.fullmatch(obj.envelope_sha256)
            or _sha(obj.envelope) != obj.envelope_sha256
            or not core.HEX64.fullmatch(obj.plaintext_sha256)
            or type(obj.record_count) is not int or obj.record_count < 1):
        raise PrivateManifestRejected("invalid verified encrypted backup identity")
    aws_version, b2_version = _receipt_pair(
        verified_result, obj, version_ids
    )
    content = {
        "schema": SCHEMA,
        "run_id": obj.run_id,
        "object_key": obj.object_key,
        "object_sha256": obj.envelope_sha256,
        "plaintext_sha256": obj.plaintext_sha256,
        "record_count": obj.record_count,
        "aws": {
            "name": transport.AWS.name,
            "bucket": transport.AWS.bucket,
            "region": transport.AWS.region,
            "endpoint": transport.AWS.endpoint,
            "exact_version_id": aws_version,
        },
        "backblaze": {
            "name": transport.B2.name,
            "bucket": transport.B2.bucket,
            "region": transport.B2.region,
            "endpoint": transport.B2.endpoint,
            "exact_version_id": b2_version,
        },
        "key_custody_reference_sha256": ref,
        "rights_ref_sha256": verified_result["data_rights_ref_sha256"],
    }
    raw = _canonical(content)
    if len(raw) > MAX_MANIFEST_BYTES:
        raise PrivateManifestRejected("private manifest exceeded size budget")
    # GCM authenticates schema prefix and every field; fresh nonce per receipt.
    packed = MAGIC + os.urandom(12)
    encrypted = AESGCM(manifest_key).encrypt(packed[len(MAGIC):], raw, MAGIC)
    blob = packed + encrypted
    return SealedRecoveryManifest(
        sealed_bytes=blob, sealed_sha256=_sha(blob), run_id=obj.run_id
    )


def open_private_recovery_manifest(
    *, sealed: bytes, manifest_key: bytes, expected_sha256: str,
) -> VerifiedRecoveryTargets:
    """Independent offline authenticated exact-version recovery resolution."""
    _require_key(manifest_key)
    _require_sha(expected_sha256)
    if (type(sealed) is not bytes
            or not sealed.startswith(MAGIC)
            or not len(MAGIC) + 12 + 16 < len(sealed) <= len(MAGIC) + 12 + MAX_MANIFEST_BYTES + 16
            or _sha(sealed) != expected_sha256):
        raise PrivateManifestRejected("encrypted manifest identity rejected")
    nonce = sealed[len(MAGIC):len(MAGIC) + 12]
    ciphertext = sealed[len(MAGIC) + 12:]
    try:
        raw = AESGCM(manifest_key).decrypt(nonce, ciphertext, MAGIC)
        data = json.loads(raw)
        if (type(data) is not dict or _canonical(data) != raw
                or set(data) != {"schema", "run_id", "object_key", "object_sha256",
                                 "plaintext_sha256", "record_count", "aws",
                                 "backblaze", "key_custody_reference_sha256",
                                 "rights_ref_sha256"}
                or data["schema"] != SCHEMA
                or not isinstance(data["run_id"], str)
                or not core.RUN_ID.fullmatch(data["run_id"])
                or not isinstance(data["object_key"], str)
                or not transport.KEY_RX.fullmatch(data["object_key"])
                or not isinstance(data["record_count"], int)
                or type(data["record_count"]) is not int
                or not 0 < data["record_count"] <= 1_000_000):
            raise PrivateManifestRejected("private recovery schema invalid")
        for key in ("object_sha256", "plaintext_sha256",
                    "key_custody_reference_sha256", "rights_ref_sha256"):
            _require_sha(data[key])
        if data["object_key"] != (
            f"vowsig/approved-s02/v1/{data['run_id']}/{data['object_sha256']}.aesgcm"
        ):
            raise PrivateManifestRejected("object key and ciphertext hash mismatch")
        for key, provider in (("aws", transport.AWS), ("backblaze", transport.B2)):
            entry = data[key]
            if (type(entry) is not dict
                    or set(entry) != {"name", "bucket", "region", "endpoint",
                                     "exact_version_id"}
                    or (entry["name"], entry["bucket"], entry["region"], entry["endpoint"])
                       != (provider.name, provider.bucket, provider.region, provider.endpoint)):
                raise PrivateManifestRejected("provider vault target invalid")
            _version_id(entry["exact_version_id"])
    except PrivateManifestRejected:
        raise
    except (InvalidTag, UnicodeDecodeError, ValueError, TypeError, KeyError):
        raise PrivateManifestRejected("private recovery manifest authentication failed") from None
    return VerifiedRecoveryTargets(
        object_key=data["object_key"],
        object_sha256=data["object_sha256"],
        plaintext_sha256=data["plaintext_sha256"],
        record_count=data["record_count"],
        aws_version_id=data["aws"]["exact_version_id"],
        b2_version_id=data["backblaze"]["exact_version_id"],
        run_id=data["run_id"],
        key_custody_reference_sha256=data["key_custody_reference_sha256"],
    )


def public_receipt_summary(sealed: SealedRecoveryManifest) -> dict[str, Any]:
    """Hash-only safe audit result. Opaque cloud versions MUST stay private."""
    if (not isinstance(sealed, SealedRecoveryManifest)
            or type(sealed.sealed_bytes) is not bytes
            or _sha(sealed.sealed_bytes) != _require_sha(sealed.sealed_sha256)
            or not core.RUN_ID.fullmatch(sealed.run_id)):
        raise PrivateManifestRejected("encrypted manifest audit identity invalid")
    return {
        "status": "OFFLINE_PRIVATE_RECOVERY_MANIFEST_SEALED",
        "manifest_sha256": sealed.sealed_sha256,
        "run_id": sealed.run_id,
        "real_provider_operation_authorized": False,
        "offhost_persistence_verified": False,
    }
