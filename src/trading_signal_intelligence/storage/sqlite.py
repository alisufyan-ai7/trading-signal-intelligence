from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Iterator

from trading_signal_intelligence.models import Candle


_SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    source TEXT NOT NULL,
    source_symbol TEXT NOT NULL,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp_utc TEXT NOT NULL,
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL,
    volume_kind TEXT,
    spread REAL,
    is_closed INTEGER NOT NULL,
    PRIMARY KEY (source, source_symbol, timeframe, timestamp_utc)
);

CREATE INDEX IF NOT EXISTS idx_candles_canonical
ON candles(symbol, timeframe, timestamp_utc);

CREATE INDEX IF NOT EXISTS idx_candles_source
ON candles(source, source_symbol, timeframe, timestamp_utc);
"""


class CandleStore:
    """Small deterministic SQLite store for frozen research datasets.

    The store is intentionally local and simple. Production persistence can later
    move to Postgres without changing the normalized Candle model or strategy code.
    """

    def __init__(self, path: str | Path = "data/research.sqlite") -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.path)
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as connection:
            connection.executescript(_SCHEMA)

    def upsert_candles(self, candles: Iterable[Candle]) -> int:
        rows = [
            (
                candle.source,
                candle.source_symbol,
                candle.symbol,
                candle.timeframe,
                candle.timestamp_utc.astimezone(timezone.utc).isoformat(),
                float(candle.open),
                float(candle.high),
                float(candle.low),
                float(candle.close),
                float(candle.volume) if candle.volume is not None else None,
                candle.volume_kind,
                float(candle.spread) if candle.spread is not None else None,
                1 if candle.is_closed else 0,
            )
            for candle in candles
        ]
        if not rows:
            return 0

        with self.connection() as connection:
            connection.executemany(
                """
                INSERT INTO candles (
                    source, source_symbol, symbol, timeframe, timestamp_utc,
                    open, high, low, close, volume, volume_kind, spread, is_closed
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source, source_symbol, timeframe, timestamp_utc)
                DO UPDATE SET
                    symbol = excluded.symbol,
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    volume_kind = excluded.volume_kind,
                    spread = excluded.spread,
                    is_closed = excluded.is_closed
                """,
                rows,
            )
        return len(rows)

    def load_candles(
        self,
        *,
        source: str,
        source_symbol: str,
        timeframe: str,
        closed_only: bool = True,
    ) -> list[Candle]:
        where = "source = ? AND source_symbol = ? AND timeframe = ?"
        params: list[object] = [source, source_symbol, timeframe.upper()]
        if closed_only:
            where += " AND is_closed = 1"

        with self.connection() as connection:
            rows = connection.execute(
                f"""
                SELECT source, source_symbol, symbol, timeframe, timestamp_utc,
                       open, high, low, close, volume, volume_kind, spread, is_closed
                FROM candles
                WHERE {where}
                ORDER BY timestamp_utc ASC
                """,
                params,
            ).fetchall()

        return [
            Candle(
                source=row[0],
                source_symbol=row[1],
                symbol=row[2],
                timeframe=row[3],
                timestamp_utc=datetime.fromisoformat(row[4]).astimezone(timezone.utc),
                open=Decimal(str(row[5])),
                high=Decimal(str(row[6])),
                low=Decimal(str(row[7])),
                close=Decimal(str(row[8])),
                volume=Decimal(str(row[9])) if row[9] is not None else None,
                volume_kind=row[10],
                spread=Decimal(str(row[11])) if row[11] is not None else None,
                is_closed=bool(row[12]),
            )
            for row in rows
        ]

    def summary(self) -> list[dict[str, object]]:
        with self.connection() as connection:
            rows = connection.execute(
                """
                SELECT source, source_symbol, symbol, timeframe,
                       COUNT(*) AS bars,
                       MIN(timestamp_utc) AS first_timestamp,
                       MAX(timestamp_utc) AS last_timestamp
                FROM candles
                GROUP BY source, source_symbol, symbol, timeframe
                ORDER BY source, symbol, timeframe
                """
            ).fetchall()

        return [
            {
                "source": row[0],
                "source_symbol": row[1],
                "symbol": row[2],
                "timeframe": row[3],
                "bars": row[4],
                "first_timestamp_utc": row[5],
                "last_timestamp_utc": row[6],
            }
            for row in rows
        ]
