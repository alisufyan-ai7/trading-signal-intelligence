from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.product.ai_insights import build_public_ai_insights
from trading_signal_intelligence.product.app import ROOT, health
from trading_signal_intelligence.product.catalog import market_statuses
from trading_signal_intelligence.product.evidence import evidence_summary
from trading_signal_intelligence.product.public_signals import (
    operational_event_counts,
    public_signal_history,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a public derived-signal snapshot without raw MT5 candles"
    )
    parser.add_argument("--output", default="data/public_snapshot.json")
    parser.add_argument("--signals-per-market", type=int, default=50)
    args = parser.parse_args()

    markets = market_statuses()
    live_payload = []
    for market in markets:
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
            row["signals"] = public_signal_history(
                market, limit=args.signals_per_market
            )
            row["operational_event_counts"] = operational_event_counts(market)
        live_payload.append(row)

    try:
        ai_v1 = build_public_ai_insights(ROOT)
    except Exception as exc:
        ai_v1 = {
            "schema_version": 1,
            "runtime_version": "UNAVAILABLE",
            "decision_protocol_version": "AI-v1.0",
            "protocol_version": "AI-v1.0",
            "mode": "SHADOW_ONLY",
            "status": "temporarily_unavailable",
            "customer_notice": "AI-v1 shadow insights are temporarily unavailable.",
            "health": {"healthy": False},
            "error_class": type(exc).__name__,
            "raw_market_data_included": False,
            "raw_feature_snapshots_included": False,
            "provider_request_metadata_included": False,
            "hidden_reasoning_included": False,
        }

    payload = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "health": health(),
        "evidence": evidence_summary(),
        "markets": live_payload,
        "ai_v1": ai_v1,
        "raw_market_data_included": False,
    }

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps({
        "output": str(output),
        "generated_at_utc": payload["generated_at_utc"],
        "live_signal_markets": payload["health"]["live_signal_markets"],
        "ai_runtime_version": ai_v1.get("runtime_version"),
        "ai_v1_status": ai_v1.get("status"),
        "raw_market_data_included": False,
    }, indent=2))


if __name__ == "__main__":
    main()
