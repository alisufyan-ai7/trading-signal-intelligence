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
        if cnt != 14:
            raise AssertionError("Expected 14 scoped account/research tables")
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
        _deny(app, "UPDATE vowsig.vowsig_accounts SET role='owner'")
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

    print("PG18_ISOLATED_ROLE_BOUNDARIES=PASS; tables=14; "
          "runtime_schema_ddl_denied=YES; runtime_history_dml_denied=YES; "
          "runtime_owner_promotion_denied=YES; backup_read_only=YES")


if __name__ == "__main__":
    main()
