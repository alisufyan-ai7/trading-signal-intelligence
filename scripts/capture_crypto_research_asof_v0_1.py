"""Prepare ONE as-of crypto *aggregate-only* seal, entirely locally.

DORMANT review code. Requires future separate owner approval to read live
crypto ledgers. No crypto scan, Binance/OpenAI, Task Scheduler mutation, cloud
request or publication. Never run on VPS just to test this PR.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from guarded_product_publish_v0_1 import (
    BASE_PROGRAMS, PROGRAMS, MARKETS, ROOT,
    PublicationHeld, _verify_current_expansion_claim,
    crypto_fingerprints, ensure_stable_k5, probe_k5,
    validate_candidate, validate_k5_finished,
)
from export_guarded_full_v0_1 import build_guarded_full_snapshot
from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
    SEAL_NAME, asof_program_from_seal_bytes, seal_from_verified_snapshot,
)

CONFIRM = "CAPTURE-ONE-CRYPTO-ASOF-RESEARCH-SEAL"
ENABLE = "VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED"


def produce_one_seal(root: Path) -> str:
    if os.environ.get(ENABLE) != "1":
        raise PublicationHeld("no approved crypto seal capture activation")
    output = root / "data" / SEAL_NAME
    if output.exists() or output.is_symlink():
        raise PublicationHeld("crypto seal exists; refusing overwrite")

    before = probe_k5()
    validate_k5_finished(before, datetime.now(timezone.utc))
    ledger_before = crypto_fingerprints(root)
    payload = build_guarded_full_snapshot(root)
    validate_candidate(payload, datetime.now(timezone.utc))
    _verify_current_expansion_claim(root, payload)

    after = probe_k5()
    ensure_stable_k5(before, after, datetime.now(timezone.utc))
    if crypto_fingerprints(root) != ledger_before:
        raise PublicationHeld("crypto source changed during as-of capture")
    if {p["program_id"] for p in payload["validation_programs"]} != PROGRAMS:
        raise PublicationHeld("not all three safe programs present")

    raw = seal_from_verified_snapshot(payload, datetime.now(timezone.utc))
    # Validate the exact future title/health/schema shape with both existing
    # public validators BEFORE any file is created.
    simulated = dict(payload)
    simulated["generated_at_utc"] = datetime.now(timezone.utc).isoformat()
    asof = asof_program_from_seal_bytes(raw, datetime.now(timezone.utc))
    simulated["validation_programs"] = [
        p for p in payload["validation_programs"]
        if p["program_id"] in BASE_PROGRAMS
    ] + [asof]
    validate_candidate(simulated, datetime.now(timezone.utc))

    # No automatic creation of any new destination, no overwrite/retry.
    if not output.parent.is_dir():
        raise PublicationHeld("expected production data directory absent")
    with output.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    digest = hashlib.sha256(raw).hexdigest()
    if output.read_bytes() != raw:
        raise PublicationHeld("seal changed after creation; preserve evidence")
    print(json.dumps({
        "asof_seal": "CREATED_NOT_PUBLISHED",
        "sha256": digest,
        "bytes": len(raw),
        "observed_at_utc": payload["generated_at_utc"],
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
    args = parser.parse_args()
    if args.confirm != CONFIRM:
        raise SystemExit("exact owner activation phrase required")
    produce_one_seal(ROOT)


if __name__ == "__main__":
    main()
