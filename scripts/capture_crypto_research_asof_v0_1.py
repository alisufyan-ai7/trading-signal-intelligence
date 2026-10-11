"""Prepare one PRIVATE, owner-pinned, historical crypto aggregate seal.

DORMANT. Never execute against real ledgers without a separate, specific owner
authorization. This module does not use the full product snapshot exporter:
that path reads other, unapproved live-market databases. It reads exactly
nine governed core/expansion/crypto AI ledger files and GET-only scheduler/Git
verification. No K5 scan, provider, cloud, publication or broker action.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

from guarded_product_publish_v0_1 import (
    BASE_PROGRAMS, PROGRAMS, MARKETS, ROOT,
    PublicationHeld, _reject_private_crypto,
    _verify_current_expansion_claim, crypto_fingerprints,
    ensure_stable_k5, probe_k5, validate_k5_finished,
)
from export_guarded_core_expansion_v0_2 import build_core_expansion_programs
from trading_signal_intelligence.product.ai_insights import (
    _verify_crypto_validation_adapter_source,
)
from trading_signal_intelligence.product.cloud_app import (
    _validate_validation_programs,
)
from trading_signal_intelligence.product.crypto_validation import (
    build_crypto_public_validation_program,
)
from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
    SEAL_NAME, asof_program_from_seal_bytes, seal_from_verified_snapshot,
)

CONFIRM = "CAPTURE-ONE-CRYPTO-ASOF-RESEARCH-SEAL"
ENABLE = "VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED"

# An EXACT identity allowlist, not a glob. Retired/failed ledgers, S02
# forward.sqlite, and the licensed/raw research.sqlite are out of scope.
ACTIVE_AI_LEDGER_PATHS = (
    "data/ai_v1_1_xauusd.sqlite",
    "data/ai_v1_1_ustec.sqlite",
    "data/ai_v1_1_us30.sqlite",
    "data/ai_v1_2_1_eurusd.sqlite",
    "data/ai_v1_2_1_xagusd.sqlite",
    "data/ai_v1_2_1_usoil.sqlite",
    "data/ai_v1_3_btcusdt.sqlite",
    "data/ai_v1_3_ethusdt.sqlite",
    "data/ai_v1_3_solusdt.sqlite",
)
MAX_LEDGER_BYTES = 32 * 1024 * 1024


def nine_ledger_fingerprints(root: Path) -> dict[str, tuple[int, int, str]]:
    """Read-only SHA/metadata; reject sidecars, symlinks, or missing ledgers."""
    if (root / "data").is_symlink():
        raise PublicationHeld("data directory symlink forbidden")
    result: dict[str, tuple[int, int, str]] = {}
    for relative in ACTIVE_AI_LEDGER_PATHS:
        path = root / relative
        try:
            info = path.lstat()
            if (not stat.S_ISREG(info.st_mode) or path.is_symlink()
                or not 0 < info.st_size <= MAX_LEDGER_BYTES):
                raise PublicationHeld("unsafe active AI ledger: " + relative)
            for suffix in ("-wal", "-shm", "-journal"):
                if (root / (relative + suffix)).exists():
                    raise PublicationHeld("active AI SQLite sidecar: " + relative)
            digest = hashlib.sha256()
            with path.open("rb") as source:
                for chunk in iter(lambda: source.read(1024 * 1024), b""):
                    digest.update(chunk)
            after = path.stat()
        except OSError as exc:
            raise PublicationHeld("active AI ledger read unavailable: " + relative) from exc
        if (after.st_size != info.st_size
            or after.st_mtime_ns != info.st_mtime_ns):
            raise PublicationHeld("active AI ledger changed during hashing")
        result[relative] = (info.st_size, info.st_mtime_ns, digest.hexdigest())
    if len(result) != 9:
        raise PublicationHeld("AI ledger count changed")
    return result


def build_three_program_observation(root: Path) -> dict:
    """Use only the nine-ledger builders proven in the real VPS preview."""
    # The product adapter's approved Git blob lives in the review source
    # checkout, NOT in production main (its PR is intentionally unmerged).
    _verify_crypto_validation_adapter_source(ROOT)
    base = build_core_expansion_programs(root)
    crypto = build_crypto_public_validation_program(
        root, include_scheduler=True, verify_upstream=True,
    )
    programs = base + [crypto]
    if (len(programs) != 3
        or any(not isinstance(p, dict) for p in programs)
        or {p.get("program_id") for p in programs} != PROGRAMS
        or {p.get("program_id") for p in base} != BASE_PROGRAMS):
        raise PublicationHeld("incomplete three-program research cohort")

    for p in programs:
        health = p.get("health")
        if (not isinstance(health, dict)
            or health.get("healthy") is not True
            or health.get("broker_execution_disabled") is not True
            or p.get("mode") != "SHADOW_ONLY"
            or p.get("signal_details_included") is not False):
            raise PublicationHeld("unqualified research program")
    if (crypto.get("public_signal_exposure") is not False
        or any(p.get("public_signal_exposure") is not False
               for p in base if p.get("program_id") == "market-expansion-1")):
        raise PublicationHeld("research signals must remain private")
    if ({m.get("source_symbol") for m in crypto.get("markets", [])}
        != set(MARKETS)
        or {g.get("gate_id") for g in crypto.get("gates", [])}
        != {"C1", "C2", "C3"}):
        raise PublicationHeld("wrong crypto markets or review gates")

    _reject_private_crypto(crypto)
    _validate_validation_programs({
        "validation_programs_schema_version": 1,
        "validation_programs": programs,
    })
    # Preserve the historical AI-v1.2.1 mismatch; qualify only the
    # independently proven exact registry addition, without rewriting evidence.
    _verify_current_expansion_claim(root, {"validation_programs": programs})

    now = datetime.now(timezone.utc)
    return {
        "generated_at_utc": now.isoformat(),
        "validation_programs": programs,
    }


def produce_one_seal(root: Path) -> str:
    if os.environ.get(ENABLE) != "1":
        raise PublicationHeld("no approved crypto seal capture activation")
    if not root.is_dir() or (root / "data").is_symlink():
        raise PublicationHeld("invalid live root")
    output = root / "data" / SEAL_NAME
    if output.exists() or output.is_symlink():
        raise PublicationHeld("crypto seal exists; refusing overwrite")
    if not output.parent.is_dir():
        raise PublicationHeld("expected live data directory absent")

    begin = datetime.now(timezone.utc)
    before = probe_k5()
    validate_k5_finished(before, begin)
    nine_before = nine_ledger_fingerprints(root)
    crypto_before = crypto_fingerprints(root)

    observation = build_three_program_observation(root)

    after = probe_k5()
    checked = datetime.now(timezone.utc)
    ensure_stable_k5(before, after, checked)
    if crypto_fingerprints(root) != crypto_before:
        raise PublicationHeld("crypto ledger chain changed during capture")
    if nine_ledger_fingerprints(root) != nine_before:
        raise PublicationHeld("active AI ledger changed during capture")
    if (checked - begin).total_seconds() > 120:
        raise PublicationHeld("observation exceeded 120-second budget")

    # The as-of timestamp represents the END of verified source observation,
    # not a false claim of atomic simultaneity between nine SQLite files.
    observation["generated_at_utc"] = checked.isoformat()
    raw = seal_from_verified_snapshot(observation, checked)
    asof = asof_program_from_seal_bytes(raw, checked + timedelta(seconds=1))
    _reject_private_crypto(asof)
    _validate_validation_programs({
        "validation_programs_schema_version": 1,
        "validation_programs": (
            observation["validation_programs"][:2] + [asof]
        ),
    })
    if (asof["status"] != "delayed"
        or "DELAYED" not in asof["title"]
        or asof["public_signal_exposure"] is not False
        or asof["health"]["healthy"] is not False):
        raise PublicationHeld("historical safe-display contract invalid")

    # Exclusive single-purpose local output only AFTER all validation passes.
    # Do not create this file merely because the engineering PR exists.
    with output.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    digest = hashlib.sha256(raw).hexdigest()
    if output.read_bytes() != raw:
        raise PublicationHeld("seal bytes changed after creation")
    print(json.dumps({
        "asof_seal": "CREATED_NOT_PUBLISHED",
        "sha256": digest,
        "bytes": len(raw),
        "observed_at_utc": checked.isoformat(),
        "markets": sorted(MARKETS),
        "crypto_public_signal_exposure": False,
        "broker_execution_disabled": True,
        "cloud_upload": False,
        "production_restore": False,
    }, sort_keys=True))
    return digest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", required=True)
    parser.add_argument("--live-root", type=Path, required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRM:
        raise SystemExit("exact owner activation phrase required")
    produce_one_seal(args.live_root.resolve())


if __name__ == "__main__":
    main()
