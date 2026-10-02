from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Query, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from trading_signal_intelligence.product.feedback import (
    FeedbackValidationError,
    RETENTION_MONTHS,
    export_feedback_csv,
    export_feedback_rows,
    feedback_db_path,
    feedback_summary,
    owner_token_valid,
    submit_feedback,
)


load_dotenv()

ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"


def _snapshot_path() -> Path:
    configured = os.getenv("TRADINGTOP_SNAPSHOT_PATH")
    if configured:
        return Path(configured)
    data_mount = Path("/data")
    if data_mount.exists():
        return data_mount / "public_snapshot.json"
    return ROOT / "data" / "cloud_snapshot.json"


def _load_snapshot() -> dict[str, Any] | None:
    path = _snapshot_path()
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_snapshot(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != 1:
        raise HTTPException(status_code=400, detail="Unsupported snapshot schema")
    if payload.get("raw_market_data_included") is not False:
        raise HTTPException(status_code=400, detail="Raw market data is forbidden")
    if not isinstance(payload.get("markets"), list):
        raise HTTPException(status_code=400, detail="Snapshot markets missing")
    if not isinstance(payload.get("health"), dict):
        raise HTTPException(status_code=400, detail="Snapshot health missing")

    ai_v1 = payload.get("ai_v1")
    if ai_v1 is not None:
        if not isinstance(ai_v1, dict):
            raise HTTPException(status_code=400, detail="AI-v1 snapshot must be an object")
        runtime = ai_v1.get("runtime_version")
        status = ai_v1.get("status")
        if status == "forward_validation_in_progress" and runtime not in {
            "AI-v1.0",
            "AI-v1.1",
        }:
            raise HTTPException(
                status_code=400,
                detail="Active AI snapshot runtime_version is ambiguous",
            )
        if ai_v1.get("protocol_version") != "AI-v1.0":
            raise HTTPException(
                status_code=400,
                detail="Unexpected AI decision protocol",
            )
        if ai_v1.get("decision_protocol_version") != "AI-v1.0":
            raise HTTPException(
                status_code=400,
                detail="Unexpected AI decision protocol version",
            )
        if runtime == "AI-v1.1":
            legacy = ai_v1.get("legacy_lineage")
            if not isinstance(legacy, dict):
                raise HTTPException(
                    status_code=400,
                    detail="AI-v1.1 snapshot missing separate legacy lineage",
                )
            if legacy.get("gate_counts_carried_into_active_runtime") is not False:
                raise HTTPException(
                    status_code=400,
                    detail="AI-v1.1 legacy gate-count isolation failed",
                )

        for key in (
            "raw_market_data_included",
            "raw_feature_snapshots_included",
            "provider_request_metadata_included",
            "hidden_reasoning_included",
        ):
            if ai_v1.get(key) is not False:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsafe AI-v1 snapshot field: {key}",
                )


def _market_rows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    evidence = snapshot.get("evidence", {}).get("markets", {})
    rows = []
    for raw in snapshot.get("markets", []):
        row = dict(raw)
        row["evidence"] = evidence.get(row["source_symbol"])
        if row["product_status"] == "live_signal_market":
            row["forward"] = {
                "state": row.pop("forward_state", "not_activated"),
                "ledger_valid": row.pop("ledger_valid", None),
            }
        else:
            row["forward"] = None
        rows.append(row)
    return rows


app = FastAPI(
    title="VowSig Research Beta Cloud",
    version="0.6.0",
    description="VowSig public research-beta surface fed by the private Windows collector.",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.mount("/static", StaticFiles(directory=WEB), name="static")


INDEXABLE_PATHS = (
    "/",
    "/markets/",
    "/markets/xau-usd/",
    "/markets/nasdaq-100/",
    "/markets/dow-30/",
    "/learn/",
    "/learn/buy-sell-no-trade/",
    "/learn/backtests-vs-forward-results/",
    "/learn/immutable-signal-history/",
    "/learn/shadow-validation/",
    "/learn/signal-lifecycle/",
    "/evidence/",
)


def _search_engine_noindex(path: str) -> bool:
    return (
        path == "/healthz"
        or path.startswith("/api/")
        or path.startswith("/static/")
    )


@app.middleware("http")
async def add_search_engine_headers(request: Request, call_next):
    response = await call_next(request)
    if _search_engine_noindex(request.url.path):
        response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


def _seo_file(relative: str) -> FileResponse:
    return FileResponse(WEB / relative)


@app.get("/robots.txt", include_in_schema=False)
def robots_txt() -> Response:
    body = """User-agent: *
Allow: /
Disallow: /api/
Disallow: /healthz
Disallow: /docs
Disallow: /redoc
Disallow: /openapi.json

Sitemap: https://vowsig.com/sitemap.xml
"""
    return Response(content=body, media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml() -> Response:
    urls = "".join(
        f"<url><loc>https://vowsig.com{path}</loc></url>"
        for path in INDEXABLE_PATHS
    )
    body = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"{urls}</urlset>"
    )
    return Response(content=body, media_type="application/xml")


@app.get("/markets/", include_in_schema=False)
def markets_page() -> FileResponse:
    return _seo_file("markets/index.html")


@app.get("/markets/xau-usd/", include_in_schema=False)
def xau_usd_page() -> FileResponse:
    return _seo_file("markets/xau-usd.html")


@app.get("/markets/nasdaq-100/", include_in_schema=False)
def nasdaq_100_page() -> FileResponse:
    return _seo_file("markets/nasdaq-100.html")


@app.get("/markets/dow-30/", include_in_schema=False)
def dow_30_page() -> FileResponse:
    return _seo_file("markets/dow-30.html")


@app.get("/markets/xauusd/", include_in_schema=False)
def xauusd_alias() -> RedirectResponse:
    return RedirectResponse("/markets/xau-usd/", status_code=301)


@app.get("/markets/ustec/", include_in_schema=False)
def ustec_alias() -> RedirectResponse:
    return RedirectResponse("/markets/nasdaq-100/", status_code=301)


@app.get("/markets/us30/", include_in_schema=False)
def us30_alias() -> RedirectResponse:
    return RedirectResponse("/markets/dow-30/", status_code=301)


@app.get("/learn/", include_in_schema=False)
def learn_page() -> FileResponse:
    return _seo_file("learn/index.html")


@app.get("/learn/buy-sell-no-trade/", include_in_schema=False)
def buy_sell_no_trade_page() -> FileResponse:
    return _seo_file("learn/buy-sell-no-trade.html")


@app.get("/learn/backtests-vs-forward-results/", include_in_schema=False)
def backtests_vs_forward_page() -> FileResponse:
    return _seo_file("learn/backtests-vs-forward-results.html")


@app.get("/learn/immutable-signal-history/", include_in_schema=False)
def immutable_signal_history_page() -> FileResponse:
    return _seo_file("learn/immutable-signal-history.html")


@app.get("/learn/shadow-validation/", include_in_schema=False)
def shadow_validation_page() -> FileResponse:
    return _seo_file("learn/shadow-validation.html")


@app.get("/learn/signal-lifecycle/", include_in_schema=False)
def signal_lifecycle_page() -> FileResponse:
    return _seo_file("learn/signal-lifecycle.html")


@app.get("/evidence/", include_in_schema=False)
def evidence_page() -> FileResponse:
    return _seo_file("evidence/index.html")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "vowsig"}


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")



@app.get("/api/health")
def health() -> dict:
    snapshot = _load_snapshot()
    if snapshot is None:
        return {
            "ok": False,
            "launch_ready": False,
            "product": "VowSig Research Beta",
            "launch_mode": "research_beta",
            "live_signal_markets": 3,
            "ready_collector_count": 0,
            "ready_collectors": [],
            "pending_collectors": ["XAUUSD", "USTEC", "US30"],
            "ledger_errors": [],
            "snapshot_pending": True,
        }
    return snapshot["health"] | {
        "snapshot_generated_at_utc": snapshot.get("generated_at_utc"),
        "snapshot_pending": False,
    }


@app.get("/api/evidence")
def evidence() -> dict:
    snapshot = _load_snapshot()
    return snapshot.get("evidence", {}) if snapshot else {"markets": {}}


@app.get("/api/markets")
def markets() -> list[dict]:
    snapshot = _load_snapshot()
    return _market_rows(snapshot) if snapshot else []


@app.get("/api/ai/insights")
def ai_insights() -> dict:
    snapshot = _load_snapshot()
    if snapshot is None:
        return {
            "schema_version": 1,
            "runtime_version": "UNKNOWN",
            "decision_protocol_version": "AI-v1.0",
            "protocol_version": "AI-v1.0",
            "mode": "SHADOW_ONLY",
            "status": "snapshot_pending",
            "customer_notice": "AI-v1 shadow insights are waiting for the next VPS snapshot.",
            "health": {"healthy": False},
            "raw_market_data_included": False,
            "raw_feature_snapshots_included": False,
            "provider_request_metadata_included": False,
            "hidden_reasoning_included": False,
        }
    return snapshot.get("ai_v1", {
        "schema_version": 1,
        "runtime_version": "UNKNOWN",
        "decision_protocol_version": "AI-v1.0",
        "protocol_version": "AI-v1.0",
        "mode": "SHADOW_ONLY",
        "status": "snapshot_pending",
        "customer_notice": "AI-v1 shadow insights are waiting for the next VPS snapshot.",
        "health": {"healthy": False},
        "raw_market_data_included": False,
        "raw_feature_snapshots_included": False,
        "provider_request_metadata_included": False,
        "hidden_reasoning_included": False,
    })


@app.get("/api/signals")
def signals() -> dict:
    snapshot = _load_snapshot()
    if snapshot is None:
        return {"markets": []}
    rows = []
    for market in snapshot.get("markets", []):
        if market.get("product_status") != "live_signal_market":
            continue
        rows.append(
            {
                "source_symbol": market["source_symbol"],
                "canonical_symbol": market["canonical_symbol"],
                "signals": market.get("signals", []),
                "operational_event_counts": market.get(
                    "operational_event_counts", {}
                ),
            }
        )
    return {"markets": rows}


@app.post("/api/feedback")
async def create_feedback(request: Request) -> dict:
    try:
        payload = await request.json()
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Valid JSON object required") from exc

    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required")

    try:
        result = submit_feedback(feedback_db_path(ROOT), payload)
    except FeedbackValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return {
        "accepted": True,
        "submission_id": result["submission_id"],
        "submitted_at_utc": result["submitted_at_utc"],
        "retention_months": RETENTION_MONTHS,
    }


def _require_feedback_owner(authorization: str | None) -> None:
    expected = os.getenv("SIGNALPROOF_FEEDBACK_OWNER_TOKEN")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="Feedback owner access is not configured",
        )
    if not owner_token_valid(authorization, expected):
        raise HTTPException(status_code=401, detail="Invalid feedback owner token")


@app.get("/api/internal/feedback/summary")
def owner_feedback_summary(
    authorization: str | None = Header(default=None),
) -> dict:
    _require_feedback_owner(authorization)
    return feedback_summary(feedback_db_path(ROOT))


@app.get("/api/internal/feedback/export")
def owner_feedback_export(
    format: str = Query(default="json"),
    authorization: str | None = Header(default=None),
):
    _require_feedback_owner(authorization)
    path = feedback_db_path(ROOT)
    if format == "json":
        return {
            "schema_version": 1,
            "retention_months": RETENTION_MONTHS,
            "submissions": export_feedback_rows(path),
        }
    if format == "csv":
        return Response(
            content=export_feedback_csv(path),
            media_type="text/csv",
            headers={
                "Content-Disposition": (
                    "attachment; filename=vowsig-feedback.csv"
                )
            },
        )
    raise HTTPException(status_code=400, detail="format must be json or csv")


@app.post("/api/internal/snapshot")
async def ingest_snapshot(
    request: Request,
    authorization: str | None = Header(default=None),
) -> dict:
    expected = os.getenv("TRADINGTOP_INGEST_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="Ingestion token not configured")

    prefix = "Bearer "
    supplied = (
        authorization[len(prefix):]
        if authorization and authorization.startswith(prefix)
        else ""
    )
    if not secrets.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Invalid ingestion token")

    payload = await request.json()
    if not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="JSON object required")
    _validate_snapshot(payload)

    path = _snapshot_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    temporary.replace(path)

    return {
        "accepted": True,
        "generated_at_utc": payload.get("generated_at_utc"),
        "markets": len(payload.get("markets", [])),
        "raw_market_data_included": False,
    }
