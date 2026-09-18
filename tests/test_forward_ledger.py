from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone

import pytest

from trading_signal_intelligence.forward import ForwardLedger


def test_forward_ledger_hash_chain_and_append_only(tmp_path) -> None:
    path = tmp_path / "forward.sqlite"
    ledger = ForwardLedger(path)
    t0 = datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc)

    activation = ledger.append(
        record_type="ACTIVATION",
        entity_id="test",
        effective_at_utc=t0,
        recorded_at_utc=t0,
        payload={"strategy": "S02", "config": {"x": 1}},
    )
    signal = ledger.append(
        record_type="SIGNAL",
        entity_id="sig-1",
        effective_at_utc=t0 + timedelta(hours=1),
        recorded_at_utc=t0 + timedelta(hours=1, minutes=1),
        payload={"direction": "long", "entry": 100.0},
    )

    assert signal["previous_hash"] == activation["record_hash"]
    assert ledger.verify()["valid"] is True
    assert ledger.counts_by_type() == {"ACTIVATION": 1, "SIGNAL": 1}

    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("UPDATE forward_records SET entity_id = 'changed' WHERE sequence = 1")

    with sqlite3.connect(path) as connection:
        with pytest.raises(sqlite3.DatabaseError):
            connection.execute("DELETE FROM forward_records WHERE sequence = 1")


def test_forward_ledger_rejects_duplicate_type_entity(tmp_path) -> None:
    ledger = ForwardLedger(tmp_path / "forward.sqlite")
    now = datetime(2026, 9, 18, 10, 0, tzinfo=timezone.utc)
    ledger.append(
        record_type="ACTIVATION",
        entity_id="same",
        effective_at_utc=now,
        payload={"a": 1},
        recorded_at_utc=now,
    )

    with pytest.raises(sqlite3.IntegrityError):
        ledger.append(
            record_type="ACTIVATION",
            entity_id="same",
            effective_at_utc=now,
            payload={"a": 1},
            recorded_at_utc=now,
        )
