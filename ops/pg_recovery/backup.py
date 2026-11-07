"""VowSig Railway PG18 encrypted, append-only, dual-provider backup worker.

This executable does NOT touch the web application, the Windows S02 backups,
or any existing PG schema. Both providers receive identical ciphertext and
minimal non-sensitive integrity manifests. Restore is a separate operation.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

EXPECTED_PG_HOST = "postgres.railway.internal"
EXPECTED_PG_USER = "vowsig_backup"
EXPECTED_CA = "/app/config/tls/railway-postgres-root-ca-20261104.pem"
PREFIX = "vowsig/railway-pg18/customer-db/v1"
MAX_CIPHERTEXT_BYTES = 512 * 1024 * 1024


class BackupFailure(RuntimeError):
    """Sanitized failure code, never raw errors containing secrets."""


def _required(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise BackupFailure("missing_" + name.lower())
    return value


def _pg_env() -> dict[str, str]:
    url = urlsplit(_required("VOWSIG_PG_BACKUP_DSN"))
    query = parse_qs(url.query, keep_blank_values=True)
    if (
        url.scheme not in ("postgres", "postgresql")
        or url.hostname != EXPECTED_PG_HOST
        or url.port not in (None, 5432)
        or unquote(url.username or "") != EXPECTED_PG_USER
        or not url.password
        or not re.fullmatch(r"/[A-Za-z_][A-Za-z_0-9]*", url.path)
        or url.fragment
        or query != {"sslmode": ["verify-full"], "sslrootcert": [EXPECTED_CA]}
    ):
        raise BackupFailure("source_dsn_guard")
    if not Path(EXPECTED_CA).is_file():
        raise BackupFailure("root_ca_missing")
    env = os.environ.copy()
    env.update({
        "PGHOST": EXPECTED_PG_HOST,
        "PGPORT": "5432",
        "PGDATABASE": url.path[1:],
        "PGUSER": EXPECTED_PG_USER,
        "PGPASSWORD": unquote(url.password),
        "PGSSLMODE": "verify-full",
        "PGSSLROOTCERT": EXPECTED_CA,
        "PGCONNECT_TIMEOUT": "15",
        "PGAPPNAME": "vowsig-pg18-encrypted-backup",
    })
    env.pop("VOWSIG_PG_BACKUP_DSN", None)
    return env


def _verify_toolchain() -> None:
    try:
        result = subprocess.run(
            ["pg_dump", "--version"], check=True, capture_output=True, timeout=10
        )
    except (OSError, subprocess.SubprocessError):
        raise BackupFailure("pg_dump_unavailable") from None
    if not re.search(rb"\b18\.\d+\b", result.stdout):
        raise BackupFailure("pg_dump_not_18")
    try:
        subprocess.run(["age", "--version"], check=True, capture_output=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        raise BackupFailure("age_unavailable") from None


def _encrypted_dump(path: Path, pg_env: dict[str, str], recipient: str) -> None:
    if not re.fullmatch(r"age1[0-9a-z]{40,100}", recipient):
        raise BackupFailure("invalid_age_recipient")
    # Plaintext never lands on a filesystem; pg_dump streams into age.
    with path.open("wb") as output:
        try:
            dump = subprocess.Popen(
                ["pg_dump", "--format=custom", "--no-owner", "--no-acl"],
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=pg_env,
            )
            assert dump.stdout is not None
            try:
                cipher = subprocess.run(
                    ["age", "--encrypt", "--recipient", recipient],
                    stdin=dump.stdout, stdout=output, stderr=subprocess.DEVNULL,
                    check=False, timeout=1800,
                )
            finally:
                dump.stdout.close()
                dump_rc = dump.wait(timeout=30)
        except (OSError, subprocess.SubprocessError):
            raise BackupFailure("encrypted_dump_process_failed") from None
    if cipher.returncode or dump_rc:
        raise BackupFailure("encrypted_dump_failed")
    if path.stat().st_size < 128 or path.stat().st_size > MAX_CIPHERTEXT_BYTES:
        raise BackupFailure("ciphertext_size_guard")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _clients():
    try:
        import boto3
        from botocore.config import Config
    except ImportError:
        raise BackupFailure("boto3_unavailable") from None
    config = Config(signature_version="s3v4", retries={"max_attempts": 3, "mode": "standard"})
    aws = boto3.client(
        "s3", region_name=_required("AWS_BACKUP_REGION"),
        aws_access_key_id=_required("AWS_BACKUP_ACCESS_KEY_ID"),
        aws_secret_access_key=_required("AWS_BACKUP_SECRET_ACCESS_KEY"),
        config=config,
    )
    b2_endpoint = _required("B2_BACKUP_ENDPOINT")
    parsed_b2 = urlsplit(b2_endpoint)
    if (parsed_b2.scheme != "https" or not parsed_b2.hostname
            or not parsed_b2.hostname.endswith(".backblazeb2.com")
            or parsed_b2.path not in ("", "/") or parsed_b2.username
            or parsed_b2.password or parsed_b2.query or parsed_b2.fragment):
        raise BackupFailure("b2_endpoint_tls_guard")
    b2 = boto3.client(
        "s3", endpoint_url=b2_endpoint,
        region_name=_required("B2_BACKUP_REGION"),
        aws_access_key_id=_required("B2_BACKUP_KEY_ID"),
        aws_secret_access_key=_required("B2_BACKUP_APP_KEY"),
        config=config,
    )
    return (("aws", aws, _required("AWS_BACKUP_BUCKET")),
            ("b2", b2, _required("B2_BACKUP_BUCKET")))


def _verify_download(client, bucket: str, key: str, expected_sha: str, expected_size: int):
    digest = hashlib.sha256()
    read_bytes = 0
    obj = client.get_object(Bucket=bucket, Key=key)
    try:
        for block in obj["Body"].iter_chunks(chunk_size=1024 * 1024):
            if block:
                read_bytes += len(block)
                if read_bytes > MAX_CIPHERTEXT_BYTES:
                    raise BackupFailure("remote_ciphertext_size_guard")
                digest.update(block)
    finally:
        obj["Body"].close()
    if read_bytes != expected_size or digest.hexdigest() != expected_sha:
        raise BackupFailure("remote_ciphertext_sha_mismatch")


def run() -> dict:
    pg_env = _pg_env()
    _verify_toolchain()
    recipient = _required("AGE_BACKUP_RECIPIENT")
    clients = _clients()
    now = datetime.now(timezone.utc)
    backup_id = now.strftime("pg18-%Y%m%dT%H%M%SZ-") + secrets.token_hex(8)
    key_base = f"{PREFIX}/{now:%Y/%m/%d}/{backup_id}"
    ciphertext_key = key_base + ".age"
    manifest_key = key_base + ".json"
    with tempfile.TemporaryDirectory(prefix="vowsig-pg18-") as tmp:
        path = Path(tmp) / "snapshot.age"
        os.chmod(tmp, 0o700)
        _encrypted_dump(path, pg_env, recipient)
        size = path.stat().st_size
        sha = _sha256(path)
        manifest = {
            "format": "vowsig-pg18-dual-provider-v1",
            "backup_id": backup_id,
            "created_at_utc": now.isoformat(),
            "scope": "full_logical_database_via_restricted_backup_role",
            "dump_format": "pg_dump_-Fc_18_no-owner_no-acl",
            "cipher": "age-x25519-recipient",
            "ciphertext_object_key": ciphertext_key,
            "ciphertext_sha256": sha,
            "ciphertext_bytes": size,
            "encrypted": True,
            "production_restore_permitted": False,
            "cloud_pruning_authorized": False,
        }
        payload = json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode() + b"\n"
        if len(payload) > 8192:
            raise BackupFailure("manifest_size_guard")
        verified = []
        for name, client, bucket in clients:
            try:
                with path.open("rb") as file:
                    client.put_object(Bucket=bucket, Key=ciphertext_key, Body=file,
                                      Metadata={"sha256": sha})
                client.put_object(Bucket=bucket, Key=manifest_key, Body=payload,
                                  ContentType="application/json")
                _verify_download(client, bucket, ciphertext_key, sha, size)
                saved_manifest = client.get_object(Bucket=bucket, Key=manifest_key)
                try:
                    received = saved_manifest["Body"].read(8193)
                finally:
                    saved_manifest["Body"].close()
                if received != payload:
                    raise BackupFailure("remote_manifest_mismatch")
            except BackupFailure:
                raise
            except Exception:
                raise BackupFailure("provider_" + name + "_upload_verify_failed") from None
            verified.append(name)
    return {
        "status": "DUAL_CIPHERTEXT_UPLOAD_VERIFIED",
        "backup_id": backup_id,
        "providers": verified,
        "ciphertext_sha256": sha,
        "ciphertext_bytes": size,
        "isolated_cold_restore": "NOT_YET_VERIFIED",
        "cloud_deletions": 0,
    }


def main() -> int:
    try:
        receipt = run()
    except BackupFailure as error:
        print("VOWSIG_PG_BACKUP=FAIL; code=" + str(error), file=sys.stderr)
        return 1
    except Exception:
        print("VOWSIG_PG_BACKUP=FAIL; code=unexpected_error", file=sys.stderr)
        return 1
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
