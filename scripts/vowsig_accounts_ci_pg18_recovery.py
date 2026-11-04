"""Fail-closed PG18 backup/restore and runtime-role smoke test in *disposable CI* only.

Requires GitHub Actions, explicit YES_THROWAWAY_DATABASE confirmation,
a fixed loopback-only vowsig_test connection, and the postgres:18-alpine
service container. Never accepts Railway/public database endpoints.

This proves a *logical* archive can be restored to a separate disposable DB.
It is NOT evidence of scheduled, encrypted, offsite production backups.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from urllib.parse import parse_qs, urlsplit

import psycopg
from psycopg import errors
from psycopg.rows import dict_row


def _guard() -> str:
    if (
        os.environ.get("GITHUB_ACTIONS") != "true"
        or os.environ.get("GITHUB_REPOSITORY")
        != "alisufyan-ai7/trading-signal-intelligence"
        or os.environ.get("VOWSIG_EPHEMERAL_PG_TEST_CONFIRM")
        != "YES_THROWAWAY_DATABASE"
    ):
        raise RuntimeError("Refusing non-CI or unconfirmed database recovery test")
    dsn = os.environ.get("VOWSIG_EPHEMERAL_PG_TEST_DSN", "")
    parsed = urlsplit(dsn)
    if (
        parsed.scheme != "postgresql"
        or parsed.hostname != "127.0.0.1"
        or parsed.port != 5432
        or parsed.username != "vowsig_test"
        or parsed.password != "local-ci-only-test-password"
        or parsed.path != "/vowsig_test"
        or parse_qs(parsed.query) != {"sslmode": ["disable"]}
        or parsed.fragment
    ):
        raise RuntimeError("Refusing non-loopback, nonthrowaway or altered DSN")
    return dsn


def _docker(*args: str) -> str:
    completed = subprocess.run(
        ["docker", *args], check=True, capture_output=True, text=True, timeout=90
    )
    return completed.stdout.strip()


def _snapshot(conn: psycopg.Connection) -> tuple[str, int, int]:
    """Fingerprint every vowsig_ table and its columns without printing rows."""
    with conn.cursor(row_factory=dict_row) as cur:
        # Avoid SQL LIKE escape ambiguities across PostgreSQL and drivers.
        # Select from the catalog, then do a literal prefix match in Python.
        tables = [
            row["tablename"]
            for row in cur.execute(
                """SELECT tablename FROM pg_catalog.pg_tables
                   WHERE schemaname='public' ORDER BY tablename"""
            ).fetchall()
            if row["tablename"].startswith("vowsig_")
        ]
        if len(tables) < 8 or "vowsig_accounts" not in tables:
            raise RuntimeError(f"Missing migrated account tables: found={len(tables)}; tables={tables}")
        digest = hashlib.sha256()
        total_rows = 0
        for table in tables:
            if not re.fullmatch(r"vowsig_[a-z0-9_]+", table):
                raise RuntimeError("Invalid schema table identifier")
            cols = cur.execute(
                """SELECT column_name, data_type, is_nullable
                   FROM information_schema.columns
                   WHERE table_schema='public' AND table_name=%s
                   ORDER BY ordinal_position""",
                (table,),
            ).fetchall()
            digest.update(json.dumps([table, cols], default=str, sort_keys=True).encode())
            # No values, passwords, private keys, session tokens or emails are logged.
            rows = cur.execute(f'SELECT * FROM public."{table}"').fetchall()
            canonical = sorted(
                json.dumps(row, sort_keys=True, default=str, allow_nan=False)
                for row in rows
            )
            for line in canonical:
                digest.update(line.encode())
                digest.update(b"\n")
            total_rows += len(rows)
        if total_rows < 3:
            raise RuntimeError("Expected synthetic CI records were not inserted")
        return digest.hexdigest(), len(tables), total_rows


def _check_runtime_role(conn: psycopg.Connection) -> None:
    # This role never gets CREATE / DDL privileges; isolated CI only.
    conn.execute("CREATE ROLE vowsig_runtime_ci NOLOGIN")
    conn.execute("GRANT USAGE ON SCHEMA public TO vowsig_runtime_ci")
    conn.execute(
        "GRANT SELECT,INSERT,UPDATE,DELETE ON ALL TABLES IN SCHEMA public TO vowsig_runtime_ci"
    )
    conn.execute(
        "GRANT USAGE,SELECT ON ALL SEQUENCES IN SCHEMA public TO vowsig_runtime_ci"
    )
    conn.execute("SET ROLE vowsig_runtime_ci")
    try:
        if conn.execute("SELECT count(*) FROM public.vowsig_accounts").fetchone()[0] < 3:
            raise RuntimeError("Runtime role cannot read existing synthetic accounts")
        # Explicit public schema qualification avoids the TEMP-table bypass.
        try:
            with conn.transaction():
                conn.execute(
                    "CREATE TABLE public.vowsig_ci_forbidden_schema_change (x integer)"
                )
        except errors.InsufficientPrivilege:
            pass
        else:
            raise RuntimeError("Runtime role unexpectedly permitted schema CREATE")
    finally:
        conn.execute("RESET ROLE")


def main() -> None:
    dsn = _guard()
    containers = _docker(
        "ps", "--filter", "ancestor=postgres:18-alpine", "--format", "{{.ID}}"
    ).splitlines()
    if len(containers) != 1 or not re.fullmatch(r"[0-9a-f]{12,64}", containers[0]):
        raise RuntimeError("Expected exactly one isolated PG18 CI container")
    cid = containers[0]
    if not _docker("exec", cid, "pg_dump", "--version").startswith("pg_dump (PostgreSQL) 18."):
        raise RuntimeError("Only native PG18 pg_dump may create the recovery archive")

    with psycopg.connect(dsn, connect_timeout=3) as source:
        before = _snapshot(source)

    # Archive stays inside the disposable service container. No host download,
    # external endpoint, public TCP proxy, secrets file or production volume.
    _docker(
        "exec", cid, "pg_dump", "-U", "vowsig_test", "-d", "vowsig_test",
        "--format=custom", "--no-owner", "--no-acl",
        "--file=/tmp/vowsig_ci_accounts.dump",
    )
    _docker("exec", cid, "createdb", "-U", "vowsig_test", "vowsig_restore_test")
    _docker(
        "exec", cid, "pg_restore", "-U", "vowsig_test", "-d", "vowsig_restore_test",
        "--exit-on-error", "--single-transaction", "--no-owner", "--no-acl",
        "/tmp/vowsig_ci_accounts.dump",
    )

    restored_dsn = dsn.replace("/vowsig_test?", "/vowsig_restore_test?")
    with psycopg.connect(restored_dsn, connect_timeout=3) as restored:
        after = _snapshot(restored)
        if before != after:
            raise RuntimeError("Recovery fingerprint/count mismatch")
        _check_runtime_role(restored)

    print(
        "PG18_DISPOSABLE_COLD_RESTORE=PASS; "
        f"tables={before[1]}; rows={before[2]}; "
        "separate_restored_db=YES; no_schema_create_role=PASS"
    )


if __name__ == "__main__":
    main()
