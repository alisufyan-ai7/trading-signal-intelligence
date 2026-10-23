"""EXP045 P3 — OFFLINE signed release-evidence review only.

This module never creates cloud clients, opens SQLite, reads credentials,
installs tasks or performs HTTP. Even a cryptographically valid signed record
is NOT an authorization to execute AWS/B2 requests: account billing, IAM,
Object Lock, residency and data rights need independent external checks.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

SCHEMA = "vowsig-offline-backup-release-review-v0.1"
REPOSITORY = "alisufyan-ai7/trading-signal-intelligence"
SOURCE = "data/forward.sqlite"
PROVIDERS = (
    ("AWS_S3", "vowsig-backup-s3-2026", "us-east-1", "https://s3.us-east-1.amazonaws.com"),
    ("BACKBLAZE_B2", "vowsig-backup-b2-2026", "us-east-005",
     "https://s3.us-east-005.backblazeb2.com"),
)
MAX_SIGNED_REQUESTS = 5
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_WINDOW = timedelta(days=7)
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
ALLOWED_KEYS = frozenset((
    "schema", "repository", "source_relative_path", "source_type",
    "candidate_head", "main_head", "provider_targets", "max_signed_requests",
    "max_source_bytes", "issued_utc", "expires_utc", "nonce",
    "source_rights_review_sha256", "region_and_processor_review_sha256",
    "account_billing_zero_spend_review_sha256",
    "provider_iam_versioning_retention_review_sha256",
    "offhost_key_recovery_drill_sha256",
    "windows_acl_and_scratch_review_sha256",
    "offhost_disaster_restore_drill_sha256",
    "operator_alerting_rollback_review_sha256",
))
EVIDENCE_KEYS = tuple(sorted(x for x in ALLOWED_KEYS if x.endswith("_sha256")))


class ReleaseEvidenceRejected(RuntimeError):
    """Never return signed document contents or signature material in errors."""


@dataclass(frozen=True)
class ReleaseEvidenceAssessment:
    offline_document_verified: bool
    release_status: str
    independently_verified_provider_accounts: bool
    independently_verified_zero_spend: bool
    independently_verified_storage_rights: bool
    live_provider_requests_authorized: bool


def _canonical(document: Mapping[str, Any]) -> bytes:
    return json.dumps(document, sort_keys=True, ensure_ascii=False,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def _utc(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ReleaseEvidenceRejected("evidence time format rejected")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None or dt.utcoffset() != timedelta(0):
            raise ValueError
        return dt
    except (TypeError, ValueError, OverflowError):
        raise ReleaseEvidenceRejected("evidence UTC timestamp rejected") from None


def validate_document(document: Mapping[str, Any],
                      *, now: datetime | None = None) -> bytes:
    """Verify only a tightly scoped OFFLINE evidence assertion structure.

    The digest fields must reference independently collected, reviewable evidence.
    Matching their syntax is NEVER proof of legal rights or zero cost.
    """
    if (type(document) is not dict or set(document) != ALLOWED_KEYS):
        raise ReleaseEvidenceRejected("offline release evidence schema rejected")
    if (document["schema"] != SCHEMA
            or document["repository"] != REPOSITORY
            or document["source_relative_path"] != SOURCE
            or document["source_type"] != "S02"
            or type(document["provider_targets"]) is not list
            or document["provider_targets"] != [list(p) for p in PROVIDERS]
            or type(document["max_signed_requests"]) is not int
            or document["max_signed_requests"] != MAX_SIGNED_REQUESTS
            or type(document["max_source_bytes"]) is not int
            or document["max_source_bytes"] != MAX_SOURCE_BYTES
            or not isinstance(document["candidate_head"], str)
            or not HEX40.fullmatch(document["candidate_head"])
            or not isinstance(document["main_head"], str)
            or not HEX40.fullmatch(document["main_head"])
            or document["candidate_head"] == document["main_head"]
            or not isinstance(document["nonce"], str)
            or not HEX64.fullmatch(document["nonce"])):
        raise ReleaseEvidenceRejected("release target identity rejected")
    if any(not isinstance(document[k], str) or
           not HEX64.fullmatch(document[k]) for k in EVIDENCE_KEYS):
        raise ReleaseEvidenceRejected("missing reviewed evidence fingerprints")
    issued, expires = _utc(document["issued_utc"]), _utc(document["expires_utc"])
    check_time = datetime.now(timezone.utc) if now is None else now
    if (not isinstance(check_time, datetime)
            or check_time.tzinfo is None
            or check_time.utcoffset() is None):
        raise ReleaseEvidenceRejected("clock anchor rejected")
    check_time = check_time.astimezone(timezone.utc)
    if (issued > check_time or expires <= check_time or expires <= issued
            or expires - issued > MAX_WINDOW):
        raise ReleaseEvidenceRejected("release evidence validity window rejected")
    return _canonical(document)


def verify_signed_offline_review(
    document: Mapping[str, Any],
    *, signing_public_key: bytes,
    signature: bytes,
    pinned_public_key_sha256: str,
    now: datetime | None = None,
) -> ReleaseEvidenceAssessment:
    """Verify integrity/authorship of a REVIEW, never authorize cloud I/O.

    Trusted public key hash must be pinned by an independent governance action.
    This routine deliberately offers no network-op enable flag.
    """
    if (type(signing_public_key) is not bytes or len(signing_public_key) != 32
            or type(signature) is not bytes or len(signature) != 64
            or type(pinned_public_key_sha256) is not str
            or not HEX64.fullmatch(pinned_public_key_sha256)
            or hashlib.sha256(signing_public_key).hexdigest()
               != pinned_public_key_sha256):
        raise ReleaseEvidenceRejected("trusted release signing identity rejected")
    payload = validate_document(document, now=now)
    try:
        Ed25519PublicKey.from_public_bytes(signing_public_key).verify(
            signature, payload
        )
    except (InvalidSignature, ValueError, TypeError):
        raise ReleaseEvidenceRejected("release review signature rejected") from None
    # Cryptographically signed *claims* alone do NOT establish external truth.
    # No function in this module permits any real provider API or real DB read.
    return ReleaseEvidenceAssessment(
        offline_document_verified=True,
        release_status="OFFLINE_SIGNED_EVIDENCE_ONLY_EXTERNAL_HOLDS",
        independently_verified_provider_accounts=False,
        independently_verified_zero_spend=False,
        independently_verified_storage_rights=False,
        live_provider_requests_authorized=False,
    )


def block_unattested_live_backup() -> None:
    """Unconditional until a separately approved and tested release redesign."""
    raise ReleaseEvidenceRejected(
        "real cloud backup remains disabled pending external release gate"
    )
