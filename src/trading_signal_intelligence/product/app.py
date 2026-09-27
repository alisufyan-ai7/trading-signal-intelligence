from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from trading_signal_intelligence.product.catalog import launch_catalog, market_statuses


ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"

app = FastAPI(
    title="TradingTop Early Access",
    version="0.1.0",
    description="Verified rule-based market setups with transparent evidence status.",
)

app.mount("/static", StaticFiles(directory=WEB), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB / "index.html")


@app.get("/api/health")
def health() -> dict:
    markets = market_statuses()
    live = [row for row in markets if row["product_status"] == "live_signal_market"]
    ledger_errors = [
        row["source_symbol"]
        for row in live
        if row["forward"] and row["forward"]["state"] == "ledger_error"
    ]
    ready_states = {"scanning", "active_signal"}
    ready_collectors = [
        row["source_symbol"]
        for row in live
        if row["forward"] and row["forward"]["state"] in ready_states
    ]
    pending_collectors = [
        row["source_symbol"]
        for row in live
        if row["source_symbol"] not in ready_collectors
    ]
    return {
        "ok": not ledger_errors,
        "launch_ready": not ledger_errors and len(ready_collectors) == len(live),
        "product": "TradingTop Early Access",
        "launch_mode": "research_beta",
        "live_signal_markets": len(live),
        "ready_collectors": ready_collectors,
        "ready_collector_count": len(ready_collectors),
        "pending_collectors": pending_collectors,
        "ledger_errors": ledger_errors,
    }


@app.get("/api/catalog")
def catalog() -> dict:
    return launch_catalog()


@app.get("/api/markets")
def markets() -> list[dict]:
    return market_statuses()


@app.get("/api/markets/{source_symbol}")
def market(source_symbol: str) -> dict:
    normalized = source_symbol.upper()
    for row in market_statuses():
        if row["source_symbol"].upper() == normalized:
            return row
    raise HTTPException(status_code=404, detail="Unknown launch market")
