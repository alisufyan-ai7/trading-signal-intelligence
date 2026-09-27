from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.forward import ForwardLedger


def _trim_hash(value: str | None) -> str | None:
    if value is None:
        return None
    return value[:12] + "…" + value[-8:] if len(value) > 24 else value


def public_signal_history(market: dict[str, Any], limit: int = 50) -> list[dict[str, Any]]:
    database = Path(market["forward_database"])
    if not database.exists():
        return []

    ledger = ForwardLedger(database)
    signals = ledger.records(record_type="SIGNAL")
    exits_by_entity = {
        row["entity_id"]: row for row in ledger.records(record_type="EXIT")
    }

    rows: list[dict[str, Any]] = []
    for signal in reversed(signals):
        payload = signal["payload"]
        exit_row = exits_by_entity.get(signal["entity_id"])
        exit_payload = exit_row["payload"] if exit_row else None

        rows.append(
            {
                "signal_id": signal["entity_id"],
                "source_symbol": market["source_symbol"],
                "canonical_symbol": market["canonical_symbol"],
                "strategy": market["strategy"],
                "status": "closed" if exit_row else "active",
                "direction": payload.get("direction"),
                "issued_at_utc": payload.get("signal_close_time_utc"),
                "entry_at_utc": payload.get("entry_timestamp_utc"),
                "entry": payload.get("entry"),
                "stop": payload.get("stop"),
                "target": payload.get("target"),
                "risk_reward_target_r": payload.get("target_r", 2.5),
                "recorded_lag_seconds": payload.get("recorded_lag_seconds"),
                "record_hash": _trim_hash(signal.get("record_hash")),
                "exit_at_utc": exit_payload.get("exit_bar_timestamp_utc") if exit_payload else None,
                "exit": exit_payload.get("exit") if exit_payload else None,
                "exit_reason": exit_payload.get("exit_reason") if exit_payload else None,
                "net_r": exit_payload.get("net_r") if exit_payload else None,
                "exit_record_hash": _trim_hash(exit_row.get("record_hash")) if exit_row else None,
            }
        )

        if len(rows) >= limit:
            break

    return rows


def operational_event_counts(market: dict[str, Any]) -> dict[str, int]:
    database = Path(market["forward_database"])
    if not database.exists():
        return {}

    ledger = ForwardLedger(database)
    counts = ledger.counts_by_type()
    return {
        key: counts.get(key, 0)
        for key in ("SIGNAL", "EXIT", "MISSED_SIGNAL", "SKIPPED_SIGNAL")
    }
