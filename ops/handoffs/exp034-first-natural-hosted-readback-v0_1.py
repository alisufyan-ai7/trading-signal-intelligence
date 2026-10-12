#!/usr/bin/env python3
"""EXP-034 post-activation natural guarded publisher semantic verifier; GET/read-only.

NO subprocess task starts, NO SQLite/crypto private-source calls, NO HTTP POST,
NO scheduler edits and NO sensitive source output. Safe to rerun after a
naturally scheduled Product Publish cycle; an early run reports PENDING.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence")
MAIN = "b900796dd7075a31dd01c89639c9461ef9ee3fb1"
ACTIVATION_MANIFEST = Path(r"C:\ProgramData\VowSig-EXP034-ActivationRollback-20261012\manifest.json")
SEAL_SHA = "f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4"
SEALED_AT = "2026-10-11T12:07:21.257601+00:00"
PROGRAMS = {"core-ai-shadow", "market-expansion-1", "crypto-expansion-1"}
MARKETS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
GATES = {"C1", "C2", "C3"}
PROHIBITED = frozenset((
    "entry", "entry_price", "stop", "stop_loss", "target", "take_profit",
    "direction", "confidence", "rationale", "provider_payload", "raw_candles",
    "recent_decisions", "shadow_signals", "signal_records", "raw_market_data",
    "raw_feature_snapshots", "provider_request_metadata",
))


class Held(RuntimeError):
    pass


def demand(condition: bool, reason: str) -> None:
    if not condition:
        raise Held(reason)


def utc(value: str) -> datetime:
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    demand(dt.tzinfo is not None and dt.utcoffset() is not None, "invalid observation timestamp")
    return dt.astimezone(timezone.utc)


def private_fields_absent(value: object) -> bool:
    if isinstance(value, dict):
        return not (PROHIBITED & value.keys()) and all(private_fields_absent(v) for v in value.values())
    if isinstance(value, list):
        return all(private_fields_absent(v) for v in value)
    return True


def task() -> dict:
    cmd = (
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'TradingTop Product Publish' -TaskPath '\\';"
        "$i=Get-ScheduledTaskInfo -TaskName 'TradingTop Product Publish' -TaskPath '\\';"
        "$o=[pscustomobject]@{Name=$t.TaskName;Path=$t.TaskPath;"
        "State=[string]$t.State;Action=[string]$t.Actions[0].Execute;"
        "Arguments=[string]$t.Actions[0].Arguments;"
        "LastResult=[int64]$i.LastTaskResult;"
        "LastRunUTC=$i.LastRunTime.ToUniversalTime().ToString('o')};"
        "$o|ConvertTo-Json -Compress"
    )
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", cmd],
        capture_output=True, text=True, timeout=20, check=True,
    )
    result = json.loads(p.stdout)
    demand(result.get("Name") == "TradingTop Product Publish" and result.get("Path") == "\\",
           "existing publisher task identity drifted")
    demand(result.get("State") == "Ready" and result.get("LastResult") == 0,
           "product publisher not Ready/last-result-zero")
    demand(result.get("Action", "").lower().endswith("powershell.exe")
           and "VowSig-EXP031-HourlyPublisher" in result.get("Arguments", "")
           and "current-aggregate-task-runner.ps1" in result.get("Arguments", ""),
           "existing publisher not using reviewed EXP034 successor")
    return result


def public_get(path: str):
    req = urllib.request.Request(
        "https://vowsig.com" + path,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"}, method="GET"
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        demand(response.status == 200, "hosted semantic GET unsuccessful")
        return json.load(response)


def verify() -> None:
    head = subprocess.run(
        ["git", "-C", str(ROOT), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=15, check=True,
    ).stdout.strip()
    demand(head == MAIN, "live source commit changed")
    demand(ACTIVATION_MANIFEST.is_file(), "EXP034 activation rollback manifest missing")
    stage_time = datetime.fromtimestamp(ACTIVATION_MANIFEST.stat().st_mtime, tz=timezone.utc)
    job = task()
    natural_at = utc(job["LastRunUTC"])
    if natural_at <= stage_time:
        print("EXP034_POST_ACTIVATION_NATURAL_CYCLE=PENDING")
        print("EXP034_NO_MANUAL_RUN_OR_POST=TRUE")
        return
    print("EXP034_POST_ACTIVATION_TASK=PASS")
    print("EXP034_NATURAL_RUN_UTC=" + natural_at.isoformat())

    seal = (ROOT / "data/crypto-research-asof-v0.1.json").read_bytes()
    demand(len(seal) == 3048 and hashlib.sha256(seal).hexdigest() == SEAL_SHA,
           "original historical DELAYED seal changed")
    raw = (ROOT / "data/public_snapshot.json").read_bytes()
    snapshot_hash = hashlib.sha256(raw).hexdigest()
    local = json.loads(raw)
    published_at = utc(local["generated_at_utc"])
    demand(published_at >= natural_at and published_at <= datetime.now(timezone.utc),
           "no newly generated post-activation local snapshot")

    history = ROOT / "data/guarded-snapshot-history-v0.2"
    candidates = []
    for receipt_file in history.glob("*.json.accepted"):
        receipt = json.loads(receipt_file.read_text(encoding="utf-8"))
        if receipt.get("snapshot_sha256") == snapshot_hash:
            candidates.append(receipt_file)
    demand(len(candidates) == 1, "no unique accepted local publisher receipt")
    archive = Path(str(candidates[0])[:-len(".accepted")])
    demand(archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest() == snapshot_hash,
           "accepted archive differs from published sanitized snapshot")

    hosted = public_get("/api/validation/programs")
    hosted_markets = public_get("/api/markets")
    remote_programs = hosted.get("programs")
    local_programs = local.get("validation_programs")
    demand(hosted.get("snapshot_pending") is False
           and hosted.get("generated_at_utc") == local.get("generated_at_utc"),
           "hosted generation differs from accepted local publication")
    demand(isinstance(remote_programs, list) and len(remote_programs) == 3
           and isinstance(local_programs, list) and remote_programs == local_programs
           and {p.get("program_id") for p in remote_programs} == PROGRAMS,
           "hosted validation programs differ from accepted local archive")
    for p in remote_programs:
        if p["program_id"] != "crypto-expansion-1":
            demand(p.get("health", {}).get("healthy") is True,
                   "independent core or expansion unhealthy")
    demand(isinstance(hosted_markets, list) and len(hosted_markets) == 9
           and len(local.get("markets", [])) == 9,
           "nine public markets missing")
    expected_market_status = {m["source_symbol"]: m["product_status"] for m in local["markets"]}
    demand({m.get("source_symbol") for m in hosted_markets} == set(expected_market_status)
           and all(m.get("product_status") == expected_market_status[m["source_symbol"]]
                   for m in hosted_markets), "nine public market statuses differ")

    crypto = next(p for p in remote_programs if p["program_id"] == "crypto-expansion-1")
    demand(crypto.get("public_signal_exposure") is False
           and crypto.get("signal_details_included") is False
           and crypto.get("health", {}).get("broker_execution_disabled") is True
           and private_fields_absent(crypto),
           "unsafe public crypto detail or broker exposure")
    demand({m.get("source_symbol") for m in crypto.get("markets", [])} == MARKETS
           and {g.get("gate_id") for g in crypto.get("gates", [])} == GATES,
           "frozen crypto cohort or gates differ")

    status = crypto.get("status")
    if status == "collecting":
        demand(crypto.get("health", {}).get("healthy") is True
               and crypto.get("data_freshness") != "delayed",
               "CURRENT crypto not healthy or still delayed")
        print("EXP034_HOSTED_CRYPTO_AGGREGATES=CURRENT_PASS")
    elif status == "delayed":
        demand("DELAYED" in crypto.get("title", "") and SEALED_AT in crypto.get("title", "")
               and crypto.get("health", {}).get("healthy") is False
               and crypto.get("health", {}).get("scheduler_healthy") is False,
               "historical DELAYED fallback missing provenance")
        print("EXP034_HOSTED_CRYPTO_AGGREGATES=DELAYED_FALLBACK_PASS")
    else:
        raise Held("no admissible CURRENT or DELAYED crypto state")

    print("EXP034_HOSTED_CORE_EXPANSION_AND_NINE_MARKETS=PASS")
    print("EXP034_LOCAL_ACCEPTED_ARCHIVE_AND_HOSTED_SEMANTICS=PASS")
    print("EXP034_LOCAL_SANITIZED_SNAPSHOT_SHA256=" + snapshot_hash)
    print("EXP034_PUBLIC_CRYPTO_ACTIONABLE_EXPOSURE=FALSE")
    print("EXP034_BROKER_EXECUTION_DISABLED=TRUE")
    print("EXP034_HOSTED_STORED_BYTE_DIGEST_VERIFIED=FALSE")
    print("EXP034_FIRST_POST_ACTIVATION_NATURAL_READBACK=PASS")


if __name__ == "__main__":
    try:
        verify()
    except Exception:
        # Do not print potentially sensitive local paths, XML, or source data.
        raise SystemExit("EXP034_FIRST_POST_ACTIVATION_NATURAL_READBACK=HELD_REVIEW") from None
