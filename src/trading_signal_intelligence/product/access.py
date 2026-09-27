from __future__ import annotations

import base64
import os
import secrets

from dotenv import load_dotenv
from fastapi import Request
from fastapi.responses import Response


load_dotenv()


def beta_access_enabled() -> bool:
    return bool(
        os.getenv("TRADINGTOP_BETA_USER")
        and os.getenv("TRADINGTOP_BETA_PASSWORD")
    )


async def basic_access_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/internal/"):
        return await call_next(request)

    expected_user = os.getenv("TRADINGTOP_BETA_USER")
    expected_password = os.getenv("TRADINGTOP_BETA_PASSWORD")
    if not expected_user or not expected_password:
        return await call_next(request)

    header = request.headers.get("Authorization", "")
    supplied_user = ""
    supplied_password = ""
    if header.startswith("Basic "):
        try:
            decoded = base64.b64decode(header[6:]).decode("utf-8")
            supplied_user, supplied_password = decoded.split(":", 1)
        except (ValueError, UnicodeDecodeError):
            pass

    valid = (
        secrets.compare_digest(supplied_user, expected_user)
        and secrets.compare_digest(supplied_password, expected_password)
    )
    if not valid:
        return Response(
            status_code=401,
            content="TradingTop Early Access requires an invitation.",
            headers={"WWW-Authenticate": 'Basic realm="TradingTop Early Access"'},
        )

    return await call_next(request)
