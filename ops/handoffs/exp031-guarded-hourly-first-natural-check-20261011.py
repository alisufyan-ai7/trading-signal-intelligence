#!/usr/bin/env python3
"""EXP-031 first natural hourly guarded-publisher verification. READ-ONLY."""
from __future__ import annotations
import hashlib
import json
import subprocess
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(r"C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence")
STAMP = datetime.fromisoformat("2026-10-11T17:11:45.559855+00:00")
CRYPTO_AT = "2026-10-11T12:07:21.257601+00:00"
PROGRAM_IDS = {"core-ai-shadow", "market-expansion-1", "crypto-expansion-1"}
CRYPTO_MARKETS = {"BTCUSDT", "ETHUSDT", "SOLUSDT"}
GATES = {"C1", "C2", "C3"}
SEAL_SHA = "f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4"


def require(yes: bool, message: str) -> None:
    if not yes:
        raise RuntimeError("STOP: " + message)


def utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(result.tzinfo is not None, "timestamp has no UTC offset")
    return result.astimezone(timezone.utc)


def public_get(route: str):
    req = urllib.request.Request(
        "https://vowsig.com" + route,
        headers={"Cache-Control": "no-cache", "Pragma": "no-cache"},
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=20) as response:
        require(response.status == 200, "website GET was not HTTP 200")
        return json.load(response)


def task_info():
    command = (
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'TradingTop Product Publish';"
        "$i=Get-ScheduledTaskInfo -TaskName 'TradingTop Product Publish';"
        "$o=[pscustomobject]@{Name=$t.TaskName;State=[string]$t.State;"
        "Action=$t.Actions[0].Execute;Arguments=$t.Actions[0].Arguments;"
        "TaskPath=$t.TaskPath;LastResult=$i.LastTaskResult;"
        "LastRunTime=$i.LastRunTime.ToUniversalTime().ToString('o')};"
        "$o|ConvertTo-Json -Compress"
    )
    p = subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
        text=True, capture_output=True, check=True, timeout=20,
    )
    obj = json.loads(p.stdout)
    require(obj["State"] == "Ready" and obj["LastResult"] == 0,
            "guarded hourly task not Ready with natural success")
    require(obj["Name"] == "TradingTop Product Publish" and obj["TaskPath"] == "\\",
            "Task Scheduler identity changed")
    require("powershell.exe" in obj["Action"].lower()
            and "VowSig-EXP031-HourlyPublisher" in obj["Arguments"],
            "scheduled task is not guarded process-scoped successor")
    require(utc(obj["LastRunTime"]) > STAMP,
            "no successful natural hourly task since one-shot publication")
    print("GUARDED_SAME_TASK_NATURAL_RUN=PASS")
    print("NATURAL_LAST_RUN_UTC=" + utc(obj["LastRunTime"]).isoformat())


def verify():
    task_info()
    seal = ROOT / "data/crypto-research-asof-v0.1.json"
    data = seal.read_bytes()
    require(len(data) == 3048 and hashlib.sha256(data).hexdigest() == SEAL_SHA,
            "pinned historical seal differs from approved bytes")
    raw = (ROOT / "data/public_snapshot.json").read_bytes()
    h = hashlib.sha256(raw).hexdigest()
    local = json.loads(raw)
    require(utc(local["generated_at_utc"]) > STAMP,
            "local snapshot was not regenerated after previous one-shot")
    paths = list((ROOT / "data/guarded-snapshot-history-v0.2").glob("*.json.accepted"))
    receipts = []
    for p in paths:
        receipt = json.loads(p.read_bytes())
        if receipt.get("snapshot_sha256") == h:
            receipts.append(p)
    require(len(receipts) == 1, "no unique accepted receipt for latest local snapshot")
    archive = Path(str(receipts[0])[:-len(".accepted")])
    require(archive.read_bytes() == raw, "guarded accepted snapshot archive differs")

    hosted = public_get("/api/validation/programs")
    market_rows = public_get("/api/markets")
    programs = hosted.get("programs", [])
    require(hosted.get("snapshot_pending") is False and
            hosted.get("generated_at_utc") == local["generated_at_utc"],
            "hosted latest generated_at differs from accepted current snapshot")
    require(isinstance(programs, list) and len(programs) == 3 and
            {p.get("program_id") for p in programs} == PROGRAM_IDS,
            "hosted three-program cohort changed")
    require(programs == local["validation_programs"],
            "hosted programs differ from accepted local snapshot")
    for p in programs:
        if p["program_id"] != "crypto-expansion-1":
            require(p.get("health", {}).get("healthy") is True,
                    "fresh core or expansion program unhealthy")
    crypto = next(p for p in programs if p["program_id"] == "crypto-expansion-1")
    require(crypto.get("status") == "delayed" and
            "DELAYED" in crypto.get("title", "") and CRYPTO_AT in crypto["title"],
            "historical crypto observation incorrectly refreshed or unlabeled")
    require(crypto.get("public_signal_exposure") is False and
            crypto.get("signal_details_included") is False and
            crypto.get("health", {}).get("broker_execution_disabled") is True,
            "crypto exposure or broker execution boundary changed")
    require({m.get("source_symbol") for m in crypto.get("markets", [])} == CRYPTO_MARKETS,
            "crypto symbol cohort changed")
    gates = crypto.get("gates", [])
    require(len(gates) == 3 and {g.get("gate_id") for g in gates} == GATES and
            all(g.get("eligible") is False for g in gates),
            "C1/C2/C3 gate eligibility incorrectly changed")
    require(len(market_rows) == 9 and len(local.get("markets", [])) == 9 and
            {m.get("source_symbol") for m in market_rows} ==
            {m.get("source_symbol") for m in local["markets"]},
            "nine existing public market symbols changed")
    local_status = {m["source_symbol"]: m["product_status"] for m in local["markets"]}
    require(all(m.get("product_status") == local_status[m["source_symbol"]]
                for m in market_rows),
            "nine hosted market statuses differ from accepted snapshot")
    print("HOURLY_HOSTED_PROGRAM_READBACK=PASS")
    print("HOURLY_FRESH_CORE_AND_EXPANSION=PASS")
    print("HOURLY_HISTORICAL_CRYPTO_SAME_UTC=PASS")
    print("HOURLY_NINE_MARKETS=PASS")
    print("HOURLY_LOCAL_ACCEPTANCE_RECEIPT=PASS")
    print("LOCAL_SNAPSHOT_SHA256=" + h)
    print("BROKER_EXECUTION_DISABLED=TRUE")
    print("HOSTED_FULL_STORED_BYTE_SHA_VERIFIED=FALSE")
    print("EXP031_FIRST_NATURAL_GUARDED_HOURLY_CYCLE=PASS")


if __name__ == "__main__":
    try:
        verify()
    except Exception as exc:
        raise SystemExit("EXP031_FIRST_NATURAL_GUARDED_HOURLY_CYCLE=STOP: " + str(exc)) from None
