"""Public-only, pinned as-of crypto research seal.

No live SQLite access, Task Scheduler calls, providers, network, or writers.
Creation from live reports is a separately authorized caller responsibility.
A seal is trusted only when its *entire byte string* matches an independently
owner-approved SHA-256; a self-hash inside JSON is never sufficient.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import stat
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SEAL_NAME = "crypto-research-asof-v0.1.json"
MAX_SEAL_BYTES = 65536
SOURCE_PROGRAM_ID = "crypto-expansion-1"
SYMBOLS = frozenset({"BTCUSDT", "ETHUSDT", "SOLUSDT"})
GATES = frozenset({"C1", "C2", "C3"})
HEX64 = re.compile(r"^[a-f0-9]{64}$")
PUBLIC_FIELDS = frozenset({
    "schema_version", "program_id", "title", "runtime_version",
    "decision_protocol_version", "mode", "status",
    "public_research_observability", "public_signal_exposure",
    "signal_details_included", "health", "totals", "gates", "markets",
    "raw_market_data_included", "raw_feature_snapshots_included",
    "provider_request_metadata_included", "hidden_reasoning_included",
})
FORBIDDEN = frozenset({
    "recent_decisions", "shadow_signals", "signal_records", "alerts",
    "entry", "entry_price", "stop", "stop_loss", "target", "take_profit",
    "direction", "confidence", "rationale", "provider_payload",
    "provider_request_metadata", "raw_candles", "raw_market_data",
    "feature_snapshot", "raw_feature_snapshots",
})


class AsOfSealRejected(ValueError):
    """Do not attach crypto; fresh core and expansion may continue."""


def _utc(value: Any) -> datetime:
    if not isinstance(value, str):
        raise AsOfSealRejected("missing seal UTC timestamp")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AsOfSealRejected("invalid seal timestamp") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise AsOfSealRejected("seal timestamp lacks timezone")
    return dt.astimezone(timezone.utc)


def _check_no_private(value: Any) -> None:
    if isinstance(value, dict):
        if FORBIDDEN.intersection(value):
            raise AsOfSealRejected("private crypto details in seal")
        for nested in value.values():
            _check_no_private(nested)
    elif isinstance(value, list):
        for nested in value:
            _check_no_private(nested)


def _check_original_program(program: Any) -> None:
    if not isinstance(program, dict) or set(program) != PUBLIC_FIELDS:
        raise AsOfSealRejected("public crypto program shape changed")
    if (program.get("schema_version") != 1
        or program.get("program_id") != SOURCE_PROGRAM_ID
        or program.get("runtime_version") != "AI-v1.3"
        or program.get("mode") != "SHADOW_ONLY"
        or program.get("status") != "collecting"
        or program.get("public_research_observability") is not True
        or program.get("public_signal_exposure") is not False
        or program.get("signal_details_included") is not False):
        raise AsOfSealRejected("unverified original crypto status")
    for name in ("raw_market_data_included", "raw_feature_snapshots_included",
                 "provider_request_metadata_included", "hidden_reasoning_included"):
        if program.get(name) is not False:
            raise AsOfSealRejected("unsafe crypto source field")
    h = program.get("health")
    if (not isinstance(h, dict)
        or h.get("healthy") is not True
        or h.get("ledgers_valid") is not True
        or h.get("scheduler_healthy") is not True
        or h.get("broker_execution_disabled") is not True):
        raise AsOfSealRejected("original crypto health was not verified")
    markets = program.get("markets")
    gates = program.get("gates")
    if (not isinstance(markets, list) or len(markets) != 3
        or any(not isinstance(m, dict) for m in markets)
        or {m.get("source_symbol") for m in markets} != SYMBOLS
        or any(m.get("ledger_valid") is not True
               or m.get("activation_anchor_match") is not True for m in markets)
        or not isinstance(gates, list) or len(gates) != 3
        or any(not isinstance(g, dict) for g in gates)
        or {g.get("gate_id") for g in gates} != GATES):
        raise AsOfSealRejected("incomplete crypto cohort or invalid ledger evidence")
    _check_no_private(program)


def seal_from_verified_snapshot(snapshot: dict[str, Any], now: datetime) -> bytes:
    """Call ONLY after full guarded export, K5+ledger pre/post and cloud guards pass.

    No source paths or raw report fields are ever put in the output.
    """
    if not isinstance(snapshot, dict):
        raise AsOfSealRejected("snapshot is not an object")
    programs = snapshot.get("validation_programs")
    if (not isinstance(programs, list) or len(programs) != 3
        or any(not isinstance(p, dict) for p in programs)
        or {p.get("program_id") for p in programs} != {
            "core-ai-shadow", "market-expansion-1", SOURCE_PROGRAM_ID
        }):
        raise AsOfSealRejected("three validated programs required")
    original_at = _utc(snapshot.get("generated_at_utc"))
    now_utc = now.astimezone(timezone.utc)
    if now.tzinfo is None or now.utcoffset() is None:
        raise AsOfSealRejected("capture time lacks timezone")
    if not 0 <= (now_utc - original_at).total_seconds() <= 120:
        raise AsOfSealRejected("capture must be fresh and not future")
    crypto = next(p for p in programs if p["program_id"] == SOURCE_PROGRAM_ID)
    _check_original_program(crypto)
    # The creator must independently validate the entire three-program snapshot.
    body = {
        "seal_schema_version": 1,
        "source_snapshot_generated_at_utc": original_at.isoformat(),
        "crypto_program": crypto,
    }
    raw = json.dumps(body, sort_keys=True, separators=(",", ":"),
                     ensure_ascii=False, allow_nan=False).encode("utf-8")
    if len(raw) > MAX_SEAL_BYTES:
        raise AsOfSealRejected("crypto seal too large")
    return raw


def _read_pinned_bytes(path: Path, expected_sha256: str) -> bytes:
    if not HEX64.fullmatch(expected_sha256):
        raise AsOfSealRejected("unapproved or invalid seal SHA-256")
    if path.is_symlink():
        raise AsOfSealRejected("seal symlink forbidden")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1
        or info.st_size <= 0 or info.st_size > MAX_SEAL_BYTES):
        raise AsOfSealRejected("unsafe seal file")
    before = path.read_bytes()
    if hashlib.sha256(before).hexdigest() != expected_sha256:
        raise AsOfSealRejected("crypto seal digest not approved")
    if path.stat().st_size != len(before):
        raise AsOfSealRejected("seal changed during read")
    return before


def asof_program_from_seal_bytes(raw: bytes, now: datetime) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > MAX_SEAL_BYTES:
        raise AsOfSealRejected("invalid seal content")
    try:
        document = json.loads(raw)
    except (UnicodeError, ValueError) as exc:
        raise AsOfSealRejected("invalid seal JSON") from exc
    if not isinstance(document, dict) or set(document) != {
        "seal_schema_version", "source_snapshot_generated_at_utc", "crypto_program"
    } or document["seal_schema_version"] != 1:
        raise AsOfSealRejected("unknown seal schema")
    saved_at = _utc(document["source_snapshot_generated_at_utc"])
    if now.tzinfo is None or now.utcoffset() is None:
        raise AsOfSealRejected("observation time lacks timezone")
    if saved_at >= now.astimezone(timezone.utc):
        raise AsOfSealRejected("as-of seal is not historical")
    _check_original_program(document["crypto_program"])
    program = copy.deepcopy(document["crypto_program"])
    program["status"] = "delayed"
    program["title"] = (
        "Crypto AI Shadow Validation — DELAYED "
        f"(last verified {saved_at.isoformat()} UTC)"
    )
    program["health"]["healthy"] = False
    program["health"]["scheduler_healthy"] = False
    # Deliberately no new JSON schema fields, last-verified timestamp is in
    # the prominently visible title; frozen public schema v1 is unchanged.
    return program


def load_pinned_asof_program(root: Path, now: datetime,
                            expected_sha256: str) -> dict[str, Any]:
    """Read the existing, explicitly owner-pinned public-only seal, not ledgers."""
    path = root / "data" / SEAL_NAME
    raw = _read_pinned_bytes(path, expected_sha256)
    program = asof_program_from_seal_bytes(raw, now)
    # Require identical bytes after validation, not a mutable manifest pointer.
    if _read_pinned_bytes(path, expected_sha256) != raw:
        raise AsOfSealRejected("seal changed during validation")
    return program
