"""EXP037 bounded synthetic-only S3 API transport; NO CLI or credential loader.

This module is NEVER imported by a production entry point. It requires caller-
supplied independently scoped writer/reader clients, precise endpoints, and
explicit second-stage network authorization. No boto3 import or network
connection is made by importing this module. Offline tests use fake clients.

Real synthetic cloud calls are NOT authorized by merging or testing this file.
Owner must separately approve exact two-PUT/six-request dry-run before enabling
a local, credential-protected invocation; no real VPS/database use at any time.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import b1b2_synthetic_v0_1 as b1
from . import b3_synthetic_encrypted_offsite_v0_1 as b3

# Exact owner supplied names. Do NOT derive from user input or environment.
AWS_BUCKET = "vowsig-backup-s3-2026"
AWS_REGION = "us-east-1"
AWS_ENDPOINT = "https://s3.us-east-1.amazonaws.com"
B2_BUCKET = "vowsig-backup-b2-2026"
B2_REGION = "us-east-005"
B2_ENDPOINT = "https://s3.us-east-005.backblazeb2.com"

# Tight one-time limits. This is NOT a provider-side bill/price guarantee.
MAX_ENVELOPE_BYTES = 128 * 1024
MAX_REMOTE_OPERATIONS = 6  # 2 HEAD + 2 PUT + 2 GET across both providers
APPROVAL_PHRASE = "OWNER_APPROVED_EXP037_SYNTHETIC_TWO_PROVIDER_PILOT"
KEY_RE = re.compile(r"^pilot/synthetic/v1/[a-z][a-z0-9_-]{0,39}/[0-9a-f]{64}\.aesgcm$")


class SyntheticS3PilotRejected(RuntimeError):
    """No provider exception or credentials should be exposed in operator logs."""


@dataclass(frozen=True)
class Provider:
    name: str
    bucket: str
    region: str
    endpoint: str


AWS = Provider("AWS_S3", AWS_BUCKET, AWS_REGION, AWS_ENDPOINT)
B2 = Provider("BACKBLAZE_B2", B2_BUCKET, B2_REGION, B2_ENDPOINT)


@dataclass(frozen=True)
class PilotReceipt:
    provider: str
    bucket: str
    region: str
    object_key: str
    object_sha256: str
    version_id: str
    verified_record_count: int


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _check_client(client: Any, provider: Provider) -> None:
    """Requires fixed endpoint, SigV4 and no hidden SDK retries."""
    try:
        meta = client.meta
        config = meta.config
        retries = config.retries
        if (meta.endpoint_url != provider.endpoint
                or meta.region_name != provider.region
                or not isinstance(retries, dict)
                or retries.get("total_max_attempts") != 1
                or config.signature_version != "s3v4"
                or int(config.connect_timeout) > 5
                or int(config.read_timeout) > 10):
            raise SyntheticS3PilotRejected("provider client configuration rejected")
        for method in ("head_object", "put_object", "get_object"):
            if not callable(getattr(client, method)):
                raise SyntheticS3PilotRejected("missing S3 client operation")
    except (AttributeError, TypeError, ValueError) as exc:
        raise SyntheticS3PilotRejected("unverifiable provider client configuration") from exc


def _expect_new_key(client: Any, provider: Provider, key: str, budget: list[int]) -> None:
    """HEAD 404 only; permission or transport uncertainty MUST stop."""
    if budget[0] >= MAX_REMOTE_OPERATIONS:
        raise SyntheticS3PilotRejected("synthetic API request budget exhausted")
    budget[0] += 1
    try:
        client.head_object(Bucket=provider.bucket, Key=key)
    except Exception as exc:
        response = getattr(exc, "response", None)
        error = response.get("Error", {}) if isinstance(response, dict) else {}
        metadata = response.get("ResponseMetadata", {}) if isinstance(response, dict) else {}
        if (error.get("Code") in ("404", "NoSuchKey", "NotFound")
                and metadata.get("HTTPStatusCode") == 404):
            return
        # Do not echo exception, request identifiers, tokens or URLs.
        raise SyntheticS3PilotRejected("object existence check inconclusive") from None
    raise SyntheticS3PilotRejected("synthetic object key already exists")


def _readback(client: Any, provider: Provider, key: str,
              version: str, expected_sha: str, budget: list[int]) -> bytes:
    if budget[0] >= MAX_REMOTE_OPERATIONS:
        raise SyntheticS3PilotRejected("synthetic API request budget exhausted")
    budget[0] += 1
    try:
        response = client.get_object(Bucket=provider.bucket, Key=key, VersionId=version)
        if (not isinstance(response, dict)
                or response.get("VersionId") != version
                or type(response.get("ContentLength")) is not int
                or not 0 < response["ContentLength"] <= MAX_ENVELOPE_BYTES):
            raise SyntheticS3PilotRejected("unverified provider readback metadata")
        body = response["Body"]
        try:
            downloaded = body.read(MAX_ENVELOPE_BYTES + 1)
        finally:
            body.close()
        if (not isinstance(downloaded, bytes)
                or len(downloaded) != response["ContentLength"]
                or _sha(downloaded) != expected_sha):
            raise SyntheticS3PilotRejected("synthetic readback mismatch")
        return downloaded
    except SyntheticS3PilotRejected:
        raise
    except Exception:
        raise SyntheticS3PilotRejected("synthetic provider readback failed") from None


def _run_one(provider: Provider, writer: Any, reader: Any, obj: b3.SealedSynthetic,
             key: bytes, fixture_root: Path, budget: list[int]) -> PilotReceipt:
    _check_client(writer, provider)
    _check_client(reader, provider)
    _expect_new_key(reader, provider, obj.object_key, budget)
    if budget[0] >= MAX_REMOTE_OPERATIONS:
        raise SyntheticS3PilotRejected("synthetic API request budget exhausted")
    budget[0] += 1
    arguments = dict(
        Bucket=provider.bucket,
        Key=obj.object_key,
        Body=obj.envelope,
        ContentLength=len(obj.envelope),
        ContentType="application/octet-stream",
    )
    # AWS supports an atomic no-overwrite precondition.
    # B2 support for this header is not established: do NOT assume it.
    # B2 unique random-nonce content-hash keys plus a preceding HEAD reduce
    # collision risk but DO NOT provide atomic no-overwrite guarantees.
    if provider == AWS:
        arguments["IfNoneMatch"] = "*"
    try:
        result = writer.put_object(**arguments)
        if not isinstance(result, dict):
            raise SyntheticS3PilotRejected("no provider upload receipt")
        version = result.get("VersionId")
        if (not isinstance(version, str)
                or not version
                or len(version) > 512
                or any(ch in version for ch in "\r\n")):
            raise SyntheticS3PilotRejected("missing versioned upload receipt")
    except SyntheticS3PilotRejected:
        raise
    except Exception:
        # An ambiguous write MAY already be present. NO automatic retry/delete.
        raise SyntheticS3PilotRejected("synthetic upload ambiguous; stop, do not retry") from None
    downloaded = _readback(reader, provider, obj.object_key, version,
                           obj.envelope_sha256, budget)
    # Independent restore: original SealedSynthetic object is NOT supplied.
    restore_id = "awsrestore" if provider == AWS else "b2restore"
    try:
        recovered = b3.restore_synthetic_s02(
            fixture_root, downloaded, key=key, restore_id=restore_id)
    except b3.SyntheticOffsiteRejected:
        raise SyntheticS3PilotRejected("authenticated synthetic SQLite restore failed") from None
    if (recovered.get("status") != "SYNTHETIC_ONLY_RESTORE_VERIFIED"
            or recovered.get("sha256") != obj.plaintext_sha256
            or recovered.get("records") != obj.record_count):
        raise SyntheticS3PilotRejected("synthetic restored identity mismatch")
    return PilotReceipt(
        provider=provider.name, bucket=provider.bucket,
        region=provider.region, object_key=obj.object_key,
        object_sha256=obj.envelope_sha256, version_id=version,
        verified_record_count=obj.record_count,
    )


def run_two_provider_pilot(
    *, fixture_root: Path, obj: b3.SealedSynthetic, key: bytes,
    aws_writer: Any, aws_reader: Any, b2_writer: Any, b2_reader: Any,
    network_approved: bool = False, approval_phrase: str = "",
) -> dict:
    """Gate at top before any client call; no active invocation exists in repo.

    NO startup code, no environment secrets, no scheduled calls. An approved
    future operator driver must separately create narrowly scoped boto3
    clients, must not log keys, and must obtain approval outside this module.
    """
    if network_approved is not True or approval_phrase != APPROVAL_PHRASE:
        raise SyntheticS3PilotRejected("external synthetic cloud pilot not authorized")
    if (not isinstance(obj, b3.SealedSynthetic)
            or not isinstance(obj.envelope, bytes)
            or len(obj.envelope) > MAX_ENVELOPE_BYTES
            or not KEY_RE.fullmatch(obj.object_key)
            or _sha(obj.envelope) != obj.envelope_sha256
            or obj.object_key != (
                f"{b3.OBJECT_PREFIX}"
                f"{obj.object_key.split('/')[3]}/{obj.envelope_sha256}.aesgcm")
            or not isinstance(key, bytes) or len(key) != 32):
        raise SyntheticS3PilotRejected("unapproved synthetic object or size")
    try:
        b1.assert_fixture_scope(Path(fixture_root))
        metadata, _, _, _ = b3._decode_envelope(obj.envelope)
        if (metadata.get("classification") != "SYNTHETIC_ONLY_NEVER_PRODUCTION"
                or metadata.get("plaintext_sha256") != obj.plaintext_sha256
                or metadata.get("record_count") != obj.record_count):
            raise SyntheticS3PilotRejected("synthetic manifest attestation rejected")
    except (b1.SyntheticGateRejected, b3.SyntheticOffsiteRejected, OSError) as exc:
        raise SyntheticS3PilotRejected("synthetic fixture or envelope rejected") from exc
    # Client configs are inspected before any network operation on either.
    for provider, writer, reader in (
        (AWS, aws_writer, aws_reader),
        (B2, b2_writer, b2_reader),
    ):
        _check_client(writer, provider)
        _check_client(reader, provider)
        if writer is reader:
            raise SyntheticS3PilotRejected("writer and readback credentials must be separate")
    budget = [0]
    receipts = []
    for provider, writer, reader in (
        (AWS, aws_writer, aws_reader), (B2, b2_writer, b2_reader)
    ):
        receipts.append(_run_one(provider, writer, reader, obj, key, Path(fixture_root), budget))
    if budget[0] != MAX_REMOTE_OPERATIONS or len(receipts) != 2:
        raise SyntheticS3PilotRejected("provider request budget or receipt count mismatch")
    return {
        "status": "SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES",
        "protection_class": "SYNTHETIC_ONLY_NOT_REAL_APPLICATION_BACKUP",
        "max_requests": MAX_REMOTE_OPERATIONS,
        "actual_attempted_requests": budget[0],
        "object_size_bytes": len(obj.envelope),
        "receipts": [receipt.__dict__ for receipt in receipts],
    }
