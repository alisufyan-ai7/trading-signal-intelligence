"""P3/P4 customer/admin API security, research state and UI route contracts."""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from trading_signal_intelligence.product.accounts.api import create_router
from trading_signal_intelligence.product.accounts.security import COOKIE, Identity, csrf_for_session
from trading_signal_intelligence.product.accounts.ui import create_ui_router

NOW = datetime.now(timezone.utc)
ORIGIN = "https://vowsig.example"
SECRET = "P3-ONLY-test-secret-never-use-in-production-2026"
TOKEN = base64.urlsafe_b64encode(bytes(range(32))).decode().rstrip("=")
HASH = hashlib.sha256(TOKEN.encode("ascii")).hexdigest()


def snapshot():
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "ai_v1": {
            "runtime_version": "AI-v1.1", "mode": "SHADOW_ONLY",
            "publish_allowed": True,
            "health": {"healthy": True,"broker_execution_disabled": True},
            "shadow_signals": [
                {"entity_id":"good", "source_symbol":"XAUUSD", "status":"closed",
                 "direction":"SELL", "issued_at_utc":"2026-11-04T10:00:00Z",
                 "entry":12,"stop":13,"tp1":11,"tp2":10,
                 "net_r":-1.0,"exit_reason":"STOP",
                 "secret_provider_token":"NEVER EXPOSE"},
                {"entity_id":"crypto", "source_symbol":"BTCUSDT", "status":"active",
                 "direction":"BUY","entry":100,"secret":"NEVER EXPOSE"},
            ],
            "recent_decisions": [
                {"entity_id":"no-trade", "source_symbol":"XAUUSD",
                 "recorded_at_utc":"2026-11-04T10:00:00Z",
                 "decision":"NO_TRADE","guard_publishable":False,
                 "guard_reasons":["no_setup"],"secret":"NEVER EXPOSE"},
                {"entity_id":"crypto-decision","source_symbol":"BTCUSDT",
                 "decision":"BUY","entry":100,"secret":"NEVER EXPOSE"},
            ],
        },
        "validation_programs": [
            {"program_id":"core-ai-shadow","mode":"SHADOW_ONLY",
             "public_research_observability":True,"public_signal_exposure":True,
             "signal_details_included":False,
             "health":{"broker_execution_disabled":True}},
            {"program_id":"market-expansion-1","mode":"SHADOW_ONLY",
             "public_research_observability":True,"public_signal_exposure":False},
            {"program_id":"crypto-expansion-1","mode":"SHADOW_ONLY",
             "public_research_observability":True,"public_signal_exposure":False},
        ],
    }


class Store:
    def __init__(self):
        self.owner = False
        self.revoked=False
        self.watch=["EURUSD"]
        self.saved={}
        self.prefs={"timezone":"UTC","educational_level":"beginner",
                    "research_updates_opt_in":False}
    def find_session(self,h):
        if h != HASH or self.revoked:return None
        return Identity(
            account_id="aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
            role="owner" if self.owner else "member",
            access_tier="research_free",
            email_verified_at=NOW, expires_at=NOW+timedelta(hours=1),
            revoked_at=None,disabled_at=None,mfa_verified_at=NOW if self.owner else None,
        )
    def watchlist(self,account_id):return list(self.watch)
    def save_market(self,account_id,symbol):
        self.watch.append(symbol);return self.watch
    def delete_market(self,account_id,symbol):
        self.watch.remove(symbol);return self.watch
    def preferences(self,account_id):return self.prefs.copy()
    def update_preferences(self,account_id,patch):
        self.prefs.update(patch);return self.prefs.copy()
    def saved_research(self,account_id):return list(self.saved.values())
    def save_research(self,account_id,symbol,signal_id):
        self.saved[signal_id]={"signal_id":signal_id,"symbol":symbol,
                               "saved_at_utc":NOW.isoformat()}
    def unsave_research(self,account_id,signal_id):self.saved.pop(signal_id,None)
    def revoke_session(self,token_sha256,account_id):
        if token_sha256!=HASH:return False
        self.revoked=True;return True


@pytest.fixture
def ctx():
    store=Store()
    state={"snapshot":snapshot()}
    app=FastAPI()
    app.include_router(create_router(
        read_snapshot=lambda:state["snapshot"], make_store=lambda:store,
        csrf_secret=SECRET,app_origin=ORIGIN,
    ))
    html=Path(__file__).resolve().parents[1]/"web"/"member"/"index.html"
    app.include_router(create_ui_router(make_store=lambda:store,html_path=html))
    client=TestClient(app,base_url=ORIGIN)
    return store,state,client


def login(client):
    client.cookies.set(COOKIE,TOKEN)


def csrf():
    return {"Origin":ORIGIN,"X-VowSig-CSRF":csrf_for_session(TOKEN,SECRET)}


def test_public_market_and_history_summary_no_restricted_or_full_performance(ctx):
    _,_,client=ctx
    markets=client.get("/api/v2/public/markets").json()["markets"]
    assert len(markets)==9 and len({m["symbol"] for m in markets})==9
    assert {x["symbol"] for x in markets if x["research_signal_detail_available"]}=={
        "XAUUSD","USTEC","US30"
    }
    response=client.get("/api/v2/public/history-summary")
    assert response.json()["history_complete"] is False
    assert response.json()["full_population_metrics"] is None
    assert "NEVER EXPOSE" not in response.text


def test_membership_history_filters_and_detail_permissions(ctx):
    _,state,client=ctx
    login(client)
    result=client.get("/api/v2/me/history")
    assert result.status_code==200
    rows=result.json()
    assert rows["history_complete"] is False
    assert len(rows["signals"])==1 and rows["signals"][0]["net_r"]==-1
    assert len(rows["decisions"])==1 and rows["decisions"][0]["decision"]=="NO_TRADE"
    assert "NEVER EXPOSE" not in result.text and "BTCUSDT" not in result.text
    assert "no-store" in result.headers["cache-control"]
    assert client.get("/api/v2/me/history?symbol=BTCUSDT").status_code==403
    assert client.get("/api/v2/me/history?decision=NOT_A_DECISION").status_code==400
    assert client.get("/api/v2/me/signals/good").status_code==200
    assert client.get("/api/v2/me/signals/crypto").status_code==404
    state["snapshot"]["generated_at_utc"]="2026-01-01T00:00:00Z"
    assert client.get("/api/v2/me/signals/good").status_code==404
    assert client.get("/api/v2/me/history").json()["signals"]==[]


def test_profile_preferences_export_and_csrf(ctx):
    _,_,client=ctx
    login(client)
    assert client.get("/api/v2/me/preferences").json()["educational_level"]=="beginner"
    bad=client.patch("/api/v2/me/preferences",json={"timezone":"UTC"})
    assert bad.status_code==403
    assert client.patch("/api/v2/me/preferences",headers=csrf(),
                        json={"timezone":"Not/A/Zone"}).status_code==400
    assert client.patch("/api/v2/me/preferences",headers=csrf(),
                        json={"research_updates_opt_in":"yes"}).status_code==400
    ok=client.patch("/api/v2/me/preferences",headers=csrf(),
                    json={"timezone":"Asia/Karachi","educational_level":"advanced"})
    assert ok.status_code==200 and ok.json()["timezone"]=="Asia/Karachi"
    export=client.get("/api/v2/me/export")
    assert export.status_code==200
    assert export.json()["watchlist"]==["EURUSD"]
    assert export.json()["preferences"]["educational_level"]=="advanced"
    assert "no-store" in export.headers["cache-control"]


def test_only_existing_permitted_core_signal_can_be_bookmarked(ctx):
    _,_,client=ctx
    login(client)
    assert client.put("/api/v2/me/saved/BTCUSDT/crypto",headers=csrf()).status_code==403
    assert client.put("/api/v2/me/saved/XAUUSD/unknown",headers=csrf()).status_code==404
    assert client.put("/api/v2/me/saved/XAUUSD/good").status_code==403
    assert client.put("/api/v2/me/saved/XAUUSD/good",headers=csrf()).status_code==200
    assert client.get("/api/v2/me/saved").json()["saved"][0]["signal_id"]=="good"
    assert client.delete("/api/v2/me/saved/good",headers=csrf()).status_code==200
    assert client.get("/api/v2/me/saved").json()["saved"]==[]


def test_logout_requires_csrf_revokes_cookie_and_denies_reuse(ctx):
    store,_,client=ctx
    login(client)
    assert client.post("/api/v2/me/logout").status_code==403
    response=client.post("/api/v2/me/logout",headers=csrf())
    assert response.status_code==200 and store.revoked is True
    assert "max-age=0" in response.headers["set-cookie"].lower()
    login(client)
    assert client.get("/api/v2/me").status_code==401


def test_html_not_public_and_admin_mfa_enforced(ctx):
    store,_,client=ctx
    assert client.get("/app/").status_code==401
    assert client.get("/admin/").status_code==401
    login(client)
    assert client.get("/app/signals/").status_code==200
    assert "no-store" in client.get("/app/").headers["cache-control"]
    assert client.get("/admin/").status_code==403
    assert client.get("/api/v2/admin/performance").status_code==403
    store.owner=True
    admin=client.get("/admin/")
    assert admin.status_code==200
    assert "frame-ancestors 'none'" in admin.headers["content-security-policy"]
    p=client.get("/api/v2/admin/performance")
    assert p.status_code==200 and p.json()["performance"] is None
    assert p.json()["verified_full_history"] is False
    ops=client.get("/api/v2/admin/operations")
    assert ops.status_code==200 and ops.json()["broker_execution_enabled"] is False
    growth=client.get("/api/v2/admin/growth")
    assert growth.json()["registered_accounts"] is None


def test_missing_snapshot_never_invents_entries_or_health(ctx):
    _,state,client=ctx
    login(client)
    state["snapshot"]=None
    result=client.get("/api/v2/me/history").json()
    assert result["signals"]==[] and result["decisions"]==[]
    assert result["status"]=="unavailable"
    assert client.get("/api/v2/admin/growth").status_code==403
