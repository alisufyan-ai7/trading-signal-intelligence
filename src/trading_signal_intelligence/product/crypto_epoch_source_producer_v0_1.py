"""Prospective source-attested K5 aggregate producer — no autonomous execution.

Importing this module performs NO I/O. Calling capture_completed_k5_epoch is a
PRIVATE READ operation and requires separate owner authorization; there is
intentionally NO CLI, scheduler hook, publisher import, install or entry point.

All source inputs are from the actual frozen AI-v1.3 observability/ledger
interfaces unless a caller deliberately injects synthetic test doubles.
"""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
    DATABASE_PATHS, MARKETS,
)
from trading_signal_intelligence.ai_v1.crypto_observability_v1_3 import (
    build_report_v1_3,
)
from trading_signal_intelligence.ai_v1.observability import (
    read_records_read_only, verify_records,
)
from trading_signal_intelligence.product.ai_insights import build_public_validation_program
from trading_signal_intelligence.product.crypto_validation import (
    CRYPTO_LABELS, normalize_crypto_validation_report,
)
from trading_signal_intelligence.product.crypto_epoch_bridge_v0_1 import (
    EpochBridgeHeld, _task_ok, prepare_verified_epoch,
)

UTC = timezone.utc
MAX_K5_PROCESS_SECONDS = 20


class SourceEpochHeld(EpochBridgeHeld):
    """No publishable source attestation; never export private details."""


def probe_completed_k5_task_windows() -> dict[str, Any]:
    """GET-only Task Scheduler probe; NEVER starts, edits or interrupts K5."""
    if os.name != "nt":
        raise SourceEpochHeld("native Windows K5 observation required")
    command = (
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'VowSig AI-v1.3 Crypto Shadow Scan';"
        "$i=Get-ScheduledTaskInfo -TaskName 'VowSig AI-v1.3 Crypto Shadow Scan';"
        "$o=[pscustomobject]@{TaskName=[string]$t.TaskName;State=[string]$t.State;"
        "LastTaskResult=[int64]$i.LastTaskResult;"
        "LastRunTime=$i.LastRunTime.ToString('o');"
        "NextRunTime=$i.NextRunTime.ToString('o')};"
        "$o|ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, check=True,
            timeout=MAX_K5_PROCESS_SECONDS,
        )
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise SourceEpochHeld("K5 task observation not an object")
        return payload
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        raise SourceEpochHeld("K5 task observation unavailable") from None


def _verified_read(
    root: Path,
    reader: Callable[[Path], list[dict[str, Any]]],
) -> dict[str, list[dict[str, Any]]]:
    """One three-market read with the repository's real hash-chain algorithm."""
    batch = {}
    if set(MARKETS) != {"BTCUSDT", "ETHUSDT", "SOLUSDT"}:
        raise SourceEpochHeld("unexpected frozen crypto cohort")
    for symbol in MARKETS:
        path = root / DATABASE_PATHS[symbol]
        # Refuse malicious indirection; the normal reader opens mode=ro,
        # query_only and will not initialize missing databases.
        if path.is_symlink():
            raise SourceEpochHeld("ledger path indirection forbidden")
        rows = reader(path)
        if not isinstance(rows, list) or not rows:
            raise SourceEpochHeld("empty or unsupported K5 ledger")
        proof = verify_records(rows)
        if (proof.get("valid") is not True
            or proof.get("records") != len(rows)
            or proof.get("head_hash") != rows[-1].get("record_hash")):
            raise SourceEpochHeld("private K5 hash chain invalid")
        batch[symbol] = rows
    return batch


def _fingerprint(batch: dict[str, list[dict[str, Any]]]) -> str:
    """Private-only full-row commitment; never returned or recorded."""
    digest = hashlib.sha256()
    for symbol in sorted(MARKETS):
        rows = batch[symbol]
        digest.update(symbol.encode("ascii"))
        digest.update(len(rows).to_bytes(8, "big"))
        for row in rows:
            digest.update(str(row["sequence"]).encode("ascii"))
            digest.update(row["record_hash"].encode("ascii"))
    return digest.hexdigest()


def capture_completed_k5_epoch(
    repo_root: Path,
    *,
    observed_at_utc: datetime,
    reader: Callable[[Path], list[dict[str, Any]]] = read_records_read_only,
    reporter: Callable[..., dict[str, Any]] = build_report_v1_3,
    task_probe: Callable[[], dict[str, Any]] = probe_completed_k5_task_windows,
) -> bytes:
    """PRIVATE-READ, prospective adapter; no calls unless explicitly invoked.

    The normal reporter recomputes artifact/activation/upstream/task/three
    ledger checks from frozen source. We bracket that report with TWO fully
    verified independent reads and TWO successful same-run task observations.
    Only sanitized aggregate bytes escape. No raw report or records are saved.
    """
    try:
        if (not isinstance(observed_at_utc, datetime)
            or observed_at_utc.tzinfo is None
            or observed_at_utc.utcoffset() is None):
            raise SourceEpochHeld("aware observation clock required")
        now = observed_at_utc.astimezone(UTC)
        root = Path(repo_root).resolve(strict=True)
        if not root.is_dir():
            raise SourceEpochHeld("approved repository root required")
        before = task_probe()
        _task_ok(before, now)
        last = datetime.fromisoformat(
            before["LastRunTime"].replace("Z", "+00:00")
        ).astimezone(UTC)
        # Match natural K5's closed-H1 close, not an arbitrary caller cycle.
        cycle = last.replace(minute=0, second=0, microsecond=0)
        if not cycle <= last <= now:
            raise SourceEpochHeld("invalid K5 completed H1 chronology")
        batch_before = _verified_read(root, reader)
        report = reporter(
            root, now_utc=now, include_scheduler=True, verify_upstream=True
        )
        normalized = normalize_crypto_validation_report(report)
        public = build_public_validation_program(
            normalized, program_id="crypto-expansion-1",
            title="Crypto AI Shadow Validation", market_labels=CRYPTO_LABELS,
            public_signal_exposure=False,
        )
        batch_after = _verified_read(root, reader)
        after = task_probe()
        _task_ok(after, now)
        if _fingerprint(batch_before) != _fingerprint(batch_after):
            raise SourceEpochHeld("K5 ledger advanced during evidence read")
        # Bridge independently checks task identity and equality, each
        # market terminal cycle, source/public counts/heads and C1/C2/C3.
        return prepare_verified_epoch(
            report=report,
            private_records=batch_after,
            public_program=public,
            task_before=before,
            task_after=after,
            cycle_close_utc=cycle.isoformat(),
            captured_at_utc=now.isoformat(),
            verify_chain=verify_records,
        )
    except SourceEpochHeld:
        raise
    except Exception:
        # No private ledger paths, row values, report data or OS stderr in an
        # observable exception. Preserve detailed diagnostics only inside
        # separately authorized offline synthetic tests.
        raise SourceEpochHeld("source-authenticated K5 epoch held") from None
