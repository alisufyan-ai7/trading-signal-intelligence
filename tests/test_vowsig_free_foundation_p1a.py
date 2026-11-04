"""P1A review-only contracts: no real user, cloud or DB operations."""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_signal_intelligence.product.free_foundation.api import create_router
from trading_signal_intelligence.product.free_foundation.policy import (
    CORE,
    market_directory,
    permitted_core_recent_signals,
)
from trading_signal_intelligence.product.free_foundation.security import (
    COOKIE, Identity, csrf_for_session,
)

ORIGIN = "https://vowsig.example"
SECRET = "P1A-test-only-csrf-secret-never-for-production-2026"
TOKEN_A = base64.urlsafe_b64encode(bytes(range(32))).decode("ascii").rstrip("=")
TOKEN_B = base64.urlsafe_b64encode(bytes(range(32, 64))).decode("ascii").rstrip("=")
assert len(TOKEN_A) == len(TOKEN_B) == 43


def sample_snapshot(*, stale=False, core=True):
    stamp = datetime.now(timezone.utc)
    if stale:
        stamp -= timedelta(hours=4)
    return {
        "generated_at_utc": stamp.isoformat(),
        "validation_programs": [
            {
                "program_id": "core-ai-shadow",
                "mode": "SHADOW_ONLY",
                "public_research_observability": True,
                "public_signal_exposure": True,
                "signal_details_included": False,
                "health": {"broker_execution_disabled": True},
            },
            {
                "program_id": "market-expansion-1",
                "mode": "SHADOW_ONLY",
                "public_research_observability": True,
                "public_signal_exposure": False,
                "signal_details_included": False,
                "health": {"broker_execution_disabled": True},
                # Maliciously included private data must not reach new v2 API.
                "shadow_signals": [{"direction": "BUY", "entry": 123}],
            },
            {
                "program_id": "crypto-expansion-1",
                "mode": "SHADOW_ONLY",
                "public_research_observability": True,
                "public_signal_exposure": False,
                "signal_details_included": False,
                "health": {"broker_execution_disabled": True},
            },
        ],
        "ai_v1": {
            "mode": "SHADOW_ONLY",
            "runtime_version": "AI-v1.1",
            "publish_allowed": core,
            "health": {"healthy": core, "broker_execution_disabled": True},
            "shadow_signals": [
                {
                    "entity_id": "core-s1", "source_symbol": "XAUUSD",
                    "status": "closed", "direction": "SELL", "entry": 12,
                    "stop": 13, "tp1": 11, "tp2": 10, "net_r": -1.1,
                    "rationale": "Research example", "exit_reason": "STOP",
                    "secret_provider_body": "NEVER LEAK",
                },
                {
                    "entity_id": "restricted-s1", "source_symbol": "BTCUSDT",
                    "status": "active", "direction": "BUY", "entry": 123,
                },
            ],
        },
    }


def identity(
    user: str = "aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
    role: str = "free",
    verified=True,
    valid=True,
    mfa=False,
):
    now = datetime.now(timezone.utc)
    return Identity(
        user_id=user, role=role,
        email_verified_at=now if verified else None,
        expires_at=now + (timedelta(hours=1) if valid else -timedelta(minutes=1)),
        revoked_at=None, disabled_at=None,
        mfa_verified_at=now if mfa else None,
    )


class FakeStore:
    def __init__(self):
        self.sessions = {
            hashlib.sha256(TOKEN_A.encode()).hexdigest(): identity(),
            hashlib.sha256(TOKEN_B.encode()).hexdigest(): identity(
                "bbbbbbbb-bbbb-4bbb-bbbb-bbbbbbbbbbbb"
            ),
        }
        self.saved: dict[str, set[str]] = {}

    def find_session(self, hashed):
        return self.sessions.get(hashed)

    def watchlist(self, user_id):
        return sorted(self.saved.get(user_id, set()))

    def save_market(self, user_id, symbol):
        self.saved.setdefault(user_id, set()).add(symbol)
        return self.watchlist(user_id)

    def delete_market(self, user_id, symbol):
        self.saved.setdefault(user_id, set()).discard(symbol)
        return self.watchlist(user_id)


@pytest.fixture
def env():
    store = FakeStore()
    state = {"snapshot": sample_snapshot()}
    app = FastAPI()
    app.include_router(create_router(
        read_snapshot=lambda: state["snapshot"],
        make_store=lambda: store,
        csrf_secret=SECRET, app_origin=ORIGIN,
    ))
    return store, state, TestClient(app, base_url=ORIGIN)


def _login(client, token=TOKEN_A):
    client.cookies.set(COOKIE, token)


def test_public_nine_market_directory_has_only_three_detail_permissions(env):
    _, _, client = env
    result = client.get("/api/v2/public/markets")
    assert result.status_code == 200
    rows = result.json()["markets"]
    assert len(rows) == 9
    assert len({r["symbol"] for r in rows}) == 9
    assert {r["symbol"] for r in rows if r["research_signal_detail_available"]} == CORE
    assert all(not r["commercial_customer_eligible"] for r in rows)
    assert "shadow_signals" not in result.text
    assert "restricted-s1" not in result.text
    assert "secret_provider_body" not in result.text


def test_anonymous_rejected_and_cookie_does_not_equal_identity(env):
    _, _, client = env
    for endpoint in ("/api/v2/me", "/api/v2/me/watchlist", "/api/v2/me/signals?symbol=XAUUSD"):
        assert client.get(endpoint).status_code == 401
    client.cookies.set(COOKIE, "untrusted")
    assert client.get("/api/v2/me").status_code == 401


@pytest.mark.parametrize("symbol", ["EURUSD", "XAGUSD", "USOIL", "BTCUSDT", "ETHUSDT", "SOLUSDT"])
def test_restricted_markets_have_no_member_signal_details(env, symbol):
    _, _, client = env
    _login(client)
    result = client.get("/api/v2/me/signals", params={"symbol": symbol})
    assert result.status_code == 403
    assert "123" not in result.text


def test_only_sanitized_core_history_from_fresh_source(env):
    _, state, client = env
    _login(client)
    result = client.get("/api/v2/me/signals?symbol=XAUUSD")
    assert result.status_code == 200
    signals = result.json()["signals"]
    assert len(signals) == 1
    assert signals[0]["net_r"] == -1.1
    assert result.json()["history_complete"] is False
    assert "secret_provider_body" not in result.text
    assert "BTCUSDT" not in result.text
    state["snapshot"] = sample_snapshot(stale=True)
    result = client.get("/api/v2/me/signals?symbol=XAUUSD")
    assert result.status_code == 200
    assert result.json()["signals"] == []
    assert result.json()["status"] == "unavailable"


def test_guarded_or_missing_source_never_returns_signals(env):
    _, state, client = env
    _login(client)
    state["snapshot"] = sample_snapshot(core=False)
    assert client.get("/api/v2/me/signals?symbol=XAUUSD").json()["signals"] == []
    state["snapshot"] = None
    assert client.get("/api/v2/public/markets").json()["markets"][0]["research_signal_detail_available"] is False
    assert client.get("/api/v2/me/signals?symbol=XAUUSD").json()["signals"] == []


def test_watchlist_owner_isolation_and_double_csrf_protection(env):
    _, _, client = env
    _login(client)
    csrf = csrf_for_session(TOKEN_A, SECRET)
    url = "/api/v2/me/watchlist/BTCUSDT"
    assert client.put(url).status_code == 403
    assert client.put(url, headers={"Origin": "https://evil.example", "X-VowSig-CSRF": csrf}).status_code == 403
    assert client.put(url, headers={"Origin": ORIGIN, "X-VowSig-CSRF": "bad"}).status_code == 403
    headers = {"Origin": ORIGIN, "X-VowSig-CSRF": csrf}
    assert client.put(url, headers=headers).json()["markets"] == ["BTCUSDT"]
    assert client.get("/api/v2/me/watchlist").json()["markets"] == ["BTCUSDT"]
    assert client.put("/api/v2/me/watchlist/UNKNOWN", headers=headers).status_code == 404
    _login(client, TOKEN_B)
    assert client.get("/api/v2/me/watchlist").json()["markets"] == []
    _login(client)
    assert client.delete(url, headers=headers).json()["markets"] == []


def test_unverified_expired_revoked_and_disabled_fail_closed(env):
    store, _, client = env
    _login(client)
    digest = hashlib.sha256(TOKEN_A.encode()).hexdigest()
    for change in (
        identity(verified=False),
        identity(valid=False),
        Identity(**{**identity().__dict__, "revoked_at": datetime.now(timezone.utc)}),
        Identity(**{**identity().__dict__, "disabled_at": datetime.now(timezone.utc)}),
    ):
        store.sessions[digest] = change
        assert client.get("/api/v2/me").status_code == 401


def test_admin_requires_explicit_owner_and_mfa(env):
    store, _, client = env
    _login(client)
    digest = hashlib.sha256(TOKEN_A.encode()).hexdigest()
    assert client.get("/api/v2/admin/overview").status_code == 403
    store.sessions[digest] = identity(role="owner", mfa=False)
    assert client.get("/api/v2/admin/overview").status_code == 403
    store.sessions[digest] = identity(role="owner", mfa=True)
    result = client.get("/api/v2/admin/overview")
    assert result.status_code == 200
    assert result.json()["operator_health_independently_verified"] is False
    assert "no-store" in result.headers["cache-control"]


def test_policy_does_not_infer_permission_from_catalog_or_internal_payload():
    payload = sample_snapshot(stale=True)
    assert len(market_directory(payload)["markets"]) == 9
    assert all(not r["research_signal_detail_available"] for r in market_directory(payload)["markets"])
    with pytest.raises(PermissionError):
        permitted_core_recent_signals(payload, "SOLUSDT")
