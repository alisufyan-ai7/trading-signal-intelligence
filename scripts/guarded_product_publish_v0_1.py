"""Opt-in, fail-closed product publisher; not installed on Task Scheduler."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
K5_TASK = "VowSig AI-v1.3 Crypto Shadow Scan"
MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
PROGRAMS = {"core-ai-shadow", "market-expansion-1", "crypto-expansion-1"}
MAX_K5_AGE_SECONDS = 900
MAX_SNAPSHOT_AGE_SECONDS = 120
CONFIRM = "RUN-GUARDED-PUBLISH-V0.1"


class PublicationHeld(RuntimeError):
    """Fail closed without sending any snapshot."""


def aware(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError) as exc:
        raise PublicationHeld("invalid timestamp") from exc
    if result.tzinfo is None or result.utcoffset() is None:
        raise PublicationHeld("timestamp has no timezone")
    return result.astimezone(timezone.utc)


def validate_k5_finished(task: dict[str, Any], now: datetime) -> str:
    if now.tzinfo is None or now.utcoffset() is None:
        raise PublicationHeld("current time has no timezone")
    if (task.get("TaskName") != K5_TASK or task.get("State") != "Ready"
        or type(task.get("LastTaskResult")) is not int
        or task["LastTaskResult"] != 0):
        raise PublicationHeld("K5 is running, failed, or missing")
    start = aware(task.get("LastRunTime"))
    upcoming = aware(task.get("NextRunTime"))
    age = (now.astimezone(timezone.utc) - start).total_seconds()
    if not 0 <= age <= MAX_K5_AGE_SECONDS or upcoming <= now:
        raise PublicationHeld("K5 completion is too old or scheduling is invalid")
    return start.isoformat()


def ensure_stable_k5(before: dict[str, Any], after: dict[str, Any], now: datetime) -> None:
    validate_k5_finished(after, now)
    if any(before.get(k) != after.get(k)
           for k in ("TaskName", "State", "LastTaskResult", "LastRunTime")):
        raise PublicationHeld("K5 changed during export")


def probe_k5() -> dict[str, Any]:
    if os.name != "nt":
        raise PublicationHeld("native Windows Task Scheduler required")
    command = (
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'VowSig AI-v1.3 Crypto Shadow Scan';"
        "$i=Get-ScheduledTaskInfo -TaskName 'VowSig AI-v1.3 Crypto Shadow Scan';"
        "$o=[pscustomobject]@{TaskName=[string]$t.TaskName;State=[string]$t.State;"
        "LastTaskResult=[int64]$i.LastTaskResult;LastRunTime=$i.LastRunTime.ToString('o');"
        "NextRunTime=$i.NextRunTime.ToString('o')};$o|ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            check=True, capture_output=True, text=True, timeout=20,
        )
        task = json.loads(result.stdout)
        if not isinstance(task, dict):
            raise ValueError("invalid task object")
        return task
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise PublicationHeld("scheduler probe unavailable") from exc


def crypto_fingerprints(root: Path) -> dict[str, str]:
    from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import DATABASE_PATHS
    from trading_signal_intelligence.ai_v1.observability import read_records_read_only

    if set(DATABASE_PATHS) != set(MARKETS):
        raise PublicationHeld("crypto ledger cohort changed")
    result: dict[str, str] = {}
    for symbol in MARKETS:
        records = read_records_read_only(root / DATABASE_PATHS[symbol])
        if not records:
            raise PublicationHeld("missing crypto ledger history")
        digest = hashlib.sha256()
        for row in records:
            digest.update(f"{row['sequence']}:{row['record_hash']}\n".encode("ascii"))
        result[symbol] = digest.hexdigest()
    return result


def validate_candidate(payload: dict[str, Any], now: datetime) -> None:
    from trading_signal_intelligence.product.cloud_app import _validate_snapshot
    from push_public_snapshot import _validate_snapshot_for_push

    if not isinstance(payload, dict):
        raise PublicationHeld("snapshot is not an object")
    age = (now.astimezone(timezone.utc) - aware(payload.get("generated_at_utc"))).total_seconds()
    if not 0 <= age <= MAX_SNAPSHOT_AGE_SECONDS:
        raise PublicationHeld("snapshot is stale or future-dated")
    programs = payload.get("validation_programs")
    if not isinstance(programs, list) or len(programs) != 3:
        raise PublicationHeld("expected precisely three programs")
    if not all(isinstance(p, dict) for p in programs):
        raise PublicationHeld("invalid public program")
    by_id = {p.get("program_id"): p for p in programs}
    if len(by_id) != 3 or set(by_id) != PROGRAMS:
        raise PublicationHeld("validation lineage mismatch")
    # Independent core/expansion health is required; no false healthy appearance.
    for program_id in PROGRAMS:
        state = by_id[program_id].get("health")
        if not isinstance(state, dict) or state.get("healthy") is not True:
            raise PublicationHeld("validation lineage unhealthy: " + program_id)
    crypto = by_id["crypto-expansion-1"]
    if (crypto.get("runtime_version") != "AI-v1.3"
        or crypto.get("mode") != "SHADOW_ONLY"
        or crypto.get("public_signal_exposure") is not False
        or crypto.get("signal_details_included") is not False):
        raise PublicationHeld("crypto public-signal safety boundary failed")
    h = crypto.get("health")
    if not isinstance(h, dict) or any(h.get(k) is not True for k in (
        "healthy", "ledgers_valid", "scheduler_healthy", "broker_execution_disabled"
    )):
        raise PublicationHeld("crypto health is incomplete")
    markets, gates = crypto.get("markets"), crypto.get("gates")
    if (not isinstance(markets, list) or len(markets) != 3
        or not all(isinstance(m, dict) for m in markets)
        or {m.get("source_symbol") for m in markets} != set(MARKETS)
        or not isinstance(gates, list) or len(gates) != 3
        or not all(isinstance(g, dict) for g in gates)
        or {g.get("gate_id") for g in gates} != {"C1", "C2", "C3"}):
        raise PublicationHeld("crypto market or gate cohort is incomplete")
    if any(m.get("ledger_valid") is not True
           or m.get("activation_anchor_match") is not True for m in markets):
        raise PublicationHeld("crypto market ledger verification missing")
    forbidden = {"recent_decisions", "shadow_signals", "signal_records", "alerts",
                 "entry", "entry_price", "stop_loss", "take_profit", "provider_payload",
                 "raw_candles", "feature_snapshot"}
    if forbidden.intersection(crypto):
        raise PublicationHeld("private crypto details present")
    try:
        _validate_snapshot_for_push(payload)
        _validate_snapshot(payload)
    except Exception as exc:
        raise PublicationHeld("cloud or push safety validation rejected") from exc


def run_checked(argv: list[str], root: Path, *, timeout: int) -> None:
    try:
        subprocess.run(argv, cwd=root, check=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PublicationHeld("child command failed or timed out") from exc


def publish_locked(root: Path) -> None:
    data = root / "data"
    now = datetime.now(timezone.utc)
    before = probe_k5()
    validate_k5_finished(before, now)
    ledger_before = crypto_fingerprints(root)

    # NEVER read the previous public_snapshot.json as a fallback.
    with tempfile.TemporaryDirectory(prefix="guarded-publish-", dir=data) as tmp:
        staged = Path(tmp) / "fresh.json"
        run_checked(
            [sys.executable, "-B", str(root / "scripts/export_public_snapshot.py"),
             "--output", str(staged)], root, timeout=120,
        )
        try:
            raw = staged.read_bytes()
            payload = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise PublicationHeld("fresh export was not readable") from exc
        validate_candidate(payload, datetime.now(timezone.utc))

        # Notifications are invoked independently in the future .cmd action;
        # K5 publication hold must never suppress core/expansion alerts.
        after = probe_k5()
        ensure_stable_k5(before, after, datetime.now(timezone.utc))
        if crypto_fingerprints(root) != ledger_before:
            raise PublicationHeld("crypto ledger changed during export")
        if hashlib.sha256(raw).digest() != hashlib.sha256(staged.read_bytes()).digest():
            raise PublicationHeld("staged bytes changed after verification")
        validate_candidate(payload, datetime.now(timezone.utc))

        # Exactly one HTTP snapshot push of this freshly verified staging path.
        run_checked(
            [sys.executable, "-B", str(root / "scripts/push_public_snapshot.py"),
             "--snapshot", str(staged)], root, timeout=60,
        )
        # Replace the local snapshot atomically only AFTER successful cloud acceptance.
        os.replace(staged, data / "public_snapshot.json")
        print(json.dumps({
            "guarded_publish": "PASS", "k5_last_run": after["LastRunTime"],
            "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
            "validation_programs": sorted(PROGRAMS),
            "crypto_public_signal_exposure": False,
            "broker_execution": False,
        }))


def run_guarded(root: Path) -> None:
    # Explicitly inactive unless *separately* activated on native Windows.
    if os.name != "nt" or os.environ.get("VOWSIG_GUARDED_PUBLISH_ENABLED") != "1":
        raise PublicationHeld("no native Windows owner-approved cutover activation")
    import msvcrt

    with (root / "data/.guarded_product_publisher_v0_1.lock").open("a+b") as handle:
        handle.seek(0)
        try:
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            raise PublicationHeld("publisher is already running") from exc
        try:
            publish_locked(root)
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", required=True)
    args = parser.parse_args()
    if args.confirm != CONFIRM:
        raise SystemExit("refusing publisher without exact confirmation")
    try:
        run_guarded(ROOT)
    except PublicationHeld as exc:
        raise SystemExit(f"GUARDED_PUBLISH=HELD: {exc}") from None


if __name__ == "__main__":
    main()
