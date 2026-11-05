"""Least-privilege authenticated PostgreSQL acceptance, READ-ONLY.

Real execution requires owner's controlled candidate Railway app image/secret
binding. Never log or return connection credentials or any account data.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit,parse_qs

from trading_signal_intelligence.product.accounts.tls_probe import (
    CA_FILE, TARGET,verify_ca_pem,
)


class PgAcceptanceError(ValueError):
    pass


def validate_private_runtime_dsn(dsn: str, *, ca_file: Path=CA_FILE) -> dict[str,str]:
    if not isinstance(dsn,str) or len(dsn)>8192:
        raise PgAcceptanceError("Missing or oversized authenticated DSN")
    try:
        parsed=urlsplit(dsn)
        if (parsed.scheme not in ("postgresql","postgres") or parsed.hostname!=TARGET
            or parsed.username!="vowsig_app" or not parsed.password
            or parsed.fragment or not parsed.path or parsed.path=="/"):
            raise PgAcceptanceError("Runtime role/target/scheme invalid")
        query=parse_qs(parsed.query,keep_blank_values=True,strict_parsing=True)
        if (query.get("sslmode")!=["verify-full"] or
            query.get("sslrootcert")!=[str(ca_file)] or
            any(k in query for k in ("sslcert","sslkey","sslpassword","options"))):
            raise PgAcceptanceError("Verified-full private root CA not configured")
        ca=ca_file.read_text(encoding="ascii")
        digest=verify_ca_pem(ca)
    except (OSError,ValueError,TypeError) as exc:
        raise PgAcceptanceError("Runtime DB authentication/TLS binding invalid") from exc
    return {"target":TARGET,"role":"vowsig_app",
            "pinned_ca_sha256":digest,"sslmode":"verify-full"}


def inspect_authenticated_app_connection(conn) -> dict[str,object]:
    """Exact signed-off account migration and read-only role evidence."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT current_user,current_setting('search_path'),"
                "(SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()),"
                "(SELECT version FROM pg_stat_ssl WHERE pid=pg_backend_pid())"
            )
            role,path,encrypted,tls_version=cursor.fetchone()
            cursor.execute(
                "SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls "
                "FROM pg_roles WHERE rolname=current_user"
            )
            role_flags=cursor.fetchone()
            cursor.execute(
                "SELECT has_schema_privilege(current_user,'vowsig','USAGE'),"
                "has_schema_privilege(current_user,'vowsig','CREATE'),"
                "has_table_privilege(current_user,'vowsig.vowsig_accounts','SELECT'),"
                "has_table_privilege(current_user,'vowsig.vowsig_accounts','UPDATE')"
            )
            usage,create,select,update=cursor.fetchone()
            cursor.execute(
                "SELECT "
                "has_table_privilege(current_user,'vowsig.vowsig_research_outcome_facts','INSERT'),"
                "has_table_privilege(current_user,'vowsig.vowsig_research_outcome_facts','UPDATE'),"
                "has_table_privilege(current_user,'vowsig.vowsig_research_outcome_facts','DELETE')"
            )
            prohibited=cursor.fetchone()
    except Exception as exc:
        raise PgAcceptanceError("Read-only runtime DB evidence unavailable") from exc
    if (role!="vowsig_app" or
        "".join(str(path).replace('"',"").split())!="vowsig,pg_catalog" or
        encrypted is not True or
        tls_version not in ("TLSv1.2","TLSv1.3") or
        role_flags!=(False,False,False,False) or
        (usage,create,select,update)!=(True,False,True,True) or
        prohibited!=(False,False,False)):
        raise PgAcceptanceError("Authenticated runtime privileges/TLS failed closed")
    return {
        "status":"AUTHENTICATED_APP_ROLE_RESTRICTED_SQL_READ_ONLY_PASS",
        "current_role":"vowsig_app",
        "private_hostname_required":TARGET,
        "server_ssl_verified":True,
        "server_tls_version":tls_version,
        "runtime_migration_ddl_forbidden":True,
        "research_outcome_writes_denied":True,
        "customer_signup_end_to_end_verified":False,
        "owner_totp_onboarded":False,
        "database_backup_cold_restore_verified":False,
    }


def preflight_from_private_environment() -> dict[str,object]:
    dsn=os.environ.get("VOWSIG_ACCOUNTS_DATABASE_URL","")
    identity=validate_private_runtime_dsn(dsn)
    try:
        import psycopg
        with psycopg.connect(dsn,connect_timeout=5) as conn:
            with conn.transaction():
                conn.execute("SET TRANSACTION READ ONLY")
                receipt=inspect_authenticated_app_connection(conn)
    except PgAcceptanceError:
        raise
    except Exception as exc:
        raise PgAcceptanceError("Authenticated private DB query could not complete") from exc
    return {**receipt,"pinned_ca_sha256":identity["pinned_ca_sha256"]}


def main():
    try:
        result=preflight_from_private_environment()
    except PgAcceptanceError:
        print("VOWSIG_PRIVATE_PG_AUTHENTICATED_PREFLIGHT=HOLD")
        return 1
    print("VOWSIG_PRIVATE_PG_AUTHENTICATED_PREFLIGHT=PASS")
    print("TLS_VERSION="+str(result["server_tls_version"]))
    print("ROLE=vowsig_app")
    print("SIGNED_UP_REAL_CUSTOMER=NOT_TESTED")
    print("DATABASE_RECOVERY_UNVERIFIED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
