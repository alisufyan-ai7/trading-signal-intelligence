"""Offline prototype: immutable, aggregate-only AI-v1.3 completed-cycle handoff.

NOT connected to the running K5 task, publisher, cloud API or scheduler.
A future authorized post-K5 producer must establish terminal ledger proofs
from the verified private source; callers must not fabricate them. A consumer
only accepts exact externally-pinned bytes, never mutable live SQLite reads.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
    AsOfSealRejected,
    _check_original_program,
    _reject_json_constant,
    _strict_json_pairs,
)

MARKETS = frozenset(("BTCUSDT", "ETHUSDT", "SOLUSDT"))
TERMINAL_TYPES = frozenset(("SIGNAL", "NO_TRADE", "REJECTED_INFERENCE"))
HEX64 = re.compile(r"[a-f0-9]{64}\Z")
MAX_BYTES = 65536
MAX_CAPTURE_LAG_SECONDS = 20 * 60
MAX_CURRENT_AGE_SECONDS = 90 * 60
ENVELOPE_FIELDS = frozenset((
    "schema_version", "cycle_close_utc", "captured_at_utc",
    "cohort_commitment_sha256", "crypto_program",
))


class CompletedEpochRejected(ValueError):
    """Fail closed to the existing historic DELAYED/absent crypto path."""


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise CompletedEpochRejected("missing UTC time")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise CompletedEpochRejected("invalid UTC time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise CompletedEpochRejected("naive time forbidden")
    return dt.astimezone(timezone.utc)


def _canonical(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"),
                      allow_nan=False, ensure_ascii=False).encode("utf-8")


def _clock(now: datetime) -> datetime:
    if not isinstance(now, datetime) or now.tzinfo is None or now.utcoffset() is None:
        raise CompletedEpochRejected("verified aware observation clock required")
    return now.astimezone(timezone.utc)


def _validate_times(cycle: datetime, captured: datetime) -> None:
    if cycle.minute != 0 or cycle.second != 0 or cycle.microsecond != 0:
        raise CompletedEpochRejected("completed H1 close must be an exact UTC hour")
    lag = (captured - cycle).total_seconds()
    if not 0 <= lag <= MAX_CAPTURE_LAG_SECONDS:
        raise CompletedEpochRejected("completed-cycle capture timing invalid")


def _validate_program(program: Any) -> None:
    try:
        _check_original_program(program)
    except (AsOfSealRejected, TypeError, KeyError) as exc:
        raise CompletedEpochRejected("unsafe public crypto aggregate") from exc


def create_completed_epoch_bytes(
    *, crypto_program: dict[str, Any], cycle_close_utc: str,
    captured_at_utc: str, terminal_proofs: dict[str, dict[str, Any]],
) -> bytes:
    """Create an unpublished handoff only from externally verified K5 evidence.

    terminal_proofs is PRIVATE input. Neither ledger hashes nor original private
    records/paths are serialized; only their SHA-256 commitment is exported.
    This pure API cannot itself attest source authenticity or finished K5 state.
    """
    _validate_program(crypto_program)
    cycle, captured = _utc(cycle_close_utc), _utc(captured_at_utc)
    _validate_times(cycle, captured)
    if not isinstance(terminal_proofs, dict) or set(terminal_proofs) != MARKETS:
        raise CompletedEpochRejected("all three terminal proofs required")
    evidence: list[dict[str, str]] = []
    for symbol in sorted(MARKETS):
        proof = terminal_proofs[symbol]
        if not isinstance(proof, dict) or set(proof) != {
            "source_bar_close_utc", "terminal_record_type", "ledger_head_sha256"
        }:
            raise CompletedEpochRejected("terminal proof shape invalid")
        if _utc(proof["source_bar_close_utc"]) != cycle:
            raise CompletedEpochRejected("market cycles not identical")
        if proof["terminal_record_type"] not in TERMINAL_TYPES:
            raise CompletedEpochRejected("unfinished or failed market cycle")
        head = proof["ledger_head_sha256"]
        if not isinstance(head, str) or not HEX64.fullmatch(head):
            raise CompletedEpochRejected("invalid ledger-head commitment")
        evidence.append({"market": symbol, "cycle": cycle.isoformat(),
                         "terminal_record_type": proof["terminal_record_type"],
                         "ledger_head_sha256": head})
    body = {
        "schema_version": 1,
        "cycle_close_utc": cycle.isoformat(),
        "captured_at_utc": captured.isoformat(),
        "cohort_commitment_sha256": hashlib.sha256(_canonical(evidence)).hexdigest(),
        "crypto_program": copy.deepcopy(crypto_program),
    }
    raw = _canonical(body)
    if not 0 < len(raw) <= MAX_BYTES:
        raise CompletedEpochRejected("completed epoch too large")
    return raw


def public_program_from_completed_epoch(
    raw: bytes, *, expected_sha256: str, now: datetime,
    last_published_cycle_close_utc: str | None = None,
) -> dict[str, Any]:
    """Read only complete externally SHA-pinned epochs; NEVER query crypto DBs.

    If current epoch is unavailable, malformed, stale or regresses, caller
    must continue fresh core/expansion and retain DELAYED historic crypto.
    """
    if (not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_BYTES
        or not isinstance(expected_sha256, str)
        or not HEX64.fullmatch(expected_sha256)
        or hashlib.sha256(raw).hexdigest() != expected_sha256):
        raise CompletedEpochRejected("untrusted completed-cycle bytes")
    try:
        body = json.loads(raw, object_pairs_hook=_strict_json_pairs,
                          parse_constant=_reject_json_constant)
    except (UnicodeError, ValueError, TypeError) as exc:
        raise CompletedEpochRejected("malformed completed-cycle JSON") from exc
    if (not isinstance(body, dict) or set(body) != ENVELOPE_FIELDS
        or type(body["schema_version"]) is not int or body["schema_version"] != 1):
        raise CompletedEpochRejected("unsupported completed-cycle schema")
    cycle, captured = _utc(body["cycle_close_utc"]), _utc(body["captured_at_utc"])
    _validate_times(cycle, captured)
    age = (_clock(now) - captured).total_seconds()
    if not 0 <= age < MAX_CURRENT_AGE_SECONDS:
        raise CompletedEpochRejected("not a current crypto evidence epoch")
    if last_published_cycle_close_utc is not None:
        if cycle < _utc(last_published_cycle_close_utc):
            raise CompletedEpochRejected("crypto epoch regression")
    digest = body["cohort_commitment_sha256"]
    if not isinstance(digest, str) or not HEX64.fullmatch(digest):
        raise CompletedEpochRejected("missing cohort commitment")
    _validate_program(body["crypto_program"])
    return copy.deepcopy(body["crypto_program"])


def publish_immutable_epoch(directory: Path, raw: bytes) -> tuple[Path, str]:
    """Offline atomic spool prototype; no overwrites, no implicit directories.

    Requires an explicit existing private directory. Producer safety, live
    permissions, completed task verification and publisher integration are NOT
    established by this low-level file operation.
    """
    root = Path(directory)
    if root.is_symlink():
        raise CompletedEpochRejected("epoch spool symlink forbidden")
    root_stat = root.stat()
    if not stat.S_ISDIR(root_stat.st_mode):
        raise CompletedEpochRejected("epoch spool must be a directory")
    digest = hashlib.sha256(raw).hexdigest()
    # Parse through the same strict consumer before committing the source bytes.
    # Use the recorded capture as its reference clock for schema verification.
    try:
        obj = json.loads(raw, object_pairs_hook=_strict_json_pairs,
                         parse_constant=_reject_json_constant)
        capture = _utc(obj["captured_at_utc"])
        public_program_from_completed_epoch(raw, expected_sha256=digest, now=capture)
        cycle = _utc(obj["cycle_close_utc"])
    except (UnicodeError, ValueError, TypeError, KeyError) as exc:
        raise CompletedEpochRejected("unsafe epoch candidate") from exc
    filename = f"crypto-epoch-{cycle.strftime('%Y%m%dT%H0000Z')}-{digest}.json"
    target = root / filename
    pending_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".crypto-epoch-pending-",
                                         dir=root, delete=False) as handle:
            pending_path = Path(handle.name)
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
        # Hard-link publication is atomic and refuses an existing filename.
        os.link(pending_path, target)
        if target.read_bytes() != raw:
            raise CompletedEpochRejected("spooled epoch changed")
    except FileExistsError as exc:
        raise CompletedEpochRejected("immutable epoch already exists") from exc
    finally:
        if pending_path is not None:
            pending_path.unlink(missing_ok=True)
    return target, digest


def read_immutable_epoch(path: Path, *, expected_sha256: str, now: datetime,
                         last_published_cycle_close_utc: str | None = None) -> dict[str, Any]:
    path = Path(path)
    if path.is_symlink():
        raise CompletedEpochRejected("epoch symlink forbidden")
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or not 0 < info.st_size <= MAX_BYTES:
        raise CompletedEpochRejected("unsafe epoch file")
    raw = path.read_bytes()
    if len(raw) != info.st_size or path.stat().st_size != len(raw):
        raise CompletedEpochRejected("epoch changed during read")
    program = public_program_from_completed_epoch(
        raw, expected_sha256=expected_sha256, now=now,
        last_published_cycle_close_utc=last_published_cycle_close_utc,
    )
    if path.read_bytes() != raw:
        raise CompletedEpochRejected("epoch bytes changed during verification")
    return program
