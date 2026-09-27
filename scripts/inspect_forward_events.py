from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from trading_signal_intelligence.forward import ForwardLedger
from trading_signal_intelligence.product.catalog import launch_catalog


def _event_row(record: dict[str, Any]) -> dict[str, Any]:
    payload = record["payload"]
    return {
        "sequence": record["sequence"],
        "record_type": record["record_type"],
        "entity_id": record["entity_id"],
        "recorded_at_utc": record["recorded_at_utc"],
        "effective_at_utc": record["effective_at_utc"],
        "record_hash": record["record_hash"],
        "previous_hash": record["previous_hash"],
        "direction": payload.get("direction"),
        "signal_bar_timestamp_utc": payload.get("signal_bar_timestamp_utc"),
        "signal_close_time_utc": payload.get("signal_close_time_utc"),
        "entry_timestamp_utc": payload.get("entry_timestamp_utc"),
        "entry": payload.get("entry"),
        "stop": payload.get("stop"),
        "target": payload.get("target"),
        "recorded_lag_seconds": payload.get("recorded_lag_seconds"),
        "exit_bar_timestamp_utc": payload.get("exit_bar_timestamp_utc"),
        "exit": payload.get("exit"),
        "exit_reason": payload.get("exit_reason"),
        "gross_r": payload.get("gross_r"),
        "net_r": payload.get("net_r"),
        "reason": payload.get("reason"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect immutable forward lifecycle events across launch markets"
    )
    parser.add_argument(
        "--types",
        default="SIGNAL,EXIT,MISSED_SIGNAL,SKIPPED_SIGNAL",
        help="Comma-separated record types to include",
    )
    args = parser.parse_args()
    wanted = {item.strip().upper() for item in args.types.split(",") if item.strip()}

    catalog = launch_catalog()
    markets = []
    total_events = 0

    for market in catalog["live_signal_markets"]:
        database = Path(market["forward_database"])
        ledger = ForwardLedger(database)
        verification = ledger.verify()
        records = ledger.records()
        events = [
            _event_row(row)
            for row in records
            if row["record_type"] in wanted
        ]
        total_events += len(events)
        markets.append(
            {
                "source_symbol": market["source_symbol"],
                "canonical_symbol": market["canonical_symbol"],
                "database": str(database),
                "verification": verification,
                "counts_by_type": ledger.counts_by_type(),
                "ledger_head_hash": ledger.head_hash(),
                "unresolved_signal_entities": ledger.unresolved_signal_entities(),
                "events": events,
            }
        )

    print(
        json.dumps(
            {
                "requested_record_types": sorted(wanted),
                "total_matching_events": total_events,
                "markets": markets,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
