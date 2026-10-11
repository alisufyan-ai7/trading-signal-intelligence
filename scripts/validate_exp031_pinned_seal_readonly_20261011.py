"""Read-only EXP-031 review of one owner-pinned, already-existing local seal.

No capture, SQLite, scan, provider, HTTP, mutation, upload, or publication.
Only metadata and safe validation outcomes are printed; seal bytes stay local.
Do not import or invoke the guarded publisher.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
from datetime import datetime, timezone
from pathlib import Path

PINNED_SHA256 = "f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4"
PINNED_BYTES = 3048
PINNED_AT = "2026-10-11T12:07:21.257601+00:00"
MARKETS = frozenset(("BTCUSDT", "ETHUSDT", "SOLUSDT"))
GATES = frozenset(("C1", "C2", "C3"))
REPO_SOURCE = Path(__file__).resolve().parents[1]


def _refuse_external_actions(event: str, args: tuple[object, ...]) -> None:
    """Process-level defense; not a substitute for OS-level sandboxing."""
    if (event.startswith("sqlite3.")
        or event.startswith("subprocess.")
        or event.startswith("socket.")
        or event in ("os.system", "os.startfile", "os.exec", "os.spawn",
                     "os.posix_spawn", "os.fork")):
        raise RuntimeError("Disallowed external action in read-only verifier: " + event)


def _guarded_file_state(path: Path) -> tuple[int, int, str]:
    # The file is NEVER copied. Refuse links and unexpected file sizes.
    if path.is_symlink():
        raise RuntimeError("Local seal is a symlink")
    info = path.stat()
    if (not stat.S_ISREG(info.st_mode)
        or info.st_nlink != 1
        or info.st_size != PINNED_BYTES):
        raise RuntimeError("Local seal file type, link count, or size mismatch")
    return (info.st_size, info.st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())


def _must_reject(callable_, message: str) -> None:
    from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import AsOfSealRejected
    try:
        callable_()
    except (AsOfSealRejected, ValueError):
        return
    raise RuntimeError("A forbidden seal state was accepted: " + message)


def validate(root: Path) -> None:
    sys.addaudithook(_refuse_external_actions)
    # -I -B is required in the owner shell: imported files are frozen Git
    # objects in a separate detached review worktree, never production main.
    sys.path.insert(0, str(REPO_SOURCE / "src"))
    from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
        SEAL_NAME, load_pinned_asof_program, asof_program_from_seal_bytes,
    )
    from trading_signal_intelligence.product.cloud_app import (
        _validate_validation_programs,
    )
    if SEAL_NAME != "crypto-research-asof-v0.1.json":
        raise RuntimeError("Unexpected frozen seal filename")
    source = root / "data" / SEAL_NAME
    baseline = _guarded_file_state(source)
    if baseline[2] != PINNED_SHA256:
        raise RuntimeError("Source seal hash disagrees with approved exact-byte pin")

    now = datetime.now(timezone.utc)
    if now <= datetime.fromisoformat(PINNED_AT):
        raise RuntimeError("As-of record must be strictly historical")
    program = load_pinned_asof_program(root, now, PINNED_SHA256)
    if (program.get("program_id") != "crypto-expansion-1"
        or program.get("status") != "delayed"
        or program.get("mode") != "SHADOW_ONLY"
        or program.get("public_signal_exposure") is not False
        or program.get("signal_details_included") is not False
        or program.get("public_research_observability") is not True):
        raise RuntimeError("Delayed research-only program contract changed")

    label = program.get("title")
    expected = (
        "Crypto AI Shadow Validation — DELAYED "
        "(last verified 2026-10-11T12:07:21.257601+00:00 UTC)"
    )
    if label != expected:
        raise RuntimeError("Historical UTC title incorrect; no current crypto claim permitted")

    health = program.get("health")
    if (not isinstance(health, dict)
        or health.get("healthy") is not False
        or health.get("scheduler_healthy") is not False
        or health.get("ledgers_valid") is not True
        or health.get("broker_execution_disabled") is not True):
        raise RuntimeError("Historical/offline and broker execution boundaries invalid")

    symbols = program.get("markets")
    gates = program.get("gates")
    if (not isinstance(symbols, list)
        or len(symbols) != 3
        or {m.get("source_symbol") for m in symbols} != MARKETS
        or not isinstance(gates, list)
        or len(gates) != 3
        or {g.get("gate_id") for g in gates} != GATES
        or any(g.get("eligible") is not False for g in gates)):
        raise RuntimeError("Crypto symbols or still-ineligible C1/C2/C3 gates invalid")

    _validate_validation_programs({
        "validation_programs_schema_version": 1,
        "validation_programs": [program],
    })

    # Frozen schema field-name parity (the public server validator above
    # enforces its supported semantic subset, not full JSON Schema 2020-12).
    schema_path = REPO_SOURCE / "config/public_validation_program_schema_v1.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    if (schema.get("$schema") != "https://json-schema.org/draft/2020-12/schema"
        or schema.get("additionalProperties") is not False
        or set(schema.get("required", [])) != set(program)
        or set(schema.get("properties", {})) != set(program)):
        raise RuntimeError("Frozen public JSON schema field identity changed")

    # Purely in-memory negative checks, never write any alternative seal.
    data = json.loads(source.read_bytes())
    if (set(data) != {
            "seal_schema_version", "source_snapshot_generated_at_utc",
            "crypto_program",
        }
        or data["seal_schema_version"] != 1
        or data["source_snapshot_generated_at_utc"] != PINNED_AT):
        raise RuntimeError("Seal UTC/schema metadata differ from owner-approved pin")

    raw = source.read_bytes()
    _must_reject(
        lambda: load_pinned_asof_program(root, now, "0" * 64),
        "unapproved SHA-256 pin",
    )
    _must_reject(
        lambda: asof_program_from_seal_bytes(raw, datetime.fromisoformat(PINNED_AT)),
        "present-time rather than historical status",
    )
    mutated = dict(data)
    mutated["crypto_program"] = dict(data["crypto_program"])
    mutated["crypto_program"]["public_signal_exposure"] = True
    _must_reject(
        lambda: asof_program_from_seal_bytes(
            json.dumps(mutated).encode("utf-8"), now),
        "forbidden live signal exposure",
    )

    after = _guarded_file_state(source)
    if after != baseline:
        raise RuntimeError("Original local seal changed during read-only verification")

    print("EXP031_OWNER_APPROVED_PIN=PASS")
    print("PINNED_SEAL_SHA256=" + PINNED_SHA256)
    print("PINNED_SEAL_BYTES=" + str(PINNED_BYTES))
    print("PINNED_SEAL_OBSERVED_UTC=" + PINNED_AT)
    print("LOCAL_SEAL_SHA256_AND_STAT_STABLE=PASS")
    print("FROZEN_V1_SCHEMA_FIELD_IDENTITY=PASS")
    print("CLOUD_VALIDATION_PROGRAM_CHECK=PASS")
    print("DELAYED_HISTORICAL_UTC_LABEL=PASS")
    print("CRYPTO_MARKETS=BTCUSDT,ETHUSDT,SOLUSDT")
    print("C1_C2_C3_INELIGIBLE=PASS")
    print("FORBIDDEN_LIVE_SIGNAL_EXPOSURE_REJECTED=PASS")
    print("UNAPPROVED_HASH_REJECTED=PASS")
    print("NONHISTORICAL_TIME_REJECTED=PASS")
    print("BROKER_EXECUTION_DISABLED=TRUE")
    print("NO_SQLITE_PROVIDER_TASK_CLOUD_OR_PUBLICATION=TRUE")
    print("READ_ONLY_LOCAL_PIN_VALIDATION=PASS")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live-root", required=True, type=Path)
    args = parser.parse_args()
    validate(args.live_root.resolve(strict=True))
