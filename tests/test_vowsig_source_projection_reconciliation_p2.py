"""Synthetic original-ledger to sanitized projection anchor tests; never live data."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

import pytest

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger
from trading_signal_intelligence.product.accounts.source_projection_reconciliation import (
    SourceProjectionReconciliationError, check_source_projection_link,
)


def _fixture(tmp_path, profile="ai_v1", open_only=False):
    path=tmp_path / (profile+".sqlite")
    ledger=AILedger(path) if profile=="ai_v1" else ForwardLedger(path)
    now=datetime(2026,11,4,12,tzinfo=timezone.utc)
    args={"effective_at_utc":now,"recorded_at_utc":now}
    ledger.append(record_type="ACTIVATION",entity_id="startup",
                  payload={"source":"SYNTHETIC_HIDDEN_SOURCE_PAYLOAD"},**args)
    signal=ledger.append(record_type="SIGNAL",entity_id="trade-1",
                         payload={"entry":100,"secret":"NEVER_EXPORT"},**args)
    exit_record=None
    if not open_only:
        exit_record=ledger.append(record_type="EXIT",entity_id="trade-1",
                                  payload={"net_r":-1.5},**args)
    abstain=ledger.append(record_type="NO_TRADE",entity_id="abstain-1",
                          payload={"reason":"synthetic_only"},**args)
    head=ledger.head_hash()
    rows=[
        {"entity_id":"trade-1",
         "source_record_sha256":(signal if open_only else exit_record)["record_hash"],
         "state":"open" if open_only else "closed",
         "combined_net_r":None if open_only else -1.5,
         "after_costs_verified":False if open_only else True,
         "cost_model_version":None if open_only else "synthetic-cost-v1",
         "exit_at_utc":None if open_only else "2026-11-04T12:00:00Z",
         "program_id":"core-ai-shadow","model_version":"AI-v1.1",
         "cohort":"shadow-cohort"},
        {"entity_id":"abstain-1",
         "source_record_sha256":abstain["record_hash"],
         "state":"no_trade","combined_net_r":None,
         "after_costs_verified":False,"cost_model_version":None,
         "exit_at_utc":None,
         "program_id":"core-ai-shadow","model_version":"AI-v1.1",
         "cohort":"shadow-cohort"},
    ]
    body={
        "schema_version":1,
        "source_program_id":"core-ai-shadow",
        "model_version":"AI-v1.1",
        "cohort":"shadow-cohort","source_head_hash":head,"records":rows,
    }
    raw=json.dumps(body,sort_keys=True,separators=(",",":")).encode("utf-8")
    return path,raw,{
        "sqlite_path":path,
        "source_profile":profile,
        "expected_source_head_sha256":head,
        "expected_source_ledger_records":3 if open_only else 4,
        "sanitized_bundle":raw,
        "expected_bundle_sha256":hashlib.sha256(raw).hexdigest(),
        "expected_outcome_population":2,
        "expected_source_program_id":"core-ai-shadow",
        "expected_model_version":"AI-v1.1",
        "expected_cohort":"shadow-cohort",
    }


@pytest.mark.parametrize("profile",("ai_v1","s02_forward"))
def test_full_chain_link_matches_exact_immutable_terminal_source_events(tmp_path,profile):
    path,raw,pins=_fixture(tmp_path,profile)
    sha_before=hashlib.sha256(path.read_bytes()).hexdigest()
    receipt=check_source_projection_link(**pins)
    assert receipt["status"]=="PINNED_SOURCE_TO_PROJECTION_ANCHORS_MATCH"
    assert receipt["matched_projected_source_anchors"]==2
    assert receipt["source_ledger_record_count"]==4
    assert receipt["source_record_type_counts"]["NO_TRADE"]==1
    assert receipt["source_record_type_counts"]["EXIT"]==1
    assert receipt["raw_source_payloads_exported"] is False
    assert receipt["complete_source_universe_reconciled"] is False
    assert receipt["independent_source_rights_approved"] is False
    assert receipt["independent_after_costs_proven"] is False
    assert receipt["all_market_history_verified"] is False
    assert receipt["customer_signal_publication_permitted"] is False
    assert hashlib.sha256(path.read_bytes()).hexdigest()==sha_before
    assert "NEVER_EXPORT" not in str(receipt)
    assert "SYNTHETIC_HIDDEN_SOURCE_PAYLOAD" not in str(receipt)


def test_valid_open_signal_with_no_exit_can_be_linked(tmp_path):
    _,_,pins=_fixture(tmp_path,open_only=True)
    x=check_source_projection_link(**pins)
    assert x["matched_projected_source_anchors"]==2
    assert x["complete_source_universe_reconciled"] is False


def test_wrong_sha_head_count_cohort_or_program_pin_fails_closed(tmp_path):
    _,_,pins=_fixture(tmp_path)
    for update in [
        {"expected_source_head_sha256":"0"*64},
        {"expected_source_ledger_records":5},
        {"expected_bundle_sha256":"0"*64},
        {"expected_outcome_population":3},
        {"expected_model_version":"AI-v1.2.1"},
        {"expected_cohort":"wrong"},
        {"expected_source_program_id":"market-expansion-1"},
        {"source_profile":"unknown"},
        {"expected_source_program_id":"crypto-expansion-1"},
    ]:
        with pytest.raises(SourceProjectionReconciliationError):
            check_source_projection_link(**{**pins,**update})


def test_source_hash_must_belong_to_correct_entity_and_terminal_event(tmp_path):
    _,raw,pins=_fixture(tmp_path)
    body=json.loads(raw)
    body["records"][0]["source_record_sha256"]=body["records"][1]["source_record_sha256"]
    changed=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    with pytest.raises(SourceProjectionReconciliationError):
        check_source_projection_link(**{
            **pins,"sanitized_bundle":changed,
            "expected_bundle_sha256":hashlib.sha256(changed).hexdigest(),
        })
    # A signed-looking bundle cannot reclassify a no-trade event as closed.
    body=json.loads(raw)
    body["records"][0]["source_record_sha256"]=body["records"][1]["source_record_sha256"]
    body["records"][1]["source_record_sha256"]="0"*64
    changed=json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    with pytest.raises(SourceProjectionReconciliationError):
        check_source_projection_link(**{
            **pins,"sanitized_bundle":changed,
            "expected_bundle_sha256":hashlib.sha256(changed).hexdigest(),
        })


def test_source_included_exit_prevents_false_open_signal_status(tmp_path):
    path,raw,pins=_fixture(tmp_path)
    # Locate the authentic SIGNAL row's hash; a fabricated "open" must fail
    # when the same immutable ledger already has an EXIT for this entity.
    import sqlite3
    with sqlite3.connect(f"file:{path}?mode=ro",uri=True) as conn:
        sig=conn.execute(
            "SELECT record_hash FROM ai_records WHERE record_type='SIGNAL'"
        ).fetchone()[0]
    manifest=json.loads(raw)
    manifest["records"][0].update({
        "state":"open","source_record_sha256":sig,
        "combined_net_r":None,"after_costs_verified":False,
        "cost_model_version":None,"exit_at_utc":None,
    })
    modified=json.dumps(manifest,sort_keys=True,separators=(",",":")).encode()
    with pytest.raises(SourceProjectionReconciliationError):
        check_source_projection_link(**{
            **pins,"sanitized_bundle":modified,
            "expected_bundle_sha256":hashlib.sha256(modified).hexdigest(),
        })


def test_source_changes_cannot_be_relabelled_with_original_external_head(tmp_path):
    path,_,pins=_fixture(tmp_path)
    import sqlite3
    with sqlite3.connect(path) as conn:
        conn.execute("DROP TRIGGER ai_records_no_update")
        conn.execute("UPDATE ai_records SET payload_json='{}' WHERE sequence=2")
    with pytest.raises(SourceProjectionReconciliationError):
        check_source_projection_link(**pins)
