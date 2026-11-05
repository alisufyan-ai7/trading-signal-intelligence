"""Synthetic, fully isolated frozen AI-v1.3 epoch evidence tests."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
from pathlib import Path
import pytest

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.product.accounts.private_crypto_epoch_audit import (
    FrozenCryptoEpochAuditError,audit_frozen_crypto_epoch,
)

UTC=timezone.utc
ACT=datetime(2026,10,9,19,55,tzinfo=UTC)
M="BTCUSDT"

def close(h):
    return datetime(2026,10,9,h,0,tzinfo=UTC)

def ts(dt):
    return dt.isoformat().replace("+00:00","Z")

def make(tmp_path):
    f=tmp_path/"private.sqlite"
    ledger=AILedger(f)
    ledger.append(record_type="ACTIVATION",entity_id="activation",effective_at_utc=ACT,
                  recorded_at_utc=ACT,payload={"synthetic":True})
    return f,ledger

def add(ledger,kind,dt,*,origin=None,guard=False,stage=None,reason=None):
    payload={
        "runtime_version":"AI-v1.3","source_symbol":M,
        "source_bar_close_utc":ts(dt),"public_signal_exposure_enabled":False,
        "broker_execution_enabled":False,
    }
    if kind=="INFERENCE":
        payload["feature_snapshot"]={"source_bar_close_utc":ts(dt)}
        payload["guard_publishable"]=guard
    if origin is not None:
        payload["originating_inference_record_hash"]=origin
    if stage is not None:
        payload["stage"]=stage
    if reason is not None:
        payload["reason"]=reason
    return ledger.append(record_type=kind,entity_id="AI-v1.3:"+M+":"+ts(dt),
                         effective_at_utc=dt,recorded_at_utc=dt+timedelta(minutes=2),
                         payload=payload)

def test_exact_paired_inference_error_and_miss_are_distinct(tmp_path):
    file,ledger=make(tmp_path)
    first=add(ledger,"INFERENCE",close(20),guard=False)
    add(ledger,"REJECTED_INFERENCE",close(20),origin=first["record_hash"])
    add(ledger,"ERROR",close(21),stage="provider_inference")
    add(ledger,"MISSED_INFERENCE",close(22),reason="next_h1_open_unavailable")
    evidence=audit_frozen_crypto_epoch(file,symbol=M,activated_at_utc=ts(ACT))
    assert evidence["status"]=="FROZEN_CRYPTO_INTERNAL_EPOCH_CONSISTENT_NOT_K5_CERTIFIED"
    assert evidence["matched_inference_outcomes"]==1
    assert evidence["error_stage_counts"]=={"provider_inference":1}
    assert evidence["missed_reason_counts"]=={"next_h1_open_unavailable":1}
    assert evidence["unobserved_internal_h1_closes"]==0
    assert evidence["complete_k5_natural_epoch_provenance_verified"] is False

def test_unobserved_internal_hour_is_a_coverage_hold(tmp_path):
    file,ledger=make(tmp_path)
    add(ledger,"ERROR",close(20),stage="provider_inference")
    add(ledger,"ERROR",close(22),stage="provider_inference")
    evidence=audit_frozen_crypto_epoch(file,symbol=M,activated_at_utc=ts(ACT))
    assert evidence["status"]=="FROZEN_CRYPTO_EPOCH_HOLD_SOURCE_COVERAGE_REVIEW"
    assert evidence["unobserved_internal_h1_closes"]==1

def test_invalid_inference_to_terminal_link_is_hold(tmp_path):
    file,ledger=make(tmp_path)
    add(ledger,"INFERENCE",close(20),guard=True)
    add(ledger,"SIGNAL",close(20),origin="f"*64)
    evidence=audit_frozen_crypto_epoch(file,symbol=M,activated_at_utc=ts(ACT))
    assert evidence["unmatched_inference_terminal_links"]==1
    assert evidence["status"]=="FROZEN_CRYPTO_EPOCH_HOLD_SOURCE_COVERAGE_REVIEW"

def test_wrong_market_or_non_hour_epoch_denied(tmp_path):
    file,ledger=make(tmp_path)
    add(ledger,"ERROR",close(20)+timedelta(minutes=5))
    with pytest.raises(FrozenCryptoEpochAuditError):
        audit_frozen_crypto_epoch(file,symbol=M,activated_at_utc=ts(ACT))
    with pytest.raises(FrozenCryptoEpochAuditError):
        audit_frozen_crypto_epoch(file,symbol="UNLISTED",activated_at_utc=ts(ACT))

def test_postactivation_cycles_never_promote_profit(tmp_path):
    file,ledger=make(tmp_path)
    first=add(ledger,"INFERENCE",close(20),guard=True)
    add(ledger,"SIGNAL",close(20),origin=first["record_hash"])
    evidence=audit_frozen_crypto_epoch(file,symbol=M,activated_at_utc=ts(ACT))
    assert evidence["matched_inference_outcomes"]==1
    assert evidence["after_cost_returns_verified"] is False
    assert evidence["scheduler_receipts_verified"] is False
