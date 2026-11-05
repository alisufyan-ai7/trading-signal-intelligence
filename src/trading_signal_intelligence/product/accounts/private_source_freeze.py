"""Controlled PRIVATE SQLite backup snapshots, never a live-source constructor.

Captured sources are potentially sensitive. The caller must pre-provision a
restricted-access destination outside the production repo. This tool will NOT
send or publish snapshots and does not confer independent historical acceptance.
"""
from __future__ import annotations

from contextlib import closing
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import secrets
import sqlite3
import stat
import time
from typing import Any

from trading_signal_intelligence.product.accounts.source_inventory import SOURCES
from trading_signal_intelligence.product.accounts.source_ledger_audit import (
    audit_pinned_source, SourceLedgerAuditError,
)

# Prior, separate owner-provided READ-ONLY observation, 2026-11-05T02:35:45Z.
# These are observed RECORD heads, not frozen file SHA256 or trusted signatures.
OBSERVED_PREFIXES: dict[str,tuple[int,str]] = {
    "data/ai_v1_1_xauusd.sqlite": (1324,"cd43509bfc8698b3b4675f8d3c3b8eb42f87d8aedcb60ede34ad673064434475"),
    "data/ai_v1_1_ustec.sqlite": (1331,"0e472d9d8aa75259632fcec1eb8df94e53aafe8e905fca473edb7584eed960b3"),
    "data/ai_v1_1_us30.sqlite": (1328,"847ff0c30acc3d5e21adea30326618c60ce2509b6a2f2773c65c145b8b563ca6"),
    "data/ai_v1_2_1_eurusd.sqlite": (1092,"858c67d626fcf7c4b6edc2deff96a2472a121d5cef32be13a8db06adbfc18f99"),
    "data/ai_v1_2_1_xagusd.sqlite": (1051,"1be82bacf5c9c533a8a997dae33a9ea74c7667c408aa4fb723820ae196b4e7b2"),
    "data/ai_v1_2_1_usoil.sqlite": (1055,"1ac30968d4f902b3cad1e26393e94588bf32cb7d91552939a08a078f5c019e3f"),
    "data/ai_v1_3_btcusdt.sqlite": (1091,"039c8bfd0bd19934d3029ee54467096b4538389d13904bd439b885a1a26e3fa9"),
    "data/ai_v1_3_ethusdt.sqlite": (1099,"0a7d8610f33b2105f1d6f2c4900e6e527fe927ba1230e3bbe4e2490f21c7d896"),
    "data/ai_v1_3_solusdt.sqlite": (1095,"41fea4a6113d72cbad78b91f409b96466fc1c7653fddcf0c1ad0b7c8e94d696e"),
    "data/forward.sqlite": (35,"178f0ca8b3cb674600e997c161e297a3dd4e90262583529eb58e6deaf94ab1a2"),
    "data/forward_ustec.sqlite": (45,"cc7e459fc01edf298366255b9951c5be9b43dc9a3df9cde6e7fd5567f6efdf25"),
    "data/forward_us30.sqlite": (40,"c8b92832e16795f0e0ccd6a6bddf667b71216ed05b4f4c904472977527adea7e"),
}
CRYPTO_ANCHOR_PATH = "research/forward/AI-v1.3-crypto-expansion-activation-2026-10-09T195556Z.json"
AI_EVENTS = frozenset(("ACTIVATION","INFERENCE","NO_TRADE","REJECTED_INFERENCE",
                       "SIGNAL","EXIT","PARTIAL_EXIT","MISSED_INFERENCE","ERROR"))
S02_EVENTS = frozenset(("ACTIVATION","SIGNAL","EXIT","MISSED_SIGNAL","SKIPPED_SIGNAL"))
_MAX_BACKUP_SECONDS = 180


class PrivateSourceFreezeError(ValueError):
    """Fail closed without disclosing raw SQLite rows or credentials."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _locations(repo_root: str | Path, private_root: str | Path) -> tuple[Path,Path]:
    root = Path(repo_root)
    evidence = Path(private_root)
    if root.is_symlink() or evidence.is_symlink():
        raise PrivateSourceFreezeError("Root/destination symlink refused")
    root = root.resolve(strict=True)
    evidence = evidence.resolve(strict=True)
    if root.name != "trading-signal-intelligence" or not evidence.is_dir():
        raise PrivateSourceFreezeError("Unapproved source/destination root")
    if evidence == root or root in evidence.parents or evidence in root.parents:
        raise PrivateSourceFreezeError("Destination must be outside repository and ancestors")
    if os.name != "nt" and stat.S_IMODE(evidence.stat().st_mode) & 0o077:
        raise PrivateSourceFreezeError("Private evidence directory must deny group/other access")
    return root, evidence


def _preflight(root: Path) -> None:
    if len(SOURCES) != 12 or set(OBSERVED_PREFIXES) != {s.relative_path for s in SOURCES}:
        raise PrivateSourceFreezeError("Unexpected governed source universe")
    for s in SOURCES:
        src = root / s.relative_path
        if src.is_symlink() or not src.is_file() or root not in src.resolve(strict=True).parents:
            raise PrivateSourceFreezeError("Missing, symlinked or escaped original ledger")
    anchor = root / CRYPTO_ANCHOR_PATH
    if anchor.is_symlink() or not anchor.is_file() or root not in anchor.resolve(strict=True).parents:
        raise PrivateSourceFreezeError("Crypto activation anchor unavailable")


def _backup_one(src: Path, target: Path) -> None:
    start = time.monotonic()
    def progress(status: int, remaining: int, total: int) -> None:
        if time.monotonic() - start > _MAX_BACKUP_SECONDS:
            raise PrivateSourceFreezeError("Bounded SQLite online backup timeout")
    # The only write connection is the NEW PRIVATE DESTINATION, never the source.
    with closing(sqlite3.connect(src.as_uri() + "?mode=ro", uri=True, timeout=1)) as source:
        source.execute("PRAGMA query_only=ON")
        with closing(sqlite3.connect(str(target), timeout=1)) as destination:
            source.backup(destination, pages=128, sleep=0.1, progress=progress)


def _inspect_copy(path: Path, table: str, prior: tuple[int,str], *,
                  s02: bool) -> dict[str,Any]:
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=1)) as db:
        db.execute("PRAGMA query_only=ON")
        if db.execute("PRAGMA quick_check").fetchone() != ("ok",):
            raise PrivateSourceFreezeError("Frozen SQLite quick-check failed")
        db.execute("BEGIN")
        count, max_seq = db.execute(
            f"SELECT COUNT(*),MAX(sequence) FROM {table}"
        ).fetchone()
        head_row = db.execute(
            f"SELECT record_hash FROM {table} ORDER BY sequence DESC LIMIT 1"
        ).fetchone()
        prefix_row = db.execute(
            f"SELECT record_hash FROM {table} WHERE sequence=?",
            (prior[0],)
        ).fetchone()
        groups = db.execute(
            f"SELECT record_type,COUNT(*) FROM {table} GROUP BY record_type"
        ).fetchall()
    if (not count or count < prior[0] or max_seq != count or
        not head_row or not prefix_row or prefix_row[0] != prior[1]):
        raise PrivateSourceFreezeError("Source rewind, sequence gap, or prior head mismatch")
    accepted = S02_EVENTS if s02 else AI_EVENTS
    if any(t not in accepted for t,_ in groups) or sum(n for _,n in groups) != count:
        raise PrivateSourceFreezeError("Unrecognized event kind or population mismatch")
    receipt = audit_pinned_source(
        path, profile="s02_forward" if s02 else "ai_v1",
        expected_head_sha256=head_row[0], expected_records=count,
    )
    if receipt["records"] != count or receipt["head_sha256"] != head_row[0]:
        raise PrivateSourceFreezeError("Frozen ledger chain mismatch")
    return {
        "rows":count, "terminal_sequence":max_seq,
        "terminal_record_hash":head_row[0],
        "prior_observation_prefix_match":True,
        "event_counts":dict(sorted((t,int(n)) for t,n in groups)),
        "sequence_chain_sha256":receipt["sequence_chain_sha256"],
        "full_chain_self_consistent":True,
    }


def _crypto_activation_check(root: Path, copy: Path, market: str) -> str:
    anchor = json.loads((root / CRYPTO_ANCHOR_PATH).read_text(encoding="utf-8"))
    market_anchor = anchor["markets"][market]
    with closing(sqlite3.connect(copy.as_uri() + "?mode=ro", uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        rows = db.execute(
            "SELECT record_hash,payload_json FROM ai_records "
            "WHERE record_type='ACTIVATION' ORDER BY sequence"
        ).fetchall()
    if (len(rows) != 1 or rows[0][0] != market_anchor["record_hash"] or
        json.loads(rows[0][1]) != market_anchor["payload"] or
        anchor.get("public_signal_exposure_enabled") is not False or
        anchor.get("broker_execution_enabled") is not False):
        raise PrivateSourceFreezeError("Crypto activation anchor mismatch")
    return "REPOSITORY_ACTIVATION_ANCHOR_MATCH_ONLY_K5_UNVERIFIED"


def capture_private_frozen_sources(repo_root: str | Path, private_root: str | Path) -> dict[str,Any]:
    """Online-copy twelve specific original DBs; never modify their live files.

    Copies are separate consistent database instants, NOT one synchronized
    cross-market cut. An owner/reviewer must independently custody and sign pins.
    """
    root, evidence = _locations(repo_root, private_root)
    _preflight(root)
    run_id = "source-freeze-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(6)
    run_dir = evidence / run_id
    run_dir.mkdir(mode=0o700)
    receipts: list[dict[str,Any]] = []
    try:
        for spec in SOURCES:
            original = root / spec.relative_path
            frozen = run_dir / Path(spec.relative_path).name
            start_utc = datetime.now(timezone.utc).isoformat()
            _backup_one(original, frozen)
            metadata = _inspect_copy(
                frozen, spec.table, OBSERVED_PREFIXES[spec.relative_path],
                s02=spec.program=="s02-forward",
            )
            if spec.program=="crypto-expansion-1":
                metadata["crypto_activation_bridge"] = _crypto_activation_check(
                    root, frozen, spec.symbol
                )
            frozen_sha = _sha256(frozen)
            if _sha256(frozen) != frozen_sha:
                raise PrivateSourceFreezeError("Frozen copy mutated during verification")
            os.chmod(frozen, stat.S_IREAD)
            receipts.append({
                "program":spec.program,"model_version":spec.model_version,
                "market":spec.symbol,"private_copy_name":frozen.name,
                "source_relative_path":spec.relative_path,
                "copy_started_at_utc":start_utc,
                "copy_finished_at_utc":datetime.now(timezone.utc).isoformat(),
                "frozen_file_sha256":frozen_sha, **metadata,
            })
        result = {
            "schema_version":1,
            "status":"PRIVATE_FROZEN_COPIES_SELF_CHECKED_NOT_INDEPENDENTLY_PINNED",
            "source_observation":"2026-11-05T02:35:45.711557Z",
            "snapshot_mode":"SQLITE_BACKUP_API_SEQUENTIAL_PER_DATABASE",
            "synchronized_twelve_market_point_in_time":False,
            "copy_count":len(receipts),
            "raw_source_payloads_in_private_copies":True,
            "raw_source_payloads_in_manifest":False,
            "private_directory_acl_verified_by_operator":False,
            "independent_external_source_pins_verified":False,
            "crypto_k5_epoch_provenance_verified":False,
            "complete_historical_after_cost_performance_verified":False,
            "rows":receipts,
        }
        output = run_dir / "manifest.preliminary.json"
        with output.open("x", encoding="utf-8") as writer:
            json.dump(result, writer, sort_keys=True, separators=(",",":"))
        os.chmod(output, stat.S_IREAD)
        result["manifest_sha256"] = _sha256(output)
        result["run_id"] = run_id
        return result
    except (sqlite3.Error,SourceLedgerAuditError,OSError,ValueError,KeyError,TypeError) as exc:
        # No manifest is written on failure. Any partial copies remain PRIVATE,
        # not approved; do not erase potentially forensic-sensitive evidence.
        raise PrivateSourceFreezeError("Private snapshot set INCOMPLETE; never promote") from exc


def verify_private_frozen_set(repo_root: str | Path, private_run_dir: str | Path,
                              *, externally_recorded_manifest_sha256: str) -> dict[str,Any]:
    """Separate read-only recertification of completed PRIVATE snapshots.

    An independently supplied manifest digest binds the expected file
    hashes. Matching it is not a human/source-rights/cost/K5 attestation.
    """
    import re
    if not isinstance(externally_recorded_manifest_sha256,str) or not re.fullmatch(
        r"[0-9a-f]{64}",externally_recorded_manifest_sha256
    ):
        raise PrivateSourceFreezeError("An independently supplied 64-hex manifest pin is required")
    run=Path(private_run_dir)
    # Both reviewed operators exist: the package capture uses "source-freeze-";
    # the owner-executed native Windows inline capture uses "freeze-".
    if (run.is_symlink() or not run.is_dir() or
        not run.name.startswith(("source-freeze-","freeze-"))):
        raise PrivateSourceFreezeError("Unrecognized private snapshot directory")
    root, _ = _locations(repo_root,run.parent)
    run=run.resolve(strict=True)
    manifest=run/"manifest.preliminary.json"
    if (manifest.is_symlink() or not manifest.is_file() or
            _sha256(manifest)!=externally_recorded_manifest_sha256):
        raise PrivateSourceFreezeError("Private manifest content changed or absent")
    def unique(pairs):
        obj={}
        for key,val in pairs:
            if key in obj:
                raise PrivateSourceFreezeError("Duplicated manifest keys")
            obj[key]=val
        return obj
    try:
        obj=json.loads(manifest.read_text(encoding="utf-8"),
                       object_pairs_hook=unique)
        if (obj.get("schema_version")!=1 or obj.get("copy_count")!=12 or
            obj.get("status")!="PRIVATE_FROZEN_COPIES_SELF_CHECKED_NOT_INDEPENDENTLY_PINNED"):
            raise PrivateSourceFreezeError("Invalid manifest protocol")
        rows=obj.get("rows")
        if not isinstance(rows,list) or len(rows)!=12:
            raise PrivateSourceFreezeError("Incomplete private source set")
        mapped={row.get("source_relative_path"):row for row in rows}
        if len(mapped)!=12 or set(mapped)!=set(OBSERVED_PREFIXES):
            raise PrivateSourceFreezeError("Private copy universe mismatch")
        total=0
        for spec in SOURCES:
            entry=mapped[spec.relative_path]
            if (entry.get("program")!=spec.program or entry.get("market")!=spec.symbol
                or entry.get("model_version")!=spec.model_version or
                entry.get("private_copy_name")!=Path(spec.relative_path).name):
                raise PrivateSourceFreezeError("Private ledger identity mismatch")
            frozen=run/entry["private_copy_name"]
            if frozen.is_symlink() or not frozen.is_file() or frozen.resolve().parent!=run:
                raise PrivateSourceFreezeError("Private copy path unsafe")
            frozen_sha=_sha256(frozen)
            if frozen_sha != entry.get("frozen_file_sha256"):
                raise PrivateSourceFreezeError("Private source bytes changed after manifest")
            observed=_inspect_copy(
                frozen,spec.table,OBSERVED_PREFIXES[spec.relative_path],
                s02=spec.program=="s02-forward",
            )
            if any(observed[k]!=entry.get(k) for k in observed):
                raise PrivateSourceFreezeError("Private source manifest population/hash mismatch")
            if spec.program=="crypto-expansion-1":
                if _crypto_activation_check(root,frozen,spec.symbol)!=entry.get("crypto_activation_bridge"):
                    raise PrivateSourceFreezeError("Crypto activation bridge drift")
            if _sha256(frozen)!=frozen_sha:
                raise PrivateSourceFreezeError("Private snapshot changed during verification")
            total+=observed["rows"]
    except (KeyError,TypeError,ValueError,OSError,sqlite3.Error,SourceLedgerAuditError) as exc:
        raise PrivateSourceFreezeError("Private offline source verification HELD") from exc
    return {
        "status":"PRIVATE_FROZEN_SET_RECHECKED_WITH_SUPPLIED_MANIFEST_PIN",
        "copy_count":12,
        "total_event_rows":total,
        "matched_manifest_sha256":externally_recorded_manifest_sha256,
        "original_source_bytes_transferred":False,
        "independently_reviewed_manifest_pin_proven":False,
        "crypto_k5_epoch_provenance_verified":False,
        "full_history_costs_rights_and_performance_verified":False,
    }
