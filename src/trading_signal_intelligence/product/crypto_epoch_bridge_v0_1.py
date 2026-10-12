"""Unwired, read-only-input K5 to current public crypto epoch bridge.

Production caller and publisher integration are intentionally NOT installed.
No SQLite, Task Scheduler, network or credential API is called here. The caller
must provide actual verified K5 report, independently read records and task
observations; these are synthetic inputs in this branch's tests only.
"""
from __future__ import annotations

import collections
import copy
import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
    CompletedEpochRejected, _canonical, _utc, _clock, create_completed_epoch_bytes,
    public_program_from_completed_epoch,
)

SYMBOLS = frozenset(("BTCUSDT", "ETHUSDT", "SOLUSDT"))
K5_TASK = "VowSig AI-v1.3 Crypto Shadow Scan"
TERMINAL = frozenset(("SIGNAL", "NO_TRADE", "REJECTED_INFERENCE"))
EXPECTED_BASE = frozenset(("core-ai-shadow", "market-expansion-1"))
ENVELOPE_KEYS = frozenset(("cycle_close_utc", "epoch_sha256", "epoch_filename"))
MAX_RECEIPT_BYTES = 1024
NAME = re.compile(r"crypto-epoch-(\d{8}T\d{6}Z)-([a-f0-9]{64})\.json\Z")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


class EpochBridgeHeld(CompletedEpochRejected):
    """No new CURRENT crypto evidence can be trusted; base must continue."""


def _time(value: Any) -> datetime:
    try:
        return _utc(value)
    except (ValueError, TypeError) as exc:
        raise EpochBridgeHeld("invalid timestamp") from exc


def _task_ok(task: Any, now: datetime) -> tuple[str, ...]:
    if not isinstance(task, dict) or set(task) != {
        "TaskName", "State", "LastTaskResult", "LastRunTime", "NextRunTime"
    }:
        raise EpochBridgeHeld("unknown K5 Task Scheduler observation")
    if (task["TaskName"] != K5_TASK or task["State"] != "Ready"
        or type(task["LastTaskResult"]) is not int or task["LastTaskResult"] != 0):
        raise EpochBridgeHeld("K5 not completed successfully")
    last, upcoming = _time(task["LastRunTime"]), _time(task["NextRunTime"])
    age = (now - last).total_seconds()
    if not 0 <= age <= 900 or upcoming <= now:
        raise EpochBridgeHeld("K5 run missing or stale")
    return (task["TaskName"], task["State"], str(task["LastTaskResult"]),
            last.isoformat(), upcoming.isoformat())


def prepare_verified_epoch(
    *, report: dict[str, Any], private_records: dict[str, list[dict[str, Any]]],
    public_program: dict[str, Any], task_before: dict[str, Any],
    task_after: dict[str, Any], cycle_close_utc: str,
    captured_at_utc: str, verify_chain: Callable[[list[dict[str, Any]]], Any],
) -> bytes:
    """Pure adapter. No private report or record data leaves via the return value.

    verify_chain MUST be the actual repository's hash-chain verifier in a future
    reviewed native-Windows producer; tests inject a synthetic verifier.
    """
    if not isinstance(report, dict) or not isinstance(private_records, dict):
        raise EpochBridgeHeld("verified K5 inputs missing")
    now, close = _time(captured_at_utc), _time(cycle_close_utc)
    if _task_ok(task_before, now) != _task_ok(task_after, now):
        raise EpochBridgeHeld("K5 changed during read")
    scheduler = report.get("scheduler")
    if not isinstance(scheduler, dict) or (
        scheduler.get("healthy") is not True or scheduler.get("state") != "Ready"
        or scheduler.get("task_name") != K5_TASK
        or scheduler.get("last_task_result") != 0
        or _time(scheduler.get("last_run_time")) != _time(task_after["LastRunTime"])
    ):
        raise EpochBridgeHeld("full report and scheduler observation disagree")
    last = _time(task_after["LastRunTime"])
    if not close <= last <= now:
        raise EpochBridgeHeld("K5 last run cannot establish completed cycle")
    report_at = _time(report.get("generated_at_utc"))
    if not last <= report_at <= now:
        raise EpochBridgeHeld("K5 report predates natural completed run")
    expected = {
        "healthy", "ledgers_valid", "activation_anchor_matches_ledgers",
        "crypto_artifacts_valid", "activation_anchor_upstream_valid",
        "scheduler_healthy", "public_signal_exposure_disabled", "broker_execution_disabled",
    }
    health = report.get("health")
    if not isinstance(health, dict) or any(health.get(k) is not True for k in expected):
        raise EpochBridgeHeld("K5 source, governance or broker health not verified")
    activation = report.get("activation")
    if (not isinstance(activation, dict)
        or activation.get("public_signal_exposure_enabled") is not False
        or activation.get("broker_execution_enabled") is not False
        or activation.get("backfill_prior_missed") is not False):
        raise EpochBridgeHeld("K5 activation safety boundary mismatch")
    if (report.get("runtime_version") != "AI-v1.3"
        or report.get("decision_protocol_version") != "AI-v1.0"
        or report.get("program_id") != "crypto-expansion-1"
        or report.get("mode") != "READ_ONLY"):
        raise EpochBridgeHeld("unknown K5 report lineage")
    markets = report.get("markets")
    if (not isinstance(markets, dict) or set(markets) != SYMBOLS
        or set(private_records) != SYMBOLS):
        raise EpochBridgeHeld("three-market K5 cohort missing")
    by_symbol = {m.get("source_symbol"): m for m in public_program.get("markets", [])
                 if isinstance(m, dict)} if isinstance(public_program, dict) else {}
    if set(by_symbol) != SYMBOLS or len(public_program["markets"]) != 3:
        raise EpochBridgeHeld("public market cohort inconsistent")
    source_gates = report.get("gates")
    public_gates = public_program.get("gates")
    if (not isinstance(source_gates, dict)
        or set(source_gates) != {"C1", "C2", "C3"}
        or not isinstance(public_gates, list) or len(public_gates) != 3
        or {g.get("gate_id") for g in public_gates if isinstance(g, dict)}
            != set(source_gates)):
        raise EpochBridgeHeld("three governed source gates required")
    for gate in public_gates:
        source = source_gates[gate["gate_id"]]
        if gate.get("eligible") is not source.get("eligible"):
            raise EpochBridgeHeld("public/source crypto gate eligibility mismatch")
        requirements = gate.get("requirements")
        if not isinstance(requirements, list):
            raise EpochBridgeHeld("public crypto gate requirements absent")
        by_metric = {r.get("metric"): r for r in requirements if isinstance(r, dict)}
        if len(by_metric) != len(requirements):
            raise EpochBridgeHeld("duplicate public crypto gate requirements")
        for metric in ("valid_inferences", "completed_shadow_trades"):
            actual = source.get(metric)
            observed = by_metric.get(metric)
            if (not isinstance(actual, dict) or not isinstance(observed, dict)
                or any(observed.get(k) != actual.get(k)
                       for k in ("current", "required", "met"))):
                raise EpochBridgeHeld("public crypto gate count mismatch")
        days = source.get("minimum_calendar_days")
        if type(days) is not int or days < 0:
            raise EpochBridgeHeld("unverified crypto calendar gate")
        if days == 0 and set(by_metric) != {
            "valid_inferences", "completed_shadow_trades"
        }:
            raise EpochBridgeHeld("unexpected crypto gate requirements")
        if days > 0:
            observed = by_metric.get("calendar_days")
            remaining = source.get("calendar_days_remaining")
            if (len(by_metric) != 3 or not isinstance(observed, dict)
                or type(remaining) is not int or remaining < 0
                or observed.get("required") != days
                or observed.get("current") != max(0, days - remaining)
                or observed.get("met") is not source.get("calendar_requirement_met")):
                raise EpochBridgeHeld("public crypto gate calendar mismatch")
    proofs = {}
    for symbol in sorted(SYMBOLS):
        info, rows, public = markets[symbol], private_records[symbol], by_symbol[symbol]
        if not isinstance(info, dict) or not isinstance(rows, list) or not rows:
            raise EpochBridgeHeld("K5 market evidence missing")
        verification = verify_chain(rows)
        if (not isinstance(verification, dict) or verification.get("valid") is not True
            or info.get("ledger_verification", {}).get("valid") is not True
            or info.get("activation_anchor_match") is not True):
            raise EpochBridgeHeld("private ledger chain not independently verified")
        head = rows[-1].get("record_hash") if isinstance(rows[-1], dict) else None
        if (not isinstance(head, str) or not HEX64.fullmatch(head)
            or info.get("current_head_hash") != head
            or info.get("records") != len(rows)):
            raise EpochBridgeHeld("report/private source changed during observation")
        counts = collections.Counter(row.get("record_type") for row in rows)
        if (not isinstance(info.get("counts_by_type"), dict)
            or any(info["counts_by_type"].get(t, 0) != n for t, n in counts.items())):
            raise EpochBridgeHeld("report record populations mismatch")
        reconcile = {
            "valid_inferences": "INFERENCE", "completed_shadow_trades": "EXIT",
            "signals": "SIGNAL", "no_trade": "NO_TRADE",
            "rejected_inferences": "REJECTED_INFERENCE", "missed_inferences": "MISSED_INFERENCE",
            "errors": "ERROR",
        }
        for public_name, record_type in reconcile.items():
            n = counts[record_type]
            if info["counts_by_type"].get(record_type, 0) != n or public.get(public_name) != n:
                raise EpochBridgeHeld("public crypto counts do not match private records")
        if (public.get("latest_recorded_at_utc") != info.get("latest_recorded_at_utc")):
            raise EpochBridgeHeld("public crypto latest observation mismatch")
        if (public.get("open_signals") != info.get("open_signals")
            or info.get("completed_shadow_trades") != counts["EXIT"]
            or info.get("valid_inferences") != counts["INFERENCE"]):
            raise EpochBridgeHeld("public crypto lifecycle counts disagree")
        entity = f"AI-v1.3:{symbol}:{close.isoformat().replace('+00:00', 'Z')}"
        found = [row.get("record_type") for row in rows if row.get("entity_id") == entity]
        terminal = [kind for kind in found if kind in TERMINAL]
        if (len(terminal) != 1 or found.count("INFERENCE") != 1
            or "ERROR" in found or "MISSED_INFERENCE" in found):
            raise EpochBridgeHeld("incomplete, duplicate or failed latest H1 cycle")
        proofs[symbol] = {
            "source_bar_close_utc": close.isoformat(),
            "terminal_record_type": terminal[0],
            "ledger_head_sha256": head,
        }
    totals = report.get("totals", {})
    if (not isinstance(totals, dict)
        or totals.get("valid_inferences") != sum(m["valid_inferences"] for m in by_symbol.values())
        or totals.get("completed_shadow_trades") != sum(m["completed_shadow_trades"] for m in by_symbol.values())
        or totals.get("open_shadow_signals") != sum(m["open_signals"] for m in by_symbol.values())):
        raise EpochBridgeHeld("K5 aggregate totals inconsistent")
    try:
        return create_completed_epoch_bytes(
            crypto_program=public_program, cycle_close_utc=cycle_close_utc,
            captured_at_utc=captured_at_utc, terminal_proofs=proofs,
        )
    except CompletedEpochRejected as exc:
        raise EpochBridgeHeld("crypto public envelope rejected") from exc


def signed_receipt(raw_epoch: bytes, *, key: bytes) -> bytes:
    """Pure HMAC source-identity prototype. Never log, commit or persist key."""
    if not isinstance(key, bytes) or len(key) < 32:
        raise EpochBridgeHeld("independent receipt key required")
    try:
        obj = json.loads(raw_epoch)
        cycle = _time(obj["cycle_close_utc"])
    except (ValueError, TypeError, KeyError) as exc:
        raise EpochBridgeHeld("invalid epoch for signed receipt") from exc
    digest = hashlib.sha256(raw_epoch).hexdigest()
    filename = f"crypto-epoch-{cycle.strftime('%Y%m%dT%H%M%SZ')}-{digest}.json"
    claims = {"cycle_close_utc": cycle.isoformat(),
              "epoch_sha256": digest, "epoch_filename": filename}
    mac = hmac.new(key, _canonical(claims), hashlib.sha256).hexdigest()
    return _canonical({**claims, "receipt_hmac_sha256": mac})


def verify_receipt(raw_receipt: bytes, *, key: bytes) -> dict[str, str]:
    if not isinstance(key, bytes) or len(key) < 32 or not isinstance(raw_receipt, bytes) \
            or not 0 < len(raw_receipt) <= MAX_RECEIPT_BYTES:
        raise EpochBridgeHeld("invalid trusted crypto receipt")
    try:
        obj = json.loads(raw_receipt)
    except (ValueError, UnicodeError) as exc:
        raise EpochBridgeHeld("unreadable crypto receipt") from exc
    if not isinstance(obj, dict) or set(obj) != ENVELOPE_KEYS | {"receipt_hmac_sha256"}:
        raise EpochBridgeHeld("unexpected crypto receipt")
    mac = obj["receipt_hmac_sha256"]
    claims = {k: obj[k] for k in ENVELOPE_KEYS}
    if (not isinstance(mac, str) or not HEX64.fullmatch(mac)
        or not hmac.compare_digest(
            hmac.new(key, _canonical(claims), hashlib.sha256).hexdigest(), mac)):
        raise EpochBridgeHeld("receipt authentication failed")
    digest = claims["epoch_sha256"]
    filename = claims["epoch_filename"]
    cycle = _time(claims["cycle_close_utc"])
    if (not isinstance(digest, str) or not HEX64.fullmatch(digest)
        or not isinstance(filename, str) or NAME.fullmatch(filename) is None
        or filename != f"crypto-epoch-{cycle.strftime('%Y%m%dT%H%M%SZ')}-{digest}.json"):
        raise EpochBridgeHeld("untrusted crypto epoch filename")
    return claims


def attach_current_crypto_preview(
    *, base_snapshot: dict[str, Any], raw_epoch: bytes,
    raw_receipt: bytes, key: bytes, now: datetime,
    last_accepted_cycle_close_utc: str | None,
    verify_public: Callable[[dict[str, Any]], None],
) -> dict[str, Any]:
    """Pure test-only pub adapter; return unchanged base on ANY crypto HOLD.

    Release code must use native Windows verified spool reads, a trust-rooted
    receipt/monotonic state and existing guarded snapshot verification+push.
    """
    if not isinstance(base_snapshot, dict):
        raise EpochBridgeHeld("invalid independent base snapshot")
    base = copy.deepcopy(base_snapshot)
    programs = base.get("validation_programs")
    if (not isinstance(programs, list) or len(programs) != 2
        or {p.get("program_id") for p in programs if isinstance(p, dict)} != EXPECTED_BASE):
        raise EpochBridgeHeld("only fresh independent two-program base is permitted")
    try:
        receipt = verify_receipt(raw_receipt, key=key)
        digest = hashlib.sha256(raw_epoch).hexdigest()
        if digest != receipt["epoch_sha256"]:
            raise EpochBridgeHeld("receipt/epoch mismatch")
        epoch_obj = json.loads(raw_epoch)
        if epoch_obj.get("cycle_close_utc") != receipt["cycle_close_utc"]:
            raise EpochBridgeHeld("receipt/epoch cycle mismatch")
        crypto = public_program_from_completed_epoch(
            raw_epoch, expected_sha256=digest, now=_clock(now),
            last_published_cycle_close_utc=last_accepted_cycle_close_utc)
        candidate = copy.deepcopy(base)
        candidate["validation_programs"].append(crypto)
        verify_public(candidate)
        return candidate
    except (ValueError, TypeError, KeyError, AttributeError):
        return base
