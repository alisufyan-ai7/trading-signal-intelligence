"""P3 browser-level Signal Center QA with entirely mocked same-origin APIs.

The UI may render HTML in this isolated browser harness without auth only because
the fixture serves it from memory. Real /app and /admin routes remain server-
gated and covered by separate FastAPI tests. No public server or provider runs.
"""
from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
WEB=ROOT/"web"/"member"
HOST="https://vowsig.example"
CORE=("XAUUSD","USTEC","US30")
SIX=("EURUSD","XAGUSD","USOIL","BTCUSDT","ETHUSDT","SOLUSDT")
ALL=CORE+SIX


def fixture_state():
    return {
        "unauthorized":False,
        "member_role":"member",
        "watchlist":[],
        "saved":[],
        "preferences":{
            "timezone":"UTC","educational_level":"beginner",
            "research_updates_opt_in":False,
        },
        "history":{
            "research_only":True,"history_complete":False,
            "source":"bounded_public_snapshot","status":"shadow_only",
            "snapshot_generated_at_utc":"2026-11-04T10:00:00Z",
            "commercial_customer_eligible":False,
            "record_window_notice":"Only the sanitized current snapshot; not entire history.",
            "signals":[
                {"entity_id":"loss-001","source_symbol":"XAUUSD","direction":"SELL",
                 "status":"closed","entry":100,"stop":101,"tp1":99,"tp2":98,
                 "issued_at_utc":"2026-11-03T10:00:00Z",
                 "exit_at_utc":"2026-11-03T11:00:00Z",
                 "net_r":-1.0,"exit_reason":"STOP",
                 "rationale":"Literal <img src=x onerror=alert('xss')> research text.",
                 "risk_factors":["Research signal can lose."]},
                {"entity_id":"stale-001","source_symbol":"USTEC","direction":"BUY",
                 "status":"activity_unverified","current_signal_eligible":False,
                 "issued_at_utc":"2026-01-01T00:00:00Z",
                 "rationale":"Old shadow record, not active","risk_factors":[]},
                {"entity_id":"crypto-leak","source_symbol":"BTCUSDT","direction":"BUY",
                 "status":"active","current_signal_eligible":True,
                 "rationale":"FORBIDDEN CRYPTO PAYLOAD","entry":20000},
            ],
            "decisions":[
                {"entity_id":"abstain","source_symbol":"XAUUSD","decision":"NO_TRADE",
                 "recorded_at_utc":"2026-11-04T09:00:00Z","guard_publishable":False,
                 "guard_reasons":["No qualified setup"]},
                {"entity_id":"restricted-decision","source_symbol":"SOLUSDT",
                 "decision":"BUY","rationale":"FORBIDDEN CRYPTO PAYLOAD"},
            ],
        },
        "operations":{
            "source":"public_snapshot_only","as_of_utc":"2026-11-04T10:00:00Z",
            "snapshot_fresh":False,"independent_vps_runtime_health_verified":False,
            "backup_restore_proven":False,"broker_execution_enabled":False,
            "programs":[{
                "program_id":"core-ai-shadow","reported_healthy":False,
                "valid_inferences":3,"errors":1,"completed_shadow_trades":1,
            }],
        },
    }


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as playwright:
        browser=playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def ui(browser):
    state=fixture_state()
    context=browser.new_context(viewport={"width":1280,"height":800})
    page=context.new_page()
    state["http_calls"]=[]
    def route_request(route):
        request=route.request
        url=urlsplit(request.url)
        path=unquote(url.path)
        method=request.method
        state["http_calls"].append((method,path))
        if url.scheme!="https" or url.netloc!="vowsig.example":
            route.abort()
            return
        if path.startswith("/app/") or path=="/admin/":
            route.fulfill(status=200,content_type="text/html",
                          body=(WEB/"index.html").read_bytes())
            return
        if path=="/static/member/member.js":
            route.fulfill(status=200,content_type="application/javascript",
                          body=(WEB/"member.js").read_bytes())
            return
        if path=="/static/member/member.css":
            route.fulfill(status=200,content_type="text/css",
                          body=(WEB/"member.css").read_bytes())
            return
        if path.endswith(".svg"):
            route.fulfill(status=200,content_type="image/svg+xml",
                          body="<svg xmlns='http://www.w3.org/2000/svg'/>")
            return
        if path=="/api/v2/me" and state["unauthorized"]:
            route.fulfill(status=401,content_type="application/json",body="{}")
            return
        result=None
        if path=="/api/v2/me":
            result={
                "account_id":"mock-account","role":state["member_role"],
                "access_tier":"research_free","csrf_token":"mock-csrf",
                "email_verified":True,"commercial_customer_eligible":False,
            }
        elif path=="/api/v2/public/markets":
            result={"markets":[{
                "symbol":symbol,"name":symbol,"research_status":(
                    "core_shadow_research" if symbol in CORE else "research_validation"
                ),"snapshot_fresh":False,
                "research_signal_detail_available":symbol in CORE,
                "current_signal_present":False,
            } for symbol in ALL]}
        elif path=="/api/v2/me/watchlist" and method=="GET":
            result={"markets":list(state["watchlist"])}
        elif path.startswith("/api/v2/me/watchlist/") and method in ("PUT","DELETE"):
            symbol=path.rsplit("/",1)[-1]
            if symbol not in ALL:
                route.fulfill(status=404,body="{}")
                return
            if method=="PUT" and symbol not in state["watchlist"]:
                state["watchlist"].append(symbol)
            if method=="DELETE" and symbol in state["watchlist"]:
                state["watchlist"].remove(symbol)
            result={"markets":list(state["watchlist"])}
        elif path=="/api/v2/me/history":
            result=state["history"]
        elif path=="/api/v2/me/saved":
            result={"saved":state["saved"]}
        elif path.startswith("/api/v2/me/saved/") and method=="PUT":
            result={"saved":True,"signal_id":path.rsplit("/",1)[-1]}
        elif path=="/api/v2/me/preferences" and method=="GET":
            result=state["preferences"]
        elif path=="/api/v2/me/preferences" and method=="PATCH":
            state["preferences"].update(json.loads(request.post_data or "{}"))
            result=state["preferences"]
        elif path=="/api/v2/me/export":
            result={"account_id":"mock-account","watchlist":state["watchlist"],
                    "preferences":state["preferences"]}
        elif path=="/api/v2/admin/operations":
            result=state["operations"]
        elif path=="/api/v2/admin/performance":
            result={"performance":None,"verified_full_history":False,
                    "notice":"No complete source evidence."}
        elif path=="/api/v2/admin/growth":
            result={"registered_accounts":1,"verified_accounts":1,
                    "accounts_with_watchlist":0,"retention_7d":None}
        elif path=="/api/v2/me/deletion-request":
            result={"status":"pending_reverification"}
        elif path=="/api/v2/me/logout":
            result={"signed_out":True}
        if result is None:
            route.fulfill(status=404,content_type="application/json",body="{}")
        else:
            route.fulfill(status=200,content_type="application/json",body=json.dumps(result))
    page.route("**/*",route_request)
    yield page,state
    context.close()


def open_page(page, path):
    page.goto(HOST+path,wait_until="load")
    page.locator("#app-content .panel").first.wait_for(timeout=10000)


def test_signal_center_renders_losses_no_trade_and_no_xss(ui):
    page,state=ui
    open_page(page,"/app/signals/")
    assert page.locator("h1").inner_text()=="Signal Center"
    assert page.get_by_text("XAUUSD · SELL").count()==1
    assert page.get_by_text("Combined net R:").count()==1
    assert page.get_by_text("NO_TRADE",exact=False).count()>=1
    assert page.get_by_text("Activity unverified",exact=False).count()>=1
    assert page.get_by_text("Literal <img src=x",exact=False).count()==1
    assert page.locator("img[src='x']").count()==0
    assert "FORBIDDEN CRYPTO PAYLOAD" not in page.locator("#app-content").inner_text()
    assert page.get_by_text("not a complete track record",exact=False).count()>=1


def test_mobile_directory_and_member_watchlist(ui):
    page,state=ui
    page.set_viewport_size({"width":375,"height":812})
    open_page(page,"/app/markets/")
    assert page.locator("h1").inner_text()=="All nine markets"
    assert page.locator("article.list-row").count()==9
    assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth + 1")
    assert page.get_by_text("No detailed signal exposure",exact=False).count()==6
    page.locator("article.list-row").first.get_by_role("button",name="Add to watchlist").click()
    page.get_by_role("button",name="Remove from watchlist").first.wait_for()
    assert state["watchlist"]==["XAUUSD"]
    open_page(page,"/app/watchlist/")
    assert page.get_by_text("XAUUSD",exact=False).count()>=1


def test_preferences_consent_saved_without_email_send(ui):
    page,state=ui
    open_page(page,"/app/settings/")
    page.locator("#tz").fill("Asia/Karachi")
    page.locator("#level").select_option("advanced")
    page.locator("#consent").check()
    page.get_by_role("button",name="Save preferences").click()
    page.get_by_text("Preferences saved.",exact=False).wait_for()
    assert state["preferences"]=={
        "timezone":"Asia/Karachi","educational_level":"advanced",
        "research_updates_opt_in":True,
    }
    assert not any("/send" in path or "/alerts" in path or "/billing" in path
                   for _,path in state["http_calls"])


def test_owner_analytics_do_not_imply_verified_history(ui):
    page,state=ui
    state["member_role"]="owner"
    open_page(page,"/admin/")
    assert page.locator("h1").inner_text()=="Owner research overview"
    assert page.get_by_text("Source-reconciled performance unavailable").count()==1
    assert page.get_by_text("VPS runtime independently verified",exact=False).count()>=1
    assert "VPS runtime independently verified: No" in page.locator("#app-content").inner_text()
    assert not any("/api/internal" in path for _,path in state["http_calls"])


def test_expired_session_does_not_render_private_research(ui):
    page,state=ui
    state["unauthorized"]=True
    page.goto(HOST+"/app/signals/",wait_until="load")
    page.get_by_text("Research workspace not ready").wait_for()
    assert page.get_by_text("XAUUSD · SELL").count()==0
    assert page.get_by_text("Your verified account session is unavailable",exact=False).count()>=1
