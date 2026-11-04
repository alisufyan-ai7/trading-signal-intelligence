"""Review-only P1A API: safe catalog, session verification and isolated watchlists.

No signup/login, email issuance, cookie setter, notification sender or
commercial signal entitlement is implemented. Production flag defaults OFF.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse

from trading_signal_intelligence.product.accounts.policy import (
    CORE,
    MARKETS,
    market_directory,
    permitted_core_recent_signals,
)
from trading_signal_intelligence.product.accounts.security import (
    csrf_for_session,
    current_identity,
    require_csrf,
    require_owner,
)
from trading_signal_intelligence.product.accounts.store import AccountStore


def _private(data: dict[str, Any]) -> JSONResponse:
    return JSONResponse(data, headers={
        "Cache-Control": "private, no-store",
        "X-Robots-Tag": "noindex, nofollow, noarchive",
        "Vary": "Cookie",
    })


def create_router(
    *,
    read_snapshot: Callable[[], dict[str, Any] | None],
    make_store: Callable[[], AccountStore],
    csrf_secret: str,
    app_origin: str,
) -> APIRouter:
    origin = urlsplit(app_origin)
    if (
        len(csrf_secret.encode("utf-8")) < 32
        or origin.scheme != "https"
        or not origin.netloc
        or origin.username is not None
        or origin.path not in ("", "/")
        or origin.query or origin.fragment
    ):
        raise ValueError("CSRF secret (>=32 bytes) and exact HTTPS origin required")
    router = APIRouter(prefix="/api/v2", tags=["Accounts foundation"])

    def _auth(request: Request):
        store = make_store()
        identity, token = current_identity(request, store)
        return store, identity, token

    @router.get("/public/markets")
    def markets() -> JSONResponse:
        return JSONResponse(market_directory(read_snapshot()), headers={
            "Cache-Control": "public, max-age=60",
            "X-Robots-Tag": "noindex, nofollow",
        })

    @router.get("/me")
    def me(request: Request) -> JSONResponse:
        _, user, token = _auth(request)
        return _private({
            "account_id": user.account_id,
            "role": user.role,
            "email_verified": True,
            "access_tier": user.access_tier,
            "csrf_token": csrf_for_session(token, csrf_secret),
            "commercial_customer_eligible": False,
        })

    @router.get("/me/watchlist")
    def get_watchlist(request: Request) -> JSONResponse:
        store, user, _ = _auth(request)
        return _private({"markets": store.watchlist(user.account_id)})

    @router.put("/me/watchlist/{symbol}")
    def add_market(symbol: str, request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        if symbol not in MARKETS:
            raise HTTPException(status_code=404, detail="Unsupported market")
        return _private({"markets": store.save_market(user.account_id, symbol)})

    @router.delete("/me/watchlist/{symbol}")
    def remove_market(symbol: str, request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        if symbol not in MARKETS:
            raise HTTPException(status_code=404, detail="Unsupported market")
        return _private({"markets": store.delete_market(user.account_id, symbol)})

    @router.get("/me/signals")
    def member_signals(symbol: str, request: Request) -> JSONResponse:
        _auth(request)  # Sign-in is necessary but is never sufficient for restricted markets.
        if symbol not in CORE:
            raise HTTPException(status_code=403, detail="Research details not released")
        return _private(permitted_core_recent_signals(read_snapshot(), symbol))

    @router.get("/admin/overview")
    def admin_overview(request: Request) -> JSONResponse:
        _, user, _ = _auth(request)
        require_owner(user)
        snapshot = read_snapshot()
        # This is not a VPS scheduler-status or backup-recoverability attestation.
        return _private({
            "mode": "READ_ONLY",
            "source": "public_snapshot_only",
            "snapshot_generated_at_utc": (
                snapshot.get("generated_at_utc") if isinstance(snapshot, dict) else None
            ),
            "operator_health_independently_verified": False,
            "broker_execution_enabled": False,
        })

    return router
