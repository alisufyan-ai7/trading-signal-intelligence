"""EXP050 P8: synthetic-only independent cold disaster recovery drill.

In-memory fake exact-version AWS/B2 stores and a fake encrypted escrow reader
only. No SDK/network/client construction, source SQLite capture or CLI.
The return NEVER claims actual off-host recovery, spending or release authority.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Callable

from . import live_sqlite_envelope_v0_1 as core
from . import live_dual_provider_transport_v0_1 as p2
from . import offline_immutable_receipt_escrow_v0_1 as p7

SYNTHETIC_RUN_ID = "release-test-0001"
SYNTHETIC_RECORD_COUNT = 3
FAULTS = frozenset({"none", "offline", "missing", "corrupt"})


class OfflineColdDrillRejected(RuntimeError):
    """Fixed sanitized rejection; no raw provider reference or exception."""


class SyntheticMemoryVersionReader:
    """Single-provider fake reader, cannot invoke real SDK or network operations."""

    def __init__(self, *, provider: str, object_key: str,
                 version_id: str, envelope: bytes, fault: str = "none") -> None:
        if (provider not in (p2.AWS.name, p2.B2.name)
                or type(provider) is not str
                or type(object_key) is not str or not p2.KEY_RX.fullmatch(object_key)
                or type(version_id) is not str or not version_id.startswith("fake-")
                or len(version_id) > 512
                or type(envelope) is not bytes
                or not 40 < len(envelope) <= core.MAX_ENVELOPE_BYTES
                or fault not in FAULTS):
            raise OfflineColdDrillRejected("synthetic reader configuration rejected")
        self._provider = provider
        self._object_key = object_key
        self._version = version_id
        self._envelope = envelope
        self._fault = fault
        self.read_calls = 0

    def __repr__(self) -> str:
        return "<SyntheticMemoryVersionReader private_objects=REDACTED>"

    def read_exact(self, *, provider: str, bucket: str, object_key: str,
                   version_id: str) -> bytes:
        self.read_calls += 1
        pin = p2.AWS if self._provider == p2.AWS.name else p2.B2
        if (provider != self._provider or bucket != pin.bucket
                or object_key != self._object_key or version_id != self._version):
            raise OfflineColdDrillRejected("exact synthetic version identity mismatch")
        if self._fault in ("offline", "missing"):
            raise OfflineColdDrillRejected("synthetic provider unavailable")
        if self._fault == "corrupt":
            return self._envelope[:-1] + bytes([self._envelope[-1] ^ 1])
        return self._envelope


def _read_and_restore(reader: SyntheticMemoryVersionReader, provider: Any,
                      targets: Any, version: str, data_key: bytes,
                      scratch: Path, restore_id: str) -> bool:
    """Any failure -> provider HOLD; never retry, print, or expose private values."""
    try:
        envelope = reader.read_exact(
            provider=provider.name, bucket=provider.bucket,
            object_key=targets.object_key, version_id=version,
        )
        if (type(envelope) is not bytes
                or len(envelope) > core.MAX_ENVELOPE_BYTES
                or hashlib.sha256(envelope).hexdigest() != targets.object_sha256):
            return False
        result = core.restore_verified_envelope(
            envelope=envelope, key=data_key,
            scratch_parent=scratch, restore_id=restore_id,
            expected_sha256=targets.object_sha256,
        )
        return (type(result) is dict
                and result.get("status") == "LIVE_S02_AUTHENTICATED_RESTORE_VERIFIED"
                and result.get("run_id") == targets.run_id
                and result.get("plaintext_sha256") == targets.plaintext_sha256
                and type(result.get("record_count")) is int
                and result.get("record_count") == targets.record_count)
    except Exception:
        return False


def run_synthetic_cold_disaster_drill(
    *, escrow_read_exact: Callable[[str], bytes],
    run_id: str, manifest_sha256: str,
    manifest_key: bytes, data_key: bytes,
    aws_reader: SyntheticMemoryVersionReader,
    b2_reader: SyntheticMemoryVersionReader,
    scratch_parent: Path,
) -> dict:
    """Cold-read authenticated private manifest, then both fake providers.

    Always 0 real cloud operations. If just one synthetic provider survives,
    recovery evidence is DEGRADED/HOLD and never silently called healthy.
    """
    if (run_id != SYNTHETIC_RUN_ID
            or type(manifest_key) is not bytes or len(manifest_key) != 32
            or type(data_key) is not bytes or len(data_key) != 32
            or data_key == manifest_key
            or type(aws_reader) is not SyntheticMemoryVersionReader
            or type(b2_reader) is not SyntheticMemoryVersionReader
            or aws_reader is b2_reader
            or aws_reader._provider != p2.AWS.name
            or b2_reader._provider != p2.B2.name):
        raise OfflineColdDrillRejected("synthetic-only cold drill preflight rejected")
    try:
        core._safe_directory(Path(scratch_parent))
        targets = p7.open_from_independent_escrow(
            read_exact=escrow_read_exact,
            run_id=run_id,
            manifest_sha256=manifest_sha256,
            manifest_key=manifest_key,
        )
        if (targets.run_id != SYNTHETIC_RUN_ID
                or targets.record_count != SYNTHETIC_RECORD_COUNT
                or not core.HEX64.fullmatch(targets.object_sha256)
                or not core.HEX64.fullmatch(targets.plaintext_sha256)):
            raise OfflineColdDrillRejected("not a synthetic fixture recovery target")
    except Exception:
        raise OfflineColdDrillRejected(
            "independent synthetic escrow preflight rejected"
        ) from None

    aws_pass = _read_and_restore(
        aws_reader, p2.AWS, targets, targets.aws_version_id, data_key,
        Path(scratch_parent), "p8-aws-restore-0001",
    )
    b2_pass = _read_and_restore(
        b2_reader, p2.B2, targets, targets.b2_version_id, data_key,
        Path(scratch_parent), "p8-b2-restore-0001",
    )
    if not aws_pass and not b2_pass:
        raise OfflineColdDrillRejected(
            "both synthetic recovery providers failed; no retry"
        )
    both = aws_pass and b2_pass
    return {
        "status": ("SYNTHETIC_DUAL_PROVIDER_RESTORED"
                   if both else "SYNTHETIC_ONE_PROVIDER_RESTORED_DEGRADED"),
        "aws_restore": "VERIFIED" if aws_pass else "HOLD",
        "b2_restore": "VERIFIED" if b2_pass else "HOLD",
        "verified_provider_count": int(aws_pass) + int(b2_pass),
        "verified_record_count": targets.record_count,
        "independent_escrow_used": True,
        "real_offhost_restore_proven": False,
        "live_provider_requests_authorized": False,
        "production_resume_authorized": False,
        "operator_action": ("NO_LIVE_ACTION" if both else "HOLD_AND_INVESTIGATE"),
    }
