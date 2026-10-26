"""Owner-signed, encrypted, one-backup-at-a-time S02 GFS delete plans.

Offline policy/authorization protocol. NO provider calls and NO deletions.
Opaque cloud VersionIds are contained only inside AES-GCM ciphertext and
private in-process memory. Never print or commit an unsealed plan.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from . import s02_gfs_retention_policy_v0_1 as gfs

SCHEMA = "vowsig-s02-gfs-single-version-delete-v1"
MAGIC = b"VOWSIG_S02_GFS_DELETE_PLAN_1\x00"
APPROVAL_CONTEXT = b"VOWSIG_S02_GFS_OWNER_APPROVAL_V1\n"
GRACE_DAYS = 7
MAX_PLAN_AGE_DAYS = 14
MAX_SEALED_BYTES = 24000
EXPECTED_OPERATIONS = ("aws_manifest", "aws_data", "b2_manifest", "b2_data")
AWS_BUCKET = "vowsig-backup-s3-2026"
B2_BUCKET = "vowsig-backup-b2-2026"


class GfsDeleteHold(RuntimeError):
    """Sanitized failure, without secrets or cloud version references."""


@dataclass(frozen=True, repr=False)
class SealedDeletePlan:
    blob: bytes = field(repr=False)
    sha256: str
    backup_id: str
    earliest_review_utc: str
    expires_utc: str

    def __repr__(self) -> str:
        return "<SealedGfsDeletePlan PRIVATE>"


@dataclass(frozen=True, repr=False)
class VerifiedDeletePermit:
    backup_id: str
    sealed_sha256: str
    objects: tuple[tuple[str, str, str, str], ...] = field(repr=False)
    protected_ids: frozenset[str]
    approved_at_utc: str

    def __repr__(self) -> str:
        return "<VerifiedGfsDeletePermit PRIVATE>"


def _json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=True, allow_nan=False).encode("ascii")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utc(value: str):
    return gfs._datetime(value)


def _policy_valid(policy: dict[str, Any], candidate: str) -> None:
    if type(policy) is not dict or type(candidate) is not str or not gfs.BACKUP_ID.fullmatch(candidate):
        raise GfsDeleteHold("invalid bounded GFS policy/candidate")
    actual = policy.get("plan_sha256")
    body = {k: v for k, v in policy.items() if k != "plan_sha256"}
    if (type(actual) is not str or not hmac.compare_digest(actual, _sha(_json(body)))
            or policy.get("policy") != gfs.POLICY
            or policy.get("cloud_deletion_authorized") is not False
            or policy.get("provider_deletions_performed") != 0
            or type(policy.get("eligible_ids")) is not list
            or type(policy.get("keep_ids")) is not list
            or type(policy.get("protected_ids")) is not list
            or candidate not in policy["eligible_ids"]
            or candidate in policy["keep_ids"]
            or candidate in policy["protected_ids"]
            or gfs.FIRST_MANUAL_ID not in policy["protected_ids"]
            or len(policy["keep_ids"]) < 2
            or len(set(policy["keep_ids"])) != len(policy["keep_ids"])
            or len(set(policy["eligible_ids"])) != len(policy["eligible_ids"])
            or set(policy["keep_ids"]).intersection(policy["eligible_ids"])):
        raise GfsDeleteHold("GFS eligibility or protected coverage invalid")
    expected_holds = {
        "DUAL_CLOUD_VERSION_AND_RESTORE_INVENTORY_REQUIRED",
        "SEPARATE_7_DAY_OWNER_APPROVAL_REQUIRED",
    }
    if (type(policy.get("hold_reasons")) is not list
            or set(policy["hold_reasons"]) != expected_holds):
        raise GfsDeleteHold("GFS has unresolved safety holds")


def _plan_object_rows(
    candidate: str, version_inventory: dict[str, dict[str, Any]],
    expected_backup_ids: set[str],
) -> tuple[tuple[str, str, str, str], ...]:
    """Inventory must be complete, four keyed objects/provider-pair per ID.

    Expected structure: {aws_data:{id:ObjectVersion}, aws_manifest:{...},
    b2_data:{...}, b2_manifest:{...}} returned by read-only adapter.
    """
    if type(version_inventory) is not dict or set(version_inventory) != set(EXPECTED_OPERATIONS):
        raise GfsDeleteHold("complete scoped version inventory required")
    if type(expected_backup_ids) is not set or not expected_backup_ids:
        raise GfsDeleteHold("complete expected backup ID set required")
    for role in EXPECTED_OPERATIONS:
        entries = version_inventory[role]
        if type(entries) is not dict or set(entries) != expected_backup_ids:
            raise GfsDeleteHold("cloud/version manifest inventory coverage mismatch")
    rows: list[tuple[str, str, str, str]] = []
    keys: dict[str, str] = {}
    for role in EXPECTED_OPERATIONS:
        entry = version_inventory[role][candidate]
        if type(entry.provider) is not str or type(entry.kind) is not str:
            raise GfsDeleteHold("untrusted provider identity")
        provider = "AWS_S3" if role.startswith("aws") else "BACKBLAZE_B2"
        kind = "manifest" if role.endswith("manifest") else "data"
        bucket = AWS_BUCKET if role.startswith("aws") else B2_BUCKET
        if (entry.provider != provider or entry.kind != kind
                or entry.backup_id != candidate
                or type(entry.key) is not str
                or type(entry.version_id) is not str
                or not 1 <= len(entry.version_id) <= 512
                or entry.version_id.lower() == "null"
                or any(ord(char) < 33 or ord(char) > 126 for char in entry.version_id)):
            raise GfsDeleteHold("inconsistent provider exact version reference")
        if kind == "manifest":
            expected_key = "pilot/vowsig/backup-receipts/v1/" + candidate + ".aesgcm"
            if entry.key != expected_key:
                raise GfsDeleteHold("manifest key outside immutable S02 scope")
        else:
            import re
            if re.fullmatch("pilot/vowsig/approved-s02/v1/" +
                            candidate + "/[0-9a-f]{64}\\.aesgcm", entry.key) is None:
                raise GfsDeleteHold("data key outside immutable S02 scope")
        keys[role] = entry.key
        rows.append((role, bucket, entry.key, entry.version_id))
    if keys["aws_data"] != keys["b2_data"] or keys["aws_manifest"] != keys["b2_manifest"]:
        raise GfsDeleteHold("cross-provider cloud object identity mismatch")
    return tuple(rows)


def _encrypt(payload: dict, phrase: str) -> bytes:
    if type(phrase) is not str or not 16 <= len(phrase) <= 256:
        raise GfsDeleteHold("private plan encryption passphrase required")
    salt, nonce = os.urandom(16), os.urandom(12)
    key = hashlib.scrypt(phrase.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
    result = MAGIC + salt + nonce + AESGCM(key).encrypt(nonce, _json(payload), MAGIC)
    if len(result) > MAX_SEALED_BYTES:
        raise GfsDeleteHold("retention plan exceeds safe size")
    return result


def _decrypt(blob: bytes, phrase: str) -> dict:
    if (type(blob) is not bytes or not blob.startswith(MAGIC)
            or not 80 < len(blob) <= MAX_SEALED_BYTES
            or type(phrase) is not str or not 16 <= len(phrase) <= 256):
        raise GfsDeleteHold("invalid encrypted deletion plan")
    try:
        at = len(MAGIC)
        salt, nonce, cipher = blob[at:at+16], blob[at+16:at+28], blob[at+28:]
        key = hashlib.scrypt(phrase.encode("utf-8"), salt=salt, n=16384, r=8, p=1, dklen=32)
        plain = AESGCM(key).decrypt(nonce, cipher, MAGIC)
        obj = json.loads(plain)
        if type(obj) is not dict or _json(obj) != plain:
            raise ValueError
        return obj
    except Exception:
        raise GfsDeleteHold("encrypted plan authentication failed") from None


def approval_message(sealed_sha256: str) -> bytes:
    if (type(sealed_sha256) is not str or len(sealed_sha256) != 64
            or any(c not in "0123456789abcdef" for c in sealed_sha256)):
        raise GfsDeleteHold("invalid sealed plan fingerprint")
    return APPROVAL_CONTEXT + sealed_sha256.encode("ascii")


def freeze_one_candidate(
    *, policy: dict, candidate: str, version_inventory: dict,
    prepared_utc: str, plan_passphrase: str,
) -> SealedDeletePlan:
    """Read-only, private sealed candidate; never grants authorization."""
    _policy_valid(policy, candidate)
    ts = _utc(prepared_utc)
    if _utc(policy["as_of_utc"]) != ts:
        raise GfsDeleteHold("policy snapshot timestamp changed")
    ids = set(policy["keep_ids"]) | set(policy["eligible_ids"]) | set(policy["protected_ids"])
    rows = _plan_object_rows(candidate, version_inventory, ids)
    record = {
        "schema": SCHEMA, "policy": gfs.POLICY,
        "candidate": candidate, "prepared_utc": ts.isoformat(timespec="seconds"),
        "not_before_utc": (ts + timedelta(days=GRACE_DAYS)).isoformat(timespec="seconds"),
        "expires_utc": (ts + timedelta(days=MAX_PLAN_AGE_DAYS)).isoformat(timespec="seconds"),
        "policy_plan_sha256": policy["plan_sha256"],
        "protected_ids": sorted(policy["protected_ids"]),
        "objects": [list(row) for row in rows],
    }
    blob = _encrypt(record, plan_passphrase)
    return SealedDeletePlan(blob, _sha(blob), candidate,
                            record["not_before_utc"], record["expires_utc"])


def verify_owner_signed_candidate(
    *, blob: bytes, plan_passphrase: str, signature: bytes,
    pinned_owner_public_key: bytes, current_utc: str,
    current_policy: dict, version_inventory: dict,
) -> VerifiedDeletePermit:
    """Recheck GFS and ALL four exact current versions after >=7 full days.

    Ed25519 private approval key remains OFF VPS and out of app credentials.
    Pin the public key independently during a separately approved deployment.
    """
    if (type(signature) is not bytes or len(signature) != 64
            or type(pinned_owner_public_key) is not bytes
            or len(pinned_owner_public_key) != 32):
        raise GfsDeleteHold("independent owner approval signature missing")
    fingerprint = _sha(blob)
    try:
        Ed25519PublicKey.from_public_bytes(pinned_owner_public_key).verify(
            signature, approval_message(fingerprint)
        )
    except Exception:
        raise GfsDeleteHold("owner approval signature invalid") from None
    record = _decrypt(blob, plan_passphrase)
    candidate = record.get("candidate")
    now = _utc(current_utc)
    try:
        if (set(record) != {
                "schema", "policy", "candidate", "prepared_utc", "not_before_utc",
                "expires_utc", "policy_plan_sha256", "protected_ids", "objects"}
                or record["schema"] != SCHEMA or record["policy"] != gfs.POLICY
                or _utc(record["not_before_utc"]) != _utc(record["prepared_utc"]) +
                   timedelta(days=GRACE_DAYS)
                or _utc(record["expires_utc"]) != _utc(record["prepared_utc"]) +
                   timedelta(days=MAX_PLAN_AGE_DAYS)
                or now < _utc(record["not_before_utc"])
                or now > _utc(record["expires_utc"])):
            raise GfsDeleteHold("review grace period not satisfied or plan expired")
        _policy_valid(current_policy, candidate)
        if _utc(current_policy["as_of_utc"]) != now:
            raise GfsDeleteHold("fresh policy time not bound to current check")
        if (type(record["protected_ids"]) is not list
                or not set(record["protected_ids"]).issubset(
                    set(current_policy["protected_ids"]) | set(current_policy["keep_ids"])
                )
                or type(record["objects"]) is not list
                or len(record["objects"]) != len(EXPECTED_OPERATIONS)):
            raise GfsDeleteHold("protected backup plan changed")
        current_ids = (set(current_policy["keep_ids"]) |
                       set(current_policy["eligible_ids"]) |
                       set(current_policy["protected_ids"]))
        fresh = _plan_object_rows(candidate, version_inventory, current_ids)
        if record["objects"] != [list(row) for row in fresh]:
            raise GfsDeleteHold("cloud object versions changed since owner review")
    except GfsDeleteHold:
        raise
    except Exception:
        raise GfsDeleteHold("owner plan approval could not be reconciled") from None
    return VerifiedDeletePermit(candidate, fingerprint, fresh,
                                frozenset(current_policy["protected_ids"]),
                                now.isoformat(timespec="seconds"))
