"""Free-to-operate owner TOTP step-up primitives, offline provisioning only.

Never creates owners, enrolls via HTTP, sends secrets, disables MFA, or
relies on Auth0 paid MFA. Provisioning is an independently authorized
owner/migrator-only operation. The runtime may only verify an already
provisioned encrypted secret. Release requires separate owner bootstrap,
secret custody/recovery and independent security review.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import re
import secrets
import struct
from datetime import datetime, timezone
from uuid import UUID

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class OwnerMfaRejected(ValueError):
    """Fail closed without exposing whether a secret or session exists."""


class OwnerMfaConfigurationError(RuntimeError):
    """Missing/invalid approved owner MFA encryption configuration."""


_DIGITS = re.compile(r"^[0-9]{6}$")
SECRET_BYTES = 20
MFA_LOCK_AFTER = 5
MFA_LOCK_SECONDS = 15 * 60


def _owner_aad(account_id: str) -> bytes:
    try:
        uuid = UUID(account_id)
    except (ValueError, TypeError, AttributeError) as exc:
        raise OwnerMfaConfigurationError("Invalid owner binding identity") from exc
    return b"VOWSIG-OWNER-TOTP-v1:" + uuid.bytes


def load_master_key(key_b64: str) -> bytes:
    """Only exact 32-byte canonical URL-safe base64; do not log the key."""
    if not isinstance(key_b64, str) or len(key_b64) != 43:
        raise OwnerMfaConfigurationError("Owner MFA master key missing or invalid")
    try:
        data = base64.urlsafe_b64decode(key_b64 + "=")
    except (ValueError, binascii.Error) as exc:
        raise OwnerMfaConfigurationError("Owner MFA key encoding invalid") from exc
    if len(data) != 32 or base64.urlsafe_b64encode(data).decode().rstrip("=") != key_b64:
        raise OwnerMfaConfigurationError("Owner MFA master key must be 256-bit")
    return data


def new_totp_secret() -> bytes:
    """Use only inside trusted one-time/offline owner credential provisioning."""
    return secrets.token_bytes(SECRET_BYTES)


def base32_for_authenticator(secret: bytes) -> str:
    if not isinstance(secret, bytes) or len(secret) != SECRET_BYTES:
        raise OwnerMfaConfigurationError("TOTP secret must be 160-bit")
    return base64.b32encode(secret).decode("ascii").rstrip("=")


def encrypt_for_owner(secret: bytes, account_id: str, master_key: bytes) -> bytes:
    if not isinstance(secret, bytes) or len(secret) != SECRET_BYTES:
        raise OwnerMfaConfigurationError("TOTP secret must be 160-bit")
    if not isinstance(master_key, bytes) or len(master_key) != 32:
        raise OwnerMfaConfigurationError("Encryption key must be 256-bit")
    nonce = secrets.token_bytes(12)
    return nonce + AESGCM(master_key).encrypt(nonce, secret, _owner_aad(account_id))


def decrypt_for_owner(ciphertext: bytes, account_id: str, master_key: bytes) -> bytes:
    if (not isinstance(ciphertext, bytes) or len(ciphertext) != 48
            or not isinstance(master_key, bytes) or len(master_key) != 32):
        raise OwnerMfaRejected("Owner verification unavailable")
    try:
        data = AESGCM(master_key).decrypt(
            ciphertext[:12], ciphertext[12:], _owner_aad(account_id),
        )
    except Exception as exc:  # authenticated decryption rejects all corrupt blobs
        raise OwnerMfaRejected("Owner verification unavailable") from exc
    if len(data) != SECRET_BYTES:
        raise OwnerMfaRejected("Owner verification unavailable")
    return data


def totp_at(secret: bytes, counter: int) -> str:
    if (not isinstance(secret, bytes) or len(secret) != SECRET_BYTES
            or type(counter) is not int or not 0 <= counter < 2**64):
        raise OwnerMfaConfigurationError("Invalid TOTP counter or secret")
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    pos = digest[-1] & 0x0F
    value = (int.from_bytes(digest[pos:pos+4], "big") & 0x7FFFFFFF) % 1_000_000
    return f"{value:06d}"


def match_step(code: str, secret: bytes, *, now: datetime, last_step: int) -> int | None:
    """Single-use RFC6238 SHA1/30s TOTP, ±1 step clock tolerance."""
    if not isinstance(code, str) or not _DIGITS.fullmatch(code):
        return None
    if (not isinstance(now, datetime) or now.tzinfo is None
            or type(last_step) is not int or last_step < -1):
        raise OwnerMfaConfigurationError("Untrusted TOTP verifier clock/state")
    current = int(now.astimezone(timezone.utc).timestamp()) // 30
    matched = None
    for step in (current-1, current, current+1):
        if step < 0:
            continue
        candidate = totp_at(secret, step)
        if hmac.compare_digest(candidate, code) and step > last_step:
            matched = step if matched is None else max(matched, step)
    return matched
