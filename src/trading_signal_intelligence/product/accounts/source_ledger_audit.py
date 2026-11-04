"""Original AI-v1 / S02 SQLite hash-chain verification, strict READ-ONLY.

Never initializes or alters a source ledger. Requires a separately trusted,
owner-reviewed head hash AND exact count, not self-reported by the same file.
This proves consistency with a pinned chain, NOT costs/rights/full coverage
or independently verified historical trading performance.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any

from trading_signal_intelligence.ai_v1.ledger import (
    _record_hash, canonical_json,
)

_HASH = re.compile(r"^[0-9a-f]{64}$")
_PROFILES = {
    "ai_v1": "ai_records",
    "s02_forward": "forward_records",
}
_MAX_RECORDS = 2_000_000


class SourceLedgerAuditError(ValueError):
    pass


def audit_pinned_source(
    path: str | Path, *,
    profile: str,
    expected_head_sha256: str,
    expected_records: int,
) -> dict[str, Any]:
    """Audit source in a frozen SQLite read transaction; emit counts only.

    A copied snapshot should be used where the original ledger can advance
    during an audit. Never count unanchored new rows as verified history.
    """
    if (
        not isinstance(profile,str) or profile not in _PROFILES
        or not isinstance(expected_head_sha256, str)
        or not _HASH.fullmatch(expected_head_sha256)
        or type(expected_records) is not int
        or not 1 <= expected_records <= _MAX_RECORDS
    ):
        raise SourceLedgerAuditError("Explicit independent ledger head and count required")
    file = Path(path)
    if file.is_symlink() or not file.is_file():
        raise SourceLedgerAuditError("Source must be an existing non-symlink SQLite file")
    uri = file.resolve(strict=True).as_uri() + "?mode=ro"
    table = _PROFILES[profile]
    counts: dict[str, int] = {}
    previous = None
    sequence = 0
    digest = hashlib.sha256()
    try:
        with closing(sqlite3.connect(uri, uri=True, timeout=5)) as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only=ON")
            conn.execute("BEGIN")
            cursor = conn.execute(
                "SELECT sequence,record_id,record_type,entity_id,"
                "recorded_at_utc,effective_at_utc,payload_json,"
                "previous_hash,record_hash FROM " + table +
                " ORDER BY sequence ASC"
            )
            for row in cursor:
                sequence += 1
                if sequence > expected_records or int(row["sequence"]) != sequence:
                    raise SourceLedgerAuditError("Source sequence gap or population overflow")
                if row["previous_hash"] != previous:
                    raise SourceLedgerAuditError("Source previous-hash chain mismatch")
                if not isinstance(row["payload_json"], str):
                    raise SourceLedgerAuditError("Invalid source payload encoding")
                try:
                    payload = json.loads(
                        row["payload_json"],
                        object_pairs_hook=_unique_object,
                        parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
                    )
                    payload_text = canonical_json(payload)
                except (ValueError, TypeError) as exc:
                    raise SourceLedgerAuditError("Malformed source payload JSON") from exc
                if payload_text != row["payload_json"]:
                    raise SourceLedgerAuditError("Noncanonical source ledger payload")
                actual = _record_hash(
                    record_id=row["record_id"],record_type=row["record_type"],
                    entity_id=row["entity_id"],
                    recorded_at_utc=row["recorded_at_utc"],
                    effective_at_utc=row["effective_at_utc"],
                    payload_json=payload_text,previous_hash=previous,
                )
                if not _HASH.fullmatch(str(row["record_hash"])) or row["record_hash"] != actual:
                    raise SourceLedgerAuditError("Source record hash mismatch")
                kind = row["record_type"]
                if not isinstance(kind, str) or not kind or len(kind) > 64:
                    raise SourceLedgerAuditError("Invalid source record kind")
                counts[kind] = counts.get(kind, 0) + 1
                digest.update(str(sequence).encode("ascii"))
                digest.update(b":")
                digest.update(actual.encode("ascii"))
                digest.update(b"\n")
                previous = actual
            if sequence != expected_records or previous != expected_head_sha256:
                raise SourceLedgerAuditError("Source population/head does not match external pin")
    except sqlite3.Error as exc:
        # Never leak local path, raw payload or database error text.
        raise SourceLedgerAuditError("Read-only source database audit unavailable") from exc
    return {
        "status": "PINNED_CHAIN_VERIFIED",
        "profile": profile,
        "records": sequence,
        "head_sha256": previous,
        "sequence_chain_sha256": digest.hexdigest(),
        "record_type_counts": dict(sorted(counts.items())),
        "source_rows_exported": False,
        "independent_original_source_pin_required": True,
        "source_costs_verified": False,
        "source_rights_verified": False,
        "complete_historical_performance_verified": False,
    }


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result
