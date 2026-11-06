"""P1B-0 trusted identity-provider boundary (NO login endpoint or token decoding).

A selected OIDC adapter is responsible for the actual authorization-code+PKCE
exchange, exact redirect/state/nonce validation, signature/JWKS verification,
issuer, audience, token expiry and replay checks BEFORE returning these claims.
This module only performs *defense in depth* on already cryptographically
verified provider results. Never instantiate these from untrusted HTTP JSON.
Do not identify a returning customer by email equality; the immutable pair
(issuer, subject) is the sole external identity key.

Production session issuance and initial account linking are NOT implemented.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlsplit


class IdentityContractError(ValueError):
    """OIDC result does not meet the immutable account-linking contract."""


@dataclass(frozen=True)
class TrustedOidcClaims:
    """Only an authenticated OIDC adapter may construct a trusted instance."""

    issuer: str
    subject: str
    audience: str
    nonce: str
    email: str
    email_verified: bool
    issued_at_utc: datetime
    expires_at_utc: datetime
    auth_time_utc: datetime


class OidcVerifier(Protocol):
    """Future provider-specific, security-reviewed adapter contract.

    Caller separately verifies callback state against a server-side,
    single-use browser authorization transaction; PKCE code_verifier is
    bound to that transaction. The implementation MUST exchange code only
    via its allowlisted provider token endpoint, cryptographically verify
    JWT using provider JWKS, pin issuer, audience/client ID and nonce,
    handle rotation, enforce code/nonce replay protection and return
    TrustedOidcClaims only after all verification steps succeed.
    """

    def verify_callback(
        self, *, authorization_code: str, code_verifier: str, expected_nonce: str
    ) -> TrustedOidcClaims: ...


@dataclass(frozen=True)
class IdentityProviderConfig:
    issuer: str
    client_id: str

    def __post_init__(self) -> None:
        parsed = urlsplit(self.issuer)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or not isinstance(self.client_id, str)
            or not self.client_id.strip()
        ):
            raise IdentityContractError("Exact trusted HTTPS issuer and client ID required")


def validate_verified_claims(
    claims: TrustedOidcClaims,
    config: IdentityProviderConfig,
    *,
    expected_nonce: str,
    now: datetime | None = None,
    max_auth_age_seconds: int = 600,
) -> tuple[str, str]:
    """Return (issuer,subject) after an OIDC adapter verified the JWT.

    These consistency checks are NOT a substitute for signature/JWKS, state,
    PKCE, token-endpoint, nonce replay and callback-origin verification.
    """
    if not isinstance(claims, TrustedOidcClaims):
        raise IdentityContractError("Trusted provider-verification result required")
    current = now or datetime.now(timezone.utc)
    if current.tzinfo is None:
        raise IdentityContractError("UTC-aware clock required")
    current = current.astimezone(timezone.utc)
    if claims.issuer != config.issuer or claims.audience != config.client_id:
        raise IdentityContractError("Untrusted issuer or wrong audience")
    if (
        not isinstance(claims.subject, str)
        or not claims.subject.strip()
        or len(claims.subject) > 255
        or any(ord(char) < 32 for char in claims.subject)
    ):
        raise IdentityContractError("Missing or invalid immutable provider subject")
    if not expected_nonce or claims.nonce != expected_nonce:
        raise IdentityContractError("OIDC nonce mismatch")
    if claims.email_verified is not True:
        raise IdentityContractError("Verified email required")
    if (
        not isinstance(claims.email, str)
        or len(claims.email) > 254
        or claims.email.count("@") != 1
        or not claims.email.split("@", 1)[0]
        or not claims.email.split("@", 1)[1]
        or any(c.isspace() or ord(c) < 32 for c in claims.email)
    ):
        raise IdentityContractError("Verified usable email required")
    dates = (
        claims.issued_at_utc,
        claims.expires_at_utc,
        claims.auth_time_utc,
    )
    if any(not isinstance(d, datetime) or d.tzinfo is None for d in dates):
        raise IdentityContractError("Explicit timezone-aware claims required")
    issued, expires, authenticated = (d.astimezone(timezone.utc) for d in dates)
    if (
        expires <= current
        or issued > current
        or issued >= expires
        or authenticated > current
        or authenticated > issued
        or max_auth_age_seconds <= 0
        or (current - authenticated).total_seconds() > max_auth_age_seconds
    ):
        raise IdentityContractError("Expired, future or old authentication proof")
    return claims.issuer, claims.subject


class BoundIdentityLookup(Protocol):
    """Lookup must be parameterized and must NOT fall back to email matching."""

    def find_bound_account(self, issuer: str, subject: str) -> str | None: ...


def existing_account_for_verified_claims(
    claims: TrustedOidcClaims,
    config: IdentityProviderConfig,
    *,
    expected_nonce: str,
    lookup: BoundIdentityLookup,
    now: datetime | None = None,
) -> str | None:
    issuer, subject = validate_verified_claims(
        claims, config, expected_nonce=expected_nonce, now=now
    )
    return lookup.find_bound_account(issuer, subject)
