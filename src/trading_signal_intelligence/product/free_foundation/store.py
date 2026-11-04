"""PostgreSQL persistence boundary; no schema creation or implicit provisioning.

The module imports psycopg only when a feature-flagged endpoint actually uses
the database. Auth issuance is intentionally absent in P1A.
"""
from __future__ import annotations

from typing import Protocol
from urllib.parse import parse_qs, urlsplit

from trading_signal_intelligence.product.free_foundation.security import Identity


class MemberStore(Protocol):
    def find_session(self, token_sha256: str) -> Identity | None: ...
    def watchlist(self, user_id: str) -> list[str]: ...
    def save_market(self, user_id: str, symbol: str) -> list[str]: ...
    def delete_market(self, user_id: str, symbol: str) -> list[str]: ...


class PostgresMemberStore:
    def __init__(self, dsn: str):
        if not dsn or not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("An explicit PostgreSQL connection string is required")
        # Reject plaintext or hostname-unverified PostgreSQL connections.
        if parse_qs(urlsplit(dsn).query).get("sslmode") != ["verify-full"]:
            raise ValueError("PostgreSQL connection must use sslmode=verify-full")
        self._dsn = dsn

    def _connect(self):
        # Optional dependency: install .[app,free-app] only after provider approval.
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=5)

    def find_session(self, token_sha256: str) -> Identity | None:
        with self._connect() as conn:
            record = conn.execute(
                """SELECT u.id::text AS user_id, u.role, u.email_verified_at,
                          u.disabled_at, s.expires_at, s.revoked_at,
                          s.mfa_verified_at
                   FROM vowsig_free_sessions s
                   JOIN vowsig_free_users u ON u.id = s.user_id
                   WHERE s.token_sha256 = %s""",
                (token_sha256,),
            ).fetchone()
        return Identity(**record) if record else None

    def watchlist(self, user_id: str) -> list[str]:
        with self._connect() as conn:
            records = conn.execute(
                """SELECT symbol FROM vowsig_free_watchlist
                   WHERE user_id = %s::uuid ORDER BY created_at, symbol""",
                (user_id,),
            ).fetchall()
        return [record["symbol"] for record in records]

    def save_market(self, user_id: str, symbol: str) -> list[str]:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO vowsig_free_watchlist (user_id, symbol)
                   VALUES (%s::uuid, %s) ON CONFLICT DO NOTHING""",
                (user_id, symbol),
            )
            conn.execute(
                """INSERT INTO vowsig_free_audit (user_id, action, market_symbol)
                   VALUES (%s::uuid, 'watchlist_saved', %s)""",
                (user_id, symbol),
            )
        return self.watchlist(user_id)

    def delete_market(self, user_id: str, symbol: str) -> list[str]:
        with self._connect() as conn:
            conn.execute(
                """DELETE FROM vowsig_free_watchlist
                   WHERE user_id = %s::uuid AND symbol = %s""",
                (user_id, symbol),
            )
            conn.execute(
                """INSERT INTO vowsig_free_audit (user_id, action, market_symbol)
                   VALUES (%s::uuid, 'watchlist_removed', %s)""",
                (user_id, symbol),
            )
        return self.watchlist(user_id)
