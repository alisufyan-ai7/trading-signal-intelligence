"""Synthetic-only B1/B2 SQLite consistency and immutable-copy verification prototype.

No CLI or production-entry point. Callers must pass a disposable fixture root
with a synthetic-only marker and each source must have a synthetic marker table.
Never apply this prototype to live or licensed datasets, production backups,
real VPS evidence, scheduler state, remote storage, or recovery operations.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

FIXTURE_MARKER = "VOWSIG_B1B2_SYNTHETIC_V0_1\n"
FIXTURE_FILE = ".vowsig-synthetic-only"
SYNTHETIC_TABLE = "vowsig_synthetic_fixture_only"
ALLOWED_KINDS = {"AI": "ai_records", "S02": "forward_records"}
AI_TYPES = {
    "ACTIVATION", "INFERENCE", "NO_TRADE", "REJECTED_INFERENCE", "SIGNAL",
    "PARTIAL_EXIT", "EXIT", "MISSED_INFERENCE", "ERROR",
}
NAME_RE = re.compile(r"^[a-z][a-z0-9_-]{0,39}$")
FILE_RE = re.compile(r"^[a-z][a-z0-9_-]{0,60}\.sqlite$")
RECORD_FIELDS = (
    "sequence", "record_id", "record_type", "entity_id", "recorded_at_utc",
    "effective_at_utc", "payload_json", "previous_hash", "record_hash",
)


class SyntheticGateRejected(RuntimeError):
    """Fail-closed prototype denial, not a production verification result."""


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False, default=str,
    ).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def _on_windows() -> bool:
    return os.name == "nt"


def _assert_windows_sqlite_path(path: Path) -> None:
    """Fail before SQLite tries to create an overlong journal sidecar on Windows."""
    if _on_windows() and len(str(path) + "-journal") >= 240:
        raise SyntheticGateRejected("synthetic SQLite journal path too long for Windows")


def _safe_regular(path: Path) -> None:
    if path.is_symlink() or not path.is_file():
        raise SyntheticGateRejected("unsafe or missing fixture file")
    info = path.stat()
    if info.st_nlink != 1 or getattr(info, "st_file_attributes", 0) & 0x400:
        raise SyntheticGateRejected("linked/reparse fixture is forbidden")
    if info.st_size == 0:
        raise SyntheticGateRejected("empty fixture file")


def assert_fixture_scope(root: Path) -> Path:
    if root.is_symlink() or not root.is_dir() or not root.name.startswith("vowsig-b1b2-fixture-"):
        raise SyntheticGateRejected("only disposable synthetic fixture roots are allowed")
    marker = root / FIXTURE_FILE
    _safe_regular(marker)
    if marker.read_text(encoding="utf-8") != FIXTURE_MARKER:
        raise SyntheticGateRejected("invalid synthetic-only marker")
    return root.resolve(strict=True)


def _fixture_path(root: Path, name: str) -> Path:
    if not FILE_RE.fullmatch(name):
        raise SyntheticGateRejected("invalid flat synthetic filename")
    path = root / name
    _assert_windows_sqlite_path(path)
    if path.parent.resolve(strict=True) != root:
        raise SyntheticGateRejected("fixture traversal blocked")
    _safe_regular(path)
    return path


def _readonly(path: Path) -> sqlite3.Connection:
    _safe_regular(path)
    # No immutable=1: an open synthetic WAL writer must still be considered.
    con = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1.0)
    con.row_factory = sqlite3.Row
    con.enable_load_extension(False)
    con.execute("PRAGMA query_only=ON")
    return con


def _assert_marker(con: sqlite3.Connection) -> None:
    try:
        row = con.execute("SELECT synthetic_token FROM vowsig_synthetic_fixture_only").fetchone()
    except sqlite3.DatabaseError as exc:
        raise SyntheticGateRejected("database has no synthetic-only marker") from exc
    if row is None or row[0] != FIXTURE_MARKER.strip():
        raise SyntheticGateRejected("not a designated synthetic SQLite fixture")


def _utc_timestamp(value: object) -> str:
    if not isinstance(value, str):
        raise SyntheticGateRejected("record time missing")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise SyntheticGateRejected("invalid record time") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise SyntheticGateRejected("naive record timestamp")
    return dt.astimezone(timezone.utc).isoformat()


def verify_synthetic_copy(copy_path: Path, kind: str, *, anchor_hash: str | None = None) -> dict:
    """SELECT-only verification of a sealed synthetic backup file; no schema init."""
    if kind not in ALLOWED_KINDS:
        raise SyntheticGateRejected("unsupported ledger type")
    _safe_regular(copy_path)
    before = sha256_file(copy_path)
    con = _readonly(copy_path)
    try:
        _assert_marker(con)
        integrity = [row[0] for row in con.execute("PRAGMA integrity_check")]
        if integrity != ["ok"]:
            raise SyntheticGateRejected("synthetic copy SQLite integrity check failed")
        table = ALLOWED_KINDS[kind]
        # Table identifier comes exclusively from hardcoded ALLOWED_KINDS, not user input.
        rows = con.execute(
            f"SELECT {', '.join(RECORD_FIELDS)} FROM {table} ORDER BY sequence"
        ).fetchall()
        if not rows:
            raise SyntheticGateRejected("fixture has no activation records")
        expected_previous = None
        anchor_seen = anchor_hash is None
        by_type: dict[str, int] = {}
        first_time = None
        last_time = None
        for seq, row in enumerate(rows, start=1):
            if row["sequence"] != seq or row["previous_hash"] != expected_previous:
                raise SyntheticGateRejected("ledger sequence or previous hash invalid")
            if kind == "AI" and row["record_type"] not in AI_TYPES:
                raise SyntheticGateRejected("unknown AI ledger record type")
            try:
                payload = json.loads(row["payload_json"])
                normalized = canonical_bytes(payload).decode("utf-8")
            except (ValueError, TypeError) as exc:
                raise SyntheticGateRejected("malformed synthetic payload") from exc
            material = {
                "record_id": row["record_id"],
                "record_type": row["record_type"],
                "entity_id": row["entity_id"],
                "recorded_at_utc": row["recorded_at_utc"],
                "effective_at_utc": row["effective_at_utc"],
                "payload_json": normalized,
                "previous_hash": expected_previous,
            }
            computed = hashlib.sha256(canonical_bytes(material)).hexdigest()
            if computed != row["record_hash"]:
                raise SyntheticGateRejected("synthetic ledger chain hash invalid")
            ts = _utc_timestamp(row["recorded_at_utc"])
            _utc_timestamp(row["effective_at_utc"])
            first_time = ts if first_time is None else min(first_time, ts)
            last_time = ts if last_time is None else max(last_time, ts)
            by_type[row["record_type"]] = by_type.get(row["record_type"], 0) + 1
            expected_previous = computed
            anchor_seen = anchor_seen or computed == anchor_hash
        if not anchor_seen:
            raise SyntheticGateRejected("synthetic anchor not found in chain")
        result = {
            "copy_sha256": before,
            "copy_size_bytes": copy_path.stat().st_size,
            "integrity_check": "ok",
            "ledger_chain_valid": True,
            "records": len(rows),
            "record_counts_by_type": dict(sorted(by_type.items())),
            "head_hash": expected_previous,
            "anchor_relation": "not_requested" if anchor_hash is None else "chain_member",
            "recorded_at_utc_min": first_time,
            "recorded_at_utc_max": last_time,
        }
    except sqlite3.DatabaseError as exc:
        raise SyntheticGateRejected("malformed or unsupported synthetic SQLite schema") from exc
    finally:
        con.close()
    if sha256_file(copy_path) != before:
        raise SyntheticGateRejected("sealed synthetic copy changed during verification")
    return result


@dataclass(frozen=True)
class SyntheticSpec:
    object_id: str
    filename: str
    kind: str
    rights: str = "SYNTHETIC_ALLOWED"
    anchor_hash: str | None = None


def validate_specs(root: Path, specs: list[SyntheticSpec]) -> list[tuple[SyntheticSpec, Path]]:
    base = assert_fixture_scope(root)
    if not specs or len(specs) > 32:
        raise SyntheticGateRejected("synthetic cohort must have 1..32 objects")
    seen_ids: set[str] = set()
    seen_paths: set[str] = set()
    result = []
    for spec in specs:
        if not NAME_RE.fullmatch(spec.object_id) or spec.kind not in ALLOWED_KINDS:
            raise SyntheticGateRejected("invalid synthetic spec identity or kind")
        if spec.rights != "SYNTHETIC_ALLOWED":
            raise SyntheticGateRejected("rights HOLD; cannot capture")
        if spec.object_id.casefold() in seen_ids or spec.filename.casefold() in seen_paths:
            raise SyntheticGateRejected("duplicate synthetic object ID or filename")
        seen_ids.add(spec.object_id.casefold())
        seen_paths.add(spec.filename.casefold())
        path = _fixture_path(base, spec.filename)
        # Fail before destination allocation if fixture attestation is missing.
        try:
            source = _readonly(path)
            try:
                _assert_marker(source)
            finally:
                source.close()
        except sqlite3.DatabaseError as exc:
            raise SyntheticGateRejected("invalid synthetic source") from exc
        result.append((spec, path))
    return result


def capture_synthetic_set(
    root: Path,
    specs: list[SyntheticSpec],
    *,
    set_id: str,
    max_source_bytes: int = 4 * 1024 * 1024,
    progress: Callable[[int, int, int], None] | None = None,
) -> dict:
    """Fixture-root only. Writes copy + manifest under fixture captured/<set_id>."""
    if not NAME_RE.fullmatch(set_id) or set_id.startswith("latest"):
        raise SyntheticGateRejected("invalid or mutable synthetic backup set ID")
    validated = validate_specs(root, specs)
    if max_source_bytes <= 0 or sum(p.stat().st_size for _, p in validated) > max_source_bytes:
        raise SyntheticGateRejected("synthetic test disk-byte budget exceeded")
    base = assert_fixture_scope(root)
    copy_root = base / "captured"
    if copy_root.is_symlink() or (copy_root.exists() and not copy_root.is_dir()):
        raise SyntheticGateRejected("unsafe synthetic copy destination")
    target = copy_root / set_id
    if target.exists() or target.is_symlink():
        raise SyntheticGateRejected("no-overwrite synthetic set collision")
    # Validate every SQLite destination/journal path before making directories.
    for spec, _ in validated:
        _assert_windows_sqlite_path(target / spec.filename)
    copy_root.mkdir(exist_ok=True)
    target.mkdir(exist_ok=False)
    collected = []
    try:
        for spec, src_path in validated:
            out = target / spec.filename
            started = utc_now()
            source = _readonly(src_path)
            try:
                _assert_marker(source)
                destination = sqlite3.connect(out)
                try:
                    source.backup(destination, pages=8, progress=progress, sleep=0.05)
                    destination.commit()
                finally:
                    destination.close()
            finally:
                source.close()
            finished = utc_now()
            verification = verify_synthetic_copy(out, spec.kind, anchor_hash=spec.anchor_hash)
            collected.append({
                "object_id": spec.object_id,
                "filename": spec.filename,
                "kind": spec.kind,
                "capture_start_utc": started,
                "capture_end_utc": finished,
                **verification,
            })
        body = {
            "manifest_schema": "vowsig-b1b2-synthetic-v0.1",
            "classification": "SYNTHETIC_TEST_ONLY_NOT_REAL_BACKUP",
            "set_id": set_id,
            "status": "VERIFIED_SYNTHETIC_COPY",
            "cross_database_atomic": False,
            "external_backup_verified": False,
            "independent_restore_verified": False,
            "hosted_snapshot_durability_verified": False,
            "database_objects": sorted(collected, key=lambda x: x["object_id"]),
        }
        digest = hashlib.sha256(canonical_bytes(body)).hexdigest()
        # A separate manifest digest is computed without self-reference.
        signed = {**body, "manifest_sha256": digest}
        with (target / "synthetic-manifest.json").open("x", encoding="utf-8") as stream:
            stream.write(json.dumps(signed, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        return signed
    except (sqlite3.DatabaseError, OSError) as exc:
        # Do not promote, retry with different source, or erase partial fixture.
        raise SyntheticGateRejected("synthetic capture incomplete; partial bytes preserved") from exc
