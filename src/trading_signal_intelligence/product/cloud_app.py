from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


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
    title="SignalProof AI Research Beta Cloud",
    version="0.4.0",
    description="SignalProof AI public research-beta surface fed by the private Windows collector.",
)

app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/healthz")
def healthz() -> dict:
    return {"ok": True, "service": "tradingtop-early-access"}


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
            "product": "SignalProof AI Research Beta",
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
