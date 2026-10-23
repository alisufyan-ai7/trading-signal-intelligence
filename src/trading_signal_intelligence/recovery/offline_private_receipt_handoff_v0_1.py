"""EXP048 P6: private two-provider exact-version in-memory receipt handoff.

Only the operator-supplied commit-and-readback callable may persist bytes. This
module imports NO AWS/B2 SDK, offers no runtime CLI or scheduler, and cannot
establish real off-host durability or permission for provider networking.
"""
from __future__ import annotations

import hashlib
from typing import Any, Callable

from . import live_sqlite_envelope_v0_1 as core
from . import private_versioned_restore_manifest_v0_1 as private


class ReceiptHandoffRejected(RuntimeError):
    """Never include exact raw cloud version IDs, data, or key values."""


class OfflinePrivateReceiptSink:
    """Owner-injected function that receives *only* two verified version IDs.

    This object is safe for in-memory fake-store tests, not authorization for
    real cloud. A future independent release must verify actual offhost
    persistence, access controls and recovery keys.
    """

    def __init__(
        self, *, data_key: bytes, manifest_key: bytes,
        key_custody_ref_sha256: str,
        commit_and_readback: Callable[[bytes, str, str], bytes],
    ) -> None:
        if (type(data_key) is not bytes or len(data_key) != 32
                or type(manifest_key) is not bytes or len(manifest_key) != 32
                or data_key == manifest_key
                or type(key_custody_ref_sha256) is not str
                or not core.HEX64.fullmatch(key_custody_ref_sha256)
                or not callable(commit_and_readback)):
            raise ReceiptHandoffRejected("private manifest custody configuration rejected")
        self._data_key = data_key
        self._manifest_key = manifest_key
        self._custody_ref = key_custody_ref_sha256
        self._commit = commit_and_readback
        self._invoked = False

    def __repr__(self) -> str:
        return "<OfflinePrivateReceiptSink keys=REDACTED>"

    def __call__(
        self, obj: core.SealedLiveCopy, public_verified_result: dict,
        exact_version_ids: tuple[str, str],
    ) -> dict:
        if self._invoked:
            raise ReceiptHandoffRejected("private receipt callback already consumed")
        self._invoked = True  # no retries, including on failure
        try:
            encrypted = private.seal_private_recovery_manifest(
                obj=obj,
                verified_result=public_verified_result,
                version_ids=exact_version_ids,
                manifest_key=self._manifest_key,
                data_key=self._data_key,
                offhost_key_custody_reference_sha256=self._custody_ref,
            )
            # Future implementation must supply an independently reviewed,
            # no-overwrite, off-host persistence/readback callback. This seam
            # cannot infer or assert remote durability from callback output.
            readback = self._commit(
                encrypted.sealed_bytes, encrypted.sealed_sha256,
                encrypted.run_id,
            )
            if (type(readback) is not bytes
                    or hashlib.sha256(readback).hexdigest()
                       != encrypted.sealed_sha256
                    or readback != encrypted.sealed_bytes):
                raise ReceiptHandoffRejected("encrypted manifest readback mismatch")
            opened = private.open_private_recovery_manifest(
                sealed=readback, manifest_key=self._manifest_key,
                expected_sha256=encrypted.sealed_sha256,
            )
            if (opened.aws_version_id != exact_version_ids[0]
                    or opened.b2_version_id != exact_version_ids[1]
                    or opened.object_sha256 != obj.envelope_sha256
                    or opened.run_id != obj.run_id):
                raise ReceiptHandoffRejected("independent private manifest open mismatch")
            # False means not proven independently durable and never a live
            # release claim, even if commit_and_readback is called "offhost".
            return private.public_receipt_summary(encrypted)
        except Exception:
            raise ReceiptHandoffRejected(
                "private encrypted exact-version receipt could not be verified"
            ) from None
