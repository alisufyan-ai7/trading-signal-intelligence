from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.crypto_readiness_v1_3 import (
    CANONICAL_SYMBOLS,
    MARKETS,
    collect_market_input,
    evaluate_batch_readiness,
)
from trading_signal_intelligence.connectors.binance import BinanceSpotConnector


ROOT = Path(__file__).resolve().parents[1]

CRYPTO_CONFIG = ROOT / "config" / "ai_v1_3_crypto_expansion.json"

GOVERNED_LEDGER_PATHS = (
    "data/forward.sqlite",
    "data/forward_ustec.sqlite",
    "data/forward_us30.sqlite",
    "data/ai_v1_xauusd.sqlite",
    "data/ai_v1_ustec.sqlite",
    "data/ai_v1_us30.sqlite",
    "data/ai_v1_1_xauusd.sqlite",
    "data/ai_v1_1_ustec.sqlite",
    "data/ai_v1_1_us30.sqlite",
    "data/ai_v1_2_1_eurusd.sqlite",
    "data/ai_v1_2_1_xagusd.sqlite",
    "data/ai_v1_2_1_usoil.sqlite",
)


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


def governed_ledger_hashes(active_repo_root: Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for relative in GOVERNED_LEDGER_PATHS:
        path = active_repo_root / relative
        if not path.is_file():
            raise RuntimeError(f"governed ledger missing: {path}")
        result[relative] = sha256_file(path)
    return result


def crypto_ledger_presence(active_repo_root: Path, config: dict[str, Any]) -> dict[str, bool]:
    return {
        symbol: (active_repo_root / relative).exists()
        for symbol, relative in config["planned_ledgers"].items()
    }


def load_and_validate_config() -> dict[str, Any]:
    payload = json.loads(CRYPTO_CONFIG.read_text(encoding="utf-8"))
    if payload.get("runtime_version") != "AI-v1.3":
        raise RuntimeError("crypto runtime version mismatch")
    if payload.get("status") != "design_only_preactivation":
        raise RuntimeError("crypto config must remain design_only_preactivation")
    if payload.get("primary_source_name") != "binance_spot":
        raise RuntimeError("crypto primary source mismatch")
    if [row.get("source_symbol") for row in payload.get("markets", [])] != list(MARKETS):
        raise RuntimeError("crypto market set/order mismatch")
    if payload.get("no_backfill") is not True:
        raise RuntimeError("crypto no_backfill must remain true")
    if payload.get("public_signal_exposure_enabled") is not False:
        raise RuntimeError("crypto public signal exposure must remain disabled")
    if payload.get("broker_execution_enabled") is not False:
        raise RuntimeError("broker execution must remain disabled")
    if payload.get("activation_authority") is not False:
        raise RuntimeError("crypto activation authority must remain false")
    cost = payload.get("execution_cost_profile") or {}
    if cost.get("activation_blocked_until_numeric_cost_policy_frozen") is not True:
        raise RuntimeError("numeric crypto cost policy blocker unexpectedly absent")
    if cost.get("fee_rate_per_side") is not None:
        raise RuntimeError("K1 readiness expects fee_rate_per_side to remain unfrozen")
    if cost.get("slippage_buffer_rule") is not None:
        raise RuntimeError("K1 readiness expects slippage_buffer_rule to remain unfrozen")
    if cost.get("all_in_round_trip_cost_rule") is not None:
        raise RuntimeError("K1 readiness expects all-in cost rule to remain unfrozen")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "K1 read-only Binance Spot readiness probe for the preregistered "
            "AI-v1.3 BTCUSDT / ETHUSDT / SOLUSDT cohort"
        )
    )
    parser.add_argument(
        "--active-repo-root",
        required=True,
        help="Production worktree containing governed live ledgers.",
    )
    parser.add_argument(
        "--expected-active-head",
        required=True,
        help="Exact production main commit expected in the active worktree.",
    )
    parser.add_argument(
        "--expected-probe-head",
        required=True,
        help="Exact committed AI-v1.3 readiness package under test.",
    )
    args = parser.parse_args()

    active_repo_root = Path(args.active_repo_root).resolve()
    if not active_repo_root.is_dir():
        raise RuntimeError(f"active repository root missing: {active_repo_root}")

    if git_head(ROOT) != args.expected_probe_head:
        raise RuntimeError(
            "probe package HEAD mismatch: "
            f"expected {args.expected_probe_head}, observed {git_head(ROOT)}"
        )
    if tracked_status(ROOT):
        raise RuntimeError("probe worktree tracked files are dirty")

    active_head_before = git_head(active_repo_root)
    if active_head_before != args.expected_active_head:
        raise RuntimeError(
            "active production HEAD mismatch: "
            f"expected {args.expected_active_head}, observed {active_head_before}"
        )
    active_status_before = tracked_status(active_repo_root)
    if active_status_before:
        raise RuntimeError(
            f"active production tracked worktree is dirty: {active_status_before}"
        )

    config = load_and_validate_config()

    activation_anchors_before = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "research" / "forward").glob(
            "AI-v1.3-crypto-expansion-activation-*.json"
        )
    )
    if activation_anchors_before:
        raise RuntimeError(
            f"crypto activation anchor unexpectedly exists: {activation_anchors_before}"
        )

    crypto_presence_before = crypto_ledger_presence(active_repo_root, config)
    if any(crypto_presence_before.values()):
        raise RuntimeError(
            "planned AI-v1.3 crypto ledger already exists; K1 readiness refuses"
        )

    ledgers_before = governed_ledger_hashes(active_repo_root)

    connector = BinanceSpotConnector()
    inputs = {}
    collection_errors: dict[str, str] = {}

    scan_started_utc = datetime.now(timezone.utc)

    for symbol in MARKETS:
        try:
            inputs[symbol] = collect_market_input(
                connector=connector,
                source_symbol=symbol,
                canonical_symbol=CANONICAL_SYMBOLS[symbol],
                h1_count=int(config["h1_bars"]),
                h4_count=int(config["h4_bars"]),
            )
        except Exception as exc:  # fail-closed evidence, no retry/backfill
            collection_errors[symbol] = f"{type(exc).__name__}: {exc}"

    batch_frozen_at_utc = datetime.now(timezone.utc)

    batch_report = None
    evaluation_error = None
    if not collection_errors:
        try:
            batch_report = evaluate_batch_readiness(
                inputs,
                batch_frozen_at_utc=batch_frozen_at_utc,
                h1_required=int(config["h1_bars"]),
                h4_required=int(config["h4_bars"]),
            )
        except Exception as exc:
            evaluation_error = f"{type(exc).__name__}: {exc}"

    ledgers_after = governed_ledger_hashes(active_repo_root)
    crypto_presence_after = crypto_ledger_presence(active_repo_root, config)
    active_status_after = tracked_status(active_repo_root)
    active_head_after = git_head(active_repo_root)

    activation_anchors_after = sorted(
        str(path.relative_to(ROOT))
        for path in (ROOT / "research" / "forward").glob(
            "AI-v1.3-crypto-expansion-activation-*.json"
        )
    )

    governed_ledger_byte_identity = ledgers_before == ledgers_after
    crypto_ledgers_absent = (
        not any(crypto_presence_before.values())
        and not any(crypto_presence_after.values())
    )
    activation_anchor_absent = (
        not activation_anchors_before and not activation_anchors_after
    )
    active_worktree_unchanged = (
        active_head_before == active_head_after == args.expected_active_head
        and active_status_before == active_status_after == ""
    )
    k1_market_pass = (
        batch_report is not None
        and batch_report.get("k1_market_readiness") == "PASS"
    )

    k1_pass = all(
        (
            not collection_errors,
            evaluation_error is None,
            k1_market_pass,
            governed_ledger_byte_identity,
            crypto_ledgers_absent,
            activation_anchor_absent,
            active_worktree_unchanged,
        )
    )

    report = {
        "probe": "AI-v1.3-crypto-K1-readiness-v0.1",
        "mode": "READ_ONLY",
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "program_id": "crypto-expansion-1",
        "scan_started_utc": scan_started_utc.isoformat(),
        "batch_frozen_at_utc": batch_frozen_at_utc.isoformat(),
        "probe_package_head": git_head(ROOT),
        "active_production_head_before": active_head_before,
        "active_production_head_after": active_head_after,
        "active_production_worktree_unchanged": active_worktree_unchanged,
        "collection_errors": collection_errors,
        "evaluation_error": evaluation_error,
        "batch_readiness": batch_report,
        "governed_ledger_hashes_before": ledgers_before,
        "governed_ledger_hashes_after": ledgers_after,
        "governed_ledger_byte_identity": governed_ledger_byte_identity,
        "crypto_ledger_presence_before": crypto_presence_before,
        "crypto_ledger_presence_after": crypto_presence_after,
        "crypto_ledgers_absent": crypto_ledgers_absent,
        "crypto_activation_anchors_before": activation_anchors_before,
        "crypto_activation_anchors_after": activation_anchors_after,
        "crypto_activation_anchor_absent": activation_anchor_absent,
        "numeric_crypto_cost_policy_frozen": False,
        "activation_readiness": "BLOCKED_NUMERIC_COST_POLICY_NOT_FROZEN",
        "provider_call_made": False,
        "ledger_write_performed": False,
        "scheduler_changed": False,
        "public_signal_exposure_changed": False,
        "broker_execution_enabled": False,
        "k1_readiness_check": "PASS" if k1_pass else "INCOMPLETE_OR_FAIL",
    }

    print(json.dumps(report, indent=2, allow_nan=False))

    if not k1_pass:
        raise SystemExit(3)


if __name__ == "__main__":
    main()
