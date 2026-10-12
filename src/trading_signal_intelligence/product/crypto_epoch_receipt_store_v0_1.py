"""Dormant, source-bound crypto epoch receipt spool — synthetic development.

NO key provisioning, scheduler hook, public POST, production integration, or
CLI. The caller must have independently verified a real producer's returned
public-only epoch; signing arbitrary untrusted bytes is NOT an attestation.
Do not use on VPS without a separately approved source reader and key custody.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
    _clock, _utc, publish_immutable_epoch, read_immutable_epoch,
)
from trading_signal_intelligence.product.crypto_epoch_bridge_v0_1 import (
    EpochBridgeHeld, signed_receipt, verify_receipt,
)

RECEIPT_NAME = re.compile(
    r"crypto-epoch-\d{8}T\d{6}Z-[a-f0-9]{64}\.json\.receipt\Z"
)
SHA256 = re.compile(r"[a-f0-9]{64}\Z")
MAX_RECEIPT = 1024


class ReceiptStoreHeld(EpochBridgeHeld):
    """Never select or publish a crypto epoch after an unsafe receipt read."""


def _root(directory: Path) -> Path:
    value = Path(directory)
    if value.is_symlink():
        raise ReceiptStoreHeld("receipt spool symlink refused")
    info = value.stat()
    if not stat.S_ISDIR(info.st_mode):
        raise ReceiptStoreHeld("receipt spool directory required")
    return value


def _read_once(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink():
        raise ReceiptStoreHeld("receipt path symlink refused")
    first = path.stat()
    if (not stat.S_ISREG(first.st_mode) or first.st_nlink != 1
        or first.st_size <= 0 or first.st_size > max_bytes):
        raise ReceiptStoreHeld("receipt file properties invalid")
    raw = path.read_bytes()
    second = path.stat()
    if (len(raw) != first.st_size or first.st_size != second.st_size
        or first.st_mtime_ns != second.st_mtime_ns):
        raise ReceiptStoreHeld("receipt file changed during read")
    return raw


def _write_exclusive(directory: Path, filename: str, raw: bytes) -> Path:
    """Atomic create-once receipt. Crash may leave an orphan epoch, never trust it."""
    target = directory / filename
    if target.is_symlink() or target.exists():
        raise ReceiptStoreHeld("immutable receipt already exists")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", prefix=".crypto-receipt-pending-",
            dir=directory, delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        # Atomic no-overwrite on NTFS, unlike os.replace which could erase an
        # independently accepted prior receipt.
        os.link(temporary, target)
        if _read_once(target, max_bytes=MAX_RECEIPT) != raw:
            raise ReceiptStoreHeld("immutable receipt readback mismatch")
    except FileExistsError:
        raise ReceiptStoreHeld("immutable receipt collision") from None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return target


def stage_authenticated_epoch(
    directory: Path, *, raw_epoch: bytes, signing_key: bytes,
    observation_utc: datetime,
) -> dict[str, str]:
    """Commit epoch then authenticated receipt, **without** any latest pointer.

    Source read-only attestation must happen BEFORE this function. The returned
    hashes are handoff candidates, NOT an independently trusted high-water mark.
    Key bytes never enter the files or return value.
    """
    root = _root(directory)
    if not isinstance(signing_key, bytes) or len(signing_key) < 32:
        raise ReceiptStoreHeld("independent receipt signing key required")
    receipt = signed_receipt(raw_epoch, key=signing_key)
    claims = verify_receipt(receipt, key=signing_key)
    from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
        public_program_from_completed_epoch,
    )
    public_program_from_completed_epoch(
        raw_epoch, expected_sha256=claims["epoch_sha256"],
        now=_clock(observation_utc),
    )
    if len(receipt) > MAX_RECEIPT:
        raise ReceiptStoreHeld("signed receipt exceeds size limit")
    epoch_path, epoch_sha = publish_immutable_epoch(root, raw_epoch)
    if epoch_sha != claims["epoch_sha256"] or epoch_path.name != claims["epoch_filename"]:
        raise ReceiptStoreHeld("epoch spool identity mismatch")
    receipt_path = _write_exclusive(root, epoch_path.name + ".receipt", receipt)
    return {
        "epoch_filename": epoch_path.name,
        "epoch_sha256": epoch_sha,
        "receipt_filename": receipt_path.name,
        "receipt_sha256": hashlib.sha256(receipt).hexdigest(),
        "cycle_close_utc": claims["cycle_close_utc"],
    }


def consume_trusted_epoch(
    directory: Path, *, receipt_filename: str,
    externally_pinned_receipt_sha256: str, verification_key: bytes,
    observation_utc: datetime,
    external_last_accepted_cycle_close_utc: str | None,
) -> dict[str, Any]:
    """Read only externally pinned, MAC-authenticated, strictly newer epoch.

    Receipt SHA and previous accepted cycle MUST come from a separately
    authenticated trust root; they cannot be selected from this directory.
    Does NOT update external high-water state or send HTTP.
    """
    root = _root(directory)
    if (not isinstance(receipt_filename, str)
        or RECEIPT_NAME.fullmatch(receipt_filename) is None
        or not isinstance(externally_pinned_receipt_sha256, str)
        or SHA256.fullmatch(externally_pinned_receipt_sha256) is None):
        raise ReceiptStoreHeld("externally trusted receipt pin required")
    if external_last_accepted_cycle_close_utc is not None:
        _utc(external_last_accepted_cycle_close_utc)
    raw_receipt = _read_once(root / receipt_filename, max_bytes=MAX_RECEIPT)
    if hashlib.sha256(raw_receipt).hexdigest() != externally_pinned_receipt_sha256:
        raise ReceiptStoreHeld("receipt pin mismatch")
    # The signer generates canonical JSON; reject duplicate-key / alternate
    # encodings even if a key-holding integration were to supply them.
    try:
        decoded = json.loads(raw_receipt)
        canonical = json.dumps(
            decoded, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise ReceiptStoreHeld("invalid receipt encoding") from None
    if raw_receipt != canonical:
        raise ReceiptStoreHeld("noncanonical receipt refused")
    claims = verify_receipt(raw_receipt, key=verification_key)
    if receipt_filename != claims["epoch_filename"] + ".receipt":
        raise ReceiptStoreHeld("receipt path and signed identity disagree")
    cycle = _utc(claims["cycle_close_utc"])
    if (external_last_accepted_cycle_close_utc is not None
        and cycle <= _utc(external_last_accepted_cycle_close_utc)):
        raise ReceiptStoreHeld("duplicate or regressing accepted epoch")
    return read_immutable_epoch(
        root / claims["epoch_filename"],
        expected_sha256=claims["epoch_sha256"],
        now=_clock(observation_utc),
        last_published_cycle_close_utc=external_last_accepted_cycle_close_utc,
    )
