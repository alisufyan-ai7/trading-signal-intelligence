"""Owner TOTP step-up: offline-factor encryption, RFC6238, replay and fail-close.

All secrets/keys are synthetic, never production owner credentials.
"""
from __future__ import annotations

import base64
from datetime import datetime, timezone, timedelta

import pytest

from trading_signal_intelligence.product.accounts.owner_mfa import (
    OwnerMfaRejected, OwnerMfaConfigurationError,
    MFA_LOCK_AFTER, MFA_LOCK_SECONDS,
    base32_for_authenticator, decrypt_for_owner, encrypt_for_owner,
    load_master_key, match_step, new_totp_secret, totp_at,
)

OWNER_A = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa"
OWNER_B = "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
KEY = bytes(range(32))
SECRET = b"12345678901234567890"


def test_rfc6238_sha1_30second_six_digits_and_single_use():
    now = datetime.fromtimestamp(59, timezone.utc)
    assert totp_at(SECRET, 1) == "287082"  # RFC6238 8-digit 94287082
    assert match_step("287082", SECRET, now=now, last_step=-1) == 1
    assert match_step("287082", SECRET, now=now, last_step=1) is None
    assert match_step("287082", SECRET, now=now, last_step=2) is None
    assert match_step("x287082", SECRET, now=now, last_step=-1) is None
    assert match_step("28708", SECRET, now=now, last_step=-1) is None
    assert match_step(287082, SECRET, now=now, last_step=-1) is None
    assert MFA_LOCK_AFTER == 5 and MFA_LOCK_SECONDS == 900


def test_aesgcm_mfa_secret_binds_exact_owner_and_key_and_detects_mutation():
    ciphertext = encrypt_for_owner(SECRET, OWNER_A, KEY)
    assert len(ciphertext) == 48
    assert SECRET not in ciphertext
    assert decrypt_for_owner(ciphertext, OWNER_A, KEY) == SECRET
    with pytest.raises(OwnerMfaRejected):
        decrypt_for_owner(ciphertext, OWNER_B, KEY)
    with pytest.raises(OwnerMfaRejected):
        decrypt_for_owner(ciphertext, OWNER_A, bytes(reversed(KEY)))
    damaged = bytearray(ciphertext)
    damaged[-1] ^= 1
    with pytest.raises(OwnerMfaRejected):
        decrypt_for_owner(bytes(damaged), OWNER_A, KEY)
    with pytest.raises(OwnerMfaRejected):
        decrypt_for_owner(ciphertext[:17], OWNER_A, KEY)


def test_only_exact_256bit_urlsafe_key_and_strong_offline_secret_accepted():
    encoded = base64.urlsafe_b64encode(KEY).decode().rstrip("=")
    assert load_master_key(encoded) == KEY
    for value in ("", "abc", "x"*43, encoded + "=", encoded[:-1] + "!"):
        with pytest.raises(OwnerMfaConfigurationError):
            load_master_key(value)
    fresh = new_totp_secret()
    assert len(fresh) == 20
    assert len(base32_for_authenticator(fresh)) == 32
    with pytest.raises(OwnerMfaConfigurationError):
        encrypt_for_owner(b"weak", OWNER_A, KEY)
    with pytest.raises(OwnerMfaConfigurationError):
        base32_for_authenticator(b"short")
    with pytest.raises(OwnerMfaConfigurationError):
        encrypt_for_owner(SECRET, "not-a-uuid", KEY)


def test_invalid_or_unzoned_clock_never_generates_authenticated_session():
    with pytest.raises(OwnerMfaConfigurationError):
        match_step("123456", SECRET, now=datetime(2026, 1, 1), last_step=-1)
    with pytest.raises(OwnerMfaConfigurationError):
        match_step("123456", SECRET, now=datetime.now(timezone.utc), last_step=-2)
    with pytest.raises(OwnerMfaConfigurationError):
        totp_at(SECRET, -1)
