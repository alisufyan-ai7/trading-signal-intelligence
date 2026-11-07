"""Independently cold-restore ONE downloaded VowSig encrypted PG18 backup.

Runs only against a disposable loopback PostgreSQL 18 cluster and a new,
empty database; does not connect to production or delete any database.
Execute once for AWS and once for Backblaze copy, with separate database names.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path


class RestoreFailure(RuntimeError):
    pass


def _run(args: list[str], env: dict[str, str]):
    try:
        result = subprocess.run(
            args, env=env, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            check=False, timeout=120,
        )
    except (OSError, subprocess.SubprocessError):
        raise RestoreFailure("local_postgres_command_failed") from None
    if result.returncode:
        raise RestoreFailure("local_postgres_command_failed")
    return result.stdout.decode("utf-8", errors="replace").strip()


def _local_env(database: str) -> dict[str, str]:
    if os.environ.get("VOWSIG_LOCAL_RESTORE_CONFIRM") != "YES_ISOLATED_THROWAWAY_PG18":
        raise RestoreFailure("independent_restore_confirmation_missing")
    if not re.fullmatch(r"vowsig_restore_verify_(aws|b2)_[a-f0-9]{8}", database):
        raise RestoreFailure("disposable_database_name_guard")
    password = os.environ.get("VOWSIG_LOCAL_RESTORE_PASSWORD", "")
    if not password:
        raise RestoreFailure("local_restore_password_missing")
    env = os.environ.copy()
    env.update({
        "PGHOST": "127.0.0.1", "PGHOSTADDR": "127.0.0.1", "PGPORT": "5432", "PGUSER": "postgres",
        "PGPASSWORD": password, "PGSSLMODE": "disable", "PGCONNECT_TIMEOUT": "5",
    })
    for extra in ("VOWSIG_PG_BACKUP_DSN", "PGSERVICE", "PGSERVICEFILE", "PGPASSFILE", "PGOPTIONS", "PGTARGETSESSIONATTRS"):
        env.pop(extra, None)
    env.pop("VOWSIG_LOCAL_RESTORE_PASSWORD", None)
    version = _run(["psql", "-X", "--dbname=postgres", "-At", "-c", "SHOW server_version_num"], env)
    if not version.startswith("18"):
        raise RestoreFailure("local_server_not_pg18")
    return env


def _sha256(path: Path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def verify(ciphertext: Path, manifest_path: Path, age_key: Path, database: str) -> dict:
    env = _local_env(database)
    if not ciphertext.is_file() or not manifest_path.is_file() or not age_key.is_file():
        raise RestoreFailure("missing_archive_manifest_or_offline_key")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise RestoreFailure("invalid_manifest") from None
    if (
        manifest.get("format") != "vowsig-pg18-dual-provider-v1"
        or manifest.get("dump_format") != "pg_dump_-Fc_18_vowsig_schema_no-owner_no-acl"
        or manifest.get("encrypted") is not True
        or manifest.get("production_restore_permitted") is not False
        or manifest.get("cloud_pruning_authorized") is not False
        or not re.fullmatch(r"[0-9a-f]{64}", str(manifest.get("ciphertext_sha256", "")))
        or not isinstance(manifest.get("ciphertext_bytes"), int)
        or manifest["ciphertext_bytes"] < 128
        or not re.fullmatch(r"pg18-\d{8}T\d{6}Z-[0-9a-f]{16}", str(manifest.get("backup_id", "")))
    ):
        raise RestoreFailure("manifest_policy_guard")
    if (ciphertext.stat().st_size != manifest["ciphertext_bytes"]
            or _sha256(ciphertext) != manifest["ciphertext_sha256"]):
        raise RestoreFailure("ciphertext_hash_mismatch")
    # createdb refuses to replace an existing database: no DROP, no IF EXISTS.
    _run(["createdb", "--maintenance-db=postgres", database], env)
    local = env.copy()
    local["PGDATABASE"] = database
    try:
        with ciphertext.open("rb") as input_file:
            decoder = subprocess.Popen(
                ["age", "--decrypt", "--identity", str(age_key)],
                stdin=input_file, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            )
            assert decoder.stdout is not None
            try:
                restore = subprocess.run(
                    ["pg_restore", "--exit-on-error", "--single-transaction",
                     "--no-owner", "--no-acl", "--dbname=" + database],
                    stdin=decoder.stdout, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, env=local, timeout=900,
                )
            finally:
                decoder.stdout.close()
                age_result = decoder.wait(timeout=30)
    except (OSError, subprocess.SubprocessError):
        raise RestoreFailure("cold_restore_process_failed") from None
    if age_result or restore.returncode:
        raise RestoreFailure("cold_restore_failed")
    tables = int(_run([
        "psql", "-X", "--dbname=" + database, "-At", "-c",
        "SELECT count(*) FROM pg_catalog.pg_tables WHERE schemaname='vowsig'",
    ], local))
    required = _run([
        "psql", "-X", "--dbname=" + database, "-At", "-c",
        "SELECT count(*) FROM pg_catalog.pg_tables "
        "WHERE schemaname='vowsig' AND tablename IN "
        "('vowsig_accounts','vowsig_account_sessions','vowsig_watchlist_items',"
        "'vowsig_account_consent_events')",
    ], local)
    if tables < 16 or required != "4":
        raise RestoreFailure("restored_schema_contract_failed")
    # Full logical recovery of current VowSig accounts must include at
    # least one verified identity and its enrolled owner factor. The
    # counts are aggregate evidence only; no PII ever leaves this host.
    metrics = _run([
        "psql", "-X", "--dbname=" + database, "-At", "-c",
        "SELECT (SELECT count(*) FROM vowsig.vowsig_accounts)::text || '|' || "
        "(SELECT count(*) FROM vowsig.vowsig_account_identities)::text || '|' || "
        "(SELECT count(*) FROM vowsig.vowsig_owner_totp_credentials)::text",
    ], local)
    try:
        account_rows, identity_rows, owner_factor_rows = map(int, metrics.split("|"))
    except (ValueError, TypeError):
        raise RestoreFailure("restored_identity_counts_unavailable") from None
    if min(account_rows, identity_rows, owner_factor_rows) < 1:
        raise RestoreFailure("restored_identity_contract_failed")
    return {
        "vowsig_account_rows": account_rows,
        "vowsig_identity_rows": identity_rows,
        "vowsig_owner_factors": owner_factor_rows,
        "status": "ISOLATED_COLD_RESTORE_PASS",
        "backup_id": manifest["backup_id"],
        "ciphertext_sha256": manifest["ciphertext_sha256"],
        "database": database,
        "vowsig_tables": tables,
        "production_database_mutated": False,
    }


def main():
    if len(sys.argv) != 5:
        print("Usage: verify_restore.py <ciphertext.age> <manifest.json> <owner-private-age-key> <new_throwaway_db>", file=sys.stderr)
        return 2
    try:
        result = verify(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]), sys.argv[4])
    except RestoreFailure as error:
        print("VOWSIG_PG_COLD_RESTORE=FAIL; code=" + str(error), file=sys.stderr)
        return 1
    except Exception:
        print("VOWSIG_PG_COLD_RESTORE=FAIL; code=unexpected_error", file=sys.stderr)
        return 1
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
