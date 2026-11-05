"""OIDC authorization-code redirect/callback, independently feature gated.

Never accepts trusted claims or tokens from browser input. Each callback consumes
one database-backed state bound to a secure browser cookie before code exchange;
the configured verifier validates signed ID tokens and source claims.
"""
from __future__ import annotations

import hashlib
import hmac
import re
from collections.abc import Callable
from typing import Protocol

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from trading_signal_intelligence.product.accounts.identity_contract import IdentityContractError
from trading_signal_intelligence.product.accounts.oidc_provider import (
    OidcSettings, VerifiedOidcProvider, begin_authorization,
)
from trading_signal_intelligence.product.accounts.session_lifecycle import (
    issue_verified_session, set_secure_session_cookie,
)
from trading_signal_intelligence.product.accounts.store import AccountLinkConflict

_AUTH_COOKIE = "__Host-vowsig_oidc"
_VALID = re.compile(r"^[A-Za-z0-9_-]{43}$")
_PRIVATE = {
    "Cache-Control": "private, no-store",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Referrer-Policy": "no-referrer",
}


class AuthTransactionStore(Protocol):
    def take_auth_budget(self, peer_digest: str) -> bool: ...
    def begin_oidc(
        self, *, state_sha256: str, browser_sha256: str,
        code_verifier: str, nonce: str,
    ) -> None: ...
    def consume_oidc(self, state_sha256: str, browser_sha256: str) -> dict | None: ...
    def complete_verified_login(self, **kwargs) -> str: ...


def create_auth_router(
    *, make_store: Callable[[], AuthTransactionStore],
    settings: OidcSettings, csrf_secret: str,
    verifier: VerifiedOidcProvider | None = None,
) -> APIRouter:
    if len(csrf_secret.encode("utf-8")) < 32:
        raise ValueError("Authentication rate-limit secret must be >=32 bytes")
    verifier = verifier or VerifiedOidcProvider(settings)
    router = APIRouter(include_in_schema=False)

    @router.get("/auth/start")
    def start(request: Request) -> RedirectResponse:
        # Use only the actual trusted ASGI peer; NEVER arbitrary forwarded IP
        # headers controlled by a client. Configure trusted proxy separately.
        peer = request.client.host if request.client else "unknown"
        digest = hmac.new(
            csrf_secret.encode(), peer.encode(), hashlib.sha256,
        ).hexdigest()
        store = make_store()
        if not store.take_auth_budget(digest):
            raise HTTPException(status_code=429, detail="Sign-in temporarily rate limited")
        transaction = begin_authorization(settings)
        store.begin_oidc(
            state_sha256=hashlib.sha256(transaction.state.encode()).hexdigest(),
            browser_sha256=hashlib.sha256(transaction.browser.encode()).hexdigest(),
            code_verifier=transaction.code_verifier, nonce=transaction.nonce,
        )
        response = RedirectResponse(transaction.authorization_url, status_code=302)
        response.headers.update(_PRIVATE)
        response.set_cookie(
            _AUTH_COOKIE, transaction.browser, max_age=600, path="/",
            secure=True, httponly=True, samesite="lax",
        )
        return response

    @router.get("/auth/callback")
    def callback(request: Request) -> RedirectResponse:
        # Auth0 sends the RFC 9207 `iss` authorization-server identifier.
        # Permit it ONLY when byte-for-byte identical to our configured issuer,
        # before consuming the single-use browser-bound state or exchanging a code.
        # Reject duplicates, unknown parameters, and provider error callbacks.
        params = request.query_params
        if (
            len(params.getlist("code")) != 1
            or len(params.getlist("state")) != 1
            or len(params.getlist("iss")) > 1
            or len(params.getlist("session_state")) > 1
            or ("iss" in params and params["iss"] != settings.issuer)
            or params.get("error")
            or set(params) - {"code", "state", "session_state", "iss"}
        ):
            raise HTTPException(status_code=400, detail="Sign-in response rejected")
        code, state = params["code"], params["state"]
        browser = request.cookies.get(_AUTH_COOKIE, "")
        if (
            not _VALID.fullmatch(state)
            or not _VALID.fullmatch(browser)
            or not 1 <= len(code) <= 2048
        ):
            raise HTTPException(status_code=400, detail="Sign-in state rejected")
        store = make_store()
        auth = store.consume_oidc(
            hashlib.sha256(state.encode()).hexdigest(),
            hashlib.sha256(browser.encode()).hexdigest(),
        )
        if auth is None:
            raise HTTPException(status_code=400, detail="Sign-in expired or already used")
        try:
            claims = verifier.verify_callback(
                authorization_code=code,
                code_verifier=auth["code_verifier"],
                expected_nonce=auth["nonce"],
            )
            issued = issue_verified_session(
                claims=claims,
                configuration=settings_identity(settings),
                expected_nonce=auth["nonce"], store=store,
            )
        except (IdentityContractError, AccountLinkConflict) as exc:
            # Email collision and unverified identity have the same opaque user response.
            raise HTTPException(status_code=401, detail="Verified sign-in rejected") from exc
        # No untrusted redirect_uri or return_to: always relative /app/.
        response = RedirectResponse("/app/", status_code=303)
        response.headers.update(_PRIVATE)
        set_secure_session_cookie(response, issued)
        response.delete_cookie(_AUTH_COOKIE, secure=True, httponly=True,
                               samesite="lax", path="/")
        return response

    return router


def settings_identity(settings: OidcSettings):
    from trading_signal_intelligence.product.accounts.identity_contract import IdentityProviderConfig
    return IdentityProviderConfig(settings.issuer, settings.client_id)
