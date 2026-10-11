#!/usr/bin/env python3
"""One-shot EXP031 validation helper; READ-ONLY. Never POST, mutate or write."""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

GIT_MAIN = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
SEAL_SHA = "f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4"
STAMP = "2026-10-11T12:07:21.257601+00:00"
PROGRAMS = {"core-ai-shadow", "market-expansion-1", "crypto-expansion-1"}
CRYPTO = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
GATES = {"C1", "C2", "C3"}
SITE = "https://vowsig.com"


def demand(ok: bool, msg: str) -> None:
    if not ok:
        raise RuntimeError("STOP: " + msg)


def public_get(url: str):
    request = urllib.request.Request(
        url, headers={"Cache-Control": "no-cache", "Pragma": "no-cache",
                      "User-Agent": "VowSig-EXP031-Release-Verification/1.0"})
    with urllib.request.urlopen(request, timeout=20) as response:
        demand(response.status == 200, "public GET returned non-200")
        return json.load(response)


def validate_crypto(p: dict) -> None:
    demand(p.get("program_id") == "crypto-expansion-1", "wrong crypto program ID")
    demand(p.get("status") == "delayed", "crypto not explicitly DELAYED")
    demand("DELAYED" in p.get("title", "") and STAMP in p.get("title", ""),
           "historical UTC not prominent in crypto title")
    demand(p.get("public_signal_exposure") is False
           and p.get("signal_details_included") is False,
           "actionable crypto exposure is enabled")
    h = p.get("health", {})
    demand(h.get("broker_execution_disabled") is True and h.get("healthy") is False
           and h.get("scheduler_healthy") is False, "wrong delayed health boundary")
    markets, gates = p.get("markets", []), p.get("gates", [])
    demand(len(markets) == 3 and {x.get("source_symbol") for x in markets} == CRYPTO,
           "wrong public crypto symbol cohort")
    demand(len(gates) == 3 and {g.get("gate_id") for g in gates} == GATES
           and all(g.get("eligible") is False for g in gates),
           "C1/C2/C3 are not all ineligible")


def validate_snapshot(payload: dict) -> None:
    from guarded_product_publish_v0_1 import validate_candidate
    from trading_signal_intelligence.product.cloud_app import _validate_snapshot
    from push_public_snapshot import _validate_snapshot_for_push
    now = datetime.now(timezone.utc)
    _validate_snapshot(payload)
    _validate_snapshot_for_push(payload)
    validate_candidate(payload, now)
    p = payload.get("validation_programs", [])
    demand(len(p) == 3 and {x.get("program_id") for x in p} == PROGRAMS,
           "three-program history release incomplete")
    validate_crypto(next(x for x in p if x["program_id"] == "crypto-expansion-1"))
    m = payload.get("markets", [])
    demand(len(m) == 9 and len({x.get("source_symbol") for x in m}) == 9,
           "nine existing market statuses not preserved")


def preflight(root: Path):
    from dotenv import dotenv_values
    from push_public_snapshot import _validated_endpoint
    from guarded_product_publish_v0_1 import (
        CRYPTO_WRITER_INTERLOCK_READY, _verify_current_expansion_claim
    )
    from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
        load_pinned_asof_program,
    )
    from export_guarded_core_expansion_v0_2 import build_core_expansion_snapshot
    demand(CRYPTO_WRITER_INTERLOCK_READY is False,
           "live crypto writer interlock unexpectedly changed")

    dot = dotenv_values(root / ".env") if (root / ".env").is_file() else {}
    url = os.getenv("TRADINGTOP_INGEST_URL") or dot.get("TRADINGTOP_INGEST_URL")
    token = os.getenv("TRADINGTOP_INGEST_TOKEN") or dot.get("TRADINGTOP_INGEST_TOKEN")
    demand(bool(url) and bool(token), "production ingest credentials are not available")
    target = _validated_endpoint(str(url))
    demand(urlparse(target).hostname == "vowsig.com",
           "ingest target is not the authorized VowSig domain")
    print("INGEST_TOKEN_PRESENT=TRUE")
    print("INGEST_TARGET_VOWSIG=PASS")

    original_markets = public_get(SITE + "/api/markets")
    original_programs = public_get(SITE + "/api/validation/programs")
    demand(isinstance(original_markets, list) and len(original_markets) == 9,
           "hosted before-state has not got nine markets")
    before_ids = {p.get("program_id") for p in original_programs.get("programs", [])}
    demand(original_programs.get("snapshot_pending") is False and
           before_ids == {"core-ai-shadow", "market-expansion-1"},
           "hosted crypto card already present or old programs changed")

    payload = build_core_expansion_snapshot(root)
    historical = load_pinned_asof_program(root, datetime.now(timezone.utc), SEAL_SHA)
    payload["validation_programs"].append(historical)
    validate_snapshot(payload)
    _verify_current_expansion_claim(root, payload)
    demand({x["source_symbol"] for x in payload["markets"]} ==
           {x["source_symbol"] for x in original_markets},
           "existing market cohort changed in local candidate")
    demand(all(next(y for y in payload["markets"]
                    if y["source_symbol"] == x["source_symbol"])["product_status"]
               == x["product_status"] for x in original_markets),
           "existing market product status changed")
    print("READONLY_COMPOSITE_PREVIEW=PASS")
    print("EXPECTED_PROGRAM_IDS=core-ai-shadow,crypto-expansion-1,market-expansion-1")
    print("HISTORICAL_UTC=" + STAMP)
    print("C1_C2_C3_INELIGIBLE=PASS")
    print("MARKET_COUNT=9")
    print("BROKER_EXECUTION_DISABLED=TRUE")
    print("ONE_POST_NOT_YET_STARTED=TRUE")


def postflight(root: Path, original_archive_names: list[str]):
    from guarded_product_publish_v0_1 import HISTORY_NAME
    folder = root / "data" / HISTORY_NAME
    files = sorted(p for p in folder.iterdir() if p.is_file())
    added = [p for p in files if p.name not in original_archive_names]
    demand(len(added) == 2, "one archive and one receipt were not created")
    archive = next((p for p in added if p.suffix == ".json"), None)
    receipt = next((p for p in added if p.name.endswith(".json.accepted")), None)
    demand(archive is not None and receipt is not None and
           receipt.name == archive.name + ".accepted",
           "guarded archive/acceptance pair identity mismatch")
    raw = archive.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    rec = json.loads(receipt.read_bytes())
    demand(rec.get("snapshot_sha256") == digest, "accepted receipt SHA mismatch")
    local = (root / "data/public_snapshot.json").read_bytes()
    demand(local == raw, "local accepted public snapshot differs from archive")
    candidate = json.loads(raw)
    validate_snapshot(candidate)

    hosted = public_get(SITE + "/api/validation/programs")
    hosted_markets = public_get(SITE + "/api/markets")
    demand(hosted.get("snapshot_pending") is False
           and hosted.get("generated_at_utc") == candidate.get("generated_at_utc"),
           "hosted generated UTC not equal to locally accepted snapshot")
    expected_programs = candidate["validation_programs"]
    observed_programs = hosted.get("programs", [])
    demand(isinstance(observed_programs, list) and
           {p.get("program_id") for p in observed_programs} == PROGRAMS,
           "public programs still do not show all three lineages")
    expected_by_id = {p["program_id"]: p for p in expected_programs}
    observed_by_id = {p["program_id"]: p for p in observed_programs}
    demand(observed_by_id == expected_by_id, "hosted public programs do not match")
    validate_crypto(observed_by_id["crypto-expansion-1"])
    demand(isinstance(hosted_markets, list) and len(hosted_markets) == 9 and
           {m["source_symbol"] for m in hosted_markets} ==
           {m["source_symbol"] for m in candidate["markets"]},
           "hosted nine market symbols not preserved")
    demand(all(
        next(x for x in candidate["markets"] if x["source_symbol"] == y["source_symbol"])
        ["product_status"] == y["product_status"] for y in hosted_markets
    ), "hosted market statuses not preserved")
    print("ONE_GUARDED_ACCEPTED_RECEIPT=PASS")
    print("LOCAL_ACCEPTED_SNAPSHOT_SHA256=" + digest)
    print("HOSTED_SEMANTIC_PROGRAM_READBACK=PASS")
    print("HOSTED_NINE_MARKETS=PASS")
    print("DELAYED_CRYPTO_HISTORICAL_CARD=PASS")
    print("NO_CURRENT_CRYPTO_SIGNAL_EXPOSURE=PASS")
    print("HOSTED_STORED_BYTE_DIGEST_VERIFIED=FALSE")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("preview", "postflight"))
    parser.add_argument("--root", required=True)
    parser.add_argument("--before-list", default="")
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    sys.path[:0] = [str(root / "scripts"), str(root / "src")]
    if args.mode == "preview":
        preflight(root)
    else:
        names = json.loads(args.before_list)
        demand(isinstance(names, list) and all(isinstance(x, str) for x in names),
               "invalid pre-publication archive inventory")
        postflight(root, names)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        raise SystemExit("EXP031_READONLY_CONTRACT=STOP: " + str(exc)) from None
