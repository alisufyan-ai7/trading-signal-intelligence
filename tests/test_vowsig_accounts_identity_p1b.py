"""P1B-0 provider-neutral identity contract, no live auth or HTTP calls."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from trading_signal_intelligence.product.accounts.identity_contract import (
    IdentityContractError,
    IdentityProviderConfig,
    TrustedOidcClaims,
    existing_account_for_verified_claims,
    validate_verified_claims,
)

NOW = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
CFG = IdentityProviderConfig(issuer="https://identity.example.test/oidc", client_id="vowsig-client")


def valid_claims():
    return TrustedOidcClaims(
        issuer=CFG.issuer,
        subject="issuer-specific-opaque-user-001",
        audience=CFG.client_id,
        nonce="server-bound-one-time-nonce",
        email="person@example.test",
        email_verified=True,
        issued_at_utc=NOW-timedelta(seconds=20),
        expires_at_utc=NOW+timedelta(minutes=4),
        auth_time_utc=NOW-timedelta(seconds=40),
    )


class InMemoryBindings:
    def __init__(self):
        self.links = {}
        self.lookups = []

    def find_bound_account(self, issuer, subject):
        self.lookups.append((issuer, subject))
        return self.links.get((issuer, subject))


def check(claims, *, config=CFG, nonce="server-bound-one-time-nonce"):
    return validate_verified_claims(claims, config, expected_nonce=nonce, now=NOW)


def test_same_exact_issuer_and_subject_is_only_identity_key():
    lookup = InMemoryBindings()
    claims = valid_claims()
    lookup.links[(claims.issuer, claims.subject)] = "account-a"
    assert existing_account_for_verified_claims(
        claims, CFG, expected_nonce=claims.nonce, lookup=lookup, now=NOW
    ) == "account-a"
    assert lookup.lookups == [(claims.issuer, claims.subject)]


def test_same_verified_email_from_different_subject_is_not_an_existing_account():
    lookup = InMemoryBindings()
    original = valid_claims()
    lookup.links[(original.issuer, original.subject)] = "account-a"
    other = replace(original, subject="different-provider-identity", email=original.email)
    assert existing_account_for_verified_claims(
        other, CFG, expected_nonce=other.nonce, lookup=lookup, now=NOW
    ) is None
    assert lookup.lookups == [(other.issuer, other.subject)]


def test_email_address_change_does_not_change_bound_identity_key():
    original = valid_claims()
    updated = replace(original, email="newaddress@example.test")
    assert check(original) == check(updated)


@pytest.mark.parametrize("changes", [
    {"issuer": "https://lookalike.example.test/oidc"},
    {"audience": "another-application"},
    {"nonce": "different"},
    {"email_verified": False},
    {"email": ""},
    {"email": "not-an-email"},
    {"email": "two@@example.test"},
    {"email": "@example.test"},
    {"email": "person@"},
    {"subject": ""},
    {"subject": " "},
    {"subject": "\nsub"},
    {"subject": "x" * 256},
    {"issued_at_utc": NOW + timedelta(seconds=2)},
    {"expires_at_utc": NOW},
    {"auth_time_utc": NOW - timedelta(hours=1)},
    {"auth_time_utc": NOW + timedelta(seconds=1)},
    {"issued_at_utc": NOW-timedelta(hours=2)},
    {"issued_at_utc": datetime(2026, 11, 4, 11, 59, 40)},
    {"auth_time_utc": None},
    {"expires_at_utc": NOW-timedelta(minutes=5)},
])
def test_untrusted_or_stale_claims_fail_closed(changes):
    with pytest.raises(IdentityContractError):
        check(replace(valid_claims(), **changes))


@pytest.mark.parametrize("issuer", [
    "http://identity.example.test",
    "https://user:pass@identity.example.test",
    "https://identity.example.test?redirect=x",
    "https://identity.example.test#part",
    "",
])
def test_identity_issuer_config_requires_exact_https_domain(issuer):
    with pytest.raises(IdentityContractError):
        IdentityProviderConfig(issuer=issuer, client_id="vowsig-client")


def test_wrong_type_and_missing_expected_nonce_fail_closed():
    with pytest.raises(IdentityContractError):
        check({"issuer": CFG.issuer})
    with pytest.raises(IdentityContractError):
        check(valid_claims(), nonce="")


def test_rejected_provider_result_does_not_query_account_mapping():
    lookup = InMemoryBindings()
    with pytest.raises(IdentityContractError):
        existing_account_for_verified_claims(
            replace(valid_claims(), email_verified=False),
            CFG,
            expected_nonce="server-bound-one-time-nonce",
            lookup=lookup,
            now=NOW,
        )
    assert lookup.lookups == []


def test_paid_tier_not_part_of_oidc_subject_proof():
    claim = valid_claims()
    assert not hasattr(claim, "role")
    assert not hasattr(claim, "access_tier")
    assert check(claim) == (CFG.issuer, claim.subject)


def test_issuer_trailing_slash_is_valid_only_when_exactly_configured():
    # Some compliant OIDC providers publish a trailing-slash issuer.
    config = IdentityProviderConfig(
        issuer="https://identity.example.test/oidc/",
        client_id=CFG.client_id,
    )
    claims = replace(valid_claims(), issuer=config.issuer)
    assert validate_verified_claims(
        claims, config, expected_nonce=claims.nonce, now=NOW
    ) == (config.issuer, claims.subject)
    with pytest.raises(IdentityContractError):
        check(claims, config=CFG)
