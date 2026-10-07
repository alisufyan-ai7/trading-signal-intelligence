from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.expansion_v1_2_1 import (
    DATABASE_PATHS as SUCCESSOR_DATABASE_PATHS,
    MARKETS,
    PREDECESSOR_DATABASE_PATHS,
    PREDECESSOR_FAILURE_EVIDENCE,
    expansion_market_specs_v1_2_1,
    preactivation_report_v1_2_1,
)
from trading_signal_intelligence.ai_v1.readiness_v1_2_1 import (
    probe_market_readiness_v1_2_1,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS as ACTIVE_DATABASE_PATHS,
)
from trading_signal_intelligence.connectors.mt5 import MT5Connector


ROOT = Path(__file__).resolve().parents[1]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_head(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def tracked_status(repo_root: Path) -> str:
    return subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=no"],
        cwd=repo_root,
        text=True,
        stderr=subprocess.STDOUT,
    ).strip()


def ledger_hashes(
    repo_root: Path,
    paths: dict[str, str],
    *,
    label: str,
) -> dict[str, str]:
    result: dict[str, str] = {}
    for symbol, relative in paths.items():
        path = repo_root / relative
        if not path.is_file():
            raise RuntimeError(f"{label} ledger missing: {path}")
        result[symbol] = sha256_file(path)
    return result


def ledger_presence(
    repo_root: Path,
    paths: dict[str, str],
) -> dict[str, bool]:
    return {
        symbol: (repo_root / relative).exists()
        for symbol, relative in paths.items()
    }


def expected_predecessor_hashes() -> dict[str, str]:
    payload = json.loads(
        (ROOT / PREDECESSOR_FAILURE_EVIDENCE).read_text(encoding="utf-8")
    )
    return {
        symbol: str(payload["markets"][symbol]["ledger_file_sha256_after"])
        for symbol in MARKETS
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only live MT5 readiness probe for the AI-v1.2.1 correction. "
            "It also proves AI-v1.1 and failed AI-v1.2 ledgers remain unchanged."
        )
    )
    parser.add_argument("--terminal-path", default=None)
    parser.add_argument("--active-repo-root", required=True)
    parser.add_argument("--expected-active-head", required=True)
    args = parser.parse_args()

    active_repo_root = Path(args.active_repo_root).resolve()
    if not active_repo_root.is_dir():
        raise RuntimeError(
            f"active repository root does not exist: {active_repo_root}"
        )

    observed_active_head = git_head(active_repo_root)
    if observed_active_head != args.expected_active_head:
        raise RuntimeError(
            "active production HEAD mismatch: "
            f"expected {args.expected_active_head}, "
            f"observed {observed_active_head}"
        )
    active_status_before = tracked_status(active_repo_root)
    if active_status_before:
        raise RuntimeError(
            "active production tracked worktree is not clean: "
            f"{active_status_before}"
        )

    preflight = preactivation_report_v1_2_1(ROOT)
    if preflight["preactivation_check"] != "PASS":
        print(json.dumps({"preactivation": preflight}, indent=2))
        raise SystemExit(2)

    successor_before = ledger_presence(
        active_repo_root,
        SUCCESSOR_DATABASE_PATHS,
    )
    if any(successor_before.values()):
        raise RuntimeError(
            "AI-v1.2.1 successor ledger already exists; readiness probe refuses"
        )

    active_before = ledger_hashes(
        active_repo_root,
        ACTIVE_DATABASE_PATHS,
        label="active AI-v1.1",
    )
    predecessor_before = ledger_hashes(
        active_repo_root,
        PREDECESSOR_DATABASE_PATHS,
        label="failed AI-v1.2",
    )
    frozen_predecessor = expected_predecessor_hashes()
    if predecessor_before != frozen_predecessor:
        raise RuntimeError(
            "failed AI-v1.2 predecessor ledger hashes do not match "
            "frozen P2 evidence"
        )

    scan_started = datetime.now(timezone.utc)
    specs = expansion_market_specs_v1_2_1(ROOT)
    connector = MT5Connector(source_name="exness_mt5_demo")
    results: dict[str, dict] = {}

    connector.connect(args.terminal_path)
    try:
        mt5 = connector._mt5()
        for symbol in MARKETS:
            info = mt5.symbol_info(symbol)
            if info is None:
                results[symbol] = {
                    "source_symbol": symbol,
                    "readiness": "FAIL_SYMBOL_UNKNOWN",
                    "symbol_visible": None,
                    "provider_call_made": False,
                    "ledger_write_performed": False,
                    "broker_execution_enabled": False,
                }
                continue

            visible = bool(getattr(info, "visible", False))
            if not visible:
                results[symbol] = {
                    "source_symbol": symbol,
                    "readiness": "INCONCLUSIVE_SYMBOL_NOT_VISIBLE",
                    "symbol_visible": False,
                    "note": (
                        "Read-only probe did not change Market Watch visibility."
                    ),
                    "provider_call_made": False,
                    "ledger_write_performed": False,
                    "broker_execution_enabled": False,
                }
                continue

            result = probe_market_readiness_v1_2_1(
                connector=connector,
                market=specs[symbol],
                scan_started_utc=scan_started,
                h1_count=500,
                h4_count=200,
            )
            result["symbol_visible"] = True
            results[symbol] = result
    finally:
        connector.disconnect()

    active_after = ledger_hashes(
        active_repo_root,
        ACTIVE_DATABASE_PATHS,
        label="active AI-v1.1",
    )
    predecessor_after = ledger_hashes(
        active_repo_root,
        PREDECESSOR_DATABASE_PATHS,
        label="failed AI-v1.2",
    )
    successor_after = ledger_presence(
        active_repo_root,
        SUCCESSOR_DATABASE_PATHS,
    )
    active_status_after = tracked_status(active_repo_root)

    active_identity = active_before == active_after
    predecessor_identity = (
        predecessor_before == predecessor_after == frozen_predecessor
    )
    successor_absent = (
        not any(successor_before.values())
        and not any(successor_after.values())
    )
    active_worktree_unchanged = (
        active_status_before == ""
        and active_status_after == ""
        and git_head(active_repo_root) == args.expected_active_head
    )
    markets_ready = all(
        results.get(symbol, {}).get("readiness") == "READY"
        for symbol in MARKETS
    )

    report = {
        "probe": "AI-v1.2.1-expansion-correction-readiness-v0.1",
        "mode": "READ_ONLY",
        "runtime_version": "AI-v1.2.1",
        "decision_protocol_version": "AI-v1.0",
        "predecessor_runtime_version": "AI-v1.2",
        "scan_started_utc": scan_started.isoformat(),
        "correction_worktree_head": git_head(ROOT),
        "active_production_head_before": observed_active_head,
        "active_production_head_after": git_head(active_repo_root),
        "active_production_worktree_unchanged": active_worktree_unchanged,
        "markets": results,
        "active_ai_v1_1_ledger_hashes_before": active_before,
        "active_ai_v1_1_ledger_hashes_after": active_after,
        "active_ai_v1_1_ledger_byte_identity": active_identity,
        "failed_ai_v1_2_ledger_hashes_expected": frozen_predecessor,
        "failed_ai_v1_2_ledger_hashes_before": predecessor_before,
        "failed_ai_v1_2_ledger_hashes_after": predecessor_after,
        "failed_ai_v1_2_ledger_byte_identity": predecessor_identity,
        "successor_ledger_presence_before": successor_before,
        "successor_ledger_presence_after": successor_after,
        "successor_ledgers_absent": successor_absent,
        "provider_call_made": False,
        "ledger_write_performed": False,
        "scheduler_changed": False,
        "public_exposure_changed": False,
        "broker_execution_enabled": False,
        "readiness_check": (
            "PASS"
            if markets_ready
            and active_identity
            and predecessor_identity
            and successor_absent
            and active_worktree_unchanged
            else "INCOMPLETE_OR_FAIL"
        ),
    }
    print(json.dumps(report, indent=2, allow_nan=False))
    if report["readiness_check"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
