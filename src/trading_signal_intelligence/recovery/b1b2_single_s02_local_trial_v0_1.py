"""B1/B2 single-S02 local-copy prototype: implementation PREPARATION ONLY.

No CLI, scheduler, runtime import or production entrypoint. No real VPS source
may be opened by this module without a separate explicit owner authorization.
Develop/test with disposable, locally created SQLite fixtures only.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

MAX_TRIAL_BYTES = 10 * 1024 * 1024
MAX_DURATION_SECONDS = 30
TRIAL_ID_RE = re.compile(r"^[a-z][a-z0-9-]{3,39}$")
_SOURCE_RELATIVE = Path("data/forward.sqlite")
_COLUMNS = (
    "sequence", "record_id", "record_type", "entity_id", "recorded_at_utc",
    "effective_at_utc", "payload_json", "previous_hash", "record_hash",
)
_REQUIRED_TRIGGERS = {"forward_records_no_update", "forward_records_no_delete"}


class TrialRejected(RuntimeError):
    """No complete, verified single-ledger local copy can be attested."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    ).encode("utf-8")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise TrialRejected("file missing or symlinked")
    info = path.stat()
    if info.st_size == 0 or info.st_nlink != 1:
        raise TrialRejected("empty or hard-linked file")
    if getattr(info, "st_file_attributes", 0) & 0x400:
        raise TrialRejected("reparse-point file forbidden")


def _safe_dir(path: Path) -> None:
    if not path.is_dir() or path.is_symlink():
        raise TrialRejected("unsafe directory")
    if getattr(path.stat(), "st_file_attributes", 0) & 0x400:
        raise TrialRejected("reparse-point directory forbidden")


def _journal_path_safe(path: Path) -> None:
    if os.name == "nt" and len(str(path) + "-journal") >= 240:
        raise TrialRejected("Windows SQLite journal filename too long")


def _utc(value: object) -> str:
    if not isinstance(value, str):
        raise TrialRejected("non-text record timestamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TrialRejected("invalid record timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise TrialRejected("naive record timestamp")
    return stamp.astimezone(timezone.utc).isoformat()


def verify_sealed_s02_copy(copy_path: Path) -> dict[str, Any]:
    """Read-only, non-initializing SELECT verifier; never use ForwardLedger()."""
    copy_path = Path(copy_path)
    _safe_file(copy_path)
    _journal_path_safe(copy_path)
    before = _sha256(copy_path)
    connection = sqlite3.connect(copy_path.resolve().as_uri() + "?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        connection.execute("PRAGMA query_only=ON")
        result = [r[0] for r in connection.execute("PRAGMA integrity_check")]
        if result != ["ok"]:
            raise TrialRejected("sealed copy integrity_check not ok")
        triggers = {
            str(r[0]) for r in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'"
            )
        }
        if not _REQUIRED_TRIGGERS.issubset(triggers):
            raise TrialRejected("sealed copy missing append-only triggers")
        cols = [
            str(r[1]) for r in connection.execute("PRAGMA table_info(forward_records)")
        ]
        if not all(c in cols for c in _COLUMNS):
            raise TrialRejected("sealed copy missing S02 ledger columns")
        rows = connection.execute(
            "SELECT " + ", ".join(_COLUMNS) +
            " FROM forward_records ORDER BY sequence ASC"
        ).fetchall()
        if not rows:
            raise TrialRejected("sealed copy has no S02 records")
        prev = None
        counts: dict[str, int] = {}
        first = None
        last = None
        for seq, row in enumerate(rows, 1):
            if row["sequence"] != seq or row["previous_hash"] != prev:
                raise TrialRejected("S02 sequence/previous-hash mismatch")
            try:
                parsed = json.loads(row["payload_json"])
                if not isinstance(parsed, dict):
                    raise ValueError("non-object S02 payload")
                canonical_payload = _canonical(parsed).decode("utf-8")
            except (TypeError, ValueError) as exc:
                raise TrialRejected("invalid S02 record payload") from exc
            material = {
                "record_id": row["record_id"],
                "record_type": row["record_type"],
                "entity_id": row["entity_id"],
                "recorded_at_utc": row["recorded_at_utc"],
                "effective_at_utc": row["effective_at_utc"],
                "payload_json": canonical_payload,
                "previous_hash": prev,
            }
            expected = hashlib.sha256(_canonical(material)).hexdigest()
            if row["record_hash"] != expected:
                raise TrialRejected("S02 canonical record hash mismatch")
            recorded = _utc(row["recorded_at_utc"])
            _utc(row["effective_at_utc"])
            first = min(first, recorded) if first else recorded
            last = max(last, recorded) if last else recorded
            kind = str(row["record_type"])
            counts[kind] = counts.get(kind, 0) + 1
            prev = expected
        report: dict[str, Any] = {
            "integrity_check": "ok",
            "s02_chain_valid": True,
            "record_count": len(rows),
            "counts_by_type": dict(sorted(counts.items())),
            "head_hash": prev,
            "recorded_utc_first": first,
            "recorded_utc_last": last,
            "copy_size_bytes": copy_path.stat().st_size,
            "copy_sha256": before,
        }
    except sqlite3.DatabaseError as exc:
        raise TrialRejected("sealed copy SQLite read/validation failed") from exc
    finally:
        connection.close()
    if _sha256(copy_path) != before:
        raise TrialRejected("sealed copy changed during verification")
    return report


def _preflight(
    repo_root: Path, output_parent: Path, trial_id: str,
) -> tuple[Path, Path]:
    _safe_dir(repo_root)
    if repo_root.name.lower().startswith("vowsig-b1b2-"):
        raise TrialRejected("repository root confused with trial output")
    _safe_dir(repo_root / "data")
    _safe_dir(output_parent)
    if not output_parent.name.startswith("vowsig-b1b2-"):
        raise TrialRejected("trial output must be in separately named scratch")
    if output_parent.resolve().is_relative_to(repo_root.resolve()):
        raise TrialRejected("trial output must be outside the repository")
    if not TRIAL_ID_RE.fullmatch(trial_id):
        raise TrialRejected("invalid immutable trial ID")
    source = repo_root / _SOURCE_RELATIVE
    _safe_file(source)
    _journal_path_safe(source)
    for suffix in ("-wal", "-shm", "-journal"):
        if Path(str(source) + suffix).exists():
            raise TrialRejected("source SQLite sidecar present; refuse WAL/writers")
    if source.stat().st_size > MAX_TRIAL_BYTES:
        raise TrialRejected("source exceeds single-ledger 10 MiB trial budget")
    # Read only the source SQLite header to reject WAL before sqlite3 opens it.
    with source.open("rb") as stream:
        header = stream.read(100)
    if len(header) != 100 or header[:16] != b"SQLite format 3\x00":
        raise TrialRejected("invalid SQLite file header")
    if header[18:20] != b"\x01\x01":
        raise TrialRejected("WAL or unsupported SQLite journal format")
    target = output_parent / trial_id
    if target.exists() or target.is_symlink():
        raise TrialRejected("no-overwrite trial directory already exists")
    _journal_path_safe(target / "forward.sqlite")
    return source, target


def capture_single_s02_trial(
    *,
    repo_root: Path,
    output_parent: Path,
    trial_id: str,
    source_revision: str,
    real_source_access_explicitly_approved: bool = False,
) -> dict[str, Any]:
    """Owner-gated local prototype; tests may approve ONLY synthetic fixtures.

    The boolean is a secondary fail-closed guard, not evidence of owner consent.
    Never invoke with a real VPS DB until separately approved for one file.
    """
    if not real_source_access_explicitly_approved:
        raise TrialRejected("owner authorization for SQLite access not supplied")
    if not re.fullmatch(r"[0-9a-f]{40}", source_revision):
        raise TrialRejected("missing exact pinned source Git revision")
    repo_root, output_parent = Path(repo_root), Path(output_parent)
    source, target = _preflight(repo_root, output_parent, trial_id)
    before_size = source.stat().st_size
    started = _utc_now()
    deadline = time.monotonic() + MAX_DURATION_SECONDS
    # No source changes or real backup execution in the preparation phase.
    target.mkdir(exist_ok=False)
    copied = target / "forward.sqlite"

    source_connection = None
    destination_connection = None
    try:
        source_connection = sqlite3.connect(
            source.resolve().as_uri() + "?mode=ro", uri=True, timeout=1.0
        )
        source_connection.execute("PRAGMA query_only=ON")
        destination_connection = sqlite3.connect(copied, timeout=1.0)
        page_size = int(source_connection.execute("PRAGMA page_size").fetchone()[0])

        def bounded_progress(_status: int, _remaining: int, total: int) -> None:
            if time.monotonic() >= deadline:
                raise TrialRejected("single S02 trial time budget exceeded")
            if total * page_size > MAX_TRIAL_BYTES:
                raise TrialRejected("single S02 trial page budget exceeded")

        source_connection.backup(
            destination_connection, pages=16, progress=bounded_progress, sleep=0.05
        )
        destination_connection.commit()
    except (OSError, sqlite3.DatabaseError) as exc:
        raise TrialRejected("single S02 online copy failed; partial held") from exc
    finally:
        if destination_connection is not None:
            destination_connection.close()
        if source_connection is not None:
            source_connection.close()

    if copied.stat().st_size > MAX_TRIAL_BYTES:
        raise TrialRejected("captured S02 copy exceeds 10 MiB")
    ended = _utc_now()
    verification = verify_sealed_s02_copy(copied)
    manifest: dict[str, Any] = {
        "schema": "vowsig-single-s02-local-trial-v0.1",
        "classification": "PRIVATE_LOCAL_EXPERIMENTAL_COPY_ONLY",
        "trial_id": trial_id,
        "source_relative_path": "data/forward.sqlite",
        "source_git_revision": source_revision,
        "source_size_bytes_pre": before_size,
        "source_size_bytes_post": source.stat().st_size,
        "capture_started_utc": started,
        "capture_ended_utc": ended,
        "verified_utc": _utc_now(),
        "cross_database_atomic": False,
        "offsite_copy_verified": False,
        "independent_restore_verified": False,
        "publisher_cutover_authorized": False,
        **verification,
    }
    manifest["manifest_sha256"] = hashlib.sha256(_canonical(manifest)).hexdigest()
    with (target / "local-trial-manifest.json").open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest
