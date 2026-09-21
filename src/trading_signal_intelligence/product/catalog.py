from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from trading_signal_intelligence.forward import ForwardLedger


DEFAULT_CONFIG = Path("config/launch_universe.json")


def launch_catalog(path: str | Path = DEFAULT_CONFIG) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _forward_state(market: dict[str, Any]) -> dict[str, Any]:
    database = Path(market["forward_database"])
    entity = market["forward_entity"]

    if not database.exists():
        return {
            "state": "not_activated",
            "ledger_exists": False,
            "ledger_valid": None,
            "record_counts": {},
            "ledger_head_hash": None,
            "active_signal": None,
            "last_exit": None,
        }

    ledger = ForwardLedger(database)
    verification = ledger.verify()
    counts = ledger.counts_by_type()
    activations = ledger.records(record_type="ACTIVATION", entity_id=entity)

    if not activations:
        state = "not_activated"
    elif not verification["valid"]:
        state = "ledger_error"
    else:
        unresolved = [
            row
            for row in ledger.records(record_type="SIGNAL")
            if row["entity_id"] in set(ledger.unresolved_signal_entities())
        ]
        state = "active_signal" if unresolved else "scanning"

    unresolved_ids = set(ledger.unresolved_signal_entities())
    active_signal = next(
        (
            row
            for row in reversed(ledger.records(record_type="SIGNAL"))
            if row["entity_id"] in unresolved_ids
        ),
        None,
    )
    exits = ledger.records(record_type="EXIT")

    return {
        "state": state,
        "ledger_exists": True,
        "ledger_valid": verification["valid"],
        "record_counts": counts,
        "ledger_head_hash": ledger.head_hash(),
        "active_signal": active_signal,
        "last_exit": exits[-1] if exits else None,
    }


def market_statuses(path: str | Path = DEFAULT_CONFIG) -> list[dict[str, Any]]:
    catalog = launch_catalog(path)
    rows: list[dict[str, Any]] = []

    for market in catalog["live_signal_markets"]:
        rows.append(
            {
                **market,
                "product_status": "live_signal_market",
                "forward": _forward_state(market),
            }
        )

    for market in catalog["research_monitoring_markets"]:
        rows.append(
            {
                **market,
                "product_status": "research_monitoring",
                "forward": None,
            }
        )

    return rows
