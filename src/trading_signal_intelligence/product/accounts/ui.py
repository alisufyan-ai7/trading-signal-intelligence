"""Authentication-gated member SPA and MFA-gated owner SPA.

No user data is embedded in HTML or JavaScript. Static files under /static are
public assets only. Dynamic /app and /admin HTML requires a real DB session.
These routes are attached ONLY under the disabled-by-default accounts flag.
"""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse

from trading_signal_intelligence.product.accounts.security import (
    current_identity, require_owner,
)
from trading_signal_intelligence.product.accounts.store import AccountStore

_MEMBER_PAGES = ("", "signals", "history", "markets", "watchlist", "learn", "settings")
_PRIVATE_HEADERS = {
    "Cache-Control": "private, no-store",
    "X-Robots-Tag": "noindex, nofollow, noarchive",
    "Vary": "Cookie",
    "Content-Security-Policy": (
        "default-src 'self'; script-src 'self'; style-src 'self'; "
        "img-src 'self'; connect-src 'self'; form-action 'self'; "
        "base-uri 'none'; frame-ancestors 'none'; object-src 'none'"
    ),
    "Referrer-Policy": "no-referrer",
}


def create_ui_router(
    *, make_store: Callable[[], AccountStore], html_path: Path,
) -> APIRouter:
    router = APIRouter(include_in_schema=False)

    def html(request: Request, owner: bool = False) -> FileResponse:
        identity, _ = current_identity(request, make_store())
        if owner:
            require_owner(identity)
        return FileResponse(html_path, media_type="text/html", headers=_PRIVATE_HEADERS)

    @router.get("/app/")
    def member_home(request: Request):
        return html(request)

    for page in _MEMBER_PAGES[1:]:
        def handler(request: Request):
            return html(request)
        router.add_api_route(f"/app/{page}/", handler, methods=["GET"])

    @router.get("/admin/")
    def owner_home(request: Request):
        return html(request, owner=True)

    return router
