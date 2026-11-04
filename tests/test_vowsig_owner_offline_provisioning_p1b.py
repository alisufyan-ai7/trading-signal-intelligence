"""Offline owner provisioning tests: synthetic identities and ephemeral Ed25519 keys."""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path

import pytest

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    OwnerProvisioningDenied, _canonical, verify_owner_approval,
)

NOW = datetime(2026, 11, 4, 17, 0, tzinfo=timezone.utc)
OWNER = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
OPERATION = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"


def approval(**changes):
    result = {
        "schema_version": 1,
        "purpose": "VOWSIG_OFFLINE_OWNER_MFA_V1",
        "operation_id": OPERATION,
        "operation": "first_owner",
        "account_id": OWNER,
        "oidc_issuer": "https://synthetic.auth0.example.test/",
        "oidc_subject_sha256": hashlib.sha256(b"immutable-owner-subject").hexdigest(),
        "reviewer_id": "reviewer.security",
        "approved_at_utc": "2026-11-04T16:58:00Z",
        "expires_at_utc": "2026-11-04T17:28:00Z",
        "owner_identity_reverified": True,
        "owner_consent_confirmed": True,
    }
    result.update(changes)
    return result


def signer():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return private, public, hashlib.sha256(public).hexdigest()


def signed(private, body):
    signature = private.sign(_canonical(body))
    return _canonical({
        "authorization": body,
        "signature_ed25519_b64u": base64.urlsafe_b64encode(signature).decode().rstrip("="),
    })


def test_exact_subject_pinned_external_review_with_30minute_expiry():
    key, public, pin = signer()
    body = approval()
    result = verify_owner_approval(signed(key, body),
                                   trusted_reviewer_public_key_pem=public,
                                   trusted_key_sha256=pin, now=NOW)
    assert result == body
    assert "immutable-owner-subject" not in str(result)


@pytest.mark.parametrize("change", [
    {"operation": "create_unlimited_owners"},
    {"operation_id": "not-a-uuid"},
    {"account_id": "not-a-uuid"},
    {"schema_version": 0},
    {"schema_version": True},
    {"purpose": "OTHER"},
    {"oidc_issuer": "http://identity.test"},
    {"oidc_subject_sha256": "short"},
    {"owner_identity_reverified": False},
    {"owner_consent_confirmed": False},
    {"reviewer_id": "@@@"},
    {"expires_at_utc": "2026-11-04T18:58:01Z"},
    {"expires_at_utc": "2026-11-04T16:59:00Z"},
])
def test_invalid_even_when_review_signature_is_genuine(change):
    key, public, pin = signer()
    with pytest.raises(OwnerProvisioningDenied):
        verify_owner_approval(signed(key, approval(**change)),
                              trusted_reviewer_public_key_pem=public,
                              trusted_key_sha256=pin, now=NOW)


def test_expired_future_reviewer_and_pin_mismatch_fail_closed():
    key, public, pin = signer()
    doc = signed(key, approval())
    for when in [NOW + timedelta(hours=1), NOW - timedelta(hours=1)]:
        with pytest.raises(OwnerProvisioningDenied):
            verify_owner_approval(doc, trusted_reviewer_public_key_pem=public,
                                  trusted_key_sha256=pin, now=when)
    _, wrong_public, wrong_pin = signer()
    with pytest.raises(OwnerProvisioningDenied):
        verify_owner_approval(doc, trusted_reviewer_public_key_pem=wrong_public,
                              trusted_key_sha256=wrong_pin, now=NOW)
    with pytest.raises(OwnerProvisioningDenied):
        verify_owner_approval(doc, trusted_reviewer_public_key_pem=public,
                              trusted_key_sha256="f"*64, now=NOW)


def test_tampering_duplicate_json_and_unknown_fields_are_refused():
    key, public, pin = signer()
    raw = signed(key, approval())
    tampered = json.loads(raw)
    tampered["authorization"]["account_id"] = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    with pytest.raises(OwnerProvisioningDenied):
        verify_owner_approval(_canonical(tampered),
                              trusted_reviewer_public_key_pem=public,
                              trusted_key_sha256=pin, now=NOW)
    for replaced in [
        raw.replace(b'"schema_version":1',
                    b'"schema_version":1,"schema_version":1'),
        raw.replace(b'"reviewer_id":"reviewer.security"',
                    b'"extra":true,"reviewer_id":"reviewer.security"'),
        b"{}",
    ]:
        with pytest.raises(OwnerProvisioningDenied):
            verify_owner_approval(replaced, trusted_reviewer_public_key_pem=public,
                                  trusted_key_sha256=pin, now=NOW)


def test_cli_remains_preview_only_by_default_and_no_non_private_dsn():
    import ast
    p=Path(__file__).resolve().parents[1]/"scripts"/"vowsig_owner_offline_operator.py"
    script=p.read_text()
    ast.parse(script)
    assert 'default="preview"' in script
    assert 'args.acknowledge != ACK' in script
    assert "sys.stdin.isatty()" in script and "sys.stdout.isatty()" in script
    assert 'p.hostname != "postgres.railway.internal"' in script
    assert 'params.get("sslmode") != ["verify-full"]' in script
    assert 'getpass.getpass(' in script
    assert "print(json.dumps(receipt" in script
