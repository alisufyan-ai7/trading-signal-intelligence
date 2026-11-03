"""VowSig S02: manual one-shot AWS S3 + Backblaze B2 encrypted backup/restore.

This module is a real provider-capable implementation, not a fake client pilot.
Nothing is sent or read until explicitly invoked by the separate interactive
CLI, using only ephemeral owner-entered scoped credential pairs and a private
passphrase. Never schedule this CLI or supply keys in arguments/environment.

A minimal-cost preference is not a guarantee of zero bills. No automatic
upload retry, overwrite, delete, version pruning, or retention changes.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
import re
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import live_sqlite_envelope_v0_1 as s02
from . import live_dual_provider_transport_v0_1 as endpoints

DATA_MAX = s02.MAX_ENVELOPE_BYTES
MANIFEST_MAX = 16384
MAGIC = b"VOWSIG_DUAL_S02_RECEIPT_V1\x00"
OBJECT_PREFIX = "pilot/vowsig/approved-s02/v1/"
MANIFEST_PREFIX = "pilot/vowsig/backup-receipts/v1/"
RUN_RX = re.compile(r"^backup-[0-9a-f]{32}$")
CLIENT_TIMEOUT = 10


class BackupOperationError(RuntimeError):
    """All errors are fixed and sanitized; provider exceptions never escape."""


def new_run_id() -> str:
    return "backup-" + uuid.uuid4().hex


def _hash(blob: bytes) -> str:
    return hashlib.sha256(blob).hexdigest()


def _canonical(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _check_id(backup_id: str) -> None:
    if type(backup_id) is not str or not RUN_RX.fullmatch(backup_id):
        raise BackupOperationError("invalid backup identifier")


def _manifest_key(backup_id: str) -> str:
    _check_id(backup_id)
    return MANIFEST_PREFIX + backup_id + ".aesgcm"


def _configured_clients(
    credentials: tuple[tuple[str, str], ...],
    providers: tuple[endpoints.Provider, ...],
) -> tuple[Any, ...]:
    """Explicit role-scoped clients. No ambient credentials or file reading."""
    if (type(credentials) is not tuple or len(credentials) != len(providers)
            or any(type(p) is not tuple or len(p) != 2 for p in credentials)):
        raise BackupOperationError("scoped provider identities required")
    ids = []
    for access, secret in credentials:
        if (type(access) is not str or type(secret) is not str
                or not 8 <= len(access) <= 256 or not 8 <= len(secret) <= 256
                or not all(32 < ord(x) < 127 for x in access + secret)):
            raise BackupOperationError("invalid credential input")
        ids.append(access)
    if len(set(ids)) != len(ids):
        raise BackupOperationError("separate cloud identities required")
    try:
        import boto3
        from botocore.config import Config
        clients = []
        for provider, (access, secret) in zip(providers, credentials):
            cfg = Config(
                region_name=provider.region, signature_version="s3v4",
                s3={"addressing_style": "path", "payload_signing_enabled": True},
                retries={"mode": "standard", "total_max_attempts": 1},
                connect_timeout=5, read_timeout=CLIENT_TIMEOUT,
                max_pool_connections=1,
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                proxies={},
            )
            session = boto3.session.Session(
                aws_access_key_id=access, aws_secret_access_key=secret,
                region_name=provider.region,
            )
            client = session.client(
                "s3", endpoint_url=provider.endpoint,
                region_name=provider.region,
                aws_access_key_id=access, aws_secret_access_key=secret,
                config=cfg, verify=True,
            )
            if (client.meta.endpoint_url != provider.endpoint
                    or client.meta.region_name != provider.region):
                raise BackupOperationError("cloud client region/endpoint mismatch")
            clients.append(client)
        return tuple(clients)
    except Exception:
        raise BackupOperationError("explicit cloud client creation failed") from None


def _provider_clients(credentials: tuple[tuple[str, str], ...]) -> tuple[Any, ...]:
    return _configured_clients(
        credentials, (endpoints.AWS, endpoints.AWS, endpoints.B2, endpoints.B2)
    )


def _provider_readers(credentials: tuple[tuple[str, str], ...]) -> tuple[Any, ...]:
    return _configured_clients(credentials, (endpoints.AWS, endpoints.B2))


def _read_exact(reader: Any, provider: endpoints.Provider,
                object_key: str, version_id: str | None,
                max_bytes: int) -> bytes:
    try:
        args: dict[str, Any] = {"Bucket": provider.bucket, "Key": object_key}
        if version_id is not None:
            args["VersionId"] = version_id
        result = reader.get_object(**args)
        if (not isinstance(result, dict)
                or type(result.get("ContentLength")) is not int
                or not 0 < result["ContentLength"] <= max_bytes
                or (version_id is not None
                    and result.get("VersionId") != version_id)):
            raise BackupOperationError("provider exact read metadata invalid")
        stream = result["Body"]
        try:
            body = stream.read(max_bytes + 1)
        finally:
            stream.close()
        if type(body) is not bytes or len(body) != result["ContentLength"]:
            raise BackupOperationError("provider bounded ciphertext read invalid")
        return body
    except Exception:
        raise BackupOperationError("provider encrypted object read failed") from None


def _version(value: Any) -> str:
    if (type(value) is not str or not 0 < len(value) <= 512
            or any(ord(c) < 33 or ord(c) > 126 for c in value)):
        raise BackupOperationError("provider did not return an exact version ID")
    return value


def _put_verified(writer: Any, reader: Any, provider: endpoints.Provider,
                  *, object_key: str, content: bytes, max_bytes: int) -> str:
    if (type(object_key) is not str
            or not object_key.startswith("pilot/vowsig/")
            or type(content) is not bytes or not 0 < len(content) <= max_bytes):
        raise BackupOperationError("encrypted upload scope/size rejected")
    try:
        if provider == endpoints.B2:
            # B2 S3-compatible PUT does not implement S3 IfNoneMatch: *.
            # Random run IDs prevent practical collision; no retry/overwrite
            # is permitted by this program, but this is NOT atomic exclusivity.
            try:
                reader.head_object(Bucket=provider.bucket, Key=object_key)
            except Exception as exc:
                details = getattr(exc, "response", None)
                err = details.get("Error", {}) if isinstance(details, dict) else {}
                meta = details.get("ResponseMetadata", {}) if isinstance(details, dict) else {}
                if (err.get("Code") not in ("404", "NoSuchKey", "NotFound")
                        or meta.get("HTTPStatusCode") != 404):
                    raise BackupOperationError("B2 object preflight uncertain") from None
            else:
                raise BackupOperationError("B2 object already exists")
        args: dict[str, Any] = {
            "Bucket": provider.bucket, "Key": object_key,
            "Body": content, "ContentLength": len(content),
            "ContentType": "application/octet-stream",
        }
        if provider == endpoints.AWS:
            args["IfNoneMatch"] = "*"
        response = writer.put_object(**args)
        version = _version(response.get("VersionId"))
        readback = _read_exact(reader, provider, object_key, version, max_bytes)
        if readback != content:
            raise BackupOperationError("provider exact-version readback mismatch")
        return version
    except Exception:
        raise BackupOperationError(
            "upload/readback incomplete or ambiguous; never auto retry"
        ) from None


def _derive(passphrase: str, salt: bytes) -> bytes:
    if (type(passphrase) is not str or len(passphrase) < 16
            or type(salt) is not bytes or len(salt) != 16):
        raise BackupOperationError("recovery passphrase must contain 16+ characters")
    try:
        return hashlib.scrypt(passphrase.encode("utf-8"), salt=salt,
                              n=16384, r=8, p=1, dklen=32)
    except Exception:
        raise BackupOperationError("recovery key derivation failed") from None


def _seal_manifest(value: dict, *, backup_id: str, passphrase: str) -> bytes:
    _check_id(backup_id)
    raw = _canonical(value)
    if not 0 < len(raw) <= MANIFEST_MAX - 64:
        raise BackupOperationError("recovery manifest over limit")
    salt, nonce = os.urandom(16), os.urandom(12)
    aad = MAGIC + backup_id.encode("ascii")
    ciphertext = AESGCM(_derive(passphrase, salt)).encrypt(nonce, raw, aad)
    return MAGIC + salt + nonce + ciphertext


def _open_manifest(blob: bytes, *, backup_id: str, passphrase: str) -> dict:
    _check_id(backup_id)
    if (type(blob) is not bytes or not blob.startswith(MAGIC)
            or not len(MAGIC) + 16 + 12 + 16 < len(blob) <= MANIFEST_MAX):
        raise BackupOperationError("encrypted manifest format rejected")
    salt_start = len(MAGIC)
    salt = blob[salt_start:salt_start + 16]
    nonce = blob[salt_start + 16:salt_start + 28]
    ciphertext = blob[salt_start + 28:]
    try:
        raw = AESGCM(_derive(passphrase, salt)).decrypt(
            nonce, ciphertext, MAGIC + backup_id.encode("ascii"),
        )
        data = json.loads(raw)
        if (type(data) is not dict or _canonical(data) != raw
                or set(data) != {"schema", "backup_id", "object_key",
                                 "object_sha256", "plaintext_sha256",
                                 "record_count", "data_key", "aws_version", "b2_version"}
                or data["schema"] != "vowsig-dual-s02-receipt-v1"
                or data["backup_id"] != backup_id
                or type(data["object_key"]) is not str
                or data["object_key"] != OBJECT_PREFIX + backup_id + "/" +
                   data["object_sha256"] + ".aesgcm"
                or not s02.HEX64.fullmatch(data["object_sha256"])
                or not s02.HEX64.fullmatch(data["plaintext_sha256"])
                or type(data["record_count"]) is not int
                or not 0 < data["record_count"] <= 1_000_000):
            raise ValueError
        key = base64.b64decode(data["data_key"], validate=True)
        if type(key) is not bytes or len(key) != 32:
            raise ValueError
        _version(data["aws_version"])
        _version(data["b2_version"])
        return data
    except Exception:
        raise BackupOperationError(
            "manifest password, integrity, identity or schema invalid"
        ) from None


def _write_local_receipt(blob: bytes, backup_id: str, directory: Path) -> Path:
    """Encrypted contingency copy kept even if remote receipt upload fails."""
    _check_id(backup_id)
    directory = Path(directory)
    if directory.is_symlink():
        raise BackupOperationError("receipt directory cannot be a link")
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / (backup_id + ".aesgcm")
    try:
        with target.open("xb") as out:
            out.write(blob)
        return target
    except Exception:
        raise BackupOperationError("local encrypted receipt cannot be saved") from None


def backup_once(*, repo_root: Path, receipt_dir: Path,
                credentials: tuple[tuple[str, str], ...],
                passphrase: str) -> dict:
    """One synchronous encrypted S02 snapshot to both providers, manual only."""
    backup_id = new_run_id()
    _check_id(backup_id)
    data_key = os.urandom(32)
    with tempfile.TemporaryDirectory(prefix="vowsig-s02-offsite-") as folder:
        temp = Path(folder)
        rights_ref = _hash(b"owner-directed-app-s02-encrypted-offsite-backup-v1")
        owner_ref = _hash(b"owner-authorized-S02-backup-request-2026-10-24")
        permit = s02.SourceAuthorization(
            s02.SOURCE_REL, "S02", rights_ref, owner_ref,
            (endpoints.AWS.region, endpoints.B2.region),
        )
        try:
            copied = s02.capture_approved_s02(
                repo_root=Path(repo_root), scratch_parent=temp,
                run_id=backup_id, authorization=permit,
            )
            sealed = s02.seal_verified_copy(
                copied=copied, run_id=backup_id, key=data_key,
                authorization=permit,
            )
        except Exception:
            raise BackupOperationError(
                "scoped S02 SQLite capture, size or chain verification failed"
            ) from None
        if not sealed.object_key.startswith(OBJECT_PREFIX):
            raise BackupOperationError("encrypted source key outside permitted IAM scope")
        aws_writer, aws_reader, b2_writer, b2_reader = _provider_clients(credentials)
        # Do not retry failed writes: remote state may be ambiguous.
        try:
            aws_version = _put_verified(
                aws_writer, aws_reader, endpoints.AWS,
                object_key=sealed.object_key, content=sealed.envelope,
                max_bytes=DATA_MAX,
            )
            b2_version = _put_verified(
                b2_writer, b2_reader, endpoints.B2,
                object_key=sealed.object_key, content=sealed.envelope,
                max_bytes=DATA_MAX,
            )
            # Both cloud copies are cryptographically authenticated and the
            # actual SQLite hash-chain is checked independently from each.
            for label, reader, provider, version in (
                ("aws", aws_reader, endpoints.AWS, aws_version),
                ("b2", b2_reader, endpoints.B2, b2_version),
            ):
                retrieved = _read_exact(
                    reader, provider, sealed.object_key, version, DATA_MAX,
                )
                restored = s02.restore_verified_envelope(
                    envelope=retrieved, key=data_key, scratch_parent=temp,
                    restore_id="restore-" + label + "-" + backup_id[7:],
                    expected_sha256=sealed.envelope_sha256,
                )
                if (restored["plaintext_sha256"] != sealed.plaintext_sha256
                        or restored["record_count"] != sealed.record_count):
                    raise BackupOperationError("provider SQLite restore mismatch")
        except Exception:
            raise BackupOperationError(
                "DATA_UPLOAD_PARTIAL_OR_UNKNOWN: no automatic retry or delete; " +
                backup_id
            ) from None
        manifest = {
            "schema": "vowsig-dual-s02-receipt-v1",
            "backup_id": backup_id,
            "object_key": sealed.object_key,
            "object_sha256": sealed.envelope_sha256,
            "plaintext_sha256": sealed.plaintext_sha256,
            "record_count": sealed.record_count,
            "data_key": base64.b64encode(data_key).decode("ascii"),
            "aws_version": aws_version,
            "b2_version": b2_version,
        }
        receipt = _seal_manifest(manifest, backup_id=backup_id, passphrase=passphrase)
        receipt_file = _write_local_receipt(receipt, backup_id, receipt_dir)
        try:
            manifest_path = _manifest_key(backup_id)
            _put_verified(
                aws_writer, aws_reader, endpoints.AWS,
                object_key=manifest_path, content=receipt,
                max_bytes=MANIFEST_MAX,
            )
            _put_verified(
                b2_writer, b2_reader, endpoints.B2,
                object_key=manifest_path, content=receipt,
                max_bytes=MANIFEST_MAX,
            )
        except Exception:
            raise BackupOperationError(
                "RECEIPT_UPLOAD_PARTIAL_OR_UNKNOWN: local encrypted receipt preserved " +
                backup_id
            ) from None
        return {
            "status": "BACKUP_TWO_PROVIDER_VERIFIED",
            "backup_id": backup_id,
            "record_count": sealed.record_count,
            "source_encrypted": True,
            "aws_exact_version_restored": True,
            "b2_exact_version_restored": True,
            "encrypted_receipt_in_both_clouds": True,
            "local_encrypted_receipt": str(receipt_file),
            "scheduled_backup_enabled": False,
        }


def restore_once(*, backup_id: str, output_path: Path,
                 credentials: tuple[tuple[str, str], ...],
                 passphrase: str, local_receipt: Path | None = None) -> dict:
    """Disaster recovery from cloud or encrypted local receipt; never overwrite."""
    _check_id(backup_id)
    dest = Path(output_path)
    if dest.exists() or dest.is_symlink() or not dest.parent.is_dir():
        raise BackupOperationError("recovery destination must be new existing-parent path")
    aws_reader, b2_reader = _provider_readers(credentials)
    manifest_bytes = []
    if local_receipt is not None:
        try:
            local = Path(local_receipt)
            if local.is_symlink() or local.name != backup_id + ".aesgcm":
                raise ValueError
            raw = local.read_bytes()
            _open_manifest(raw, backup_id=backup_id, passphrase=passphrase)
            manifest_bytes.append(raw)
        except Exception:
            raise BackupOperationError("local encrypted receipt invalid") from None
    for provider, reader in ((endpoints.AWS, aws_reader), (endpoints.B2, b2_reader)):
        try:
            blob = _read_exact(reader, provider, _manifest_key(backup_id),
                               None, MANIFEST_MAX)
            _open_manifest(blob, backup_id=backup_id, passphrase=passphrase)
            manifest_bytes.append(blob)
        except Exception:
            pass
    if not manifest_bytes:
        raise BackupOperationError("no authenticated encrypted recovery receipt available")
    # All valid copies must match bit-for-bit; discrepancies are not silently
    # accepted as an authoritative manifest.
    if any(x != manifest_bytes[0] for x in manifest_bytes):
        raise BackupOperationError("recovery receipt replicas differ; manual review")
    manifest = _open_manifest(manifest_bytes[0], backup_id=backup_id,
                              passphrase=passphrase)
    data_key = base64.b64decode(manifest["data_key"], validate=True)
    winners = []
    with tempfile.TemporaryDirectory(prefix="vowsig-s02-restore-") as folder:
        temp = Path(folder)
        for provider, reader, version, label in (
            (endpoints.AWS, aws_reader, manifest["aws_version"], "aws"),
            (endpoints.B2, b2_reader, manifest["b2_version"], "b2"),
        ):
            try:
                data = _read_exact(reader, provider, manifest["object_key"],
                                   version, DATA_MAX)
                if _hash(data) != manifest["object_sha256"]:
                    raise BackupOperationError("remote data digest mismatch")
                result = s02.restore_verified_envelope(
                    envelope=data, key=data_key, scratch_parent=temp,
                    restore_id="restore-" + label + "-" + backup_id[7:],
                    expected_sha256=manifest["object_sha256"],
                )
                if (result["plaintext_sha256"] != manifest["plaintext_sha256"]
                        or result["record_count"] != manifest["record_count"]):
                    raise BackupOperationError("SQLite canonical record verification failed")
                winners.append(label)
            except Exception:
                continue
        if not winners:
            raise BackupOperationError("neither remote provider could restore SQLite")
        verified_source = temp / ("restore-" + winners[0] +
                                  "-" + backup_id[7:]) / "forward.sqlite"
        try:
            with verified_source.open("rb") as src, dest.open("xb") as out:
                shutil.copyfileobj(src, out, length=65536)
        except Exception:
            try:
                dest.unlink(missing_ok=True)
            except Exception:
                pass
            raise BackupOperationError("verified recovery output write failed") from None
    return {
        "status": ("BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED"
                   if len(winners) == 2 else "BACKUP_RECOVERY_DEGRADED_ONE_PROVIDER"),
        "backup_id": backup_id,
        "record_count": manifest["record_count"],
        "aws_restored": "aws" in winners,
        "b2_restored": "b2" in winners,
        "restored_to_new_file": str(dest),
        "production_source_overwritten": False,
    }
