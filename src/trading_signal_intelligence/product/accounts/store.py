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


class AccountLinkConflict(ValueError):
    """A verified identity cannot be silently linked to an occupied email."""


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

    def take_auth_budget(self, peer_digest: str) -> bool:
        """Atomic 30-per-ten-minute coarse peer throttle, no raw IP stored."""
        now = datetime.now(timezone.utc)
        bucket = datetime.fromtimestamp(
            int(now.timestamp()) // 600 * 600, timezone.utc,
        )
        with self._connect() as conn:
            row = conn.execute(
                """INSERT INTO vowsig_auth_rate_windows
                   (subject_digest,bucket_start,attempts)
                   VALUES (%s,%s,1)
                   ON CONFLICT (subject_digest,bucket_start)
                   DO UPDATE SET attempts=vowsig_auth_rate_windows.attempts+1
                   WHERE vowsig_auth_rate_windows.attempts < 30
                   RETURNING attempts""",
                (peer_digest, bucket),
            ).fetchone()
        return row is not None

    def begin_oidc(
        self, *, state_sha256: str, browser_sha256: str,
        code_verifier: str, nonce: str,
    ) -> None:
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO vowsig_oidc_authorizations
                   (state_sha256,browser_sha256,code_verifier,nonce,expires_at)
                   VALUES (%s,%s,%s,%s,now()+interval '10 minutes')""",
                (state_sha256,browser_sha256,code_verifier,nonce),
            )

    def consume_oidc(self, state_sha256: str, browser_sha256: str) -> dict[str, str] | None:
        """Single-use consume is atomic even across concurrent app workers."""
        with self._connect() as conn:
            row = conn.execute(
                """DELETE FROM vowsig_oidc_authorizations
                   WHERE state_sha256=%s AND browser_sha256=%s
                     AND expires_at>now()
                   RETURNING code_verifier,nonce""",
                (state_sha256,browser_sha256),
            ).fetchone()
        return dict(row) if row else None

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
        from psycopg import errors

        try:
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
                        raise AccountLinkConflict("Verified identity email changed; manual review required")
                    account_id = existing["account_id"]
                else:
                    # Existing email with different issuer+subject raises unique violation
                    # instead of silently binding a second identity.
                    account_id = str(uuid4())
                    conn.execute(
                        """INSERT INTO vowsig_accounts
                           (id,email,email_verified_at)
                           VALUES (%s::uuid,%s,%s)""",
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
        except errors.UniqueViolation as exc:
            # Unique issuer+subject, one-issuer-per-account or casefolded email
            # collisions must not reveal whether an email exists.
            raise AccountLinkConflict("Verified account link conflict") from exc
        return account_id

    def verify_owner_totp(
        self, *, token_sha256: str, account_id: str, code: str,
        master_key_b64: str, now: datetime | None = None,
    ) -> tuple[datetime, str, datetime]:
        """Atomic, cross-worker replay-safe MFA; no online enrollment.

        Rotate the original session cookie token atomically with accepted MFA,
        preventing theft of a pre-MFA session from inheriting the elevation.
        Failed attempts are persisted before rejecting the HTTP request.
        """
        from trading_signal_intelligence.product.accounts.owner_mfa import (
            OwnerMfaConfigurationError, OwnerMfaRejected, decrypt_for_owner,
            load_master_key, match_step, MFA_LOCK_AFTER, MFA_LOCK_SECONDS,
        )
        if not isinstance(token_sha256, str) or len(token_sha256) != 64:
            raise OwnerMfaRejected("Owner verification rejected")
        key = load_master_key(master_key_b64)
        current = now or datetime.now(timezone.utc)
        if current.tzinfo is None:
            raise OwnerMfaConfigurationError("MFA clock must be timezone-aware")
        current = current.astimezone(timezone.utc)
        verified = False
        rotated_token = None
        rotated_expires = None
        with self._connect() as conn:
            row = conn.execute(
                """SELECT c.secret_ciphertext,c.last_accepted_step,
                          c.failed_attempts,c.locked_until,
                          s.expires_at AS session_expires_at
                   FROM vowsig_owner_totp_credentials c
                   JOIN vowsig_accounts a ON a.id=c.account_id
                   JOIN vowsig_account_sessions s ON s.account_id=a.id
                   JOIN vowsig_account_entitlements e ON e.account_id=a.id
                   WHERE a.id=%s::uuid AND a.role='owner'
                     AND a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL
                     AND e.status='active'
                     AND s.token_sha256=%s
                     AND s.revoked_at IS NULL AND s.expires_at>%s
                   FOR UPDATE OF c,s""",
                (account_id,token_sha256,current),
            ).fetchone()
            if row is None:
                raise OwnerMfaRejected("Owner verification rejected")
            if row["locked_until"] is not None and row["locked_until"] > current:
                raise OwnerMfaRejected("Owner verification temporarily locked")
            secret = decrypt_for_owner(
                bytes(row["secret_ciphertext"]), account_id, key,
            )
            step = match_step(
                code, secret, now=current, last_step=int(row["last_accepted_step"]),
            )
            if step is None:
                attempts = int(row["failed_attempts"]) + 1
                locked = (
                    current + timedelta(seconds=MFA_LOCK_SECONDS)
                    if attempts >= MFA_LOCK_AFTER else None
                )
                conn.execute(
                    """UPDATE vowsig_owner_totp_credentials
                       SET failed_attempts=%s, locked_until=%s
                       WHERE account_id=%s::uuid""",
                    (0 if locked is not None else attempts, locked, account_id),
                )
            else:
                conn.execute(
                    """UPDATE vowsig_owner_totp_credentials
                       SET last_accepted_step=%s, failed_attempts=0,
                           locked_until=NULL
                       WHERE account_id=%s::uuid""",
                    (step, account_id),
                )
                import hashlib
                import secrets
                rotated_token = secrets.token_urlsafe(32)
                if len(rotated_token) != 43:
                    raise OwnerMfaConfigurationError("Invalid rotated session token")
                new_hash = hashlib.sha256(rotated_token.encode("ascii")).hexdigest()
                changed = conn.execute(
                    """UPDATE vowsig_account_sessions
                       SET token_sha256=%s, mfa_verified_at=%s
                       WHERE token_sha256=%s AND account_id=%s::uuid
                         AND revoked_at IS NULL AND expires_at>%s
                       RETURNING expires_at""",
                    (new_hash,current,token_sha256,account_id,current),
                ).fetchone()
                if changed is None:
                    raise OwnerMfaRejected("Owner session expired")
                rotated_expires = changed["expires_at"]
                verified = True
        if not verified:
            raise OwnerMfaRejected("Owner verification rejected")
        assert rotated_token is not None and rotated_expires is not None
        return current, rotated_token, rotated_expires

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

    def admin_verified_performance(self) -> dict[str, Any]:
        """Verify one independently attested cohort; never infer platform history.

        Both the signed manifest AND a trusted reviewer public key fingerprint
        must be configured through the application's private runtime settings.
        Neither this method nor an API endpoint can sign, promote or ingest data.
        """
        import hashlib
        import os
        from pathlib import Path

        from trading_signal_intelligence.product.accounts.verified_history import (
            HistoryAttestationError, verify_signed_history_attestation,
            reconcile_attested_history,
        )

        unavailable = {
            "status": "awaiting_complete_source_reconciliation",
            "verified_full_history": False,
            "verified_full_cohort_history": False,
            "source_ledger_independently_reconciled": False,
            "performance": None,
        }
        document_path = os.environ.get("VOWSIG_HISTORY_SIGNED_ATTESTATION_PATH", "")
        reviewer_path = os.environ.get("VOWSIG_HISTORY_REVIEWER_PUBLIC_KEY_PATH", "")
        key_sha = os.environ.get("VOWSIG_HISTORY_REVIEWER_PUBLIC_KEY_SHA256", "")
        if not any((document_path, reviewer_path, key_sha)):
            return unavailable
        if not all((document_path, reviewer_path, key_sha)):
            return {**unavailable, "status": "independent_evidence_configuration_incomplete"}
        try:
            if len(key_sha) != 64 or any(c not in "0123456789abcdef" for c in key_sha):
                raise HistoryAttestationError("Reviewer trust pin missing")
            doc = Path(document_path)
            key = Path(reviewer_path)
            if doc.stat().st_size > 64_000 or key.stat().st_size > 4_096:
                raise HistoryAttestationError("Invalid attestation/key size")
            key_pem = key.read_bytes()
            if hashlib.sha256(key_pem).hexdigest() != key_sha:
                raise HistoryAttestationError("Reviewer public key not pinned")
            att = verify_signed_history_attestation(
                doc.read_bytes(), reviewer_public_key_pem=key_pem,
            )
            with self._connect() as conn:
                snapshots = conn.execute(
                    """SELECT source_program_id, model_version,
                              source_snapshot_sha256, source_head_hash,
                              ingest_status, completeness_verified, id
                       FROM vowsig_research_source_snapshots
                       WHERE source_program_id=%s AND model_version=%s
                         AND source_snapshot_sha256=%s
                       LIMIT 2""",
                    (att["source_program_id"], att["model_version"],
                     att["source_snapshot_sha256"]),
                ).fetchall()
                if len(snapshots) != 1:
                    raise HistoryAttestationError("Missing unique source projection")
                rows = conn.execute(
                    """SELECT entity_id, source_record_sha256, state,
                              exit_at_utc, combined_net_r, cost_model_version,
                              after_costs_verified, cohort
                       FROM vowsig_research_outcome_facts
                       WHERE source_snapshot_id=%s ORDER BY entity_id
                       LIMIT 250001""",
                    (snapshots[0]["id"],),
                ).fetchall()
            result = reconcile_attested_history(
                att, snapshot=snapshots[0], facts=[dict(row) for row in rows],
            )
            return result
        except (HistoryAttestationError, OSError, ValueError):
            # Never degrade to bounded public snapshot or trust a database
            # completeness flag alone when the reviewer signature is invalid.
            return {**unavailable, "status": "independent_evidence_rejected"}

    def admin_evidence_inventory(self) -> dict[str, Any]:
        """Owner-only projection inventory; never asserts independent verification.

        Only stored source projections are counted. A verified *database flag*
        is not independent source authentication, population coverage, rights
        clearance or proof of after-cost historical analytics. No source event
        payload or customer PII is exposed by this method.
        """
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT s.source_program_id, s.model_version,
                          s.source_snapshot_sha256, s.source_head_hash,
                          s.observed_at_utc, s.ingest_status,
                          s.completeness_verified,
                          count(f.entity_id) AS projected_records,
                          count(f.entity_id) FILTER (WHERE f.state='closed')
                            AS projected_closed,
                          count(f.entity_id) FILTER (WHERE f.state='open')
                            AS projected_open,
                          count(f.entity_id) FILTER (WHERE f.state='no_trade')
                            AS projected_no_trade,
                          count(f.entity_id) FILTER (WHERE f.state='rejected')
                            AS projected_rejected,
                          count(f.entity_id) FILTER (WHERE f.state='error')
                            AS projected_error,
                          count(f.entity_id) FILTER
                            (WHERE f.state='closed'
                               AND f.after_costs_verified=TRUE)
                            AS projected_closed_after_costs
                   FROM vowsig_research_source_snapshots AS s
                   LEFT JOIN vowsig_research_outcome_facts AS f
                     ON f.source_snapshot_id=s.id
                   GROUP BY s.id
                   ORDER BY s.observed_at_utc DESC, s.id DESC
                   LIMIT 101"""
            ).fetchall()
        truncated = len(rows) > 100
        # A projection record count is NEVER silently treated as an independently
        # verified complete source-ledger population.
        return {
            "source": "research_projection_database",
            "source_ledger_independently_reconciled": False,
            "historical_performance_publishing_permitted": False,
            "verified_full_history": False,
            "status": "awaiting_independent_source_reconciliation",
            "snapshots": [{
                "source_program_id": row["source_program_id"],
                "model_version": row["model_version"],
                "source_snapshot_sha256": row["source_snapshot_sha256"],
                "source_head_hash": row["source_head_hash"],
                "observed_at_utc": row["observed_at_utc"].isoformat(),
                "ingest_status": row["ingest_status"],
                "database_completeness_flag": row["completeness_verified"],
                "projected_records": row["projected_records"],
                "projected_closed": row["projected_closed"],
                "projected_open": row["projected_open"],
                "projected_no_trade": row["projected_no_trade"],
                "projected_rejected": row["projected_rejected"],
                "projected_error": row["projected_error"],
                "projected_closed_after_costs": row["projected_closed_after_costs"],
                "independently_verified": False,
            } for row in rows[:100]],
            "inventory_truncated": truncated,
            "next_evidence_required": (
                "Independent original-ledger source rights, immutable hashes, "
                "full cohort counts, after-cost outcomes, and reviewer sign-off."
            ),
        }

    def admin_model_diagnostics(self) -> dict[str, Any]:
        """Actual database projection populations by program/version/cohort.

        Stored 'verified' is a DATABASE flag, not independent original-ledger
        approval. Never derive profitability/accuracy from these rows.
        Cohorts lacking facts are explicitly reported as unclassified.
        """
        with self._connect() as conn:
            rows=conn.execute(
                """SELECT s.source_program_id,s.model_version,
                          coalesce(f.cohort,'unclassified') AS cohort,
                          s.ingest_status,
                          count(DISTINCT s.id) AS source_projections,
                          count(f.entity_id) AS projected_outcomes,
                          count(f.entity_id) FILTER (WHERE f.state='closed')
                            AS projected_closed,
                          count(f.entity_id) FILTER (WHERE f.state='open')
                            AS projected_open,
                          count(f.entity_id) FILTER (WHERE f.state='no_trade')
                            AS projected_no_trade,
                          count(f.entity_id) FILTER (WHERE f.state='rejected')
                            AS projected_rejected,
                          count(f.entity_id) FILTER (WHERE f.state='error')
                            AS projected_error,
                          count(f.entity_id) FILTER (
                            WHERE f.state='closed' AND f.after_costs_verified=TRUE
                          ) AS projected_cost_flagged_closed,
                          max(s.observed_at_utc) AS last_observed_at_utc
                   FROM vowsig_research_source_snapshots s
                   LEFT JOIN vowsig_research_outcome_facts f
                     ON f.source_snapshot_id=s.id
                   GROUP BY s.source_program_id,s.model_version,
                            coalesce(f.cohort,'unclassified'),s.ingest_status
                   ORDER BY max(s.observed_at_utc) DESC,
                            s.source_program_id,s.model_version,cohort,s.ingest_status
                   LIMIT 101"""
            ).fetchall()
        return {
            "source":"postgres_research_projection_only",
            "model_version_history_verified":False,
            "all_market_performance_verified":False,
            "complete_historical_track_record_available":False,
            "groups_truncated":len(rows)>100,
            "groups":[{
                "source_program_id":r["source_program_id"],
                "model_version":r["model_version"],
                "cohort":r["cohort"],
                "projection_ingest_status":r["ingest_status"],
                "source_projection_count":int(r["source_projections"]),
                "projected_outcomes":int(r["projected_outcomes"]),
                "projected_closed":int(r["projected_closed"]),
                "projected_open":int(r["projected_open"]),
                "projected_no_trade":int(r["projected_no_trade"]),
                "projected_rejected":int(r["projected_rejected"]),
                "projected_error":int(r["projected_error"]),
                "database_cost_flagged_closed":int(r["projected_cost_flagged_closed"]),
                "last_observed_at_utc":r["last_observed_at_utc"].isoformat(),
                "source_ledger_independently_audited":False,
                "historical_return_metrics":None,
            } for r in rows[:100]],
            "notice":(
                "These are exact PostgreSQL projection counts, NOT independently "
                "verified trades, model accuracy, R returns or current VPS health. "
                "An after-cost flag in the database is not an independent audit."
            ),
        }

    def admin_growth(self) -> dict[str, Any]:
        """Privacy-safe *observed* owner growth/security metrics from actual SQL.

        Returning login events are NOT complete D7 retention when session
        records may be purged. No dollar revenue or subscription claims.
        """
        with self._connect() as conn:
            accounts=conn.execute(
                """SELECT count(*) AS total,
                          count(*) FILTER (WHERE email_verified_at IS NOT NULL)
                            AS verified,
                          count(*) FILTER (WHERE created_at >= now()-interval '24 hours')
                            AS created_24h,
                          count(*) FILTER (WHERE created_at >= now()-interval '7 days')
                            AS created_7d,
                          count(*) FILTER (WHERE created_at >= now()-interval '30 days')
                            AS created_30d
                   FROM vowsig_accounts WHERE disabled_at IS NULL"""
            ).fetchone()
            watchlists=conn.execute(
                """SELECT count(DISTINCT w.account_id) AS with_watchlist
                   FROM vowsig_watchlist_items w
                   JOIN vowsig_accounts a ON a.id=w.account_id
                   WHERE a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL"""
            ).fetchone()
            saved=conn.execute(
                """SELECT count(DISTINCT r.account_id) AS with_saved
                   FROM vowsig_saved_research r
                   JOIN vowsig_accounts a ON a.id=r.account_id
                   WHERE a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL"""
            ).fetchone()
            consent=conn.execute(
                """SELECT count(*) AS opted_in
                   FROM vowsig_account_preferences p
                   JOIN vowsig_accounts a ON a.id=p.account_id
                   WHERE p.research_updates_opt_in=TRUE
                     AND a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL"""
            ).fetchone()
            deletions=conn.execute(
                """SELECT count(*) AS pending
                   FROM vowsig_account_deletion_requests d
                   JOIN vowsig_accounts a ON a.id=d.account_id
                   WHERE d.status IN ('pending_reverification','under_review')
                     AND a.disabled_at IS NULL"""
            ).fetchone()
            sessions=conn.execute(
                """SELECT count(*) FILTER (
                            WHERE s.revoked_at IS NULL AND s.expires_at>now()
                          ) AS currently_valid,
                          count(*) FILTER (
                            WHERE s.created_at >= now()-interval '7 days'
                          ) AS issued_7d
                   FROM vowsig_account_sessions s
                   JOIN vowsig_accounts a ON a.id=s.account_id
                   WHERE a.disabled_at IS NULL"""
            ).fetchone()
            owner_factors=conn.execute(
                """SELECT count(*) AS enrolled_owner_count
                   FROM vowsig_owner_totp_credentials m
                   JOIN vowsig_accounts a ON a.id=m.account_id
                   WHERE a.role='owner' AND a.email_verified_at IS NOT NULL
                     AND a.disabled_at IS NULL"""
            ).fetchone()
        verified=int(accounts["verified"])
        total=int(accounts["total"])
        with_watchlist=int(watchlists["with_watchlist"])
        return {
            "source":"account_database_aggregate",
            "registered_accounts":total,
            "verified_accounts":verified,
            "unverified_accounts":total-verified,
            "new_accounts_24h":int(accounts["created_24h"]),
            "new_accounts_7d":int(accounts["created_7d"]),
            "new_accounts_30d":int(accounts["created_30d"]),
            "verified_rate":verified/total if total else None,
            "accounts_with_watchlist":with_watchlist,
            "accounts_with_saved_research":int(saved["with_saved"]),
            "research_updates_opted_in_accounts":int(consent["opted_in"]),
            "pending_deletion_requests":int(deletions["pending"]),
            "valid_account_sessions_now":int(sessions["currently_valid"]),
            "issued_sessions_last_7d":int(sessions["issued_7d"]),
            "owner_totp_enrolled_accounts":int(owner_factors["enrolled_owner_count"]),
            "activation_rate":with_watchlist/verified if verified else None,
            "retention_7d":None,
            "revenue":None,
            "retention_notice":"D7 user retention is NOT yet instrumented; session issue counts are not retention.",
            "backup_restore_proven":False,
            "backup_notice":"Railway PostgreSQL backup and independent restore remain unverified; owner accepted post-launch integration.",
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
