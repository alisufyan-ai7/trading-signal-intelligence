"""Prospective real-S02 offline backup core, NOT an installed backup service.

No network/SDK/runtime entrypoint. A future approved operator must provide an
exact data-rights scope and off-host encryption key. Never import synthetic B1-B6
into a real-data production flow. No source DB is read on module import.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import time
from dataclasses import dataclass
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

SCHEMA = "vowsig-live-s02-aes256gcm-v1"
MAGIC = b"VOWSIG_LIVE_S02_GCM_V1\x00"
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_ENVELOPE_BYTES = MAX_SOURCE_BYTES + 4096
MAX_CAPTURE_SECONDS = 60
SOURCE_REL = "data/forward.sqlite"
RUN_ID = re.compile(r"^[a-z][a-z0-9-]{7,55}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
COLUMNS = ("sequence","record_id","record_type","entity_id","recorded_at_utc",
           "effective_at_utc","payload_json","previous_hash","record_hash")


class LiveBackupRejected(RuntimeError):
    """Fixed failure category; never include source data, secrets or SDK errors."""


@dataclass(frozen=True)
class SourceAuthorization:
    """Attested scope, NOT self-proving legal or account permission."""
    source_relative_path: str
    source_kind: str
    rights_attestation_sha256: str
    owner_source_access_approval_sha256: str
    permitted_provider_regions: tuple[str, str]
    classification: str = "APPROVED_PRIVATE_S02_ENCRYPTED_ONLY"

    def validate(self) -> None:
        if (self.source_relative_path != SOURCE_REL or self.source_kind != "S02"
                or self.classification != "APPROVED_PRIVATE_S02_ENCRYPTED_ONLY"
                or not HEX64.fullmatch(self.rights_attestation_sha256)
                or not HEX64.fullmatch(self.owner_source_access_approval_sha256)
                or len(self.permitted_provider_regions) != 2
                or len(set(self.permitted_provider_regions)) != 2
                or any(not re.fullmatch(r"[a-z]{2}-[a-z]+-\d+|us-east-\d{3}", r)
                       for r in self.permitted_provider_regions)):
            raise LiveBackupRejected("missing scoped source and rights approval")


@dataclass(frozen=True)
class SealedLiveCopy:
    """Never log envelope or key; ciphertext may contain private information."""
    object_key: str
    envelope: bytes
    envelope_sha256: str
    plaintext_sha256: str
    record_count: int
    run_id: str
    metadata_sha256: str


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _safe_file(path: Path) -> None:
    if not path.is_file() or path.is_symlink():
        raise LiveBackupRejected("SQLite source/copy missing or linked")
    st = path.stat()
    if (not 0 < st.st_size <= MAX_SOURCE_BYTES or st.st_nlink != 1
            or getattr(st, "st_file_attributes", 0) & 0x400
            or path.suffix.lower() != ".sqlite"):
        raise LiveBackupRejected("unsafe SQLite source/copy")


def _safe_directory(path: Path) -> None:
    if (not path.is_dir() or path.is_symlink()
            or getattr(path.stat(), "st_file_attributes", 0) & 0x400):
        raise LiveBackupRejected("unsafe source or private scratch directory")


def verify_s02_copy(path: Path) -> tuple[str, int]:
    """Read-only integrity, append-only triggers and entire canonical hash chain."""
    _safe_file(path)
    before = _sha(path.read_bytes())
    try:
        conn = sqlite3.connect(path.resolve(strict=True).as_uri() + "?mode=ro",
                               uri=True, timeout=2.0)
        try:
            conn.execute("PRAGMA query_only=ON")
            if [r[0] for r in conn.execute("PRAGMA integrity_check")] != ["ok"]:
                raise LiveBackupRejected("SQLite integrity check failed")
            names = {str(r[1]) for r in conn.execute("PRAGMA table_info(forward_records)")}
            if not set(COLUMNS).issubset(names):
                raise LiveBackupRejected("S02 ledger schema not recognized")
            triggers = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='trigger'")}
            if not {"forward_records_no_update", "forward_records_no_delete"}.issubset(triggers):
                raise LiveBackupRejected("S02 append-only controls absent")
            previous = None
            count = 0
            for count, row in enumerate(conn.execute(
                    "SELECT " + ",".join(COLUMNS) + " FROM forward_records ORDER BY sequence"), 1):
                seq, ident, kind, entity, recorded, effective, payload, prev, digest = row
                if seq != count or prev != previous:
                    raise LiveBackupRejected("S02 hash-chain sequence invalid")
                parsed = json.loads(payload)
                if not isinstance(parsed, dict):
                    raise LiveBackupRejected("S02 payload schema invalid")
                normalized = json.dumps(parsed, sort_keys=True, separators=(",", ":"),
                                        ensure_ascii=False, allow_nan=False, default=str)
                material = {"record_id": ident, "record_type": kind, "entity_id": entity,
                            "recorded_at_utc": recorded, "effective_at_utc": effective,
                            "payload_json": normalized, "previous_hash": previous}
                computed = hashlib.sha256(json.dumps(
                    material, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                    allow_nan=False, default=str).encode("utf-8")).hexdigest()
                if computed != digest:
                    raise LiveBackupRejected("S02 ledger record hash invalid")
                previous = computed
            if count < 1:
                raise LiveBackupRejected("empty S02 backup rejected")
        finally:
            conn.close()
    except LiveBackupRejected:
        raise
    except (OSError, ValueError, TypeError, sqlite3.DatabaseError):
        raise LiveBackupRejected("S02 database verification failed") from None
    if _sha(path.read_bytes()) != before:
        raise LiveBackupRejected("S02 backup changed during verification")
    return before, count


def capture_approved_s02(*, repo_root: Path, scratch_parent: Path, run_id: str,
                         authorization: SourceAuthorization) -> Path:
    """One permitted source; read-only online SQLite backup to new private scratch.

    File ACL and offsite transfer rights are separately operator-attested.
    Never automatically capture all databases or data/research.sqlite.
    """
    authorization.validate()
    if not RUN_ID.fullmatch(run_id):
        raise LiveBackupRejected("invalid immutable run identity")
    repo_root, scratch_parent = Path(repo_root), Path(scratch_parent)
    _safe_directory(repo_root)
    _safe_directory(repo_root / "data")
    _safe_directory(scratch_parent)
    if scratch_parent.resolve().is_relative_to(repo_root.resolve()):
        raise LiveBackupRejected("scratch directory inside repository")
    source = repo_root / SOURCE_REL
    _safe_file(source)
    if source.resolve(strict=True).parent != (repo_root / "data").resolve(strict=True):
        raise LiveBackupRejected("source path escaped approved boundary")
    target = scratch_parent / run_id
    if target.exists() or target.is_symlink():
        raise LiveBackupRejected("no-overwrite backup set collision")
    output = target / "forward.sqlite"
    if os.name == "nt" and len(str(output) + "-journal") >= 240:
        raise LiveBackupRejected("Windows SQLite journal path over budget")
    target.mkdir(mode=0o700, exist_ok=False)
    begin = time.monotonic()
    try:
        src = sqlite3.connect(source.resolve(strict=True).as_uri() + "?mode=ro",
                              uri=True, timeout=2.0)
        dst = None
        try:
            src.execute("PRAGMA query_only=ON")
            dst = sqlite3.connect(output, timeout=2.0)
            page = int(src.execute("PRAGMA page_size").fetchone()[0])
            def progress(status: int, remaining: int, total: int) -> None:
                if time.monotonic() - begin >= MAX_CAPTURE_SECONDS:
                    raise LiveBackupRejected("online backup time budget exceeded")
                if page * total > MAX_SOURCE_BYTES:
                    raise LiveBackupRejected("online backup byte budget exceeded")
            src.backup(dst, pages=16, progress=progress, sleep=0.05)
            dst.commit()
        finally:
            if dst is not None:
                dst.close()
            src.close()
    except LiveBackupRejected:
        raise
    except (OSError, sqlite3.DatabaseError):
        raise LiveBackupRejected("SQLite snapshot failed closed") from None
    verify_s02_copy(output)
    return output


def seal_verified_copy(*, copied: Path, run_id: str, key: bytes,
                       authorization: SourceAuthorization) -> SealedLiveCopy:
    authorization.validate()
    if not RUN_ID.fullmatch(run_id) or type(key) is not bytes or len(key) != 32:
        raise LiveBackupRejected("invalid release ID or encryption key")
    copied = Path(copied)
    if copied.name != "forward.sqlite" or copied.parent.name != run_id:
        raise LiveBackupRejected("wrong captured source identity")
    original_sha, count = verify_s02_copy(copied)
    plaintext = copied.read_bytes()
    if _sha(plaintext) != original_sha:
        raise LiveBackupRejected("copy changed during sealing")
    metadata = {"schema": SCHEMA, "classification": authorization.classification,
                "run_id": run_id, "plaintext_sha256": original_sha,
                "plaintext_size": len(plaintext), "s02_records": count,
                "rights_ref_sha256": authorization.rights_attestation_sha256}
    aad = _canonical(metadata)
    if len(aad) > 2048:
        raise LiveBackupRejected("metadata budget exceeded")
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, aad)
    envelope = MAGIC + len(aad).to_bytes(2, "big") + nonce + aad + ciphertext
    if len(envelope) > MAX_ENVELOPE_BYTES:
        raise LiveBackupRejected("envelope size over budget")
    sha = _sha(envelope)
    return SealedLiveCopy(f"pilot/vowsig/approved-s02/v1/{run_id}/{sha}.aesgcm",
                          envelope, sha, original_sha, count, run_id, _sha(aad))


def restore_verified_envelope(*, envelope: bytes, key: bytes, scratch_parent: Path,
                              restore_id: str, expected_sha256: str | None = None) -> dict:
    """Independent authenticated SQLite recovery; NO original source access."""
    if type(key) is not bytes or len(key) != 32 or not RUN_ID.fullmatch(restore_id):
        raise LiveBackupRejected("invalid recovery key or restore ID")
    if type(envelope) is not bytes or not 40 < len(envelope) <= MAX_ENVELOPE_BYTES:
        raise LiveBackupRejected("invalid encrypted object")
    if expected_sha256 is not None and (
            not HEX64.fullmatch(expected_sha256) or _sha(envelope) != expected_sha256):
        raise LiveBackupRejected("ciphertext SHA mismatch")
    if not envelope.startswith(MAGIC):
        raise LiveBackupRejected("unsupported backup envelope")
    start = len(MAGIC)
    length = int.from_bytes(envelope[start:start + 2], "big")
    if not 0 < length <= 2048:
        raise LiveBackupRejected("invalid envelope metadata length")
    nonce = envelope[start + 2:start + 14]
    aad = envelope[start + 14:start + 14 + length]
    ciphertext = envelope[start + 14 + length:]
    if len(nonce) != 12 or len(aad) != length or len(ciphertext) < 17:
        raise LiveBackupRejected("truncated encrypted backup")
    try:
        meta = json.loads(aad)
        if (not isinstance(meta, dict) or _canonical(meta) != aad
                or set(meta) != {"schema","classification","run_id",
                                   "plaintext_sha256","plaintext_size",
                                   "s02_records","rights_ref_sha256"}
                or meta["schema"] != SCHEMA
                or meta["classification"] != "APPROVED_PRIVATE_S02_ENCRYPTED_ONLY"
                or not RUN_ID.fullmatch(meta["run_id"])
                or not HEX64.fullmatch(meta["rights_ref_sha256"])
                or not HEX64.fullmatch(meta["plaintext_sha256"])
                or type(meta["plaintext_size"]) is not int
                or not 0 < meta["plaintext_size"] <= MAX_SOURCE_BYTES
                or type(meta["s02_records"]) is not int
                or not 0 < meta["s02_records"] <= 1_000_000):
            raise LiveBackupRejected("backup metadata invalid")
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, aad)
    except (InvalidTag, KeyError, TypeError, ValueError):
        raise LiveBackupRejected("authentication failed; no recovery") from None
    if len(plaintext) != meta["plaintext_size"] or _sha(plaintext) != meta["plaintext_sha256"]:
        raise LiveBackupRejected("authenticated identity mismatch")
    scratch_parent = Path(scratch_parent)
    _safe_directory(scratch_parent)
    target = scratch_parent / restore_id
    if target.exists() or target.is_symlink():
        raise LiveBackupRejected("recovery directory collision")
    target.mkdir(mode=0o700, exist_ok=False)
    output = target / "forward.sqlite"
    try:
        with output.open("xb") as handle:
            handle.write(plaintext)
        sha, count = verify_s02_copy(output)
    except Exception:
        raise LiveBackupRejected("independent restored database validation failed") from None
    if sha != meta["plaintext_sha256"] or count != meta["s02_records"]:
        raise LiveBackupRejected("restored record count or digest mismatch")
    return {"status": "LIVE_S02_AUTHENTICATED_RESTORE_VERIFIED",
            "run_id": meta["run_id"], "plaintext_sha256": sha,
            "record_count": count, "rights_ref_sha256": meta["rights_ref_sha256"]}
