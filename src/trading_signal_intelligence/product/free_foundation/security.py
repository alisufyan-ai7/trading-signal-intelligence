"""Fail-closed session verification for a future separately approved identity issuer.

No token creation, login, email verification, owner bootstrap or cookies are
issued by this foundation. Issuance requires a separate reviewed implementation.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol
from urllib.parse import urlsplit

from fastapi import HTTPException, Request

COOKIE = "__Host-vowsig_session"
_TOKEN = re.compile(r"^[A-Za-z0-9_-]{43}$")  # 32 random bytes, base64url no padding


@dataclass(frozen=True)
class Identity:
    user_id: str
    role: str
    email_verified_at: datetime | None
    expires_at: datetime
    revoked_at: datetime | None
    disabled_at: datetime | None
    mfa_verified_at: datetime | None


class SessionLookup(Protocol):
    def find_session(self, token_sha256: str) -> Identity | None: ...


def _unauthorized() -> HTTPException:
    return HTTPException(status_code=401, detail="Verified sign-in required")


def current_identity(request: Request, store: SessionLookup) -> tuple[Identity, str]:
    token = request.cookies.get(COOKIE, "")
    if not _TOKEN.fullmatch(token):
        raise _unauthorized()
    digest = hashlib.sha256(token.encode("ascii")).hexdigest()
    identity = store.find_session(digest)
    if identity is None:
        raise _unauthorized()
    dates = (identity.expires_at, identity.email_verified_at)
    if any(d is not None and d.tzinfo is None for d in dates):
        raise _unauthorized()
    if (
        identity.email_verified_at is None
        or identity.revoked_at is not None
        or identity.disabled_at is not None
        or identity.expires_at <= datetime.now(timezone.utc)
        or identity.role not in ("free", "owner")
    ):
        raise _unauthorized()
    return identity, token


def require_owner(identity: Identity) -> None:
    if identity.role != "owner" or identity.mfa_verified_at is None:
        raise HTTPException(status_code=403, detail="Owner MFA session required")
    now = datetime.now(timezone.utc)
    if (
        identity.mfa_verified_at.tzinfo is None
        or identity.mfa_verified_at > now
        or (now - identity.mfa_verified_at).total_seconds() > 15 * 60
    ):
        raise HTTPException(status_code=403, detail="Fresh owner MFA required")


def csrf_for_session(token: str, secret: str) -> str:
    if len(secret.encode("utf-8")) < 32:
        raise ValueError("CSRF secret must be at least 32 UTF-8 bytes")
    return hmac.new(secret.encode("utf-8"), token.encode("ascii"), hashlib.sha256).hexdigest()


def require_csrf(request: Request, token: str, secret: str, app_origin: str) -> None:
    # The issuer must additionally set Secure, HttpOnly, Path=/, SameSite cookies.
    origin = request.headers.get("origin", "")
    parsed = urlsplit(app_origin)
    if parsed.scheme != "https" or not parsed.netloc or parsed.path not in ("", "/"):
        raise ValueError("A single explicit HTTPS origin is required")
    if origin != app_origin.rstrip("/"):
        raise HTTPException(status_code=403, detail="CSRF origin rejected")
    presented = request.headers.get("x-vowsig-csrf", "")
    expected = csrf_for_session(token, secret)
    if not hmac.compare_digest(presented, expected):
        raise HTTPException(status_code=403, detail="CSRF token rejected")
