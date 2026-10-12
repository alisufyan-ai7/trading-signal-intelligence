"""One-shot bounded K5 H1 source inspection; safe aggregate stdout only.

This file is executed by filename, never by PowerShell's python -c.
It makes no file writes, provider calls, trading actions, scheduler changes,
HTTP requests or Git mutations. Caller must pin file and production sources.
"""
from __future__ import annotations

import collections
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

UTC = timezone.utc
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")
TASK_NAME = "VowSig AI-v1.3 Crypto Shadow Scan"
EXPECTED_MAIN = "a4f00578c00c5e23eb4fae073cf2df18c78d9a0a"
MAX_RUN_AGE_SECONDS = 75 * 60
SOURCE_BLOBS = {
    "src/trading_signal_intelligence/ai_v1/observability.py": "b4ba334e6c7c2e54c301251268f5bfe2746c75cd",
    "src/trading_signal_intelligence/ai_v1/crypto_observability_v1_3.py": "c974d65354ccc17060e0e1c6a85d1e7d9237281e",
    "src/trading_signal_intelligence/ai_v1/crypto_activation_v1_3.py": "afba5b93cfeb1f849f70f242f137bd16bd24fd6d",
    "config/ai_v1_3_crypto_review_gates.json": "e74e4102ec71fdea362a460130bcadee61e1777e",
}


class VerificationHeld(RuntimeError):
    """A short nonprivate reason code for fail-closed inspection."""


def require(condition: Any, reason: str) -> None:
    if not condition:
        raise VerificationHeld(reason)


def utc(value: Any) -> datetime:
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise VerificationHeld("INVALID_TASK_TIMESTAMP") from None
    require(dt.tzinfo is not None and dt.utcoffset() is not None, "NAIVE_TASK_TIMESTAMP")
    return dt.astimezone(UTC)


def _git(root: Path, *arguments: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *arguments], check=True,
            capture_output=True, text=True, timeout=15,
        )
        return result.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise VerificationHeld("SOURCE_PIN_GIT_UNAVAILABLE") from None


def verify_live_source_pins(root: Path) -> None:
    require(root.is_dir() and (root / "src").is_dir(), "SOURCE_ROOT_MISSING")
    require(_git(root, "rev-parse", "HEAD") == EXPECTED_MAIN, "LIVE_MAIN_HEAD_CHANGED")
    for relative, pin in SOURCE_BLOBS.items():
        path = root / relative
        require(path.is_file() and not path.is_symlink(), "PINNED_SOURCE_MISSING")
        require(_git(root, "rev-parse", f"HEAD:{relative}") == pin, "SOURCE_COMMIT_PIN_CHANGED")
        require(
            _git(root, "hash-object", f"--path={relative}", "--", str(path)) == pin,
            "SOURCE_DISK_PIN_CHANGED",
        )


def scheduler_observation(sample: dict[str, Any], now: datetime) -> tuple[datetime, float]:
    require(isinstance(sample, dict), "TASK_OBSERVATION_INVALID")
    require(sample.get("available") is True and sample.get("task_name") == TASK_NAME, "TASK_UNAVAILABLE")
    require(
        sample.get("state") == "Ready"
        and type(sample.get("last_task_result")) is int
        and sample.get("last_task_result") == 0,
        "TASK_NOT_NATURALLY_FINISHED",
    )
    last = utc(sample.get("last_run_time"))
    future = utc(sample.get("next_run_time"))
    age = (now - last).total_seconds()
    require(0 <= age <= MAX_RUN_AGE_SECONDS and future > now, "COMPLETED_K5_RUN_NOT_RECENT")
    return last, age


def inspect(
    root: Path,
    *,
    now: datetime,
    markets: tuple[str, ...],
    database_paths: dict[str, str],
    task_reader: Callable[[], dict[str, Any]],
    record_reader: Callable[[Path], list[dict[str, Any]]],
    record_verifier: Callable[[list[dict[str, Any]]], dict[str, Any]],
    report_builder: Callable[..., dict[str, Any]],
    gates_reader: Callable[[Path], dict[str, Any]],
) -> dict[str, Any]:
    require(tuple(markets) == SYMBOLS and set(database_paths) == set(SYMBOLS), "CRYPTO_COHORT_CHANGED")
    require(now.tzinfo is not None and now.utcoffset() is not None, "NAIVE_NOW")
    now = now.astimezone(UTC)

    def verified_batch() -> dict[str, tuple[list[dict[str, Any]], tuple[tuple[int, str], ...]]]:
        batch = {}
        for symbol in SYMBOLS:
            file = root / database_paths[symbol]
            require(file.is_file() and not file.is_symlink(), "SOURCE_LEDGER_MISSING")
            rows = record_reader(file)
            require(isinstance(rows, list) and bool(rows), "SOURCE_LEDGER_EMPTY")
            proof = record_verifier(rows)
            require(
                proof.get("valid") is True and proof.get("records") == len(rows)
                and proof.get("head_hash") == rows[-1].get("record_hash"),
                "SOURCE_CHAIN_INVALID",
            )
            batch[symbol] = (rows, tuple((r["sequence"], r["record_hash"]) for r in rows))
        return batch

    before = task_reader()
    last, age = scheduler_observation(before, now)
    first = verified_batch()
    report = report_builder(root, now_utc=now, include_scheduler=True, verify_upstream=True)
    second = verified_batch()
    after = task_reader()
    repeated_last, _ = scheduler_observation(after, now)
    require(
        all(before.get(k) == after.get(k) for k in (
            "task_name", "state", "last_task_result", "last_run_time"
        )) and repeated_last == last,
        "TASK_CHANGED_DURING_INSPECTION",
    )
    require(
        report.get("runtime_version") == "AI-v1.3"
        and report.get("program_id") == "crypto-expansion-1"
        and report.get("mode") == "READ_ONLY", "SOURCE_REPORT_ID_MISMATCH",
    )
    health = report.get("health", {})
    require(
        all(health.get(k) is True for k in (
            "healthy", "ledgers_valid", "activation_anchor_matches_ledgers",
            "crypto_artifacts_valid", "activation_anchor_upstream_valid",
            "scheduler_healthy", "public_signal_exposure_disabled", "broker_execution_disabled",
        )), "SOURCE_REPORT_HEALTH_HELD",
    )
    activation = report.get("activation", {})
    require(
        activation.get("public_signal_exposure_enabled") is False
        and activation.get("broker_execution_enabled") is False,
        "CRYPTO_EXPOSURE_BOUNDARY_HELD",
    )
    frozen = gates_reader(root)
    gates = report.get("gates", {})
    require(
        frozen.get("valid") is True and set(gates) == set(frozen.get("gates", {}))
        == {"C1", "C2", "C3"}, "FROZEN_GATES_INVALID",
    )
    for name, spec in frozen["gates"].items():
        reported = gates[name]
        require(
            all(reported[measure]["required"] == spec[measure]
                for measure in ("valid_inferences", "completed_shadow_trades"))
            and reported["minimum_calendar_days"] == spec["minimum_calendar_days"],
            "FROZEN_GATE_THRESHOLD_DRIFT",
        )
    scheduler = report.get("scheduler", {})
    require(
        scheduler.get("healthy") is True
        and scheduler.get("task_name") == TASK_NAME
        and scheduler.get("state") == "Ready"
        and scheduler.get("last_task_result") == 0
        and utc(scheduler.get("last_run_time")) == last,
        "SOURCE_REPORT_TASK_DRIFT",
    )
    close = last.replace(minute=0, second=0, microsecond=0)
    safe_rows = []
    for symbol in SYMBOLS:
        rows, prior_signature = first[symbol]
        current, later_signature = second[symbol]
        require(prior_signature == later_signature, "SOURCE_LEDGER_MOVED")
        market = report.get("markets", {}).get(symbol, {})
        require(
            market.get("ledger_verification", {}).get("valid") is True
            and market.get("activation_anchor_match") is True
            and market.get("records") == len(rows)
            and market.get("current_head_hash") == current[-1]["record_hash"],
            "REPORT_LEDGER_DRIFT",
        )
        counts = collections.Counter(row["record_type"] for row in current)
        require(dict(counts) == market.get("counts_by_type"), "REPORT_COUNTS_DRIFT")
        entity = f"AI-v1.3:{symbol}:{close.isoformat().replace('+00:00', 'Z')}"
        found = [row["record_type"] for row in current if row["entity_id"] == entity]
        terminal = [v for v in found if v in ("SIGNAL", "NO_TRADE", "REJECTED_INFERENCE")]
        completed = (
            len(terminal) == 1 and found.count("INFERENCE") == 1
            and not any(k in found for k in ("ERROR", "MISSED_INFERENCE"))
        )
        safe_rows.append({
            "market": symbol,
            "valid_inferences": int(market["valid_inferences"]),
            "completed_shadow_trades": int(market["completed_shadow_trades"]),
            "open_shadow_signals": int(market["open_signals"]),
            "no_trade": int(counts["NO_TRADE"]),
            "rejected_inferences": int(counts["REJECTED_INFERENCE"]),
            "missed_inferences": int(counts["MISSED_INFERENCE"]),
            "errors": int(counts["ERROR"]),
            "latest_cycle_complete": completed,
        })
    totals = report.get("totals", {})
    for key in ("valid_inferences", "completed_shadow_trades", "open_shadow_signals"):
        require(totals.get(key) == sum(row[key] for row in safe_rows), "SOURCE_TOTALS_DRIFT")
    return {
        "result": "PASS" if all(m["latest_cycle_complete"] for m in safe_rows)
            else "HOLD_INCOMPLETE_NATURAL_CYCLE",
        "verification": "BOUNDED_REAL_K5_READ_ONLY_ONCE",
        "observed_at_utc": now.isoformat(),
        "scheduler_last_run_utc": last.isoformat(),
        "cycle_close_utc": close.isoformat(),
        "within_publication_15_min_window": age <= 900,
        "source_chains_anchors_artifacts_valid": True,
        "public_crypto_exposure_enabled": False,
        "broker_execution_enabled": False,
        "markets": safe_rows,
    }


def main(argv: list[str]) -> int:
    try:
        require(len(argv) == 2, "EXPECTED_LIVE_REPO_ARGUMENT")
        require(os.name == "nt" and sys.version_info[:2] == (3, 12), "WINDOWS_PYTHON_312_REQUIRED")
        root = Path(argv[1]).resolve(strict=True)
        verify_live_source_pins(root)
        # Imports occur strictly AFTER source verification; there are no
        # provider adapters, runtime runners, scheduler edits or API requests.
        from trading_signal_intelligence.ai_v1 import (
            crypto_activation_v1_3 as activation,
            crypto_observability_v1_3 as observability,
            observability as base_observability,
        )
        for module, relative in (
            (base_observability, "src/trading_signal_intelligence/ai_v1/observability.py"),
            (observability, "src/trading_signal_intelligence/ai_v1/crypto_observability_v1_3.py"),
            (activation, "src/trading_signal_intelligence/ai_v1/crypto_activation_v1_3.py"),
        ):
            require(
                Path(module.__file__).resolve() == (root / relative).resolve(),
                "UNPINNED_RUNTIME_MODULE",
            )
        result = inspect(
            root, now=datetime.now(UTC),
            markets=activation.MARKETS, database_paths=activation.DATABASE_PATHS,
            task_reader=observability.probe_windows_scheduler_v1_3,
            record_reader=base_observability.read_records_read_only,
            record_verifier=base_observability.verify_records,
            report_builder=observability.build_report_v1_3,
            gates_reader=activation.validate_review_gates,
        )
        print("BOUNDED_K5_READ_ONLY_RESULT=" + json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0 if result["result"] == "PASS" else 2
    except VerificationHeld as exc:
        print("BOUNDED_K5_READ_ONLY_RESULT=" + json.dumps({"result": "HELD", "reason_code": str(exc)}))
        return 2
    except Exception:
        print('BOUNDED_K5_READ_ONLY_RESULT={"result":"HELD","reason_code":"UNEXPECTED_READ_ONLY_ERROR"}')
        return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
