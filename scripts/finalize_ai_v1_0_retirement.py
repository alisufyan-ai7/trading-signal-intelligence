from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.retirement_v1_0 import (
    build_v1_0_retirement_document,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Finalize and write AI-v1.0 retirement metadata after the legacy "
            "scheduler has been disabled. This script does not mutate AI-v1.0 "
            "ledgers, call MT5/OpenAI, or activate AI-v1.1."
        )
    )
    parser.add_argument("--preview-file", required=True)
    parser.add_argument(
        "--confirm",
        required=True,
        choices=["WRITE-AI-V1.0-RETIREMENT-METADATA"],
    )
    args = parser.parse_args()

    preview_path = Path(args.preview_file)
    if not preview_path.is_absolute():
        preview_path = (ROOT / preview_path).resolve()
    preview = json.loads(preview_path.read_text(encoding="utf-8"))
    if not isinstance(preview, dict):
        raise SystemExit("retirement preview root must be a JSON object")

    existing = sorted(
        (ROOT / "research" / "forward").glob("AI-v1.0-retired-*.json")
    )
    if existing:
        raise SystemExit(
            "Refusing retirement metadata write because a retirement record "
            "already exists: " + ", ".join(
                str(path.relative_to(ROOT)) for path in existing
            )
        )

    finalized_at = datetime.now(timezone.utc)
    document = build_v1_0_retirement_document(
        ROOT,
        preview=preview,
        retired_at_utc=finalized_at,
        verify_upstream=True,
    )

    name = (
        "AI-v1.0-retired-"
        + finalized_at.strftime("%Y-%m-%dT%H%M%SZ")
        + ".json"
    )
    path = ROOT / "research" / "forward" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "retirement_metadata": "PASS",
                "retired_at_utc": document["retired_at_utc"],
                "retirement_file": str(path.relative_to(ROOT)),
                "ledger_mutation_performed": False,
                "provider_call_made": False,
                "mt5_call_made": False,
                "broker_execution_enabled": False,
                "legacy_scheduler_before_disable": document[
                    "scheduler_before_disable"
                ].get("state"),
                "legacy_scheduler_after_disable": document[
                    "scheduler_after_disable"
                ].get("state"),
                "next_required_step": (
                    "Commit/push this retirement metadata before AI-v1.1 "
                    "activation. Do not run AI-v1.1 live inference yet."
                ),
            },
            indent=2,
            allow_nan=False,
        )
    )


if __name__ == "__main__":
    main()
