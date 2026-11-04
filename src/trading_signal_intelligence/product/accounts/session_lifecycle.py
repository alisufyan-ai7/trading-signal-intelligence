"""Provider-neutral verified-login/session lifecycle, unavailable via HTTP until OIDC configured.

Only pass TrustedOidcClaims from a verifier which checked signed ID token,
audience, issuer, one-time state/nonce, PKCE and auth_time. A dataclass by itself
is not proof of cryptographic verification, so NO public route accepts it.
"""
from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Protocol

from fastapi import Response

from trading_signal_intelligence.product.accounts.identity_contract import (
    IdentityProviderConfig, TrustedOidcClaims, validate_verified_claims,
)
from trading_signal_intelligence.product.accounts.security import COOKIE

SESSION_TTL = timedelta(days=1)
SESSION_MAX_AGE = 7 * 24 * 3600


@dataclass(frozen=True)
class IssuedSession:
    account_id: str
    token: str
    expires_at: datetime


class VerifiedLoginStore(Protocol):
    def complete_verified_login(
        self, *, issuer: str, subject: str, verified_email: str,
        token_sha256: str, issued_at: datetime, expires_at: datetime,
    ) -> str: ...

    def revoke_session(self, token_sha256: str, account_id: str) -> bool: ...


def issue_verified_session(
    *, claims: TrustedOidcClaims, configuration: IdentityProviderConfig,
    expected_nonce: str, store: VerifiedLoginStore, now: datetime | None = None,
) -> IssuedSession:
    """Atomic binding+session operation after provider cryptographic verification."""
    now = now or datetime.now(timezone.utc)
    issuer, subject = validate_verified_claims(
        claims, configuration, expected_nonce=expected_nonce, now=now
    )
    token = secrets.token_urlsafe(32)
    if len(token) != 43:
        raise RuntimeError("Unexpected session token encoding")
    expiry = now + SESSION_TTL
    account_id = store.complete_verified_login(
        issuer=issuer, subject=subject, verified_email=claims.email,
        token_sha256=hashlib.sha256(token.encode("ascii")).hexdigest(),
        issued_at=now, expires_at=expiry,
    )
    return IssuedSession(account_id=account_id, token=token, expires_at=expiry)


def set_secure_session_cookie(response: Response, issued: IssuedSession) -> None:
    """Use only after successful audited provider callback over HTTPS."""
    response.set_cookie(
        COOKIE, issued.token, httponly=True, secure=True, samesite="lax",
        path="/", max_age=int(SESSION_TTL.total_seconds()),
    )
    response.headers["Cache-Control"] = "private, no-store"


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, secure=True, httponly=True, samesite="lax", path="/")
    response.headers["Cache-Control"] = "private, no-store"
