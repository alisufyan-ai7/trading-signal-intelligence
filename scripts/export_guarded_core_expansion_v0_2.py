"""Fresh core/expansion-only derived snapshot; isolated guarded publisher helper.

Do not call the original three-program exporter on crypto failure: its builder
requires crypto health and would suppress otherwise healthy lineages.
This module has no network, broker, provider or live trade operation.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.active_observability import (
    build_active_report,
    v1_1_state,
)
from trading_signal_intelligence.product.ai_insights import (
    CORE_MARKET_LABELS,
    EXPANSION_MARKET_LABELS,
    _v1_2_1_state,
    build_public_ai_insights,
    build_public_validation_program,
)
from trading_signal_intelligence.product.app import ROOT, health
from trading_signal_intelligence.product.catalog import market_statuses
from trading_signal_intelligence.product.evidence import evidence_summary
from trading_signal_intelligence.product.public_signals import (
    operational_event_counts,
    public_signal_history,
)


def build_core_expansion_programs(root: Path) -> list[dict]:
    core = build_active_report(root, include_scheduler=True, verify_upstream=True)
    programs = [
        build_public_validation_program(
            core, program_id="core-ai-shadow",
            title="Core AI Shadow Validation",
            market_labels=CORE_MARKET_LABELS,
            public_signal_exposure=True,
        )
    ]
    expansion = _v1_2_1_state(root)
    if not expansion["any_state"] or not expansion["complete_shape"]:
        raise RuntimeError("active expansion ledger or anchor missing")
    from trading_signal_intelligence.ai_v1.observability_v1_2_1 import (
        build_report_v1_2_1,
    )
    report = build_report_v1_2_1(
        root, include_scheduler=True, verify_upstream=True,
    )
    if report.get("health", {}).get("healthy") is True:
        expansion_program = build_public_validation_program(
            report, program_id="market-expansion-1",
            title="Expansion Shadow Validation",
            market_labels=EXPANSION_MARKET_LABELS,
            public_signal_exposure=False,
        )
    else:
        # Historic anchor verification remains False. A separate, narrow,
        # read-only compatibility attestation may qualify publication only
        # if EXACTLY the two registered crypto mappings were later added.
        from trading_signal_intelligence.product.expansion_registry_compat_v0_1 import (
            build_compatibility_qualified_program,
        )
        expansion_program = build_compatibility_qualified_program(root, report)
    programs.append(expansion_program)
    return programs


def build_core_expansion_snapshot(root: Path) -> dict:
    # Match the existing production exporter schema and safe market catalog.
    live_payload = []
    for market in market_statuses():
        row = {
            "source_symbol": market["source_symbol"],
            "canonical_symbol": market["canonical_symbol"],
            "asset_class": market["asset_class"],
            "product_status": market["product_status"],
            "evidence_status": market["evidence_status"],
        }
        if market["product_status"] == "live_signal_market":
            row["forward_state"] = market["forward"]["state"]
            row["ledger_valid"] = market["forward"]["ledger_valid"]
            row["signals"] = public_signal_history(market, limit=50)
            row["operational_event_counts"] = operational_event_counts(market)
        live_payload.append(row)

    ai_v1 = build_public_ai_insights(root)
    if ai_v1.get("publish_allowed") is False or v1_1_state(root)["any_state"] is not True:
        raise RuntimeError("core AI public transition not publishable")
    programs = build_core_expansion_programs(root)
    if {p["program_id"] for p in programs} != {
        "core-ai-shadow", "market-expansion-1"
    }:
        raise RuntimeError("core/expansion contract incomplete")
    return {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "health": health(),
        "evidence": evidence_summary(),
        "markets": live_payload,
        "ai_v1": ai_v1,
        "validation_programs_schema_version": 1,
        "validation_programs": programs,
        "raw_market_data_included": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists():
        raise SystemExit("refusing to overwrite pre-existing export")
    # Guarded caller provides a fresh, unique private staging directory.
    payload = build_core_expansion_snapshot(ROOT)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({"generated_at_utc": payload["generated_at_utc"],
                      "validation_program_count": 2,
                      "raw_market_data_included": False}))


if __name__ == "__main__":
    main()
