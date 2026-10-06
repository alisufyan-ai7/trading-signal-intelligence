from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.expansion_v1_2 import (
    DATABASE_PATHS as EXPANSION_DATABASE_PATHS,
    MARKETS,
    expansion_market_specs,
    preactivation_report_v1_2,
)
from trading_signal_intelligence.ai_v1.readiness_v1_2 import (
    probe_market_readiness_v1_2,
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


def active_ledger_hashes() -> dict[str, str]:
    result = {}
    for symbol, relative in ACTIVE_DATABASE_PATHS.items():
        path = ROOT / relative
        if not path.is_file():
            raise RuntimeError(f"active AI-v1.1 ledger missing: {path}")
        result[symbol] = sha256_file(path)
    return result


def expansion_ledger_presence() -> dict[str, bool]:
    return {
        symbol: (ROOT / relative).exists()
        for symbol, relative in EXPANSION_DATABASE_PATHS.items()
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read-only live MT5 compatibility probe for the preregistered "
            "AI-v1.2 expansion markets"
        )
    )
    parser.add_argument("--terminal-path", default=None)
    args = parser.parse_args()

    preflight = preactivation_report_v1_2(ROOT)
    if preflight["preactivation_check"] != "PASS":
        print(json.dumps({"preactivation": preflight}, indent=2))
        raise SystemExit(2)

    expansion_before = expansion_ledger_presence()
    if any(expansion_before.values()):
        raise RuntimeError(
            "AI-v1.2 expansion ledger already exists; readiness probe refuses"
        )

    active_before = active_ledger_hashes()
    scan_started = datetime.now(timezone.utc)
    specs = expansion_market_specs(ROOT)

    connector = MT5Connector(source_name="exness_mt5_demo")
    results = {}

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
                        "Read-only probe did not call symbol_select; "
                        "Market Watch state was not modified."
                    ),
                    "provider_call_made": False,
                    "ledger_write_performed": False,
                    "broker_execution_enabled": False,
                }
                continue

            result = probe_market_readiness_v1_2(
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

    active_after = active_ledger_hashes()
    expansion_after = expansion_ledger_presence()

    active_ledger_byte_identity = active_before == active_after
    expansion_ledgers_absent = (
        not any(expansion_before.values())
        and not any(expansion_after.values())
    )
    markets_ready = all(
        results.get(symbol, {}).get("readiness") == "READY"
        for symbol in MARKETS
    )

    report = {
        "probe": "AI-v1.2-expansion-readiness-v0.1",
        "mode": "READ_ONLY",
        "runtime_version": "AI-v1.2",
        "decision_protocol_version": "AI-v1.0",
        "scan_started_utc": scan_started.isoformat(),
        "markets": results,
        "active_ai_v1_1_ledger_hashes_before": active_before,
        "active_ai_v1_1_ledger_hashes_after": active_after,
        "active_ai_v1_1_ledger_byte_identity": active_ledger_byte_identity,
        "expansion_ledger_presence_before": expansion_before,
        "expansion_ledger_presence_after": expansion_after,
        "expansion_ledgers_absent": expansion_ledgers_absent,
        "provider_call_made": False,
        "ledger_write_performed": False,
        "scheduler_changed": False,
        "public_exposure_changed": False,
        "broker_execution_enabled": False,
        "readiness_check": (
            "PASS"
            if markets_ready
            and active_ledger_byte_identity
            and expansion_ledgers_absent
            else "INCOMPLETE_OR_FAIL"
        ),
    }
    print(json.dumps(report, indent=2, allow_nan=False))

    if report["readiness_check"] != "PASS":
        raise SystemExit(3)


if __name__ == "__main__":
    main()
