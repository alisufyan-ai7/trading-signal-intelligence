"""P1B session issuance and cookie attributes; never provides a public auth endpoint."""
from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi import Response

from trading_signal_intelligence.product.accounts.identity_contract import (
    IdentityContractError, IdentityProviderConfig, TrustedOidcClaims,
)
from trading_signal_intelligence.product.accounts.session_lifecycle import (
    COOKIE, clear_session_cookie, issue_verified_session, set_secure_session_cookie,
)

NOW = datetime(2026, 11, 4, 12, 30, tzinfo=timezone.utc)
CONFIG = IdentityProviderConfig("https://identity.example.test", "client-vowsig")


def claims():
    return TrustedOidcClaims(
        issuer=CONFIG.issuer, audience=CONFIG.client_id, nonce="single-use-nonce",
        subject="auth0-opaque-subject", email="verified@example.test",
        email_verified=True, issued_at_utc=NOW-timedelta(seconds=15),
        expires_at_utc=NOW+timedelta(minutes=5),
        auth_time_utc=NOW-timedelta(seconds=30),
    )


class LoginStore:
    def __init__(self):
        self.calls=[]
    def complete_verified_login(self, **kwargs):
        self.calls.append(kwargs)
        return str(uuid4())


def test_opaque_session_and_only_digest_passed_to_store():
    store=LoginStore()
    result=issue_verified_session(
        claims=claims(), configuration=CONFIG,
        expected_nonce="single-use-nonce", store=store, now=NOW,
    )
    assert len(result.token)==43
    assert result.expires_at==NOW+timedelta(days=1)
    assert len(store.calls)==1
    payload=store.calls[0]
    assert payload["token_sha256"]==hashlib.sha256(result.token.encode()).hexdigest()
    assert result.token not in str(payload)
    assert payload["issuer"]==CONFIG.issuer and payload["subject"]==claims().subject
    assert "role" not in payload and "access_tier" not in payload


def test_cookie_is_host_only_secure_http_only_no_store():
    store=LoginStore()
    result=issue_verified_session(
        claims=claims(), configuration=CONFIG,
        expected_nonce="single-use-nonce", store=store, now=NOW,
    )
    response=Response()
    set_secure_session_cookie(response,result)
    cookie=response.headers["set-cookie"]
    assert COOKIE in cookie and "httponly" in cookie.lower()
    assert "secure" in cookie.lower() and "path=/" in cookie.lower()
    assert "samesite=lax" in cookie.lower()
    assert "domain=" not in cookie.lower()
    assert response.headers["cache-control"]=="private, no-store"
    clear_session_cookie(response)
    assert "max-age=0" in response.headers["set-cookie"].lower()


def test_unverified_provider_result_never_touches_store():
    store=LoginStore()
    with pytest.raises(IdentityContractError):
        issue_verified_session(
            claims=replace(claims(),email_verified=False),
            configuration=CONFIG,expected_nonce="single-use-nonce",
            store=store,now=NOW,
        )
    assert store.calls==[]
    with pytest.raises(IdentityContractError):
        issue_verified_session(
            claims=claims(),configuration=CONFIG,expected_nonce="wrong",
            store=store,now=NOW,
        )
    assert store.calls==[]
