from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ALLOWED_RECORD_TYPES = {
    "ACTIVATION",
    "INFERENCE",
    "NO_TRADE",
    "REJECTED_INFERENCE",
    "SIGNAL",
    "PARTIAL_EXIT",
    "EXIT",
    "MISSED_INFERENCE",
    "ERROR",
}


_SCHEMA = """
CREATE TABLE IF NOT EXISTS ai_records (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    record_id TEXT NOT NULL UNIQUE,
    record_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    recorded_at_utc TEXT NOT NULL,
    effective_at_utc TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    previous_hash TEXT,
    record_hash TEXT NOT NULL UNIQUE,
    UNIQUE(record_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_ai_records_type
ON ai_records(record_type, sequence);

CREATE INDEX IF NOT EXISTS idx_ai_records_entity
ON ai_records(entity_id, sequence);

CREATE TRIGGER IF NOT EXISTS ai_records_no_update
BEFORE UPDATE ON ai_records
BEGIN
    SELECT RAISE(ABORT, 'AI ledger is append-only: UPDATE forbidden');
END;

CREATE TRIGGER IF NOT EXISTS ai_records_no_delete
BEFORE DELETE ON ai_records
BEGIN
    SELECT RAISE(ABORT, 'AI ledger is append-only: DELETE forbidden');
END;
"""


def _iso_utc(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("AI-ledger timestamps must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat()


def canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
        default=str,
    )


def _record_hash(
    *,
    record_id: str,
    record_type: str,
    entity_id: str,
    recorded_at_utc: str,
    effective_at_utc: str,
    payload_json: str,
    previous_hash: str | None,
) -> str:
    material = {
        "record_id": record_id,
        "record_type": record_type,
        "entity_id": entity_id,
        "recorded_at_utc": recorded_at_utc,
        "effective_at_utc": effective_at_utc,
        "payload_json": payload_json,
        "previous_hash": previous_hash,
    }
    return hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()


class AILedger:
    """Independent append-only hash-chained ledger for AI-v1."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        connection = self._connect()
        try:
            connection.executescript(_SCHEMA)
            connection.commit()
        finally:
            connection.close()

    def append(
        self,
        *,
        record_type: str,
        entity_id: str,
        effective_at_utc: datetime,
        payload: dict[str, Any],
        recorded_at_utc: datetime | None = None,
        record_id: str | None = None,
    ) -> dict[str, Any]:
        if record_type not in ALLOWED_RECORD_TYPES:
            raise ValueError(f"unsupported AI record type: {record_type}")

        recorded = _iso_utc(recorded_at_utc or datetime.now(timezone.utc))
        effective = _iso_utc(effective_at_utc)
        payload_json = canonical_json(payload)
        record_id = record_id or uuid.uuid4().hex

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            previous = connection.execute(
                "SELECT record_hash FROM ai_records ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous["record_hash"] if previous else None
            record_hash = _record_hash(
                record_id=record_id,
                record_type=record_type,
                entity_id=entity_id,
                recorded_at_utc=recorded,
                effective_at_utc=effective,
                payload_json=payload_json,
                previous_hash=previous_hash,
            )
            cursor = connection.execute(
                """
                INSERT INTO ai_records (
                    record_id, record_type, entity_id,
                    recorded_at_utc, effective_at_utc,
                    payload_json, previous_hash, record_hash
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record_id,
                    record_type,
                    entity_id,
                    recorded,
                    effective,
                    payload_json,
                    previous_hash,
                    record_hash,
                ),
            )
            sequence = int(cursor.lastrowid)
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

        return {
            "sequence": sequence,
            "record_id": record_id,
            "record_type": record_type,
            "entity_id": entity_id,
            "recorded_at_utc": recorded,
            "effective_at_utc": effective,
            "payload": json.loads(payload_json),
            "previous_hash": previous_hash,
            "record_hash": record_hash,
        }

    def records(
        self,
        *,
        record_type: str | None = None,
        entity_id: str | None = None,
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[object] = []
        if record_type is not None:
            where.append("record_type = ?")
            params.append(record_type)
        if entity_id is not None:
            where.append("entity_id = ?")
            params.append(entity_id)
        clause = (" WHERE " + " AND ".join(where)) if where else ""

        connection = self._connect()
        try:
            rows = connection.execute(
                f"""
                SELECT sequence, record_id, record_type, entity_id,
                       recorded_at_utc, effective_at_utc,
                       payload_json, previous_hash, record_hash
                FROM ai_records
                {clause}
                ORDER BY sequence ASC
                """,
                params,
            ).fetchall()
        finally:
            connection.close()

        return [
            {
                "sequence": int(row["sequence"]),
                "record_id": row["record_id"],
                "record_type": row["record_type"],
                "entity_id": row["entity_id"],
                "recorded_at_utc": row["recorded_at_utc"],
                "effective_at_utc": row["effective_at_utc"],
                "payload": json.loads(row["payload_json"]),
                "previous_hash": row["previous_hash"],
                "record_hash": row["record_hash"],
            }
            for row in rows
        ]

    def has(self, *, record_type: str, entity_id: str) -> bool:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT 1 FROM ai_records WHERE record_type = ? AND entity_id = ? LIMIT 1",
                (record_type, entity_id),
            ).fetchone()
            return row is not None
        finally:
            connection.close()

    def counts_by_type(self) -> dict[str, int]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT record_type, COUNT(*) AS n
                FROM ai_records
                GROUP BY record_type
                ORDER BY record_type
                """
            ).fetchall()
            return {str(row["record_type"]): int(row["n"]) for row in rows}
        finally:
            connection.close()

    def head_hash(self) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT record_hash FROM ai_records ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            return row["record_hash"] if row else None
        finally:
            connection.close()

    def verify(self) -> dict[str, Any]:
        rows = self.records()
        expected_previous: str | None = None
        for row in rows:
            payload_json = canonical_json(row["payload"])
            expected_hash = _record_hash(
                record_id=row["record_id"],
                record_type=row["record_type"],
                entity_id=row["entity_id"],
                recorded_at_utc=row["recorded_at_utc"],
                effective_at_utc=row["effective_at_utc"],
                payload_json=payload_json,
                previous_hash=expected_previous,
            )
            if row["previous_hash"] != expected_previous:
                return {
                    "valid": False,
                    "records": len(rows),
                    "failed_sequence": row["sequence"],
                    "reason": "previous_hash_mismatch",
                }
            if row["record_hash"] != expected_hash:
                return {
                    "valid": False,
                    "records": len(rows),
                    "failed_sequence": row["sequence"],
                    "reason": "record_hash_mismatch",
                }
            expected_previous = row["record_hash"]

        return {
            "valid": True,
            "records": len(rows),
            "head_hash": expected_previous,
        }

    def unresolved_signal_entities(self) -> list[str]:
        signals = {row["entity_id"] for row in self.records(record_type="SIGNAL")}
        exits = {row["entity_id"] for row in self.records(record_type="EXIT")}
        return sorted(signals - exits)
