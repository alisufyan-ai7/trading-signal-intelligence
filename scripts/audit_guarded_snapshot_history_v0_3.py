"""Offline/read-only audit of prospective guarded publisher local snapshot evidence.

Verifies SHA-addressed archived candidate files and independently written
'accepted' receipts. It NEVER writes, prunes, restores, uploads, or queries
private ledgers. A local receipt is evidence of client-reported HTTP acceptance,
NOT independent proof of hosted durability or external backup.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HISTORY_NAME = "guarded-snapshot-history-v0.2"
ARCHIVE_RE = re.compile(r"^snapshot-(\d{8}T\d{6}Z)-([0-9a-f]{64})\.json$")
RECEIPT_SUFFIX = ".accepted"
MAX_SINGLE_SNAPSHOT_BYTES = 8 * 1024 * 1024
MAX_ARCHIVES_PER_AUDIT = 100_000


class HistoryAuditRejected(RuntimeError):
    pass


def _aware(ts: Any) -> datetime:
    if not isinstance(ts, str):
        raise HistoryAuditRejected("missing UTC timestamp")
    try:
        result = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HistoryAuditRejected("invalid UTC timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise HistoryAuditRejected("unqualified timestamp")
    return result.astimezone(timezone.utc)


def _read_regular(path: Path, *, max_bytes: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise HistoryAuditRejected("missing or unsafe archived object")
    try:
        size = path.stat().st_size
        if size <= 0 or size > max_bytes:
            raise HistoryAuditRejected("oversized or empty archived object")
        raw = path.read_bytes()
    except OSError as exc:
        raise HistoryAuditRejected("cannot read archived object") from exc
    if len(raw) != size:
        raise HistoryAuditRejected("archive changed during audit")
    return raw


def audit_local_history(root: Path) -> dict[str, Any]:
    """Read-only summary; fail closed on malformed, modified or orphan evidence."""
    folder = root / "data" / HISTORY_NAME
    if not folder.exists():
        return {
            "status": "NO_LOCAL_HISTORY",
            "accepted_snapshots": 0,
            "pending_candidates": 0,
            "local_archived_bytes": 0,
            "external_backup_verified": False,
            "hosted_snapshot_durability_verified": False,
        }
    if folder.is_symlink() or not folder.is_dir():
        raise HistoryAuditRejected("archive root is not a local directory")
    try:
        all_entries = list(folder.iterdir())
    except OSError as exc:
        raise HistoryAuditRejected("cannot list archive directory") from exc
    if len(all_entries) > MAX_ARCHIVES_PER_AUDIT * 2:
        raise HistoryAuditRejected("history inventory exceeds bounded audit")
    names = {p.name for p in all_entries}
    archives: dict[str, tuple[Path, re.Match[str]]] = {}
    receipts: dict[str, Path] = {}
    for item in all_entries:
        if item.is_symlink() or not item.is_file():
            raise HistoryAuditRejected("non-regular archive directory entry")
        if item.name.endswith(RECEIPT_SUFFIX):
            base = item.name[:-len(RECEIPT_SUFFIX)]
            if not ARCHIVE_RE.fullmatch(base):
                raise HistoryAuditRejected("invalid acceptance receipt filename")
            receipts[base] = item
        else:
            match = ARCHIVE_RE.fullmatch(item.name)
            if not match:
                raise HistoryAuditRejected("unknown archive directory entry")
            archives[item.name] = (item, match)
    if not set(receipts).issubset(archives):
        raise HistoryAuditRejected("accepted receipt without immutable snapshot")
    accepted = 0
    bytes_total = 0
    timestamps = []
    for name in sorted(archives):
        path, match = archives[name]
        raw = _read_regular(path, max_bytes=MAX_SINGLE_SNAPSHOT_BYTES)
        bytes_total += len(raw)
        if hashlib.sha256(raw).hexdigest() != match.group(2):
            raise HistoryAuditRejected("SHA-addressed archived candidate has changed")
        try:
            payload = json.loads(raw)
        except ValueError as exc:
            raise HistoryAuditRejected("archived JSON is invalid") from exc
        if (not isinstance(payload, dict)
            or payload.get("schema_version") != 1
            or payload.get("raw_market_data_included") is not False
            or not isinstance(payload.get("validation_programs"), list)
            or not isinstance(payload.get("markets"), list)):
            raise HistoryAuditRejected("archived public snapshot contract incomplete")
        created = _aware(payload.get("generated_at_utc"))
        if created.strftime("%Y%m%dT%H%M%SZ") != match.group(1):
            raise HistoryAuditRejected("archived timestamp mismatch")
        if name in receipts:
            evidence = _read_regular(receipts[name], max_bytes=4096)
            try:
                receipt = json.loads(evidence)
            except ValueError as exc:
                raise HistoryAuditRejected("accepted receipt JSON invalid") from exc
            if (not isinstance(receipt, dict)
                or set(receipt) != {"schema", "snapshot_sha256", "accepted_at_utc"}
                or receipt.get("schema") != 1
                or receipt.get("snapshot_sha256") != match.group(2)
                or _aware(receipt.get("accepted_at_utc")) < created):
                raise HistoryAuditRejected("archived acceptance receipt invalid")
            accepted += 1
            timestamps.append(created.isoformat())
    disk = shutil.disk_usage(folder)
    return {
        "status": "LOCAL_HASHES_PASS",
        "accepted_snapshots": accepted,
        "pending_candidates": len(archives) - accepted,
        "local_archived_bytes": bytes_total,
        "oldest_accepted_generated_at_utc": min(timestamps) if timestamps else None,
        "newest_accepted_generated_at_utc": max(timestamps) if timestamps else None,
        "free_disk_bytes_observed": disk.free,
        # This file-based inspection cannot verify offsite copies or cloud.
        "external_backup_verified": False,
        "hosted_snapshot_durability_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    args = ap.parse_args()
    try:
        summary = audit_local_history(args.root)
    except HistoryAuditRejected as exc:
        print("LOCAL_HISTORY_AUDIT=STOP_FOR_REVIEW")
        print("FAILURE_CLASS=" + type(exc).__name__)
        print("FAILURE_DETAIL=" + str(exc))
        return 2
    print("LOCAL_HISTORY_AUDIT=" + summary["status"])
    for k, v in summary.items():
        if k != "status":
            print(k.upper() + "=" + str(v))
    print("FILES_WRITTEN=NONE")
    print("LEDGERS_READ=NONE")
    print("NETWORK_REQUESTS=NONE")
    print("RESTORE_ATTEMPTED=NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
