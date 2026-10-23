"""EXP049 P7: strict private encrypted-manifest escrow seam, OFFLINE ONLY.

Owner-injected exclusive-create and read-only callbacks. No client factory,
SDK, credential loader, network code, local persistence or active CLI.
Neither an acknowledgement nor a successful readback proves off-host durability.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable

from . import live_sqlite_envelope_v0_1 as core
from . import private_versioned_restore_manifest_v0_1 as manifest

ESCROW_PREFIX = "vowsig/private-recovery-receipts/v1"
MAX_SEALED_BYTES = len(manifest.MAGIC) + 12 + manifest.MAX_MANIFEST_BYTES + 16


class ReceiptEscrowRejected(RuntimeError):
    """Fixed, non-sensitive exception; never include callback exceptions."""


def _digest(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _identity(run_id: Any, sha256: Any) -> str:
    if (type(run_id) is not str or not core.RUN_ID.fullmatch(run_id)
            or type(sha256) is not str
            or not core.HEX64.fullmatch(sha256)):
        raise ReceiptEscrowRejected("invalid private escrow identity")
    return f"{ESCROW_PREFIX}/{run_id}/{sha256}.aesgcm"


def _sealed_bytes(blob: Any, digest: str) -> bytes:
    if (type(blob) is not bytes
            or not blob.startswith(manifest.MAGIC)
            or not len(manifest.MAGIC) + 12 + 16 < len(blob) <= MAX_SEALED_BYTES
            or _digest(blob) != digest):
        raise ReceiptEscrowRejected("invalid encrypted receipt content")
    return blob


def _attested_digest(value: Any) -> bool:
    return type(value) is str and core.HEX64.fullmatch(value) is not None


class OfflineImmutableReceiptEscrow:
    """P6 commit-and-readback seam using two separately injected operations.

    The writer MUST provide atomic exclusive-create semantics at the eventual
    approved independent backend. The reader MUST read the immutable key using
    an independently scoped identity. These contracts cannot be established
    by callbacks or hex attestations alone; use only synthetic callbacks until
    an independently reviewed external release. Do not claim off-host proof.
    """

    def __init__(
        self, *, write_once: Callable[[str, bytes, str], dict],
        read_exact: Callable[[str], bytes],
        writer_scope_ref_sha256: str,
        reader_scope_ref_sha256: str,
        owner_recovery_custody_ref_sha256: str,
    ) -> None:
        refs = (writer_scope_ref_sha256, reader_scope_ref_sha256,
                owner_recovery_custody_ref_sha256)
        if (not callable(write_once) or not callable(read_exact)
                or write_once is read_exact
                or not all(_attested_digest(x) for x in refs)
                or len(set(refs)) != 3):
            raise ReceiptEscrowRejected("independent receipt custody setup rejected")
        self._write_once = write_once
        self._read_exact = read_exact
        self._invoked = False

    def __repr__(self) -> str:
        return "<OfflineImmutableReceiptEscrow callbacks=REDACTED offhost_verified=False>"

    def __call__(self, sealed_bytes: bytes, digest: str, run_id: str) -> bytes:
        """One exclusive write + one independent read; never retry ambiguity.

        Returns encrypted bytes only for the existing P6 sink's own independent
        manifest decryption/verification. Does not return any live-release flag.
        """
        key = _identity(run_id, digest)
        _sealed_bytes(sealed_bytes, digest)
        if self._invoked:
            raise ReceiptEscrowRejected("private receipt escrow already attempted")
        self._invoked = True
        try:
            ack = self._write_once(key, sealed_bytes, digest)
            if (type(ack) is not dict
                    or set(ack) != {"status", "key", "sha256"}
                    or ack["status"] != "CREATED_EXCLUSIVELY"
                    or ack["key"] != key
                    or ack["sha256"] != digest):
                raise ReceiptEscrowRejected("exclusive create not acknowledged")
            readback = self._read_exact(key)
            if (_sealed_bytes(readback, digest) != sealed_bytes):
                raise ReceiptEscrowRejected("private receipt readback inconsistent")
            return readback
        except Exception:
            raise ReceiptEscrowRejected(
                "exclusive encrypted receipt commit/readback failed; no retry"
            ) from None


def open_from_independent_escrow(
    *, read_exact: Callable[[str], bytes],
    run_id: str, manifest_sha256: str, manifest_key: bytes,
) -> manifest.VerifiedRecoveryTargets:
    """Cold restart: independently locate/read/decrypt without source or writer.

    The caller must preserve the run ID, receipt SHA, vault configuration and
    manifest key independently of the original VPS. This never fetches the
    underlying AWS/B2 data backup or proves off-host persistence.
    """
    key = _identity(run_id, manifest_sha256)
    if not callable(read_exact):
        raise ReceiptEscrowRejected("independent read-only escrow reader required")
    try:
        blob = _sealed_bytes(read_exact(key), manifest_sha256)
        opened = manifest.open_private_recovery_manifest(
            sealed=blob, manifest_key=manifest_key,
            expected_sha256=manifest_sha256,
        )
        if opened.run_id != run_id:
            raise ReceiptEscrowRejected("recovery receipt identity mismatch")
        return opened
    except Exception:
        raise ReceiptEscrowRejected(
            "independent encrypted recovery receipt unavailable or invalid"
        ) from None
