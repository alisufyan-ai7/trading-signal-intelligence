from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from trading_signal_intelligence.product.catalog import launch_catalog, market_statuses
from trading_signal_intelligence.product.evidence import evidence_summary, market_evidence
from trading_signal_intelligence.product.public_signals import (
    operational_event_counts,
    public_signal_history,
)


ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "web"

app = FastAPI(
    title="TradingTop Early Access",
    version="0.3.0",
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


@app.get("/api/evidence")
def evidence() -> dict:
    return evidence_summary()


@app.get("/api/markets")
def markets() -> list[dict]:
    rows = market_statuses()
    for row in rows:
        row["evidence"] = market_evidence(row["source_symbol"])
        if row["product_status"] == "live_signal_market":
            row["operational_event_counts"] = operational_event_counts(row)
    return rows


@app.get("/api/markets/{source_symbol}")
def market(source_symbol: str) -> dict:
    normalized = source_symbol.upper()
    for row in market_statuses():
        if row["source_symbol"].upper() == normalized:
            row["evidence"] = market_evidence(row["source_symbol"])
            if row["product_status"] == "live_signal_market":
                row["signals"] = public_signal_history(row, limit=20)
                row["operational_event_counts"] = operational_event_counts(row)
            return row
    raise HTTPException(status_code=404, detail="Unknown launch market")


@app.get("/api/markets/{source_symbol}/evidence")
def market_evidence_endpoint(source_symbol: str) -> dict:
    result = market_evidence(source_symbol)
    if result is None:
        raise HTTPException(status_code=404, detail="No frozen evidence summary for this market")
    return result


@app.get("/api/markets/{source_symbol}/signals")
def market_signals(
    source_symbol: str,
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    normalized = source_symbol.upper()
    for row in market_statuses():
        if (
            row["product_status"] == "live_signal_market"
            and row["source_symbol"].upper() == normalized
        ):
            return {
                "source_symbol": row["source_symbol"],
                "canonical_symbol": row["canonical_symbol"],
                "signals": public_signal_history(row, limit=limit),
                "operational_event_counts": operational_event_counts(row),
            }
    raise HTTPException(status_code=404, detail="Unknown live-signal market")


@app.get("/api/signals")
def signals(limit_per_market: int = Query(default=20, ge=1, le=100)) -> dict:
    live = [
        row
        for row in market_statuses()
        if row["product_status"] == "live_signal_market"
    ]
    return {
        "markets": [
            {
                "source_symbol": row["source_symbol"],
                "canonical_symbol": row["canonical_symbol"],
                "signals": public_signal_history(row, limit=limit_per_market),
                "operational_event_counts": operational_event_counts(row),
            }
            for row in live
        ]
    }
