"""PostgreSQL persistence boundary; no schema creation or implicit provisioning.

The module imports psycopg only when a feature-flagged endpoint actually uses
the database. Auth issuance is intentionally absent in P1A.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol
from uuid import uuid4
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
                   WHERE s.token_sha256 = %s
                     AND s.revoked_at IS NULL AND s.expires_at > now()
                     AND a.disabled_at IS NULL
                     AND a.email_verified_at IS NOT NULL""",
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


    def complete_verified_login(
        self, *, issuer: str, subject: str, verified_email: str,
        token_sha256: str, issued_at: datetime, expires_at: datetime,
    ) -> str:
        """Create new member or reuse exactly bound identity in ONE transaction.

        The caller MUST already have cryptographically verified OIDC results.
        Never attach by matching email; a collision aborts the transaction.
        """
        if (
            issued_at.tzinfo is None or expires_at.tzinfo is None
            or not issued_at < expires_at <= issued_at + timedelta(days=7)
            or len(token_sha256) != 64
        ):
            raise ValueError("Invalid session TTL or token digest")
        with self._connect() as conn:
            existing = conn.execute(
                """SELECT a.id::text AS account_id, a.email
                   FROM vowsig_account_identities i
                   JOIN vowsig_accounts a ON a.id=i.account_id
                   JOIN vowsig_account_entitlements e ON e.account_id=a.id
                   WHERE i.issuer=%s AND i.subject=%s
                     AND a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL AND e.status='active'
                   FOR UPDATE OF a""",
                (issuer, subject),
            ).fetchone()
            if existing:
                if existing["email"].strip().casefold() != verified_email.strip().casefold():
                    raise ValueError("Verified identity email changed; account review required")
                account_id = existing["account_id"]
            else:
                # Existing email with different issuer+subject raises unique violation
                # instead of silently binding a second identity.
                account_id = str(uuid4())
                conn.execute(
                    """INSERT INTO vowsig_accounts
                       (id,email,role,email_verified_at)
                       VALUES (%s::uuid,%s,'member',%s)""",
                    (account_id, verified_email, issued_at),
                )
                conn.execute(
                    """INSERT INTO vowsig_account_entitlements
                       (account_id, access_tier, status)
                       VALUES (%s::uuid,'research_free','active')""",
                    (account_id,),
                )
                conn.execute(
                    """INSERT INTO vowsig_account_identities
                       (account_id,issuer,subject,last_verified_at)
                       VALUES (%s::uuid,%s,%s,%s)""",
                    (account_id, issuer, subject, issued_at),
                )
            # Revoking previous sessions limits fixation and multi-device replay.
            conn.execute(
                """UPDATE vowsig_account_sessions SET revoked_at=%s
                   WHERE account_id=%s::uuid AND revoked_at IS NULL""",
                (issued_at, account_id),
            )
            conn.execute(
                """INSERT INTO vowsig_account_sessions
                   (token_sha256,account_id,created_at,expires_at)
                   VALUES (%s,%s::uuid,%s,%s)""",
                (token_sha256, account_id, issued_at, expires_at),
            )
        return account_id

    def revoke_session(self, token_sha256: str, account_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                """UPDATE vowsig_account_sessions SET revoked_at=now()
                   WHERE token_sha256=%s AND account_id=%s::uuid
                     AND revoked_at IS NULL
                   RETURNING token_sha256""",
                (token_sha256, account_id),
            ).fetchone()
        return row is not None

    def preferences(self, account_id: str) -> dict[str, Any]:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT timezone,educational_level,research_updates_opt_in
                   FROM vowsig_account_preferences
                   WHERE account_id=%s::uuid""",
                (account_id,),
            ).fetchone()
        return dict(row) if row else {
            "timezone": "UTC", "educational_level": "beginner",
            "research_updates_opt_in": False,
        }

    def update_preferences(self, account_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        # Validated by member_profile; defaults are only for absent columns.
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO vowsig_account_preferences
                   (account_id,timezone,educational_level,research_updates_opt_in)
                   VALUES (%s::uuid,COALESCE(%s,'UTC'),COALESCE(%s,'beginner'),
                           COALESCE(%s,FALSE))
                   ON CONFLICT (account_id) DO UPDATE SET
                     timezone=COALESCE(%s,vowsig_account_preferences.timezone),
                     educational_level=COALESCE(
                         %s,vowsig_account_preferences.educational_level),
                     research_updates_opt_in=COALESCE(
                         %s,vowsig_account_preferences.research_updates_opt_in),
                     updated_at=now()""",
                (account_id,patch.get("timezone"),patch.get("educational_level"),
                 patch.get("research_updates_opt_in"),
                 patch.get("timezone"),patch.get("educational_level"),
                 patch.get("research_updates_opt_in")),
            )
            if "research_updates_opt_in" in patch:
                conn.execute(
                    """INSERT INTO vowsig_account_consent_events
                       (account_id,purpose,opted_in)
                       VALUES (%s::uuid,'research_product_updates',%s)""",
                    (account_id,patch["research_updates_opt_in"]),
                )
        return self.preferences(account_id)

    def saved_research(self, account_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT signal_id,source_symbol,created_at
                   FROM vowsig_saved_research WHERE account_id=%s::uuid
                   ORDER BY created_at DESC,signal_id LIMIT 100""",
                (account_id,),
            ).fetchall()
        return [{"signal_id":r["signal_id"], "symbol":r["source_symbol"],
                 "saved_at_utc":r["created_at"].isoformat()} for r in rows]

    def save_research(self, account_id: str, symbol: str, signal_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO vowsig_saved_research(account_id,source_symbol,signal_id)
                   VALUES (%s::uuid,%s,%s) ON CONFLICT DO NOTHING""",
                (account_id,symbol,signal_id),
            )

    def unsave_research(self, account_id: str, signal_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                """DELETE FROM vowsig_saved_research
                   WHERE account_id=%s::uuid AND signal_id=%s""",
                (account_id,signal_id),
            )

    def account_export(self, account_id: str) -> dict[str, Any]:
        """Own account's basic data only; never a substitute for legal full export."""
        with self._connect() as conn:
            row=conn.execute(
                """SELECT id::text AS account_id,email,created_at,
                          email_verified_at,role FROM vowsig_accounts
                   WHERE id=%s::uuid AND disabled_at IS NULL""",
                (account_id,),
            ).fetchone()
            consent=conn.execute(
                """SELECT purpose,opted_in,recorded_at FROM vowsig_account_consent_events
                   WHERE account_id=%s::uuid ORDER BY recorded_at DESC LIMIT 200""",
                (account_id,),
            ).fetchall()
            deletion=conn.execute(
                """SELECT status,requested_at FROM vowsig_account_deletion_requests
                   WHERE account_id=%s::uuid""", (account_id,),
            ).fetchone()
        if row is None:
            raise ValueError("Account unavailable")
        return {
            "account_id": row["account_id"], "email": row["email"],
            "role": row["role"], "created_at_utc": row["created_at"].isoformat(),
            "email_verified_at_utc": (
                row["email_verified_at"].isoformat() if row["email_verified_at"] else None
            ),
            "consent_events": [{
                "purpose":x["purpose"],"opted_in":x["opted_in"],
                "recorded_at_utc":x["recorded_at"].isoformat(),
            } for x in consent],
            "consent_history_complete": len(consent) < 200,
            "deletion_request": ({
                "status":deletion["status"],
                "requested_at_utc":deletion["requested_at"].isoformat(),
            } if deletion else None),
        }

    def request_deletion(self, account_id: str) -> dict[str, str]:
        """Record an intent for reverified deletion; do NOT actually erase data."""
        with self._connect() as conn:
            row=conn.execute(
                """INSERT INTO vowsig_account_deletion_requests
                   (account_id,status) VALUES (%s::uuid,'pending_reverification')
                   ON CONFLICT (account_id) DO UPDATE SET
                     status=CASE WHEN vowsig_account_deletion_requests.status='cancelled'
                                 THEN 'pending_reverification'
                                 ELSE vowsig_account_deletion_requests.status END
                   RETURNING status,requested_at""",
                (account_id,),
            ).fetchone()
        return {
            "status":row["status"], "requested_at_utc":row["requested_at"].isoformat(),
            "notice":"Request recorded. No data is erased until verified owner-reviewed processing.",
        }

    def admin_growth(self) -> dict[str, Any]:
        """Verified account and watchlist counts only; privacy-safe aggregates."""
        with self._connect() as conn:
            accounts=conn.execute(
                """SELECT count(*) AS total,
                          count(*) FILTER (WHERE email_verified_at IS NOT NULL)
                            AS verified
                   FROM vowsig_accounts WHERE disabled_at IS NULL""",
            ).fetchone()
            watchlists=conn.execute(
                """SELECT count(DISTINCT w.account_id) AS with_watchlist
                   FROM vowsig_watchlist_items w
                   JOIN vowsig_accounts a ON a.id=w.account_id
                   WHERE a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL""",
            ).fetchone()
        verified=accounts["verified"]
        return {
            "source":"account_database_aggregate",
            "registered_accounts":accounts["total"],
            "verified_accounts":verified,
            "accounts_with_watchlist":watchlists["with_watchlist"],
            "activation_rate": (
                watchlists["with_watchlist"] / verified if verified else None
            ),
            "retention_7d":None,"revenue":None,
            "retention_notice":"No privacy-reviewed D7 cohort collection or billing enabled.",
        }

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
