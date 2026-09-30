from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.activation_v1_1 import (
    build_activation_anchor_document_v1_1,
    build_activation_payload_v1_1,
    preactivation_report_v1_1,
)
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.observability import (
    probe_windows_scheduler,
    verify_anchor_upstream,
)
from trading_signal_intelligence.ai_v1.retirement_v1_0 import (
    build_v1_0_retirement_preview,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS,
    MARKETS,
)


ROOT = Path(__file__).resolve().parents[1]


def _require_committed_retirement() -> dict:
    candidates = sorted(
        (ROOT / "research" / "forward").glob("AI-v1.0-retired-*.json")
    )
    if len(candidates) != 1:
        raise SystemExit(
            "Expected exactly one AI-v1.0 retirement metadata file before "
            f"AI-v1.1 activation; found {len(candidates)}."
        )
    path = candidates[0]
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise SystemExit("AI-v1.0 retirement metadata root must be object")
    if payload.get("runtime_version") != "AI-v1.0":
        raise SystemExit("AI-v1.0 retirement runtime mismatch")
    if payload.get("metadata_write_performed") is not True:
        raise SystemExit("AI-v1.0 retirement metadata is not finalized")
    if payload.get("ledger_mutation_performed") is not False:
        raise SystemExit("AI-v1.0 retirement ledger mutation boundary failed")
    if payload.get("backfilled_into_ai_v1_1") is not False:
        raise SystemExit("AI-v1.0 retirement backfill boundary failed")
    if payload.get("broker_execution_enabled") is not False:
        raise SystemExit("Broker execution boundary failed in retirement metadata")
    if payload.get("scheduler_after_disable", {}).get("state") != "Disabled":
        raise SystemExit("Retirement metadata does not prove disabled v1.0 task")

    upstream = verify_anchor_upstream(ROOT, path)
    if upstream.get("valid") is not True:
        raise SystemExit(
            "AI-v1.0 retirement metadata is not committed/pushed upstream."
        )

    current = build_v1_0_retirement_preview(
        ROOT,
        include_scheduler=False,
        verify_upstream=True,
    )
    for symbol in MARKETS:
        expected = payload["markets"][symbol]
        observed = current["markets"][symbol]
        for key in ("ledger_sha256", "head_hash", "records", "counts_by_type"):
            if observed.get(key) != expected.get(key):
                raise SystemExit(
                    f"{symbol} AI-v1.0 ledger changed after retirement metadata "
                    f"was committed: {key}"
                )
    if current["cutover_preconditions"]["unresolved_signal_count"] != 0:
        raise SystemExit("AI-v1.0 unresolved signals are no longer zero")
    return {
        "file": str(path.relative_to(ROOT)),
        "upstream": upstream,
        "payload": payload,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Create exactly three AI-v1.1 activation-only ledgers and one "
            "aggregate activation anchor. No provider/MT5 call, scheduler "
            "installation, backfill, or broker execution occurs."
        )
    )
    parser.add_argument(
        "--confirm",
        required=True,
        choices=["ACTIVATE-AI-V1.1-LEDGERS"],
    )
    args = parser.parse_args()

    preactivation = preactivation_report_v1_1(ROOT)
    if preactivation["preactivation_check"] != "PASS":
        raise SystemExit("AI-v1.1 preactivation check is not PASS")

    legacy_scheduler = probe_windows_scheduler()
    if legacy_scheduler.get("available") is not True:
        raise SystemExit("Unable to verify legacy AI-v1.0 scheduler state")
    if legacy_scheduler.get("state") != "Disabled":
        raise SystemExit(
            "Legacy AI-v1.0 scheduler must be Disabled before AI-v1.1 activation"
        )

    retirement = _require_committed_retirement()

    existing_ledgers = [
        str(ROOT / relative)
        for relative in DATABASE_PATHS.values()
        if (ROOT / relative).exists()
    ]
    existing_anchors = sorted(
        (ROOT / "research" / "forward").glob("AI-v1.1-activation-*.json")
    )
    if existing_ledgers or existing_anchors:
        raise SystemExit(
            "Refusing AI-v1.1 activation because v1.1 state already exists."
        )

    activated_at = datetime.now(timezone.utc)
    payloads = {
        market: build_activation_payload_v1_1(
            repo_root=ROOT,
            market=market,
            activated_at_utc=activated_at,
        )
        for market in MARKETS
    }

    with tempfile.TemporaryDirectory(
        prefix="signalproof-ai-v1-1-activation-"
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
                entity_id=f"AI-v1.1:{market}:ACTIVATION",
                effective_at_utc=activated_at,
                recorded_at_utc=activated_at,
                payload=payloads[market],
            )
            verification = ledger.verify()
            if not verification["valid"] or verification["records"] != 1:
                raise RuntimeError(
                    f"AI-v1.1 activation ledger verification failed for "
                    f"{market}: {verification}"
                )
            temp_paths[market] = temp_path
            records[market] = record

        anchor = build_activation_anchor_document_v1_1(
            repo_root=ROOT,
            activated_at_utc=activated_at,
            activation_records=records,
        )
        anchor_name = (
            "AI-v1.1-activation-"
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

        for market in MARKETS:
            os.replace(temp_paths[market], ROOT / DATABASE_PATHS[market])
        os.replace(temp_anchor, anchor_path)

    print(
        json.dumps(
            {
                "activation": "PASS",
                "runtime_version": "AI-v1.1",
                "decision_protocol_version": "AI-v1.0",
                "activated_at_utc": activated_at.isoformat(),
                "repository_commit_sha": anchor["repository_commit_sha"],
                "retirement_metadata": retirement["file"],
                "provider_call_made": False,
                "mt5_call_made": False,
                "broker_execution_enabled": False,
                "scheduler_installed": False,
                "backfill_performed": False,
                "anchor_file": str(anchor_path.relative_to(ROOT)),
                "ledger_heads": {
                    market: records[market]["record_hash"]
                    for market in MARKETS
                },
                "next_required_step": (
                    "Commit/push only the generated AI-v1.1 activation anchor, "
                    "then run the activation-only runtime verifier before any "
                    "AI-v1.1 scheduler installation or live inference."
                ),
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
