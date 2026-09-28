from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.shadow_runtime import (
    MARKETS,
    DATABASE_PATHS,
    discover_active_anchor,
    market_specs,
)


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Archive a pre-performance AI-v1 activation without deleting evidence. "
            "Refuses if any ledger contains records beyond its single ACTIVATION."
        )
    )
    parser.add_argument(
        "--confirm",
        required=True,
        choices=["SUPERSEDE-PREPERFORMANCE-ACTIVATION"],
    )
    parser.parse_args()

    anchor_path, anchor = discover_active_anchor(ROOT)
    specs = market_specs(ROOT)

    archived_at = datetime.now(timezone.utc)
    archive_tag = (
        str(anchor["activated_at_utc"])
        .replace(":", "")
        .replace("-", "")
        .replace("+00:00", "Z")
        .replace(".", "_")
    )
    archive_root = ROOT / "data" / "ai-v1-superseded" / archive_tag

    validations: dict[str, Any] = {}
    for symbol in MARKETS:
        db_path = specs[symbol].database_path
        if not db_path.exists():
            raise SystemExit(f"Missing active AI-v1 database: {db_path}")

        ledger = AILedger(db_path)
        verification = ledger.verify()
        records = ledger.records()
        if not verification["valid"]:
            raise SystemExit(f"{symbol} ledger verification failed: {verification}")
        if len(records) != 1 or records[0]["record_type"] != "ACTIVATION":
            raise SystemExit(
                f"Refusing supersession: {symbol} has {len(records)} records; "
                "expected exactly one ACTIVATION and no performance-bearing records."
            )

        anchored = anchor["markets"][symbol]
        if records[0]["record_hash"] != anchored["record_hash"]:
            raise SystemExit(f"{symbol} activation hash does not match committed anchor")
        if records[0]["payload"] != anchored["payload"]:
            raise SystemExit(f"{symbol} activation payload does not match committed anchor")

        validations[symbol] = {
            "source_database": str(db_path.relative_to(ROOT)),
            "record_hash": records[0]["record_hash"],
            "records": 1,
            "verification": verification,
        }

    archive_root.mkdir(parents=True, exist_ok=False)

    moved: dict[str, str] = {}
    for symbol in MARKETS:
        source = specs[symbol].database_path
        destination = archive_root / source.name
        os.replace(source, destination)
        moved[symbol] = str(destination.relative_to(ROOT))

    supersession = {
        "protocol_version": "AI-v1.0",
        "status": "SUPERSEDED_PREPERFORMANCE_ACTIVATION",
        "superseded_anchor_file": str(anchor_path.relative_to(ROOT)),
        "superseded_activated_at_utc": anchor["activated_at_utc"],
        "superseded_at_utc": archived_at.isoformat(),
        "reason": (
            "The first activation was correctly ledger-only, but the live shadow "
            "runtime/scheduler implementation was not yet committed into the activation "
            "repository tree. No performance-bearing AI-v1 record existed. The activation "
            "is preserved and archived before creating a replacement activation that binds "
            "the final runtime implementation."
        ),
        "performance_bearing_records_observed": False,
        "provider_call_made_during_supersession": False,
        "broker_execution_enabled": False,
        "archived_databases": moved,
        "validated_activation_records": validations,
    }

    output_path = (
        ROOT
        / "research"
        / "forward"
        / (
            "AI-v1-activation-"
            + pd_timestamp(anchor["activated_at_utc"])
            + "-SUPERSEDED.json"
        )
    )
    output_path.write_text(
        json.dumps(supersession, indent=2) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "supersession": "PASS",
                "performance_bearing_records_observed": False,
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "superseded_anchor": str(anchor_path.relative_to(ROOT)),
                "supersession_anchor": str(output_path.relative_to(ROOT)),
                "archived_databases": moved,
                "next_required_step": (
                    "Commit/push the supersession anchor, then run activate_ai_v1.py "
                    "again from the final runtime commit."
                ),
            },
            indent=2,
        )
    )


def pd_timestamp(value: str) -> str:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return parsed.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


if __name__ == "__main__":
    main()
