"""PostgreSQL persistence boundary; no schema creation or implicit provisioning.

The module imports psycopg only when a feature-flagged endpoint actually uses
the database. Auth issuance is intentionally absent in P1A.
"""
from __future__ import annotations

from typing import Protocol
from urllib.parse import parse_qs, urlsplit

from trading_signal_intelligence.product.accounts.security import Identity


class AccountStore(Protocol):
    def find_session(self, token_sha256: str) -> Identity | None: ...
    def watchlist(self, account_id: str) -> list[str]: ...
    def save_market(self, account_id: str, symbol: str) -> list[str]: ...
    def delete_market(self, account_id: str, symbol: str) -> list[str]: ...


class PostgresAccountStore:
    def __init__(self, dsn: str):
        if not dsn or not dsn.startswith(("postgresql://", "postgres://")):
            raise ValueError("An explicit PostgreSQL connection string is required")
        # Reject plaintext or hostname-unverified PostgreSQL connections.
        if parse_qs(urlsplit(dsn).query).get("sslmode") != ["verify-full"]:
            raise ValueError("PostgreSQL connection must use sslmode=verify-full")
        self._dsn = dsn

    def _connect(self):
        # Optional dependency: install .[app,accounts] only after provider approval.
        import psycopg
        from psycopg.rows import dict_row

        return psycopg.connect(self._dsn, row_factory=dict_row, connect_timeout=5)

    def find_session(self, token_sha256: str) -> Identity | None:
        with self._connect() as conn:
            record = conn.execute(
                """SELECT a.id::text AS account_id, a.role, e.access_tier,
                          a.email_verified_at, a.disabled_at, s.expires_at,
                          s.revoked_at, s.mfa_verified_at
                   FROM vowsig_account_sessions s
                   JOIN vowsig_accounts a ON a.id = s.account_id
                   JOIN vowsig_account_entitlements e
                     ON e.account_id = a.id AND e.status = 'active'
                   WHERE s.token_sha256 = %s""",
                (token_sha256,),
            ).fetchone()
        return Identity(**record) if record else None

    def find_bound_account(self, issuer: str, subject: str) -> str | None:
        """Exact OIDC issuer+subject lookup only, never automatic email linking.

        This method is NOT a callback verifier. The caller must first use the
        trusted identity adapter and validate_verified_claims to establish the
        cryptographically verified identity.
        """
        with self._connect() as conn:
            row = conn.execute(
                """SELECT a.id::text AS account_id
                   FROM vowsig_account_identities i
                   JOIN vowsig_accounts a ON a.id = i.account_id
                   JOIN vowsig_account_entitlements e ON e.account_id = a.id
                   WHERE i.issuer = %s AND i.subject = %s
                     AND a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL
                     AND e.status = 'active'""",
                (issuer, subject),
            ).fetchone()
        return row["account_id"] if row else None

    def watchlist(self, account_id: str) -> list[str]:
        with self._connect() as conn:
            records = conn.execute(
                """SELECT symbol FROM vowsig_watchlist_items
                   WHERE account_id = %s::uuid ORDER BY created_at, symbol""",
                (account_id,),
            ).fetchall()
        return [record["symbol"] for record in records]

    def save_market(self, account_id: str, symbol: str) -> list[str]:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO vowsig_watchlist_items (account_id, symbol)
                   VALUES (%s::uuid, %s) ON CONFLICT DO NOTHING""",
                (account_id, symbol),
            )
            conn.execute(
                """INSERT INTO vowsig_account_audit (account_id, action, market_symbol)
                   VALUES (%s::uuid, 'watchlist_saved', %s)""",
                (account_id, symbol),
            )
        return self.watchlist(account_id)

    def delete_market(self, account_id: str, symbol: str) -> list[str]:
        with self._connect() as conn:
            conn.execute(
                """DELETE FROM vowsig_watchlist_items
                   WHERE account_id = %s::uuid AND symbol = %s""",
                (account_id, symbol),
            )
            conn.execute(
                """INSERT INTO vowsig_account_audit (account_id, action, market_symbol)
                   VALUES (%s::uuid, 'watchlist_removed', %s)""",
                (account_id, symbol),
            )
        return self.watchlist(account_id)
