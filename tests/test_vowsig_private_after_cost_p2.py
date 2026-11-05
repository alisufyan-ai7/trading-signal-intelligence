"""Disposable cost/R arithmetic parity, mutation and fail-closed tests."""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import pytest
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.product.accounts.private_after_cost_audit import (
    FrozenCostAuditHold,audit_frozen_after_costs,
)

UTC=timezone.utc
NOW=datetime(2026,11,5,tzinfo=UTC)

def sample(tmp_path,crypto=False,partial=True,tamper=None):
    f=tmp_path/"private-ai.sqlite"
    ledger=AILedger(f)
    sig={
        "source_symbol":"BTCUSDT" if crypto else "XAUUSD",
        "direction":"BUY","entry":100.0,"risk_price":10.0,
        "tp1_position_fraction":0.5,
        "total_cost_price":0.2,
    }
    if crypto:
        sig.update({
            "cost_policy_version":"AI-v1.3-crypto-cost-v0.1",
            "round_trip_fee_price":0.2,
            "spread_crossing_price":0.0,
            "slippage_buffer_price":0.0,
            "reference_midpoint":100.0,
            "estimated_cost_r":0.02,
        })
    else:
        sig.update({"spread_price":0.1,"cost_multiplier":2.0})
    signal=ledger.append(record_type="SIGNAL",entity_id="synthetic",
                         effective_at_utc=NOW,payload=sig)
    ph=None
    if partial:
        pp={
            "source_symbol":sig["source_symbol"],
            "direction":"BUY","exit_price":110.0,"fraction":0.5,
            "gross_contribution_r":0.5,
            "cost_contribution_r":0.01,
            "net_contribution_r":0.49,
            "signal_record_hash":signal["record_hash"],
        }
        part=ledger.append(record_type="PARTIAL_EXIT",entity_id="synthetic",
                           effective_at_utc=NOW,payload=pp)
        ph=part["record_hash"]
    ep={
        "source_symbol":sig["source_symbol"],
        "direction":"BUY","exit_price":90.0,
        "remaining_fraction":0.5 if partial else 1.0,
        "gross_contribution_r":-0.5 if partial else -1.0,
        "cost_contribution_r":0.01 if partial else 0.02,
        "net_contribution_r":-0.51 if partial else -1.02,
        "total_combined_signal_net_r":-0.02 if partial else -1.02,
        "signal_record_hash":signal["record_hash"],
        "partial_exit_record_hash":ph,
    }
    if tamper=="combined":
        ep["total_combined_signal_net_r"]=4.0
    if tamper=="fraction":
        ep["remaining_fraction"]=1.0
    last=ledger.append(record_type="EXIT",entity_id="synthetic",
                       effective_at_utc=NOW,payload=ep)
    pin=hashlib.sha256(f.read_bytes()).hexdigest()
    return f,pin,last["record_hash"]

@pytest.mark.parametrize("crypto,partial",[(False,False),(False,True),(True,True)])
def test_actual_original_signal_exit_cost_math_is_recomputed(tmp_path,crypto,partial):
    file,sha,head=sample(tmp_path,crypto=crypto,partial=partial)
    result=audit_frozen_after_costs(file,
        model_version="AI-v1.3" if crypto else "AI-v1.1",
        market="BTCUSDT" if crypto else "XAUUSD",
        expected_frozen_file_sha256=sha,expected_terminal_record_hash=head)
    assert result["closed_signal_count"]==1
    assert result["partial_exit_event_count"]==int(partial)
    assert result["closed_after_cost_arithmetic_checked"]==1
    assert result["historical_profitability_certified"] is False
    assert result["actual_broker_or_provider_costs_verified"] is False

@pytest.mark.parametrize("fault",["combined","fraction"])
def test_bad_net_return_or_overallocated_position_holds(tmp_path,fault):
    file,sha,head=sample(tmp_path,tamper=fault)
    with pytest.raises(FrozenCostAuditHold):
        audit_frozen_after_costs(file,model_version="AI-v1.1",market="XAUUSD",
            expected_frozen_file_sha256=sha,expected_terminal_record_hash=head)

def test_changed_evidence_and_wrong_market_fail_closed(tmp_path):
    file,sha,head=sample(tmp_path)
    with pytest.raises(FrozenCostAuditHold):
        audit_frozen_after_costs(file,model_version="AI-v1.1",market="EURUSD",
            expected_frozen_file_sha256=sha,expected_terminal_record_hash=head)
    with file.open("ab") as f:
        f.write(b"changed")
    with pytest.raises(FrozenCostAuditHold):
        audit_frozen_after_costs(file,model_version="AI-v1.1",market="XAUUSD",
            expected_frozen_file_sha256=sha,expected_terminal_record_hash=head)
