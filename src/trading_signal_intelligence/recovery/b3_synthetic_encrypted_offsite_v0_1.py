"""B3 synthetic-only authenticated backup/restore with two isolated memory stores.

NO cloud SDK, network, CLI, scheduling, credentials, or production database access.
Only an explicitly marked, disposable B1/B2 SQLite synthetic fixture is accepted.
The encrypted envelope contains all decryption metadata except the separately held
key; a source-machine loss must not make cloud recovery impossible.
Never wire this module to a production runtime or real cloud uploader.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import b1b2_synthetic_v0_1 as b1b2

MAX_FILE_BYTES = 1_048_576
MAX_OBJECT_BYTES = 1_100_000
OBJECT_PREFIX = "pilot/synthetic/v1/"
MAGIC = b"VOWSIG_B3_SYNTHETIC_V1\x00"
MAX_AAD_BYTES = 2048
ID_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
SHA_RE = re.compile(r"^[a-f0-9]{64}$")


class SyntheticOffsiteRejected(RuntimeError):
    """Reject an unsafe synthetic test without exposing confidential content."""


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _valid_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) != 32:
        raise SyntheticOffsiteRejected("32-byte test encryption key required")


def _decode_envelope(envelope: bytes) -> tuple[dict, bytes, bytes, bytes]:
    """Strict bounded parsing of untrusted ciphertext and authenticated metadata."""
    if not isinstance(envelope, bytes) or not 0 < len(envelope) <= MAX_OBJECT_BYTES:
        raise SyntheticOffsiteRejected("synthetic object size or type rejected")
    if not envelope.startswith(MAGIC):
        raise SyntheticOffsiteRejected("unsupported synthetic object envelope")
    start = len(MAGIC)
    if len(envelope) < start + 2 + 12 + 16:
        raise SyntheticOffsiteRejected("truncated synthetic object")
    aad_length = int.from_bytes(envelope[start:start + 2], "big")
    if aad_length <= 0 or aad_length > MAX_AAD_BYTES:
        raise SyntheticOffsiteRejected("invalid synthetic metadata size")
    nonce = envelope[start + 2:start + 14]
    aad = envelope[start + 14:start + 14 + aad_length]
    ciphertext = envelope[start + 14 + aad_length:]
    if len(aad) != aad_length or len(ciphertext) < 17:
        raise SyntheticOffsiteRejected("truncated synthetic authenticated fields")
    try:
        metadata = json.loads(aad.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise SyntheticOffsiteRejected("invalid synthetic metadata encoding") from exc
    if not isinstance(metadata, dict) or _canonical(metadata) != aad:
        raise SyntheticOffsiteRejected("invalid synthetic canonical metadata")
    if (set(metadata) != {
        "schema", "classification", "artifact_id", "plaintext_sha256",
        "plaintext_size", "record_count",
    } or metadata["schema"] != "vowsig-synthetic-aes256gcm-v1"
            or metadata["classification"] != "SYNTHETIC_ONLY_NEVER_PRODUCTION"
            or not isinstance(metadata["artifact_id"], str)
            or not ID_RE.fullmatch(metadata["artifact_id"])
            or not isinstance(metadata["plaintext_sha256"], str)
            or not SHA_RE.fullmatch(metadata["plaintext_sha256"])
            or type(metadata["plaintext_size"]) is not int
            or not 0 < metadata["plaintext_size"] <= MAX_FILE_BYTES
            or type(metadata["record_count"]) is not int
            or not 0 < metadata["record_count"] <= 1_000_000):
        raise SyntheticOffsiteRejected("synthetic metadata classification rejected")
    return metadata, nonce, aad, ciphertext


@dataclass(frozen=True)
class SealedSynthetic:
    """Local test locator; restore requires only envelope bytes and off-host key."""

    object_key: str
    envelope: bytes
    envelope_sha256: str
    plaintext_sha256: str
    plaintext_size: int
    record_count: int


def seal_captured_synthetic_s02(root: Path, copied: Path, *,
                                artifact_id: str, key: bytes) -> SealedSynthetic:
    """Accept only an already-verified synthetic captured/S02 file, never live data."""
    _valid_key(key)
    if not ID_RE.fullmatch(artifact_id):
        raise SyntheticOffsiteRejected("invalid immutable synthetic artifact ID")
    try:
        base = b1b2.assert_fixture_scope(Path(root))
        source = Path(copied)
        if source.is_symlink() or source.name != "forward.sqlite":
            raise SyntheticOffsiteRejected("synthetic forward copy required")
        resolved = source.resolve(strict=True)
        # No paths outside <synthetic fixture>/captured/<immutable set>/.
        if (resolved.parent.parent != base / "captured"
                or not ID_RE.fullmatch(resolved.parent.name)
                or resolved.parent.is_symlink()
                or resolved.parent.parent.is_symlink()):
            raise SyntheticOffsiteRejected("outside synthetic captured fixture")
        length = resolved.stat().st_size
        if not 0 < length <= MAX_FILE_BYTES:
            raise SyntheticOffsiteRejected("synthetic size budget exceeded")
        verification = b1b2.verify_synthetic_copy(resolved, "S02")
        plaintext = resolved.read_bytes()
        if _digest(plaintext) != verification["copy_sha256"]:
            raise SyntheticOffsiteRejected("synthetic copy changed during sealing")
    except (OSError, b1b2.SyntheticGateRejected) as exc:
        raise SyntheticOffsiteRejected("synthetic fixture attestation failed") from exc
    metadata = {
        "schema": "vowsig-synthetic-aes256gcm-v1",
        "classification": "SYNTHETIC_ONLY_NEVER_PRODUCTION",
        "artifact_id": artifact_id,
        "plaintext_sha256": _digest(plaintext),
        "plaintext_size": len(plaintext),
        "record_count": verification["records"],
    }
    aad = _canonical(metadata)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    if len(aad) > MAX_AAD_BYTES:
        raise SyntheticOffsiteRejected("synthetic authenticated metadata too large")
    envelope = MAGIC + len(aad).to_bytes(2, "big") + nonce + aad + ciphertext
    if len(envelope) > MAX_OBJECT_BYTES:
        raise SyntheticOffsiteRejected("encrypted synthetic object over byte limit")
    return SealedSynthetic(
        object_key=f"{OBJECT_PREFIX}{artifact_id}/{_digest(envelope)}.aesgcm",
        envelope=envelope, envelope_sha256=_digest(envelope),
        plaintext_sha256=_digest(plaintext), plaintext_size=len(plaintext),
        record_count=verification["records"],
    )


class MemoryBucket:
    """No network provider implementation; stores only synthetic ciphertext."""

    def __init__(self, name: str):
        if name not in ("aws-s3-synthetic", "b2-synthetic"):
            raise SyntheticOffsiteRejected("unrecognized synthetic destination")
        self.name = name
        self._objects: dict[str, bytes] = {}

    def put_new(self, obj: SealedSynthetic) -> None:
        if (not obj.object_key.startswith(OBJECT_PREFIX)
                or len(obj.envelope) > MAX_OBJECT_BYTES
                or _digest(obj.envelope) != obj.envelope_sha256
                or not obj.object_key.endswith(f"/{obj.envelope_sha256}.aesgcm")
                or obj.object_key in self._objects):
            raise SyntheticOffsiteRejected("invalid or duplicate synthetic object")
        _decode_envelope(obj.envelope)
        self._objects[obj.object_key] = obj.envelope

    def get(self, key: str) -> bytes:
        if not key.startswith(OBJECT_PREFIX) or key not in self._objects:
            raise SyntheticOffsiteRejected("synthetic object missing")
        return self._objects[key]


def replicate_and_readback(obj: SealedSynthetic, aws: MemoryBucket,
                           b2: MemoryBucket) -> dict:
    """No rollback/overwrite on partial failure; both stores are independent."""
    if aws.name != "aws-s3-synthetic" or b2.name != "b2-synthetic" or aws is b2:
        raise SyntheticOffsiteRejected("independent synthetic stores required")
    for store in (aws, b2):
        store.put_new(obj)
        if _digest(store.get(obj.object_key)) != obj.envelope_sha256:
            raise SyntheticOffsiteRejected("synthetic provider readback mismatch")
    return {
        "status": "SYNTHETIC_ONLY_TWO_MEMORY_READBACKS_VERIFIED",
        "object_key": obj.object_key,
        "envelope_sha256": obj.envelope_sha256,
        "plaintext_sha256": obj.plaintext_sha256,
        "provider_count": 2,
        "cloud_uploads": 0,
        "billable_requests": 0,
    }


def restore_synthetic_s02(root: Path, downloaded: bytes, *, key: bytes,
                          restore_id: str) -> dict:
    """Restore from remote bytes and off-host key; no original local manifest required."""
    _valid_key(key)
    if not ID_RE.fullmatch(restore_id):
        raise SyntheticOffsiteRejected("invalid synthetic restore ID")
    try:
        base = b1b2.assert_fixture_scope(Path(root))
        metadata, nonce, aad, ciphertext = _decode_envelope(downloaded)
        # Authenticate and check plaintext BEFORE making any filesystem changes.
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
        if (_digest(plaintext) != metadata["plaintext_sha256"]
                or len(plaintext) != metadata["plaintext_size"]):
            raise SyntheticOffsiteRejected("synthetic restored plaintext mismatch")
        restored_dir = base / "restored"
        if restored_dir.is_symlink():
            raise SyntheticOffsiteRejected("unsafe synthetic restore directory")
        restored_dir.mkdir(exist_ok=True)
        target_dir = restored_dir / restore_id
        target_dir.mkdir(exist_ok=False)
        out = target_dir / "forward.sqlite"
        with out.open("xb") as stream:
            stream.write(plaintext)
        report = b1b2.verify_synthetic_copy(out, "S02")
        if (report["records"] != metadata["record_count"]
                or report["copy_sha256"] != metadata["plaintext_sha256"]):
            raise SyntheticOffsiteRejected("synthetic restored ledger verification failed")
        return {"status": "SYNTHETIC_ONLY_RESTORE_VERIFIED",
                "sha256": report["copy_sha256"], "records": report["records"],
                "cloud_uploads": 0}
    except (InvalidTag, ValueError, OSError, b1b2.SyntheticGateRejected) as exc:
        raise SyntheticOffsiteRejected("synthetic authentication or restore failed") from exc
