"""Owner operational/market diagnostics: strict bounded, no fabricated VPS proof."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from trading_signal_intelligence.product.accounts.owner_diagnostics import (
    owner_market_reliability,owner_operational_diagnostics,
)

NOW=datetime(2026,11,4,16,0,tzinfo=timezone.utc)


def snapshot():
    return {
        "generated_at_utc":"2026-11-04T15:30:00Z",
        "health":{"ok":True, "private_key":"MUST_NOT_LEAK"},
        "validation_programs":[
            {
                "program_id":"core-ai-shadow","runtime_version":"AI-v1.1",
                "mode":"SHADOW_ONLY","public_signal_exposure":True,
                "public_research_observability":True,"signal_details_included":False,
                "health":{
                    "healthy":True,"ledgers_valid":True,"scheduler_healthy":True,
                    "broker_execution_disabled":True,
                },
                "totals":{
                    "valid_inferences":177,"missed_inferences":156,
                    "no_current_h1_tick_count":153,"processing_miss_count":3,
                    "processing_miss_denominator":180,
                    "completed_shadow_trades":3,"no_trade":129,"errors":0,
                    "private_key":"MUST_NOT_LEAK",
                },
                "markets":[
                    {
                        "source_symbol":"XAUUSD","ledger_valid":True,
                        "activation_anchor_match":True,
                        "valid_inferences":40,"missed_inferences":10,
                        "errors":0,"no_trade":10,
                        "provider_request_metadata":"MUST_NOT_LEAK",
                        "entry":1234,"stop":1220,
                    },
                    {"source_symbol":"USTEC","ledger_valid":True,
                     "activation_anchor_match":True,"valid_inferences":20,
                     "errors":0,"no_trade":3},
                ],
            },
            {
                "program_id":"market-expansion-1","runtime_version":"AI-v1.2.1",
                "mode":"SHADOW_ONLY","public_signal_exposure":False,
                "health":{"healthy":False,"broker_execution_disabled":True},
                "totals":{"valid_inferences":7,"missed_inferences":3,"errors":0},
                "markets":[{"source_symbol":"EURUSD","ledger_valid":False,
                            "activation_anchor_match":False,"valid_inferences":7,
                            "no_trade":4,"missed_inferences":3}],
            },
            {
                "program_id":"crypto-expansion-1","runtime_version":"AI-v1.3",
                "mode":"SHADOW_ONLY","public_signal_exposure":False,
                "health":{"healthy":True,"broker_execution_disabled":True},
                "totals":{"valid_inferences":13,"errors":0},
                "markets":[{"source_symbol":"BTCUSDT","ledger_valid":True,
                            "activation_anchor_match":True,"valid_inferences":13,
                            "completed_shadow_trades":2}],
            },
        ],
    }


def test_operational_counts_preserve_no_tick_vs_processing_miss_distinction():
    report=owner_operational_diagnostics(snapshot(),now=NOW)
    assert report["snapshot_fresh"] is True
    assert report["snapshot_age_seconds"]==1800
    assert report["vps_schedulers_independently_verified"] is False
    assert report["publisher_last_success_independently_verified"] is False
    assert report["broker_execution_independently_verified"] is False
    assert report["backup_restore_proven"] is False
    assert len(report["programs"])==3
    core=next(p for p in report["programs"] if p["program_id"]=="core-ai-shadow")
    assert core["reported_scheduler_healthy"] is True
    assert core["totals"]["missed_inferences"]==156
    assert core["totals"]["no_current_h1_tick_count"]==153
    assert core["totals"]["processing_miss_count"]==3
    assert core["totals"]["processing_miss_denominator"]==180
    assert core["processing_miss_rate"]==3/180
    assert core["independent_scheduler_probe"] is False
    assert "MUST_NOT_LEAK" not in str(report)


def test_missing_or_invalid_split_never_invents_processing_miss_rate():
    data=snapshot()
    core=data["validation_programs"][0]
    core["totals"]["no_current_h1_tick_count"]=None
    a=owner_operational_diagnostics(data,now=NOW)["programs"]
    c=next(x for x in a if x["program_id"]=="core-ai-shadow")
    assert c["totals"]["processing_miss_count"] is None
    assert c["processing_miss_rate"] is None
    core["totals"]["no_current_h1_tick_count"]=152
    assert owner_operational_diagnostics(data,now=NOW)["programs"][0]["processing_miss_rate"] is None
    core["totals"]["no_current_h1_tick_count"]=153
    core["totals"]["processing_miss_denominator"]=179
    assert owner_operational_diagnostics(data,now=NOW)["programs"][0]["processing_miss_rate"] is None
    core["totals"]["processing_miss_denominator"]=180
    core["totals"]["valid_inferences"]=True
    assert owner_operational_diagnostics(data,now=NOW)["programs"][0]["processing_miss_rate"] is None


def test_market_report_keeps_nine_catalog_markets_and_never_exposes_private_fields():
    report=owner_market_reliability(snapshot(),now=NOW)
    assert report["market_count"]==9
    assert {x["symbol"] for x in report["markets"]}=={
        "XAUUSD","USTEC","US30","EURUSD","XAGUSD","USOIL",
        "BTCUSDT","ETHUSDT","SOLUSDT",
    }
    gold=next(x for x in report["markets"] if x["symbol"]=="XAUUSD")
    assert gold["reported_counts"]["valid_inferences"]==40
    assert gold["reported_counts"]["missed_inferences"]==10
    assert gold["processing_miss_count"] is None
    assert gold["after_costs_per_market_verified"] is False
    assert gold["independent_ledger_audit"] is False
    assert gold["no_signal_detail_access_granted_by_diagnostics"] is True
    assert not any(x in str(report) for x in (
        "MUST_NOT_LEAK","provider_request_metadata","1234","1220"
    ))
    missing=next(x for x in report["markets"] if x["symbol"]=="US30")
    assert missing["source_metrics_present"] is False
    assert missing["reported_counts"]["valid_inferences"] is None
    crypto=next(x for x in report["markets"] if x["symbol"]=="BTCUSDT")
    assert crypto["program_id"]=="crypto-expansion-1"
    assert crypto["reported_counts"]["completed_shadow_trades"]==2


def test_stale_or_future_snapshot_and_duplicate_programs_fail_closed():
    s=snapshot()
    s["generated_at_utc"]=(NOW-timedelta(hours=4)).isoformat()
    report=owner_operational_diagnostics(s,now=NOW)
    assert report["snapshot_fresh"] is False
    assert "SNAPSHOT_MISSING_OR_DELAYED" in report["risk_flags"]
    s["generated_at_utc"]=(NOW+timedelta(hours=1)).isoformat()
    assert owner_operational_diagnostics(s,now=NOW)["snapshot_fresh"] is False
    s["validation_programs"].append(deepcopy(s["validation_programs"][0]))
    result=owner_operational_diagnostics(s,now=NOW)
    core=next(x for x in result["programs"] if x["program_id"]=="core-ai-shadow")
    assert core["status"]=="snapshot_missing"
    assert core["totals"]["valid_inferences"] is None
    market=owner_market_reliability(s,now=NOW)
    xau=next(x for x in market["markets"] if x["symbol"]=="XAUUSD")
    assert xau["source_metrics_present"] is False


def test_shadow_boundary_violation_is_reported_but_cannot_grant_rights():
    s=snapshot()
    s["validation_programs"][1]["public_signal_exposure"]=True
    s["validation_programs"][2]["health"]["broker_execution_disabled"]=False
    report=owner_operational_diagnostics(s,now=NOW)
    assert "SHADOW_BOUNDARY_REPORTED_VIOLATION" in report["risk_flags"]
    assert sum(x["boundary_violation_reported"] is True for x in report["programs"])==2
    markets=owner_market_reliability(s,now=NOW)["markets"]
    assert all(x["no_signal_detail_access_granted_by_diagnostics"] for x in markets)
    assert all(x["after_costs_per_market_verified"] is False for x in markets)


def test_empty_snapshot_does_not_invent_nine_healthy_windows_schedulers():
    ops=owner_operational_diagnostics(None,now=NOW)
    assert ops["snapshot_fresh"] is False
    assert ops["snapshot_age_seconds"] is None
    assert all(x["status"]=="snapshot_missing" for x in ops["programs"])
    assert all(x["reported_scheduler_healthy"] is None for x in ops["programs"])
    markets=owner_market_reliability(None,now=NOW)
    assert len(markets["markets"])==9
    assert all(x["source_metrics_present"] is False for x in markets["markets"])
