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
        self.owner_mfa_active = False
        self.active_hash = HASH
        self.revoked=False
        self.watch=["EURUSD"]
        self.saved={}
        self.prefs={"timezone":"UTC","educational_level":"beginner",
                    "research_updates_opt_in":False}
    def find_session(self,h):
        if h != self.active_hash or self.revoked:return None
        return Identity(
            account_id="aaaaaaaa-aaaa-4aaa-aaaa-aaaaaaaaaaaa",
            role="owner" if self.owner else "member",
            access_tier="research_free",
            email_verified_at=NOW, expires_at=NOW+timedelta(hours=1),
            revoked_at=None,disabled_at=None,mfa_verified_at=NOW if self.owner and self.owner_mfa_active else None,
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
    def account_export(self,account_id):
        return {
            "account_id":account_id,"email":"member@example.test",
            "role":"owner" if self.owner else "member",
            "created_at_utc":NOW.isoformat(),"email_verified_at_utc":NOW.isoformat(),
            "consent_events":[],"consent_history_complete":True,
            "deletion_request": getattr(self,"deletion_request",None),
        }
    def request_deletion(self,account_id):
        self.deletion_request={
            "status":"pending_reverification","requested_at_utc":NOW.isoformat(),
            "notice":"Request recorded; no data erased",
        }
        return self.deletion_request
    def admin_evidence_inventory(self):
        return {
            "source": "research_projection_database",
            "status": "awaiting_independent_source_reconciliation",
            "verified_full_history": False,
            "source_ledger_independently_reconciled": False,
            "historical_performance_publishing_permitted": False,
            "snapshots": [{
                "source_program_id": "core-ai-shadow",
                "model_version": "AI-v1.1",
                "ingest_status": "quarantined",
                "projected_records": 4,
                "projected_closed": 1,
                "projected_open": 1,
                "projected_no_trade": 1,
                "projected_rejected": 1,
                "projected_error": 0,
                "projected_closed_after_costs": 1,
                "independently_verified": False,
            }],
            "inventory_truncated": False,
            "next_evidence_required": "Independent original-ledger reconciliation required",
        }
    def admin_growth(self):
        return {
            "source":"account_database_aggregate","registered_accounts":1,
            "verified_accounts":1,"accounts_with_watchlist":1,
            "activation_rate":1.0,"retention_7d":None,"revenue":None,
            "unverified_accounts":0,"new_accounts_24h":1,
            "new_accounts_7d":1,"new_accounts_30d":1,
            "verified_rate":1.0,"accounts_with_saved_research":0,
            "research_updates_opted_in_accounts":0,"pending_deletion_requests":0,
            "valid_account_sessions_now":1,"issued_sessions_last_7d":1,
            "owner_totp_enrolled_accounts":1,"backup_restore_proven":False,
            "backup_notice":"PostgreSQL recovery unverified",
        }
    def verify_owner_totp(self,*,token_sha256,account_id,code,master_key_b64):
        from trading_signal_intelligence.product.accounts.owner_mfa import (
            OwnerMfaRejected, OwnerMfaConfigurationError,
        )
        if not master_key_b64:
            raise OwnerMfaConfigurationError("Offline setup required")
        if token_sha256!=self.active_hash or not self.owner or code!="123456":
            raise OwnerMfaRejected("Synthetic challenge rejected")
        self.owner_mfa_active=True
        rotated=base64.urlsafe_b64encode(bytes(reversed(range(32)))).decode().rstrip("=")
        self.active_hash=hashlib.sha256(rotated.encode("ascii")).hexdigest()
        return datetime.now(timezone.utc),rotated,NOW+timedelta(hours=1)
    def revoke_session(self,token_sha256,account_id):
        if token_sha256!=self.active_hash:return False
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
    for wrong in ([], {}, 12, False, None):
        assert client.patch("/api/v2/me/preferences",headers=csrf(),
                            json={"educational_level":wrong}).status_code==400
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
    assert client.get("/api/v2/admin/evidence").status_code==403
    store.owner=True
    assert client.get("/admin/").status_code==403
    store.owner_mfa_active=True
    admin=client.get("/admin/")
    assert admin.status_code==200
    assert "frame-ancestors 'none'" in admin.headers["content-security-policy"]
    p=client.get("/api/v2/admin/performance")
    assert p.status_code==200 and p.json()["performance"] is None
    assert p.json()["verified_full_history"] is False
    evidence=client.get("/api/v2/admin/evidence")
    assert evidence.status_code==200
    assert evidence.json()["source_ledger_independently_reconciled"] is False
    assert evidence.json()["historical_performance_publishing_permitted"] is False
    assert evidence.json()["snapshots"][0]["projected_records"]==4
    assert evidence.json()["snapshots"][0]["independently_verified"] is False
    assert "no-store" in evidence.headers["cache-control"]
    ops=client.get("/api/v2/admin/operations")
    assert ops.status_code==200 and ops.json()["broker_execution_enabled"] is False
    growth=client.get("/api/v2/admin/growth")
    assert growth.json()["registered_accounts"] == 1
    assert growth.json()["retention_7d"] is None


def test_owner_totp_stepup_requires_owner_session_csrf_and_provisioned_key(ctx,monkeypatch):
    from trading_signal_intelligence.product.accounts.owner_mfa import OwnerMfaRejected
    store,_,client=ctx
    route="/api/v2/me/owner-mfa/verify"
    assert client.post(route,json={"code":"123456"},headers=csrf()).status_code==401
    login(client)
    assert client.post(route,json={"code":"123456"},headers=csrf()).status_code==403
    store.owner=True
    assert client.post(route,json={"code":"123456"}).status_code==403
    assert client.post(route,json={"code":123456},headers=csrf()).status_code==400
    assert client.post(route,json={"code":"123456","enroll":True},
                       headers=csrf()).status_code==400
    assert client.post(route,json={"code":"123456"},headers=csrf()).status_code==503
    monkeypatch.setenv("VOWSIG_OWNER_TOTP_MASTER_KEY_B64","synthetic-test-key")
    bad=client.post(route,json={"code":"000000"},headers=csrf())
    assert bad.status_code==403 and "no-store" not in bad.headers.get("cache-control","")
    ok=client.post(route,json={"code":"123456"},headers=csrf())
    assert ok.status_code==200 and ok.json()["verified"] is True
    assert ok.json()["owner_admin_route"]=="/admin/"
    assert "no-store" in ok.headers["cache-control"]
    assert "VOWSIG_OWNER_TOTP_MASTER_KEY_B64" not in ok.text
    assert "__Host-vowsig_session=" in ok.headers["set-cookie"]
    assert "httponly" in ok.headers["set-cookie"].lower()
    assert "secure" in ok.headers["set-cookie"].lower()
    new_token=ok.headers["set-cookie"].split(";",1)[0].split("=",1)[1]
    assert new_token!=TOKEN and len(new_token)==43
    client.cookies.clear()
    client.cookies.set(COOKIE,TOKEN)
    assert client.get("/api/v2/me").status_code==401
    client.cookies.clear()
    client.cookies.set(COOKIE,new_token)
    assert client.get("/api/v2/me").status_code==200
    assert client.get("/admin/").status_code==200


def test_missing_snapshot_never_invents_entries_or_health(ctx):
    _,state,client=ctx
    login(client)
    state["snapshot"]=None
    result=client.get("/api/v2/me/history").json()
    assert result["signals"]==[] and result["decisions"]==[]
    assert result["status"]=="unavailable"
    assert client.get("/api/v2/admin/growth").status_code==403


def test_deletion_request_is_explicit_non_destructive_and_csrf_protected(ctx):
    store,_,client=ctx
    login(client)
    assert client.post("/api/v2/me/deletion-request").status_code==403
    result=client.post("/api/v2/me/deletion-request",headers=csrf())
    assert result.status_code==200
    assert result.json()["status"]=="pending_reverification"
    assert client.get("/api/v2/me").status_code==200
    export=client.get("/api/v2/me/export").json()
    assert export["email"]=="member@example.test"
    assert export["deletion_request"]["status"]=="pending_reverification"
    assert store.revoked is False


def test_active_shadow_lifecycle_requires_current_issued_at_and_h1_hold(ctx):
    _,state,client=ctx
    login(client)
    record={
        "entity_id":"active-core","source_symbol":"USTEC","status":"active",
        "direction":"BUY","entry":120,"stop":119,
        "issued_at_utc":datetime.now(timezone.utc).isoformat(),
        "max_hold_h1_bars":2,
    }
    state["snapshot"]["ai_v1"]["shadow_signals"].append(record)
    directory=client.get("/api/v2/public/markets").json()["markets"]
    assert next(x for x in directory if x["symbol"]=="USTEC")["current_signal_present"]
    data=client.get("/api/v2/me/signals?symbol=USTEC").json()
    assert data["signals"][0]["current_signal_eligible"] is True
    # Freshly generated *snapshot* is NOT enough when the active row is old.
    record["issued_at_utc"]="2026-01-01T00:00:00Z"
    directory=client.get("/api/v2/public/markets").json()["markets"]
    assert not next(x for x in directory if x["symbol"]=="USTEC")["current_signal_present"]
    data=client.get("/api/v2/me/signals?symbol=USTEC").json()
    assert data["signals"][0]["status"]=="activity_unverified"
    assert data["signals"][0]["current_signal_eligible"] is False
    # Missing declared lifetime must never silently produce an active setup.
    record["issued_at_utc"]=datetime.now(timezone.utc).isoformat()
    record.pop("max_hold_h1_bars")
    data=client.get("/api/v2/me/signals?symbol=USTEC").json()
    assert data["signals"][0]["status"]=="activity_unverified"
