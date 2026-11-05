"""CI-only PG18 role separation, DDL boundary, and immutable-history write denial.

NO production endpoints, passwords, network proxies, or Railway credentials.
The roles and schema are created only in a separate disposable database.
"""
from __future__ import annotations

import os
from pathlib import Path

import psycopg
from psycopg import errors

ROOT = Path(__file__).resolve().parents[1]
MIGRATIONS = [
    "001_accounts_sessions_entitlements_watchlist.sql",
    "002_verified_identity_binding.sql",
    "003_preferences_and_saved_research.sql",
    "004_research_read_model_contract.sql",
    "005_consent_audit_deletion_requests.sql",
    "006_oidc_auth_transactions.sql",
    "007_restricted_roles_and_grants.sql",
    "008_owner_mfa_stepup.sql",
    "009_owner_offline_provisioning_audit.sql",
]


def _guard() -> str:
    expected = "postgresql://vowsig_test:local-ci-only-test-password@127.0.0.1:5432/vowsig_test?sslmode=disable"
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY") != "alisufyan-ai7/trading-signal-intelligence"
        or os.environ.get("VOWSIG_EPHEMERAL_PG_TEST_CONFIRM") != "YES_THROWAWAY_DATABASE"
        or os.environ.get("VOWSIG_EPHEMERAL_PG_TEST_DSN") != expected
    ):
        raise RuntimeError("CI-only role isolation refused outside known disposable database")
    return expected


def _deny(conn: psycopg.Connection, statement: str, params=None) -> None:
    try:
        with conn.transaction():
            conn.execute(statement, params)
    except errors.InsufficientPrivilege:
        pass
    else:
        raise AssertionError("Forbidden SQL operation unexpectedly succeeded")


def main() -> None:
    dsn = _guard()
    target = dsn.replace("/vowsig_test?", "/vowsig_roles_test?")
    with psycopg.connect(dsn, autocommit=True) as admin:
        for name in ("vowsig_app", "vowsig_backup", "vowsig_migrator"):
            admin.execute(
                "CREATE ROLE " + name +
                " NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS"
            )
        admin.execute("CREATE DATABASE vowsig_roles_test")

    with psycopg.connect(target, autocommit=True) as admin:
        admin.execute("CREATE SCHEMA vowsig AUTHORIZATION vowsig_migrator")
        admin.execute("SET ROLE vowsig_migrator")
        admin.execute("SET search_path TO vowsig, pg_catalog")
        for name in MIGRATIONS:
            sql = (ROOT / "sql" / "accounts" / name).read_text(encoding="utf-8")
            admin.execute(sql, prepare=False)
        admin.execute("RESET ROLE")
        cnt = admin.execute(
            "SELECT count(*) FROM pg_catalog.pg_tables "
            "WHERE schemaname='vowsig' AND left(tablename,7)='vowsig_'"
        ).fetchone()[0]
        if cnt != 16:
            raise AssertionError("Expected 16 scoped account/research tables")
        assert admin.execute(
            "SELECT has_schema_privilege('vowsig_app','vowsig','CREATE')"
        ).fetchone()[0] is False
        assert admin.execute(
            "SELECT has_table_privilege('vowsig_app',"
            "'vowsig.vowsig_research_outcome_facts','INSERT,UPDATE,DELETE')"
        ).fetchone()[0] is False
        assert admin.execute(
            "SELECT has_table_privilege('vowsig_backup','vowsig.vowsig_accounts','SELECT')"
        ).fetchone()[0] is True

    with psycopg.connect(target, autocommit=True) as app:
        app.execute("SET SESSION AUTHORIZATION vowsig_app")
        app.execute("SET search_path TO vowsig, pg_catalog")
        assert app.execute("SELECT count(*) FROM vowsig_accounts").fetchone()[0] == 0
        app.execute(
            "INSERT INTO vowsig_accounts (id,email,email_verified_at) "
            "VALUES ('00000000-0000-4000-8000-000000000001','ci-only@example.test',now())"
        )
        app.execute(
            "INSERT INTO vowsig_account_entitlements (account_id) "
            "VALUES ('00000000-0000-4000-8000-000000000001')"
        )
        app.execute(
            "INSERT INTO vowsig_account_identities "
            "(account_id,issuer,subject) VALUES "
            "('00000000-0000-4000-8000-000000000001',"
            "'https://idp.example.test','ci-identity')"
        )
        app.execute(
            "INSERT INTO vowsig_account_audit (account_id,action) VALUES "
            "('00000000-0000-4000-8000-000000000001','watchlist_saved')"
        )
        _deny(app, "CREATE TABLE vowsig.cannot_create (n integer)")
        _deny(app, "DROP TABLE vowsig.vowsig_accounts")
        _deny(app, "INSERT INTO vowsig.vowsig_research_source_snapshots "
              "(source_program_id,model_version,source_snapshot_sha256,observed_at_utc) "
              "VALUES ('source','model',repeat('a',64),now())")
        _deny(app, "DELETE FROM vowsig.vowsig_research_outcome_facts")
        # Runtime credentials must not be allowed to seed an owner role, even
        # via an INSERT that bypasses the normal application code.
        _deny(app, "INSERT INTO vowsig_accounts "
              "(id,email,role,email_verified_at) VALUES "
              "('00000000-0000-4000-8000-000000000003',"
              "'forbidden@example.test','owner',now())")
        _deny(app, "UPDATE vowsig.vowsig_accounts SET role='owner'")
        # A compromised runtime role may check owner MFA but cannot install
        # or replace a factor, nor update its encrypted secret.
        _deny(app, "INSERT INTO vowsig_owner_totp_credentials "
              "(account_id,secret_ciphertext) VALUES "
              "('00000000-0000-4000-8000-000000000001',repeat('x',48)::bytea)")
        _deny(app, "UPDATE vowsig_owner_totp_credentials "
              "SET secret_ciphertext=repeat('x',48)::bytea")
        assert app.execute(
            "SELECT has_column_privilege('vowsig_app', "
            "'vowsig.vowsig_owner_totp_credentials', "
            "'last_accepted_step','UPDATE')"
        ).fetchone()[0] is True
        _deny(app, "INSERT INTO vowsig_owner_provisioning_audit "
              "(operation_id,account_id,operation,reviewer_id,operator_id,"
              "approved_payload_sha256,revoked_sessions) VALUES "
              "('ffffffff-ffff-4fff-8fff-ffffffffffff',"
              "'00000000-0000-4000-8000-000000000001',"
              "'first_owner','reviewer.ci','operator.ci',repeat('a',64),0)")
        _deny(app, "UPDATE vowsig_owner_provisioning_audit "
              "SET operation='rotate_factor'")
        _deny(app, "SET ROLE vowsig_migrator")

    with psycopg.connect(target, autocommit=True) as backup:
        backup.execute("SET SESSION AUTHORIZATION vowsig_backup")
        backup.execute("SET search_path TO vowsig, pg_catalog")
        assert backup.execute("SELECT count(*) FROM vowsig_accounts").fetchone()[0] == 1
        assert backup.execute("SELECT count(*) FROM vowsig_research_source_snapshots").fetchone()[0] == 0
        _deny(backup, "INSERT INTO vowsig_accounts (id,email) VALUES "
              "('00000000-0000-4000-8000-000000000002','deny@example.test')")
        _deny(backup, "CREATE TABLE vowsig.cannot_create (n integer)")
        _deny(backup, "DELETE FROM vowsig.vowsig_accounts")


    # True runtime role acceptance must exercise the verified-login SQL, not
    # merely inspect has_table_privilege() or seed data using admin credentials.
    # Every connection below is an isolated PostgreSQL 18 CI role session.
    from concurrent.futures import ThreadPoolExecutor
    from datetime import datetime, timedelta, timezone
    from psycopg.rows import dict_row
    from trading_signal_intelligence.product.accounts.store import PostgresAccountStore

    class RestrictedCiStore(PostgresAccountStore):
        def __init__(self):
            pass  # CI loopback is intentionally sslmode=disable, never production.

        def _connect(self):
            conn = psycopg.connect(target, row_factory=dict_row, connect_timeout=3)
            conn.execute("SET SESSION AUTHORIZATION vowsig_app")
            conn.execute("SET search_path TO vowsig, pg_catalog")
            conn.commit()
            assert conn.execute("SELECT current_user").fetchone()["current_user"] == "vowsig_app"
            conn.commit()
            return conn

    role_store = RestrictedCiStore()
    issuer = "https://idp.example.test"
    signed_at = datetime.now(timezone.utc)
    ttl = signed_at + timedelta(hours=1)
    # First actual restricted-role login for an already-bound account.
    bound_id = role_store.complete_verified_login(
        issuer=issuer, subject="ci-identity", verified_email="ci-only@example.test",
        token_sha256="a" * 64, issued_at=signed_at, expires_at=ttl,
    )
    assert bound_id == "00000000-0000-4000-8000-000000000001"

    # First login of an independently verified new identity must INSERT only
    # the permitted account columns, without account UPDATE or owner promotion.
    registered_id = role_store.complete_verified_login(
        issuer=issuer, subject="new-disposable-verified", verified_email="ci-new@example.test",
        token_sha256="b" * 64, issued_at=signed_at, expires_at=ttl,
    )
    assert registered_id != bound_id
    assert role_store.find_bound_account(issuer, "new-disposable-verified") == registered_id

    # Two near-simultaneous returning logins for the same immutable subject
    # serialize under the transaction advisory lock; only one session survives.
    def relogin(digest: str) -> str:
        return role_store.complete_verified_login(
            issuer=issuer, subject="new-disposable-verified",
            verified_email="ci-new@example.test",
            token_sha256=digest, issued_at=signed_at, expires_at=ttl,
        )

    with ThreadPoolExecutor(max_workers=2) as pool:
        concurrent_ids = list(pool.map(relogin, ("c" * 64, "d" * 64)))
    assert concurrent_ids == [registered_id, registered_id]
    with psycopg.connect(target, row_factory=dict_row) as admin:
        active = admin.execute(
            "SELECT token_sha256 FROM vowsig.vowsig_account_sessions "
            "WHERE account_id=%s::uuid AND revoked_at IS NULL", (registered_id,)
        ).fetchall()
        assert len(active) == 1
        assert active[0]["token_sha256"] in ("c" * 64, "d" * 64)
        assert admin.execute(
            "SELECT role FROM vowsig.vowsig_accounts WHERE id=%s::uuid", (registered_id,)
        ).fetchone()["role"] == "member"
        assert admin.execute(
            "SELECT has_table_privilege('vowsig_app','vowsig.vowsig_accounts','UPDATE') AS can_update"
        ).fetchone()["can_update"] is False
    print("PG18_VERIFIED_LOGIN_RESTRICTED_APP_AND_CONCURRENCY=PASS; "
          "accounts_update_denied=YES; session_rotation_single_active=YES")

    print("PG18_ISOLATED_ROLE_BOUNDARIES=PASS; tables=16; "
          "runtime_schema_ddl_denied=YES; runtime_history_dml_denied=YES; "
          "runtime_owner_promotion_denied=YES; backup_read_only=YES")


if __name__ == "__main__":
    main()
