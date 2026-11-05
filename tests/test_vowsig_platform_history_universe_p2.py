"""Two independent dummy signing keys; nine synthetic source cohorts only."""
from __future__ import annotations

import base64
import hashlib
from datetime import datetime,timezone
import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding,PublicFormat

from trading_signal_intelligence.product.accounts.platform_history import (
    PlatformHistoryHold, verify_all_nine_market_history, _canon,
)
from trading_signal_intelligence.product.accounts.source_inventory import SOURCES
from trading_signal_intelligence.product.accounts.verified_history import outcome_population_sha256

EXPECTED="e"*64
STAMP="2026-10-05T00:00:00Z"


def _pem(key):
    return key.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)


def _signed(private,body,label):
    raw=private.sign(_canon(body))
    return _canon({label:body,"signature_ed25519_b64u":base64.urlsafe_b64encode(raw).decode().rstrip("=")})


def _make():
    source_priv=Ed25519PrivateKey.generate()
    universe_priv=Ed25519PrivateKey.generate()
    source_pub=_pem(source_priv);universe_pub=_pem(universe_priv)
    sources=[]
    inputs={}
    for spec in SOURCES:
        if spec.program=="s02-forward":
            continue
        cohort="frozen-"+spec.symbol.lower()
        facts=[{
            "entity_id":"test-original-"+spec.symbol,
            "source_record_sha256":"f"*64,"state":"closed",
            "exit_at_utc":STAMP,"combined_net_r":-0.15,
            "cost_model_version":"test-cost-v1",
            "after_costs_verified":True,"cohort":cohort,
        }]
        sha=hashlib.sha256(spec.symbol.encode()).hexdigest()
        att={
            "schema_version":1,"source_program_id":spec.program,
            "model_version":spec.model_version,"cohort":cohort,
            "source_head_hash":"a"*64,"source_snapshot_sha256":sha,
            "expected_population_count":1,"expected_closed_count":1,
            "outcome_population_sha256":outcome_population_sha256(facts),
            "source_evidence_sha256":"b"*64,
            "source_rights_approved":True,
            "independent_source_reconciliation":True,
            "reviewer_id":"cohort-independent-auditor",
            "verified_at_utc":datetime.now(timezone.utc).isoformat(),
            "window_start_utc":"2026-10-01T00:00:00Z",
            "window_end_utc":"2026-10-31T23:59:59Z",
            "as_of_utc":"2026-11-01T00:00:00Z",
            "cost_model_version":"test-cost-v1",
        }
        signed=_signed(source_priv,att,"attestation")
        sources.append({
            "source_program_id":spec.program,"model_version":spec.model_version,
            "market":spec.symbol,"cohort":cohort,
            "source_snapshot_sha256":sha,"source_head_hash":"a"*64,
            "source_evidence_sha256":"b"*64,
            "signed_cohort_attestation_sha256":hashlib.sha256(signed).hexdigest(),
            "expected_population_count":1,"expected_closed_count":1,
        })
        inputs[spec.symbol]={
            "signed_attestation":signed,
            "source_snapshot":{
                "source_program_id":spec.program,"model_version":spec.model_version,
                "source_snapshot_sha256":sha,"source_head_hash":"a"*64,
                "ingest_status":"verified","completeness_verified":True,
            },
            "facts":facts,
        }
    universe={
        "schema_version":1,"repository":"alisufyan-ai7/trading-signal-intelligence",
        "research_scope":"ALL_NINE_AI_MARKET_COHORTS",
        "original_twelve_source_manifest_sha256":EXPECTED,
        "market_sources":sources,"reviewer_id":"separate-universe-auditor",
        "reviewed_at_utc":datetime.now(timezone.utc).isoformat(),
        "complete_market_cohort_windows":True,
        "external_crypto_k5_h1_h4_opportunity_coverage_approved":True,
        "source_rights_independently_approved":True,
        "full_after_cost_method_independently_approved":True,
        "s02_benchmark_kept_separate":True,
    }
    def check(u=None,cohorts=None,key_pin=None):
        return verify_all_nine_market_history(
            signed_universe=_signed(universe_priv,universe if u is None else u,"universe"),
            universe_reviewer_pem=universe_pub,
            universe_reviewer_key_sha256=key_pin or hashlib.sha256(universe_pub).hexdigest(),
            cohort_reviewer_pem=source_pub,
            cohort_reviewer_key_sha256=hashlib.sha256(source_pub).hexdigest(),
            owner_recorded_original_manifest_sha256=EXPECTED,
            scoped_private_cohorts=inputs if cohorts is None else cohorts,
        )
    return universe,inputs,check


def test_nine_signed_full_populations_are_required_before_platform_scope():
    universe,inputs,check=_make()
    report=check()
    assert report["verified_full_history"] is True
    assert report["ai_market_count"]==9
    assert report["source_programs"]==3
    assert report["s02_benchmark_is_not_ai_history"] is True
    assert report["production_performance_publishing_automatically_authorized"] is False
    assert "test-original" not in str(report)


@pytest.mark.parametrize("field",[
    "external_crypto_k5_h1_h4_opportunity_coverage_approved",
    "source_rights_independently_approved",
    "full_after_cost_method_independently_approved",
    "complete_market_cohort_windows",
    "s02_benchmark_kept_separate",
])
def test_missing_external_independent_source_truth_refuses_all_platform(field):
    u,inputs,check=_make()
    u[field]=False
    with pytest.raises(PlatformHistoryHold):
        check(u)


def test_missing_market_and_wrong_model_are_holds():
    u,inputs,check=_make()
    u["market_sources"].pop()
    with pytest.raises(PlatformHistoryHold):
        check(u)
    u,inputs,check=_make()
    u["market_sources"][0]["model_version"]="FAKE"
    with pytest.raises(PlatformHistoryHold):
        check(u)


def test_wrong_source_attestation_and_mutated_fact_are_holds():
    u,inputs,check=_make()
    copy_input={k:dict(v) for k,v in inputs.items()}
    copy_input["BTCUSDT"]["signed_attestation"]=b"wrong"
    with pytest.raises(PlatformHistoryHold):
        check(cohorts=copy_input)
    u,inputs,check=_make()
    copy_input=copy.deepcopy(inputs)
    copy_input["ETHUSDT"]["facts"][0]["combined_net_r"]=10.0
    with pytest.raises(PlatformHistoryHold):
        check(cohorts=copy_input)


def test_wrong_owner_pin_and_extra_scope_holds():
    u,inputs,check=_make()
    with pytest.raises(PlatformHistoryHold):
        check(key_pin="0"*64)
    u,inputs,check=_make()
    inputs["XAUUSD_FAKE"]=inputs["XAUUSD"]
    with pytest.raises(PlatformHistoryHold):
        check(cohorts=inputs)
