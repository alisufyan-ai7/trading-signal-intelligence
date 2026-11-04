"""Review-only P1A API: safe catalog, session verification and isolated watchlists.

No signup/login, email issuance, cookie setter, notification sender or
commercial signal entitlement is implemented. Production flag defaults OFF.
"""
from __future__ import annotations

from collections.abc import Callable
import hashlib
from typing import Any
from urllib.parse import urlsplit

from fastapi import APIRouter, HTTPException, Query, Request
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
from trading_signal_intelligence.product.accounts.market_views import (
    bounded_history, current_research_feed, research_signal_by_id,
)
from trading_signal_intelligence.product.accounts.member_profile import (
    InvalidMemberPreference, validate_preference_patch,
)
from trading_signal_intelligence.product.accounts.performance import (
    admin_snapshot_diagnostics,
)
from trading_signal_intelligence.product.accounts.session_lifecycle import (
    clear_session_cookie,
)


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

    @router.get("/public/overview")
    def public_overview() -> JSONResponse:
        return JSONResponse({
            "research_only": True, "commercial_customer_eligible": False,
            "catalog": market_directory(read_snapshot()),
            "complete_history_available": False,
        }, headers={"Cache-Control": "public, max-age=60"})

    @router.get("/public/history-summary")
    def public_history_summary() -> JSONResponse:
        feed = current_research_feed(read_snapshot())
        return JSONResponse({
            "source": feed["source"], "history_complete": False,
            "snapshot_generated_at_utc": feed["snapshot_generated_at_utc"],
            "recent_research_signal_rows": len(feed["signal_records"]),
            "recent_research_decision_rows": len(feed["decisions"]),
            "full_population_metrics": None, "research_only": True,
        }, headers={"Cache-Control": "public, max-age=60"})

    @router.get("/me/history")
    def history(
        request: Request,
        symbol: str | None = Query(default=None),
        decision: str | None = Query(default=None),
        lifecycle: str | None = Query(default=None),
    ) -> JSONResponse:
        _auth(request)
        try:
            return _private(bounded_history(
                read_snapshot(), symbol=symbol,
                decision=decision, lifecycle=lifecycle,
            ))
        except PermissionError as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @router.get("/me/signals/{entity_id}")
    def signal_detail(entity_id: str, request: Request) -> JSONResponse:
        _auth(request)
        record = research_signal_by_id(read_snapshot(), entity_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Permitted research signal not found")
        return _private(record)

    @router.get("/me/preferences")
    def preferences(request: Request) -> JSONResponse:
        store, user, _ = _auth(request)
        return _private(store.preferences(user.account_id))

    @router.patch("/me/preferences")
    async def patch_preferences(request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        try:
            patch = validate_preference_patch(await request.json())
        except (ValueError, InvalidMemberPreference) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _private(store.update_preferences(user.account_id, patch))

    @router.get("/me/saved")
    def saved_research(request: Request) -> JSONResponse:
        store, user, _ = _auth(request)
        return _private({"saved": store.saved_research(user.account_id)})

    @router.put("/me/saved/{symbol}/{entity_id}")
    def save_research(symbol: str, entity_id: str, request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        if symbol not in CORE or len(entity_id) > 128:
            raise HTTPException(status_code=403, detail="Restricted research record")
        record = research_signal_by_id(read_snapshot(), entity_id)
        if record is None or record["source_symbol"] != symbol:
            raise HTTPException(status_code=404, detail="Research record unavailable")
        store.save_research(user.account_id, symbol, entity_id)
        return _private({"saved": True, "signal_id": entity_id})

    @router.delete("/me/saved/{entity_id}")
    def unsave_research(entity_id: str, request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        if not entity_id or len(entity_id) > 128:
            raise HTTPException(status_code=400, detail="Invalid research record")
        store.unsave_research(user.account_id, entity_id)
        return _private({"saved": False, "signal_id": entity_id})

    @router.get("/me/export")
    def account_export(request: Request) -> JSONResponse:
        store, user, _ = _auth(request)
        return _private({
            "schema_version": 1,
            **store.account_export(user.account_id),
            "access_tier": user.access_tier,
            "preferences": store.preferences(user.account_id),
            "watchlist": store.watchlist(user.account_id),
            "saved_research": store.saved_research(user.account_id),
            "notice": "Account data excerpt (max 200 consent events); not complete legal export.",
        })

    @router.post("/me/deletion-request")
    def deletion_request(request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        return _private(store.request_deletion(user.account_id))

    @router.post("/me/logout")
    def logout(request: Request) -> JSONResponse:
        store, user, token = _auth(request)
        require_csrf(request, token, csrf_secret, app_origin)
        if not store.revoke_session(
            hashlib.sha256(token.encode("ascii")).hexdigest(), user.account_id,
        ):
            raise HTTPException(status_code=503, detail="Session revocation unconfirmed")
        response = _private({"signed_out": True})
        clear_session_cookie(response)
        return response

    @router.get("/admin/performance")
    def admin_performance(request: Request) -> JSONResponse:
        _, user, _ = _auth(request)
        require_owner(user)
        return _private({
            "status": "awaiting_complete_source_reconciliation",
            "verified_full_history": False,
            "performance": None,
            "preview": admin_snapshot_diagnostics(read_snapshot()),
            "notice": "Partial public snapshot cannot certify historical net-R performance.",
        })

    @router.get("/admin/operations")
    def admin_operations(request: Request) -> JSONResponse:
        _, user, _ = _auth(request)
        require_owner(user)
        return _private(admin_snapshot_diagnostics(read_snapshot()))

    @router.get("/admin/growth")
    def admin_growth(request: Request) -> JSONResponse:
        _, user, _ = _auth(request)
        require_owner(user)
        store, _, _ = _auth(request)
        return _private(store.admin_growth())

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
