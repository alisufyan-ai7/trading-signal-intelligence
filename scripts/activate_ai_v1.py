from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation import (
    MARKETS,
    artifact_hashes,
    build_activation_payload,
    load_json,
    require_provider_key,
)
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.local_env import load_project_env


ROOT = Path(__file__).resolve().parents[1]
DB_PATHS = {
    "XAUUSD": ROOT / "data" / "ai_v1_xauusd.sqlite",
    "USTEC": ROOT / "data" / "ai_v1_ustec.sqlite",
    "US30": ROOT / "data" / "ai_v1_us30.sqlite",
}


def main() -> None:
    load_project_env(ROOT / ".env")
    parser = argparse.ArgumentParser(
        description=(
            "Create AI-v1 ACTIVATION ledgers only. "
            "This script makes no model call and installs no scheduler."
        )
    )
    parser.add_argument(
        "--confirm",
        required=True,
        choices=["ACTIVATE-SHADOW-LEDGERS"],
        help="Explicit acknowledgement required.",
    )
    args = parser.parse_args()

    provider_config = load_json(ROOT / "config" / "ai_v1_provider.json")
    require_provider_key(provider_config)

    existing = [str(path) for path in DB_PATHS.values() if path.exists()]
    if existing:
        raise SystemExit(
            "Refusing activation because AI-v1 DB path(s) already exist: "
            + ", ".join(existing)
        )

    activated_at = datetime.now(timezone.utc)
    payloads = {
        market: build_activation_payload(
            repo_root=ROOT,
            market=market,
            activated_at_utc=activated_at,
        )
        for market in MARKETS
    }

    # Build and verify all ledgers under a temporary directory first. No model
    # call occurs. Final files are installed only after all three validate.
    with tempfile.TemporaryDirectory(prefix="signalproof-ai-v1-activation-") as temp:
        temp_root = Path(temp)
        temp_paths: dict[str, Path] = {}
        records: dict[str, dict] = {}

        for market in MARKETS:
            temp_path = temp_root / DB_PATHS[market].name
            ledger = AILedger(temp_path)
            record = ledger.append(
                record_type="ACTIVATION",
                entity_id=f"AI-v1.0:{market}:ACTIVATION",
                effective_at_utc=activated_at,
                recorded_at_utc=activated_at,
                payload=payloads[market],
            )
            verification = ledger.verify()
            if not verification["valid"] or verification["records"] != 1:
                raise RuntimeError(
                    f"activation ledger verification failed for {market}: "
                    f"{verification}"
                )
            temp_paths[market] = temp_path
            records[market] = {
                "record_hash": record["record_hash"],
                "verification": verification,
                "payload": payloads[market],
            }

        for path in DB_PATHS.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        for market in MARKETS:
            os.replace(temp_paths[market], DB_PATHS[market])

    anchor = {
        "protocol_version": "AI-v1.0",
        "status": "ACTIVATED_LEDGER_ONLY_SCHEDULER_NOT_INSTALLED",
        "activated_at_utc": activated_at.isoformat(),
        "provider_call_made": False,
        "broker_execution_enabled": False,
        "artifact_hashes": artifact_hashes(ROOT),
        "markets": records,
    }
    anchor_name = (
        "AI-v1-activation-"
        + activated_at.strftime("%Y-%m-%dT%H%M%SZ")
        + ".json"
    )
    anchor_path = ROOT / "research" / "forward" / anchor_name
    anchor_path.parent.mkdir(parents=True, exist_ok=True)
    anchor_path.write_bytes((json.dumps(anchor, indent=2) + "\n").encode("utf-8"))

    print(
        json.dumps(
            {
                "activation": "PASS",
                "activated_at_utc": activated_at.isoformat(),
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "scheduler_installed": False,
                "anchor_file": str(anchor_path.relative_to(ROOT)),
                "ledger_heads": {
                    market: records[market]["record_hash"] for market in MARKETS
                },
                "next_required_step": (
                    "Commit/anchor the generated activation file in GitHub "
                    "before installing or running the shadow scheduler."
                ),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
