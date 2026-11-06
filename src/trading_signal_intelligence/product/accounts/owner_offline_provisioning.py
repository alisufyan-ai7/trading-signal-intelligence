"""Offline owner bootstrap/recovery with independently signed authorization.

There are NO public HTTP endpoints here. The signing private key, DB migrator
login and TOTP enrollment secret must never be held by the web application.
A signature authenticates the reviewer, not their real-world due diligence:
operator must separately verify reviewer identity, owner identity and consent.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from trading_signal_intelligence.product.accounts.owner_mfa import (
    OwnerMfaConfigurationError, encrypt_for_owner, match_step,
    SECRET_BYTES,
)

_HEX = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.@-]{2,100}$")
_ENVELOPE_FIELDS = {"authorization", "signature_ed25519_b64u"}
_FIELDS = {
    "schema_version", "purpose", "operation_id", "operation",
    "account_id", "oidc_issuer", "oidc_subject_sha256",
    "reviewer_id", "approved_at_utc", "expires_at_utc",
    "owner_identity_reverified", "owner_consent_confirmed",
}
_PURPOSE = "VOWSIG_OFFLINE_OWNER_MFA_V1"
_MAX_APPROVAL_BYTES = 8_192


class OwnerProvisioningDenied(ValueError):
    """Untrusted approval, identity mismatch, replay or unsafe role transition."""


def _canonical(obj: Any) -> bytes:
    return json.dumps(
        obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _no_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate authorization field")
        result[key] = value
    return result


def _utc(value: str) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise OwnerProvisioningDenied("Approval must use UTC timestamps")
    try:
        dt = datetime.fromisoformat(value[:-1] + "+00:00")
    except (ValueError, OverflowError) as exc:
        raise OwnerProvisioningDenied("Invalid approval timestamp") from exc
    if dt.utcoffset() != timedelta(0):
        raise OwnerProvisioningDenied("Non-UTC approval timestamp")
    return dt


def _uuid(value: str) -> str:
    if not isinstance(value, str):
        raise OwnerProvisioningDenied("Invalid approval account/operation identity")
    try:
        parsed = UUID(value)
    except (ValueError, AttributeError, TypeError) as exc:
        raise OwnerProvisioningDenied("Invalid approval account/operation identity") from exc
    if str(parsed) != value or parsed.version != 4:
        raise OwnerProvisioningDenied("Approval identity must be canonical UUIDv4")
    return value


def verify_owner_approval(
    signed_document: bytes,
    *,
    trusted_reviewer_public_key_pem: bytes,
    trusted_key_sha256: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify signed exact identity, time window and one-use operation contract."""
    if not isinstance(signed_document, bytes) or len(signed_document) > _MAX_APPROVAL_BYTES:
        raise OwnerProvisioningDenied("Missing/oversized authorization")
    if (
        not isinstance(trusted_key_sha256, str)
        or not _HEX.fullmatch(trusted_key_sha256)
        or hashlib.sha256(trusted_reviewer_public_key_pem).hexdigest()
           != trusted_key_sha256
    ):
        raise OwnerProvisioningDenied("Reviewer public key pin mismatch")
    try:
        doc = json.loads(
            signed_document.decode("utf-8"),
            object_pairs_hook=_no_duplicate_keys,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
    except (ValueError, UnicodeDecodeError) as exc:
        raise OwnerProvisioningDenied("Malformed or duplicate approval fields") from exc
    if not isinstance(doc, dict) or set(doc) != _ENVELOPE_FIELDS:
        raise OwnerProvisioningDenied("Unexpected approval envelope")
    body = doc["authorization"]
    if not isinstance(body, dict) or set(body) != _FIELDS:
        raise OwnerProvisioningDenied("Incomplete or extended approval")
    try:
        key = load_pem_public_key(trusted_reviewer_public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise OwnerProvisioningDenied("Reviewer key is not Ed25519")
        signature = doc["signature_ed25519_b64u"]
        if not isinstance(signature, str) or not re.fullmatch(r"[A-Za-z0-9_-]{86}", signature):
            raise OwnerProvisioningDenied("Malformed reviewer signature")
        raw_signature = base64.urlsafe_b64decode(signature + "==")
        if len(raw_signature) != 64:
            raise OwnerProvisioningDenied("Invalid reviewer signature length")
        key.verify(raw_signature, _canonical(body))
    except (ValueError, TypeError, binascii.Error, InvalidSignature) as exc:
        raise OwnerProvisioningDenied("Approval signature invalid") from exc

    if type(body["schema_version"]) is not int or body["schema_version"] != 1:
        raise OwnerProvisioningDenied("Unsupported offline authorization version")
    if body["purpose"] != _PURPOSE or body["operation"] not in ("first_owner", "first_owner_solo", "rotate_factor"):
        raise OwnerProvisioningDenied("Unapproved operation type")
    _uuid(body["operation_id"])
    _uuid(body["account_id"])
    if (
        not isinstance(body["oidc_issuer"], str)
        or not body["oidc_issuer"].startswith("https://")
        or len(body["oidc_issuer"]) > 512
        or body["oidc_issuer"].endswith("/")
    ):
        # Auth0 issuer is commonly a trailing-slash URL; require exact value
        # from the configured OIDC provider instead of normalization.
        if (not isinstance(body["oidc_issuer"], str)
                or not body["oidc_issuer"].startswith("https://")
                or len(body["oidc_issuer"]) > 512):
            raise OwnerProvisioningDenied("Invalid approval OIDC issuer")
    if not isinstance(body["oidc_subject_sha256"], str) or not _HEX.fullmatch(
        body["oidc_subject_sha256"]
    ):
        raise OwnerProvisioningDenied("Missing immutable OIDC subject pin")
    if not isinstance(body["reviewer_id"], str) or not _IDENTIFIER.fullmatch(
        body["reviewer_id"]
    ):
        raise OwnerProvisioningDenied("Missing independent reviewer identity")
    if (body["owner_identity_reverified"] is not True
            or body["owner_consent_confirmed"] is not True):
        raise OwnerProvisioningDenied("Owner re-verification and consent are mandatory")
    now = now or datetime.now(timezone.utc)
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise OwnerProvisioningDenied("Untrusted approval clock")
    now = now.astimezone(timezone.utc)
    approved, expiry = _utc(body["approved_at_utc"]), _utc(body["expires_at_utc"])
    if not (approved <= now < expiry and
            timedelta(0) < expiry - approved <= timedelta(hours=1)):
        raise OwnerProvisioningDenied("Owner authorization expired or not yet valid")
    return body


def _identity_guard(conn: Any, body: dict[str, Any], *, lock: bool) -> dict[str, Any]:
    """Never grant privileges based on email; exact issuer+subject is mandatory."""
    lock_suffix = " FOR UPDATE OF a" if lock else ""
    rows = conn.execute(
        """SELECT a.id::text AS account_id, a.role,
                  a.email_verified_at,a.disabled_at,
                  e.status AS entitlement_status,
                  i.issuer,i.subject
           FROM vowsig_accounts a
           JOIN vowsig_account_entitlements e ON e.account_id=a.id
           JOIN vowsig_account_identities i ON i.account_id=a.id
           WHERE a.id=%s::uuid AND i.issuer=%s""" + lock_suffix,
        (body["account_id"], body["oidc_issuer"]),
    ).fetchall()
    if len(rows) != 1:
        raise OwnerProvisioningDenied("Exact immutable provider binding missing")
    row = rows[0]
    if (
        row["account_id"] != body["account_id"]
        or row["email_verified_at"] is None
        or row["disabled_at"] is not None
        or row["entitlement_status"] != "active"
        or not isinstance(row["subject"], str)
        or not hmac.compare_digest(
            hashlib.sha256(row["subject"].encode("utf-8")).hexdigest(),
            body["oidc_subject_sha256"],
        )
    ):
        raise OwnerProvisioningDenied("Verified owner identity mismatch")
    if body["operation"] in ("first_owner", "first_owner_solo") and row["role"] != "member":
        raise OwnerProvisioningDenied("First owner must begin as verified member")
    if body["operation"] == "rotate_factor" and row["role"] != "owner":
        raise OwnerProvisioningDenied("Recovery requires an existing owner")
    return dict(row)


def preflight_owner_operation(conn: Any, approval: dict[str, Any]) -> dict[str, Any]:
    """Read-only preview; no secrets, emails, subjects or SQL mutations."""
    _identity_guard(conn, approval, lock=False)
    owner_count = conn.execute(
        "SELECT count(*) AS n FROM vowsig_accounts WHERE role='owner'"
    ).fetchone()["n"]
    exists = conn.execute(
        "SELECT 1 FROM vowsig_owner_totp_credentials WHERE account_id=%s::uuid",
        (approval["account_id"],),
    ).fetchone() is not None
    used = conn.execute(
        "SELECT 1 FROM vowsig_owner_provisioning_audit WHERE operation_id=%s::uuid",
        (approval["operation_id"],),
    ).fetchone() is not None
    if used:
        raise OwnerProvisioningDenied("Owner authorization already used")
    if approval["operation"] in ("first_owner", "first_owner_solo") and (owner_count != 0 or exists):
        raise OwnerProvisioningDenied("First-owner invariant failed")
    if approval["operation"] == "rotate_factor" and (owner_count < 1 or not exists):
        raise OwnerProvisioningDenied("Existing owner factor absent")
    return {
        "status": "PREVIEW_OK",
        "operation": approval["operation"],
        "operation_id": approval["operation_id"],
        "account_id": approval["account_id"],
        "verified_provider_binding": True,
        "factors_disclosed": False,
        "sessions_modified": False,
        "pending_offline_owner_code_confirmation": True,
    }


def apply_owner_operation(
    conn: Any,
    signed_document: bytes,
    *,
    trusted_reviewer_public_key_pem: bytes,
    trusted_key_sha256: str,
    enrolled_secret: bytes,
    master_key: bytes,
    owner_code: str,
    operator_id: str,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Verify reviewer signature here, then mutate within caller transaction.

    Caller MUST hold a transaction and migration-only DB credentials; this
    function never accepts a mutable unsigned authorization dictionary.
    Human-confirmed TOTP is required from the newly enrolled owner device.
    """
    if (not isinstance(operator_id, str) or not _IDENTIFIER.fullmatch(operator_id)):
        raise OwnerProvisioningDenied("Missing offline operator identity")
    if not isinstance(enrolled_secret, bytes) or len(enrolled_secret) != SECRET_BYTES:
        raise OwnerProvisioningDenied("Invalid offline enrollment secret")
    if not isinstance(master_key, bytes) or len(master_key) != 32:
        raise OwnerProvisioningDenied("Invalid approved encryption key")
    now = now or datetime.now(timezone.utc)
    approval = verify_owner_approval(
        signed_document,
        trusted_reviewer_public_key_pem=trusted_reviewer_public_key_pem,
        trusted_key_sha256=trusted_key_sha256,
        now=now,
    )
    # Explicit single-founder policy exception: first owner only, never recovery.
    # Do not fabricate distinct human identities to satisfy separation controls.
    if approval["operation"] == "first_owner_solo":
        if operator_id != approval["reviewer_id"]:
            raise OwnerProvisioningDenied("Solo founder must self-authorize truthfully")
    elif operator_id == approval["reviewer_id"]:
        raise OwnerProvisioningDenied("Independent operations need distinct people")
    if not isinstance(now, datetime) or now.tzinfo is None:
        raise OwnerProvisioningDenied("Untrusted owner confirmation clock")
    now = now.astimezone(timezone.utc)
    step = match_step(owner_code, enrolled_secret, now=now, last_step=-1)
    if step is None:
        raise OwnerProvisioningDenied("Owner authenticator enrollment unconfirmed")
    # An offline operator must open a real explicit transaction before writes.
    # PostgreSQL advisory/table locks outside a transaction are not safe.
    from psycopg.pq import TransactionStatus
    if conn.info.transaction_status != TransactionStatus.INTRANS:
        raise OwnerProvisioningDenied("Explicit SQL transaction required")
    # Prevent any caller from using the web application's runtime privileges.
    role = conn.execute("SELECT current_user AS role").fetchone()["role"]
    if role != "vowsig_migrator":
        raise OwnerProvisioningDenied("Offline owner operation requires migrator identity")
    # All affected owner accounts serialise on the SAME audit table lock,
    # not just their individual account row; first-owner is global.
    conn.execute("LOCK TABLE vowsig_owner_provisioning_audit IN EXCLUSIVE MODE")
    _identity_guard(conn, approval, lock=True)
    preflight_owner_operation(conn, approval)
    ciphertext = encrypt_for_owner(enrolled_secret, approval["account_id"], master_key)
    if approval["operation"] in ("first_owner", "first_owner_solo"):
        conn.execute(
            """INSERT INTO vowsig_owner_totp_credentials
               (account_id, secret_ciphertext) VALUES (%s::uuid,%s)""",
            (approval["account_id"], ciphertext),
        )
        changed = conn.execute(
            """UPDATE vowsig_accounts SET role='owner'
               WHERE id=%s::uuid AND role='member' RETURNING id""",
            (approval["account_id"],),
        ).fetchone()
        if changed is None:
            raise OwnerProvisioningDenied("Owner bootstrap no longer safe")
    else:
        changed = conn.execute(
            """UPDATE vowsig_owner_totp_credentials
               SET secret_ciphertext=%s, key_version=1,
                   last_accepted_step=-1, failed_attempts=0,
                   locked_until=NULL, provisioned_at=%s
               WHERE account_id=%s::uuid RETURNING account_id""",
            (ciphertext, now, approval["account_id"]),
        ).fetchone()
        if changed is None:
            raise OwnerProvisioningDenied("Owner credential recovery no longer safe")
    revoked = conn.execute(
        """UPDATE vowsig_account_sessions
           SET revoked_at=%s,mfa_verified_at=NULL
           WHERE account_id=%s::uuid AND revoked_at IS NULL
           RETURNING token_sha256""",
        (now, approval["account_id"]),
    ).fetchall()
    # The approval hash is an audit identifier, NOT a secret; reviewer private
    # signing key and TOTP factor stay outside application and repository.
    digest = hashlib.sha256(_canonical(approval)).hexdigest()
    conn.execute(
        """INSERT INTO vowsig_owner_provisioning_audit
           (operation_id,account_id,operation,reviewer_id,operator_id,
            approved_payload_sha256,revoked_sessions)
           VALUES (%s::uuid,%s::uuid,%s,%s,%s,%s,%s)""",
        (approval["operation_id"], approval["account_id"], approval["operation"],
         approval["reviewer_id"], operator_id, digest, len(revoked)),
    )
    return {
        "status": "APPLIED_REQUIRES_FRESH_LOGIN",
        "operation": approval["operation"],
        "operation_id": approval["operation_id"],
        "account_id": approval["account_id"],
        "revoked_sessions": len(revoked),
        "factor_ciphertext_disclosed": False,
        "fresh_login_required": True,
        "independent_reviewer_involved": approval["operation"] != "first_owner_solo",
        "solo_founder_exception": approval["operation"] == "first_owner_solo",
    }
