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
            result={**state["operations"],
                "owner_operational_diagnostics":{
                    "snapshot_generated_at_utc":"2026-11-04T10:00:00Z",
                    "snapshot_age_seconds":10800,
                    "snapshot_fresh":False,
                    "vps_schedulers_independently_verified":False,
                    "publisher_last_success_independently_verified":False,
                    "broker_execution_independently_verified":False,
                    "programs":[{
                        "program_id":"core-ai-shadow",
                        "runtime_version":"AI-v1.1",
                        "status":"snapshot_delayed",
                        "reported_scheduler_healthy":None,
                        "reported_ledgers_valid":None,
                        "shadow_only_reported":True,
                        "broker_execution_disabled_reported":True,
                        "boundary_violation_reported":False,
                        "totals":{
                            "valid_inferences":3,"no_trade":2,
                            "missed_inferences":2,"no_current_h1_tick_count":None,
                            "processing_miss_count":None,
                            "errors":1,"completed_shadow_trades":1,
                        },
                        "processing_miss_rate":None,
                    }],
                },
            }
        elif path=="/api/v2/admin/models":
            result={
                "source":"postgres_research_projection_only",
                "groups_truncated":False,
                "complete_historical_track_record_available":False,
                "groups":[{
                    "source_program_id":"core-ai-shadow","model_version":"AI-v1.1",
                    "cohort":"forward-shadow","projection_ingest_status":"quarantined",
                    "source_projection_count":1,"projected_outcomes":3,
                    "projected_closed":1,"projected_open":1,
                    "projected_no_trade":1,"projected_rejected":0,
                    "projected_error":0,"database_cost_flagged_closed":1,
                    "last_observed_at_utc":"2026-11-04T14:00:00Z",
                    "source_ledger_independently_audited":False,
                    "historical_return_metrics":None,
                }],
            }
        elif path=="/api/v2/admin/market-reliability":
            result={
                "source":"public_snapshot_only",
                "snapshot_fresh":False,
                "market_count":9,
                "notice":"Per-market raw missed cycles are not missed trades.",
                "markets":[{
                    "symbol":symbol,
                    "program_id":("core-ai-shadow" if symbol in CORE else
                        "market-expansion-1" if symbol in SIX[:3] else
                        "crypto-expansion-1"),
                    "catalog_research_status":"research_validation",
                    "source_metrics_present":symbol=="XAUUSD",
                    "reported_ledger_valid":True if symbol=="XAUUSD" else None,
                    "reported_activation_anchor_match":True if symbol=="XAUUSD" else None,
                    "reported_counts":{
                        "valid_inferences":3 if symbol=="XAUUSD" else None,
                        "completed_shadow_trades":1 if symbol=="XAUUSD" else None,
                        "open_signals":0 if symbol=="XAUUSD" else None,
                        "no_trade":2 if symbol=="XAUUSD" else None,
                        "rejected_inferences":0 if symbol=="XAUUSD" else None,
                        "missed_inferences":2 if symbol=="XAUUSD" else None,
                        "errors":1 if symbol=="XAUUSD" else None,
                    },
                } for symbol in ALL],
            }
        elif path=="/api/v2/admin/performance":
            result=state.get("performance",{
                "performance":None,"verified_full_history":False,
                "notice":"No complete source evidence.",
            })
        elif path=="/api/v2/admin/evidence":
            result={
                "source":"research_projection_database",
                "verified_full_history":False,
                "source_ledger_independently_reconciled":False,
                "historical_performance_publishing_permitted":False,
                "inventory_truncated":False,
                "next_evidence_required":"Independent original-ledger verification required",
                "snapshots":[{
                    "source_program_id":"core-ai-shadow","model_version":"AI-v1.1",
                    "ingest_status":"quarantined","projected_records":2,
                    "projected_closed":1,"projected_open":0,
                    "projected_no_trade":1,"projected_rejected":0,
                    "projected_error":0,"projected_closed_after_costs":1,
                    "independently_verified":False,
                }]
            }
        elif path=="/api/v2/admin/growth":
            result={
                "registered_accounts":1,"verified_accounts":1,
                "unverified_accounts":0,"new_accounts_24h":1,
                "new_accounts_7d":1,"new_accounts_30d":1,
                "verified_rate":1.0,
                "accounts_with_watchlist":0,
                "accounts_with_saved_research":0,
                "research_updates_opted_in_accounts":0,
                "pending_deletion_requests":0,
                "valid_account_sessions_now":1,
                "issued_sessions_last_7d":1,
                "owner_totp_enrolled_accounts":1,
                "retention_7d":None,"revenue":None,
                "backup_restore_proven":False,
                "backup_notice":"Postgres backup and cold restore not yet verified.",
            }
        elif path=="/api/v2/me/deletion-request":
            result={"status":"pending_reverification"}
        elif path=="/api/v2/me/owner-mfa/verify" and method=="POST":
            code=json.loads(request.post_data or "{}").get("code")
            if state["member_role"] != "owner" or code != "123456":
                route.fulfill(status=403,content_type="application/json",body="{}")
                return
            state["owner_mfa_verified"]=True
            result={"verified":True,"verified_until_utc":"2026-11-04T16:00:00Z",
                    "owner_admin_route":"/admin/"}
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
    page.locator("#app-content .panel, #app-error:not([hidden])").first.wait_for(timeout=5000)
    if page.locator("#app-content .panel").count()==0:
        pytest.fail("Member browser render failed: " +
            page.locator("#app-error").inner_text() + " | " +
            page.locator("#app-content").inner_text())


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
    assert page.get_by_text("Independent history evidence & reconciliation").count()==1
    assert page.get_by_text("Independent source proof",exact=False).count()>=1
    assert page.get_by_text("Original-ledger verification still required").count()==1
    assert page.get_by_text("VPS runtime independently verified",exact=False).count()>=1
    assert "VPS runtime independently verified: No" in page.locator("#app-content").inner_text()
    assert page.get_by_text("Growth, access security & recovery").count()==1
    assert page.get_by_text("D7 retention",exact=False).count()>=1
    assert page.get_by_text("Independent Postgres restore",exact=False).count()==1
    assert page.get_by_text("Runtime observability & operating boundaries").count()==1
    assert page.get_by_text("Model versions & projected lifecycle populations").count()==1
    assert page.get_by_text("All-market reliability diagnostic").count()==1
    assert page.get_by_text("Raw missed cycles (not trades)",exact=False).count()>=1
    assert page.get_by_text("Source-audited returns").count()==1
    assert page.get_by_text("No-current-tick cycles").count()==1
    assert page.locator("#app-content").inner_text().count("Original-ledger independently audited")==9
    assert not any("/api/internal" in path for _,path in state["http_calls"])
    assert not any("/api/internal" in path for _,path in state["http_calls"])


def test_owner_attested_cohort_metrics_never_claim_platform_or_cash_profit(ui):
    page,state=ui
    state["member_role"]="owner"
    state["performance"]={
        "verified_full_history":False,
        "verified_full_cohort_history":True,
        "source_ledger_independently_reconciled":True,
        "reviewed_at_utc":"2026-11-04T14:00:00Z",
        "notice":"One source-attested cohort; not all lineages.",
        "performance":{
            "source_program_id":"core-ai-shadow","model_version":"AI-v1.1",
            "cohort":"forward-shadow","total_outcomes":3,
            "completed_count":2,"win_count":1,"loss_count":1,
            "breakeven_count":0,"win_rate":0.5,
            "sum_completed_net_r":1.0,"expectancy_net_r":0.5,
            "max_normalized_r_drawdown":1.0,
            "open_count":0,"no_trade_count":1,"rejected_count":0,
            "error_count":0,"sample_warning":"small_forward_sample",
        },
    }
    open_page(page,"/admin/")
    txt=page.locator("#app-content").inner_text()
    assert "Independently attested cohort" in txt
    assert "Real-money returns" in txt
    assert "Not available" in txt
    assert "Source-reconciled performance unavailable" not in txt
    assert "other lineages are not certified" in txt.lower()


def test_owner_free_totp_step_up_ui_is_owner_only_and_not_auth0_upgrade(ui):
    page,state=ui
    open_page(page,"/app/settings/")
    assert page.get_by_text("Owner MFA · authenticator app").count()==0
    state["member_role"]="owner"
    open_page(page,"/app/settings/")
    assert page.get_by_text("Owner MFA · authenticator app").count()==1
    code=page.locator("#owner-code")
    code.fill("123456")
    page.get_by_role("button",name="Verify owner authenticator code").click()
    page.get_by_text("Owner verification completed",exact=False).wait_for()
    assert state["owner_mfa_verified"] is True
    assert code.input_value()==""
    assert page.get_by_text("Open owner dashboard after verification").count()==1
    assert not any("/auth0" in path or "/billing" in path or "/upgrade" in path
                   for _,path in state["http_calls"])


def test_expired_session_does_not_render_private_research(ui):
    page,state=ui
    state["unauthorized"]=True
    page.goto(HOST+"/app/signals/",wait_until="load")
    page.get_by_text("Research workspace not ready").wait_for()
    assert page.get_by_text("XAUUSD · SELL").count()==0
    assert page.get_by_text("Your verified account session is unavailable",exact=False).count()>=1
