"""Opt-in, fail-closed product publisher; not installed on Task Scheduler."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import re
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
BASE_PROGRAMS = PROGRAMS - {"crypto-expansion-1"}
HISTORY_NAME = "guarded-snapshot-history-v0.2"
ARCHIVE_RE = re.compile(r"^snapshot-(\d{8}T\d{6}Z)-([0-9a-f]{64})\.json\.accepted$")
MAX_K5_AGE_SECONDS = 900
MAX_SNAPSHOT_AGE_SECONDS = 120
# No K5 writer-side lock is deployed or verified. Keep this LEGACY full-
# exporter/lock code path disabled. A separately opt-in double-read source-
# attested in-memory aggregate-only branch below does not use this interlock.
CRYPTO_WRITER_INTERLOCK_READY = False
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


def require_crypto_writer_interlock(root: Path) -> None:
    """No shared K5 writer/publisher protocol exists in the frozen writer.

    This intentionally cannot return successfully in the current reviewed
    source. A future separate registered version must establish and verify
    that BOTH K5's writer and this publisher enforce the same interlock, and
    that it covers export THROUGH HTTP acceptance. A simple boolean edit is
    insufficient to enable crypto publication.
    """
    raise PublicationHeld("K5 writer-side interlock is not implemented")


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


def _reject_private_crypto(value: Any) -> None:
    """Detect forbidden signal/price/provider fields even when nested."""
    forbidden = {
        "recent_decisions", "shadow_signals", "signal_records", "alerts",
        "entry", "entry_price", "stop", "stop_loss", "target",
        "take_profit", "direction", "confidence", "rationale",
        "provider_payload", "provider_request_metadata", "raw_candles",
        "raw_market_data", "feature_snapshot", "raw_feature_snapshots",
    }
    if isinstance(value, dict):
        if forbidden.intersection(value):
            raise PublicationHeld("private crypto details present")
        for entry in value.values():
            _reject_private_crypto(entry)
    elif isinstance(value, list):
        for entry in value:
            _reject_private_crypto(entry)


def validate_candidate(payload: dict[str, Any], now: datetime) -> None:
    """Validate new core/expansion data and optional crypto: current or delayed."""
    from trading_signal_intelligence.product.cloud_app import _validate_snapshot
    from push_public_snapshot import _validate_snapshot_for_push

    if not isinstance(payload, dict):
        raise PublicationHeld("snapshot is not an object")
    age = (now.astimezone(timezone.utc) - aware(payload.get("generated_at_utc"))).total_seconds()
    if not 0 <= age <= MAX_SNAPSHOT_AGE_SECONDS:
        raise PublicationHeld("snapshot is stale or future-dated")

    programs = payload.get("validation_programs")
    if not isinstance(programs, list) or len(programs) not in (2, 3):
        raise PublicationHeld("expected two or three validation programs")
    if not all(isinstance(p, dict) for p in programs):
        raise PublicationHeld("invalid public program")
    by_id = {p.get("program_id"): p for p in programs}
    if len(by_id) != len(programs) or not BASE_PROGRAMS.issubset(by_id):
        raise PublicationHeld("core/expansion lineage missing or duplicated")
    if set(by_id) not in (BASE_PROGRAMS, PROGRAMS):
        raise PublicationHeld("unexpected validation lineage")

    # Crypto cannot suppress or downgrade these independent fresh programs.
    for program_id in BASE_PROGRAMS:
        state = by_id[program_id].get("health")
        if not isinstance(state, dict) or state.get("healthy") is not True:
            raise PublicationHeld("validation lineage unhealthy: " + program_id)

    # Public schema version 1 has additionalProperties=False.
    # The historic mismatch remains in the original report and the
    # distinct signed-off operational title, not ad hoc JSON fields.
    expansion = by_id["market-expansion-1"]
    if ("registry_compatibility" in expansion
        or any(key not in {
            "healthy", "ledgers_valid", "scheduler_healthy",
            "broker_execution_disabled"
        } for key in expansion.get("health", {}))):
        raise PublicationHeld("expansion public schema must remain frozen")


    if "crypto-expansion-1" in by_id:
        crypto = by_id["crypto-expansion-1"]
        if (crypto.get("runtime_version") != "AI-v1.3"
            or crypto.get("mode") != "SHADOW_ONLY"
            or crypto.get("public_signal_exposure") is not False
            or crypto.get("signal_details_included") is not False):
            raise PublicationHeld("crypto public-signal safety boundary failed")
        _reject_private_crypto(crypto)
        health = crypto.get("health")
        if not isinstance(health, dict) or health.get("broker_execution_disabled") is not True:
            raise PublicationHeld("crypto broker boundary failed")
        delayed = crypto.get("status") == "delayed"
        if delayed:
            # Existing accepted-archive mode has extra provenance keys. New
            # owner-pinned as-of seals instead use ONLY public schema-v1 keys:
            # the exact immutable sample UTC is prominently in the title.
            if crypto.get("data_freshness") == "delayed":
                observed = aware(crypto.get("last_verified_snapshot_at_utc"))
                title = crypto.get("title", "")
                labeled = "DELAYED" in title and observed.isoformat() in title
            elif ("data_freshness" not in crypto
                  and "last_verified_snapshot_at_utc" not in crypto):
                match = re.fullmatch(
                    r"Crypto AI Shadow Validation — DELAYED "
                    r"\(last verified ([^()]+) UTC\)",
                    crypto.get("title", ""),
                )
                if match is None:
                    raise PublicationHeld("delayed crypto time label missing")
                observed = aware(match.group(1))
                labeled = True
            else:
                raise PublicationHeld("unknown delayed crypto provenance")
            if (observed > now.astimezone(timezone.utc)
                or observed >= aware(payload["generated_at_utc"])
                or not labeled
                or health.get("healthy") is not False
                or health.get("scheduler_healthy") is not False):
                raise PublicationHeld("unlabeled or implausible delayed crypto data")
        elif (crypto.get("status") != "collecting"
              or crypto.get("data_freshness") not in (None, "current")
              or any(health.get(key) is not True for key in (
                  "healthy", "ledgers_valid", "scheduler_healthy",
                  "broker_execution_disabled",
              ))):
            raise PublicationHeld("current crypto status is unverified")
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

    try:
        _validate_snapshot_for_push(payload)
        _validate_snapshot(payload)
    except Exception as exc:
        raise PublicationHeld("cloud or push safety validation rejected") from exc


def _archive_paths(root: Path, payload: dict[str, Any], raw: bytes) -> tuple[Path, Path]:
    created = aware(payload["generated_at_utc"]).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha256(raw).hexdigest()
    location = root / "data" / HISTORY_NAME
    return location / f"snapshot-{created}-{digest}.json", location / f"snapshot-{created}-{digest}.json.accepted"


def _write_new_file(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def _pending_archive(root: Path, payload: dict[str, Any], raw: bytes) -> tuple[Path, Path]:
    archive, accepted = _archive_paths(root, payload, raw)
    # Fail closed on any existing name; never overwrite historical evidence.
    if archive.exists() or accepted.exists():
        raise PublicationHeld("historical snapshot archive collision")
    try:
        _write_new_file(archive, raw)
    except OSError as exc:
        raise PublicationHeld("could not preserve snapshot before push") from exc
    if hashlib.sha256(archive.read_bytes()).digest() != hashlib.sha256(raw).digest():
        raise PublicationHeld("archived candidate bytes changed")
    return archive, accepted


def _accept_archive(archive: Path, accepted: Path, raw: bytes) -> None:
    # The acceptance receipt is written only after a successful cloud POST.
    receipt = {
        "schema": 1, "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
        "accepted_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    try:
        _write_new_file(accepted, json.dumps(receipt, sort_keys=True).encode("utf-8"))
    except OSError as exc:
        raise PublicationHeld("cloud accepted, but archive acceptance receipt failed") from exc


def _last_accepted_crypto(root: Path, now: datetime) -> dict[str, Any] | None:
    """Use only append-only accepted, byte-hashed sanitized history, never old public_snapshot."""
    folder = root / "data" / HISTORY_NAME
    if not folder.is_dir():
        return None
    receipts = sorted(folder.glob("snapshot-*.json.accepted"), reverse=True)
    for receipt_path in receipts:
        match = ARCHIVE_RE.fullmatch(receipt_path.name)
        if not match:
            raise PublicationHeld("invalid historical snapshot receipt filename")
        archive = receipt_path.with_suffix("")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            raw = archive.read_bytes()
            cached = json.loads(raw)
        except (OSError, ValueError) as exc:
            raise PublicationHeld("verified snapshot history unreadable") from exc
        if (receipt.get("schema") != 1
            or receipt.get("snapshot_sha256") != match.group(2)
            or hashlib.sha256(raw).hexdigest() != match.group(2)
            or aware(cached.get("generated_at_utc")).strftime("%Y%m%dT%H%M%SZ") != match.group(1)):
            raise PublicationHeld("snapshot history hash or timestamp mismatch")
        try:
            # Interpret the historic snapshot at its actual creation time;
            # DO NOT pretend the cached snapshot was generated now.
            validate_candidate(cached, aware(cached["generated_at_utc"]))
        except PublicationHeld as exc:
            raise PublicationHeld("historic snapshot unsafe") from exc
        by_id = {p["program_id"]: p for p in cached["validation_programs"]}
        crypto = by_id.get("crypto-expansion-1")
        # A verified DELAYED archive may use the original public schema,
        # where staleness is explicit in status/title but data_freshness is
        # deliberately absent. Never treat it as failed CURRENT evidence.
        if crypto is None or crypto.get("status") == "delayed":
            continue
        if (crypto.get("status") != "collecting"
            or crypto.get("health", {}).get("healthy") is not True):
            raise PublicationHeld("historic crypto was not independently verified")
        saved_at = aware(cached["generated_at_utc"])
        if saved_at > now.astimezone(timezone.utc):
            raise PublicationHeld("historic crypto timestamp is future")
        result = copy.deepcopy(crypto)
        result["status"] = "delayed"
        result["data_freshness"] = "delayed"
        result["last_verified_snapshot_at_utc"] = saved_at.isoformat()
        result["title"] = (
            "Crypto AI Shadow Validation — DELAYED "
            f"(last verified {saved_at.isoformat()} UTC)"
        )
        result["health"]["healthy"] = False
        result["health"]["scheduler_healthy"] = False
        return result
    return None


def _try_source_attested_crypto_aggregate(root: Path, now: datetime) -> dict[str, Any] | None:
    """Optional same-process verified aggregate; never reads K5 unless opt-in.

    This does NOT enable individual crypto signals. The exporter already holds
    a fresh two-program base, and the eventual staged/accepted snapshot is
    immutable across HTTP push. Writer lock THROUGH the HTTP post is not
    necessary because no live private record is read after this sealed copy.
    """
    if os.environ.get("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1") != "1":
        return None
    # Fixed stage labels only: never log private exceptions, records or paths.
    hold_stage = "SOURCE_CAPTURE"
    try:
        from trading_signal_intelligence.product.crypto_epoch_source_producer_v0_1 import (
            capture_completed_k5_epoch,
        )
        from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
            public_program_from_completed_epoch,
        )
        from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
            _check_original_program,
        )

        # The producer itself double-reads and verifies all three ledgers,
        # gates, natural K5 task completion, anchored artifacts and source
        # report. Only its sanitized bytes cross this boundary.
        epoch = capture_completed_k5_epoch(root, observed_at_utc=now)
        hold_stage = "EPOCH_VALIDATION"
        envelope = json.loads(epoch)
        cycle = aware(envelope.get("cycle_close_utc"))
        crypto = public_program_from_completed_epoch(
            epoch, expected_sha256=hashlib.sha256(epoch).hexdigest(), now=now
        )
        hold_stage = "PUBLIC_PROGRAM"
        _check_original_program(crypto)

        # Existing fsynced and hash-checked accepted publication archives
        # supply an independent local non-regression reference. This is a
        # same-host accidental-failure model, NOT a tamper-proof trust anchor
        # against an administrator who can rewrite local archives.
        hold_stage = "ACCEPTED_HISTORY"
        previous = _last_accepted_crypto(root, now)
        if previous is None and os.environ.get("VOWSIG_CRYPTO_ASOF_ENABLED") == "1":
            # First prospective current aggregate must not erase history
            # already visible in the original owner-pinned public-only seal.
            from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
                load_pinned_asof_program,
            )
            previous = load_pinned_asof_program(
                root, now, os.environ.get("VOWSIG_CRYPTO_ASOF_SHA256", "")
            )
        hold_stage = "NON_REGRESSION"
        if previous is not None:
            if "last_verified_snapshot_at_utc" in previous:
                earlier = aware(previous["last_verified_snapshot_at_utc"])
            else:
                # Existing as-of schema has no extra timestamp field; its
                # verified original time is intentionally embedded in title.
                match = re.fullmatch(
                    r"Crypto AI Shadow Validation — DELAYED "
                    r"\(last verified ([^()]+) UTC\)",
                    previous.get("title", ""),
                )
                if match is None:
                    raise PublicationHeld("previous crypto sample lacks provenance")
                earlier = aware(match.group(1))
            if cycle <= earlier:
                raise PublicationHeld("crypto completed cycle is not newer")
            old_markets = {
                m["source_symbol"]: m for m in previous["markets"]
            }
            if set(old_markets) != set(MARKETS):
                raise PublicationHeld("accepted crypto cohort changed")
            for market in crypto["markets"]:
                old = old_markets[market["source_symbol"]]
                for metric in (
                    "valid_inferences", "completed_shadow_trades",
                    "signals", "no_trade", "rejected_inferences",
                    "missed_inferences", "errors",
                ):
                    if market[metric] < old[metric]:
                        raise PublicationHeld("crypto source count regression")
        hold_stage = "PUBLIC_PRIVACY"
        _reject_private_crypto(crypto)
        return crypto
    except Exception:
        # Never log exception strings/types, private filenames, rows or tokens.
        # The fixed stage code is enough to locate a safe offline test boundary.
        print("CRYPTO_CURRENT_AGGREGATE=HELD")
        print("CRYPTO_CURRENT_HOLD_STAGE=" + hold_stage)
        return None


def _verify_current_expansion_claim(root: Path, payload: dict[str, Any]) -> None:
    """Reattest declared exceptional public health before sending any HTTP POST."""
    from trading_signal_intelligence.product.expansion_registry_compat_v0_1 import (
        PUBLIC_TITLE,
        prove_expansion_compatibility,
    )

    by_id = {row["program_id"]: row for row in payload["validation_programs"]}
    expansion = by_id["market-expansion-1"]
    if expansion.get("title") != PUBLIC_TITLE:
        return  # ordinary healthy expansion uses the unmodified original builder
    from trading_signal_intelligence.ai_v1.observability_v1_2_1 import (
        build_report_v1_2_1,
    )
    try:
        original = build_report_v1_2_1(
            root, include_scheduler=True, verify_upstream=True,
        )
        prove_expansion_compatibility(root, original)
    except Exception as exc:
        raise PublicationHeld("expansion registry proof changed before upload") from exc


def run_checked(argv: list[str], root: Path, *, timeout: int) -> None:
    try:
        subprocess.run(argv, cwd=root, check=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PublicationHeld("child command failed or timed out") from exc


def _staged_snapshot(staged: Path, now: datetime) -> tuple[bytes, dict[str, Any]]:
    try:
        raw = staged.read_bytes()
        payload = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise PublicationHeld("fresh export was not readable") from exc
    validate_candidate(payload, now)
    return raw, payload


def publish_locked(root: Path) -> None:
    """Publish fresh core/expansion even if the separately gated crypto cycle is incomplete."""
    data = root / "data"
    crypto_ready = False
    if CRYPTO_WRITER_INTERLOCK_READY:
        require_crypto_writer_interlock(root)
        try:
            before = probe_k5()
            validate_k5_finished(before, datetime.now(timezone.utc))
            ledger_before = crypto_fingerprints(root)
            crypto_ready = True
        except Exception:
            crypto_ready = False

    # The legacy full-export current crypto path above remains disabled.
    # The independently verified IN-MEMORY aggregate-only opt-in below
    # snapshots stable source before POST; the HTTP body is then immutable.

    with tempfile.TemporaryDirectory(prefix="guarded-publish-", dir=data) as tmp:
        staging_dir = Path(tmp)
        staged = staging_dir / "fresh.json"
        if crypto_ready:
            try:
                # Existing exporter, but NEVER the old local snapshot as fallback.
                run_checked(
                    [sys.executable, "-B", str(root / "scripts/export_guarded_full_v0_1.py"),
                     "--output", str(staged)], root, timeout=120,
                )
                raw, payload = _staged_snapshot(staged, datetime.now(timezone.utc))
                if {p["program_id"] for p in payload["validation_programs"]} != PROGRAMS:
                    raise PublicationHeld("fresh crypto program missing")
                after = probe_k5()
                ensure_stable_k5(before, after, datetime.now(timezone.utc))
                if crypto_fingerprints(root) != ledger_before:
                    raise PublicationHeld("crypto ledger changed during export")
                if staged.read_bytes() != raw:
                    raise PublicationHeld("staged bytes changed")
                validate_candidate(payload, datetime.now(timezone.utc))
            except Exception:
                # Isolate any crypto-only export/verification failure; the
                # independent fallback still re-verifies core and expansion.
                # Discard unpublishable three-program staging and generate a
                # NEW core+expansion snapshot through independently verified builders.
                crypto_ready = False
                staged = staging_dir / "core_expansion_fresh.json"

        if not crypto_ready:
            run_checked(
                [sys.executable, "-B", str(root / "scripts/export_guarded_core_expansion_v0_2.py"),
                 "--output", str(staged)], root, timeout=120,
            )
            raw, payload = _staged_snapshot(staged, datetime.now(timezone.utc))
            if {p["program_id"] for p in payload["validation_programs"]} != BASE_PROGRAMS:
                raise PublicationHeld("core/expansion fallback is not independent")
            # Explicit opt-in to SOURCE-ATTESTED AGGREGATES ONLY. No crypto
            # trader detail, K5 task change, new public schema, or broker order.
            # Preserve the frozen historical as-of program on every crypto HOLD.
            cached_crypto = _try_source_attested_crypto_aggregate(
                root, datetime.now(timezone.utc)
            )
            if cached_crypto is None and CRYPTO_WRITER_INTERLOCK_READY:
                try:
                    cached_crypto = _last_accepted_crypto(root, datetime.now(timezone.utc))
                except Exception:
                    # Corrupted/unverifiable crypto history cannot block healthy
                    # current core/expansion. Without the writer-side interlock,
                    # cached crypto is never attached under ANY circumstances.
                    cached_crypto = None
            if (cached_crypto is None and
                    os.environ.get("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1") == "1"):
                # A crypto-only HOLD must not make verified progress appear erased.
                # This reads ONLY accepted, SHA/receipt-attested PUBLIC archives,
                # never private K5 ledgers or the mutable local public snapshot.
                # _last_accepted_crypto labels the last trusted CURRENT cohort
                # DELAYED with its original publication time and unhealthy flags.
                try:
                    cached_crypto = _last_accepted_crypto(
                        root, datetime.now(timezone.utc)
                    )
                except Exception:
                    # Malformed history is never silently trusted.
                    print("CRYPTO_DELAYED_ACCEPTED_HISTORY=HELD")
                    cached_crypto = None
                if cached_crypto is not None:
                    print("CRYPTO_DELAYED_SOURCE=VERIFIED_ACCEPTED_CURRENT")
            if cached_crypto is None and os.environ.get("VOWSIG_CRYPTO_ASOF_ENABLED") == "1":
                # Fallback of last resort: unchanged immutable owner-pinned
                # October 11 aggregate. Never call it CURRENT.
                try:
                    from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
                        load_pinned_asof_program,
                    )
                    cached_crypto = load_pinned_asof_program(
                        root, datetime.now(timezone.utc),
                        os.environ.get("VOWSIG_CRYPTO_ASOF_SHA256", ""),
                    )
                except (OSError, ValueError):
                    cached_crypto = None
                if cached_crypto is not None:
                    print("CRYPTO_DELAYED_SOURCE=PINNED_ORIGINAL_SEAL")
            if cached_crypto is not None:
                # New global generated_at_utc reflects fresh core/expansion only.
                # Historic crypto remains prominently DELAYED with its original time.
                payload["validation_programs"].append(cached_crypto)
                raw = json.dumps(payload, indent=2).encode("utf-8")
                staged.write_bytes(raw)
                validate_candidate(payload, datetime.now(timezone.utc))

        if staged.read_bytes() != raw:
            raise PublicationHeld("staged bytes changed before upload")
        validate_candidate(payload, datetime.now(timezone.utc))
        _verify_current_expansion_claim(root, payload)
        archive, receipt = _pending_archive(root, payload, raw)
        if staged.read_bytes() != raw or archive.read_bytes() != raw:
            raise PublicationHeld("staged or archived bytes changed before upload")

        # Exactly one HTTP push of freshly built base programs; crypto can be
        # current, explicitly delayed, or absent, but never spuriously fresh.
        run_checked(
            [sys.executable, "-B", str(root / "scripts/push_public_snapshot.py"),
             "--snapshot", str(staged)], root, timeout=60,
        )
        _accept_archive(archive, receipt, raw)
        # Atomic local replacement AFTER confirmed cloud acceptance and receipt.
        os.replace(staged, data / "public_snapshot.json")
        final_crypto = next(
            (p for p in payload["validation_programs"]
             if p["program_id"] == "crypto-expansion-1"), None
        )
        print(json.dumps({
            "guarded_publish": "PASS",
            "crypto_status": (
                final_crypto["status"] if final_crypto is not None else "pending"
            ),
            "snapshot_sha256": hashlib.sha256(raw).hexdigest(),
            "history_receipt": receipt.name,
            "validation_programs": sorted(p["program_id"] for p in payload["validation_programs"]),
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
