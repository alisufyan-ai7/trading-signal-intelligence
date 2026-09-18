from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


_SCHEMA = """
CREATE TABLE IF NOT EXISTS forward_records (
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

CREATE INDEX IF NOT EXISTS idx_forward_records_type
ON forward_records(record_type, sequence);

CREATE INDEX IF NOT EXISTS idx_forward_records_entity
ON forward_records(entity_id, sequence);

CREATE TRIGGER IF NOT EXISTS forward_records_no_update
BEFORE UPDATE ON forward_records
BEGIN
    SELECT RAISE(ABORT, 'forward ledger is append-only: UPDATE forbidden');
END;

CREATE TRIGGER IF NOT EXISTS forward_records_no_delete
BEFORE DELETE ON forward_records
BEGIN
    SELECT RAISE(ABORT, 'forward ledger is append-only: DELETE forbidden');
END;
"""


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _utc_iso(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("Forward-ledger timestamps must be timezone-aware")
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


def sha256_json(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


class ForwardLedger:
    """Append-only, hash-chained local forward-test ledger."""

    def __init__(self, path: str | Path = "data/forward.sqlite") -> None:
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
        recorded = _utc_iso(recorded_at_utc or utc_now())
        effective = _utc_iso(effective_at_utc)
        payload_text = canonical_json(payload)
        record_id = record_id or uuid.uuid4().hex

        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            previous_row = connection.execute(
                "SELECT record_hash FROM forward_records ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            previous_hash = previous_row["record_hash"] if previous_row else None
            record_hash = _record_hash(
                record_id=record_id,
                record_type=record_type,
                entity_id=entity_id,
                recorded_at_utc=recorded,
                effective_at_utc=effective,
                payload_json=payload_text,
                previous_hash=previous_hash,
            )
            cursor = connection.execute(
                """
                INSERT INTO forward_records (
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
                    payload_text,
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
            "payload": json.loads(payload_text),
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
                FROM forward_records
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
                "SELECT 1 FROM forward_records WHERE record_type = ? AND entity_id = ? LIMIT 1",
                (record_type, entity_id),
            ).fetchone()
            return row is not None
        finally:
            connection.close()

    def head_hash(self) -> str | None:
        connection = self._connect()
        try:
            row = connection.execute(
                "SELECT record_hash FROM forward_records ORDER BY sequence DESC LIMIT 1"
            ).fetchone()
            return row["record_hash"] if row else None
        finally:
            connection.close()

    def verify(self) -> dict[str, Any]:
        records = self.records()
        expected_previous: str | None = None
        for row in records:
            payload_text = canonical_json(row["payload"])
            expected_hash = _record_hash(
                record_id=row["record_id"],
                record_type=row["record_type"],
                entity_id=row["entity_id"],
                recorded_at_utc=row["recorded_at_utc"],
                effective_at_utc=row["effective_at_utc"],
                payload_json=payload_text,
                previous_hash=expected_previous,
            )
            if row["previous_hash"] != expected_previous:
                return {
                    "valid": False,
                    "records": len(records),
                    "failed_sequence": row["sequence"],
                    "reason": "previous_hash_mismatch",
                }
            if row["record_hash"] != expected_hash:
                return {
                    "valid": False,
                    "records": len(records),
                    "failed_sequence": row["sequence"],
                    "reason": "record_hash_mismatch",
                }
            expected_previous = row["record_hash"]

        return {
            "valid": True,
            "records": len(records),
            "head_hash": expected_previous,
        }

    def counts_by_type(self) -> dict[str, int]:
        connection = self._connect()
        try:
            rows = connection.execute(
                """
                SELECT record_type, COUNT(*) AS n
                FROM forward_records
                GROUP BY record_type
                ORDER BY record_type
                """
            ).fetchall()
            return {str(row["record_type"]): int(row["n"]) for row in rows}
        finally:
            connection.close()

    def unresolved_signal_entities(self) -> list[str]:
        signals = {row["entity_id"] for row in self.records(record_type="SIGNAL")}
        exits = {row["entity_id"] for row in self.records(record_type="EXIT")}
        return sorted(signals - exits)
