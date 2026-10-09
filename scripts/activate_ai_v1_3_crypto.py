from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import (
    DATABASE_PATHS,
    MARKETS,
    build_activation_anchor_document_v1_3,
    build_activation_payload_v1_3,
    preactivation_report_v1_3,
)
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.runtime_verifier_registry_compat_v1_2_1 import (
    verify_active_runtime_registry_compat_v1_2_1,
)

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create exactly three AI-v1.3 crypto activation-only ledgers and "
            "one aggregate activation anchor. No Binance/OpenAI call, scheduler "
            "change, public signal exposure or broker/exchange execution occurs."
        )
    )
    parser.add_argument(
        "--confirm",
        required=True,
        choices=["ACTIVATE-AI-V1.3-CRYPTO-LEDGERS"],
    )
    parser.parse_args()

    preactivation = preactivation_report_v1_3(ROOT)
    if preactivation["preactivation_check"] != "PASS":
        raise SystemExit("AI-v1.3 crypto preactivation check is not PASS")

    parallel = verify_active_runtime_registry_compat_v1_2_1(
        ROOT,
        require_activation_only=False,
        include_scheduler=True,
        verify_upstream=True,
    )
    if parallel["runtime_verification"] != "PASS":
        raise SystemExit("Parallel AI-v1.2.1 runtime is not healthy")
    if parallel["broker_execution_disabled"] is not True:
        raise SystemExit("Parallel AI-v1.2.1 broker boundary failed")

    existing_ledgers = [
        str(ROOT / relative)
        for relative in DATABASE_PATHS.values()
        if (ROOT / relative).exists()
    ]
    existing_anchors = sorted(
        (ROOT / "research" / "forward").glob(
            "AI-v1.3-crypto-expansion-activation-*.json"
        )
    )
    if existing_ledgers or existing_anchors:
        raise SystemExit(
            "Refusing AI-v1.3 activation because crypto activation state already exists"
        )

    activated_at = datetime.now(UTC)
    payloads = {
        market: build_activation_payload_v1_3(
            repo_root=ROOT,
            market=market,
            activated_at_utc=activated_at,
        )
        for market in MARKETS
    }

    moved_paths: list[Path] = []
    with tempfile.TemporaryDirectory(
        prefix="vowsig-ai-v1-3-crypto-activation-"
    ) as temp:
        temp_root = Path(temp)
        temp_paths: dict[str, Path] = {}
        records: dict[str, dict] = {}

        for market in MARKETS:
            final_path = ROOT / DATABASE_PATHS[market]
            temp_path = temp_root / final_path.name
            ledger = AILedger(temp_path)
            record = ledger.append(
                record_type="ACTIVATION",
                entity_id=f"AI-v1.3:{market}:ACTIVATION",
                effective_at_utc=activated_at,
                recorded_at_utc=activated_at,
                payload=payloads[market],
            )
            verification = ledger.verify()
            if not verification["valid"] or verification["records"] != 1:
                raise RuntimeError(
                    f"AI-v1.3 activation ledger verification failed for "
                    f"{market}: {verification}"
                )
            temp_paths[market] = temp_path
            records[market] = record

        anchor = build_activation_anchor_document_v1_3(
            repo_root=ROOT,
            activated_at_utc=activated_at,
            activation_records=records,
        )
        anchor_name = (
            "AI-v1.3-crypto-expansion-activation-"
            + activated_at.strftime("%Y-%m-%dT%H%M%SZ")
            + ".json"
        )
        anchor_path = ROOT / "research" / "forward" / anchor_name
        temp_anchor = temp_root / anchor_name
        temp_anchor.write_text(
            json.dumps(anchor, indent=2, allow_nan=False) + "\n",
            encoding="utf-8",
        )

        for relative in DATABASE_PATHS.values():
            (ROOT / relative).parent.mkdir(parents=True, exist_ok=True)
        anchor_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            for market in MARKETS:
                destination = ROOT / DATABASE_PATHS[market]
                os.replace(temp_paths[market], destination)
                moved_paths.append(destination)
            os.replace(temp_anchor, anchor_path)
            moved_paths.append(anchor_path)
        except OSError:
            for path in reversed(moved_paths):
                try:
                    path.unlink(missing_ok=True)
                except OSError:
                    pass
            raise

    print(
        json.dumps(
            {
                "activation": "PASS",
                "runtime_version": "AI-v1.3",
                "decision_protocol_version": "AI-v1.0",
                "program_id": "crypto-expansion-1",
                "activated_at_utc": activated_at.isoformat(),
                "repository_commit_sha": anchor["repository_commit_sha"],
                "provider_call_made": False,
                "binance_call_made": False,
                "public_signal_exposure_enabled": False,
                "broker_execution_enabled": False,
                "scheduler_installed": False,
                "backfill_performed": False,
                "anchor_file": str(anchor_path.relative_to(ROOT)),
                "ledger_heads": {
                    market: records[market]["record_hash"]
                    for market in MARKETS
                },
                "next_required_step": (
                    "Commit/push only the generated AI-v1.3 activation anchor, "
                    "then run the activation-only runtime verifier before any "
                    "AI-v1.3 provider inference or scheduler installation."
                ),
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
