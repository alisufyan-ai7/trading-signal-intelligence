"""Private frozen lifecycle tests: synthetic entity sequences, no payload export."""
from __future__ import annotations

from datetime import datetime,timezone
from pathlib import Path
import pytest

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger
from trading_signal_intelligence.product.accounts.private_lifecycle_audit import (
    frozen_lifecycle_counts,FrozenLifecycleError,
)


def make_ledger(tmp_path, s02=False):
    path=tmp_path/"source.sqlite"
    ledger=ForwardLedger(path) if s02 else AILedger(path)
    when=datetime(2026,11,5,2,tzinfo=timezone.utc)
    def append(kind,entity):
        ledger.append(record_type=kind,entity_id=entity,effective_at_utc=when,
                      payload={"private":"UNPUBLISHED_SHADOW_OUTCOME"})
    return path,append


@pytest.mark.parametrize("s02",[True,False])
def test_closed_open_and_research_miss_remain_separate(tmp_path,s02):
    path,append=make_ledger(tmp_path,s02)
    append("ACTIVATION","activation")
    append("SIGNAL","closed")
    if not s02:
        append("PARTIAL_EXIT","closed")
    append("EXIT","closed")
    append("SIGNAL","open")
    append("MISSED_SIGNAL" if s02 else "MISSED_INFERENCE","missed")
    receipt=frozen_lifecycle_counts(path,profile="s02_forward" if s02 else "ai_v1")
    assert receipt["status"]=="SOURCE_EVENT_LIFECYCLE_SELF_CONSISTENT_NOT_FINANCIALLY_VERIFIED"
    assert receipt["signal_entities"]==2
    assert receipt["exited_signal_entities"]==1
    assert receipt["open_signal_entities"]==1
    assert receipt["partially_exited_signal_entities"]==(0 if s02 else 1)
    assert receipt["cost_model_arithmetic_verified"] is False
    assert "UNPUBLISHED_SHADOW_OUTCOME" not in str(receipt)


def test_orphan_exit_and_partial_are_held_not_miscounted_as_profit(tmp_path):
    path,append=make_ledger(tmp_path)
    append("EXIT","orphan-identity")
    append("PARTIAL_EXIT","not-a-signal")
    receipt=frozen_lifecycle_counts(path,profile="ai_v1")
    assert receipt["status"]=="SOURCE_EVENT_LIFECYCLE_HOLD_REVIEW_REQUIRED"
    assert receipt["orphan_exit_entities"]==1
    assert receipt["orphan_partial_exit_entities"]==1
    assert receipt["trading_profits_verified"] is False


def test_out_of_order_exit_and_partial_are_held(tmp_path):
    path,append=make_ledger(tmp_path)
    append("EXIT","foo")
    append("PARTIAL_EXIT","foo")
    append("SIGNAL","foo")
    receipt=frozen_lifecycle_counts(path,profile="ai_v1")
    assert receipt["status"]=="SOURCE_EVENT_LIFECYCLE_HOLD_REVIEW_REQUIRED"
    assert receipt["exit_before_signal_entities"]==1
    assert receipt["partial_before_signal_entities"]==1
    assert receipt["partial_after_exit_entities"]==1


def test_absent_and_bad_profile_never_generate_metrics(tmp_path):
    with pytest.raises(FrozenLifecycleError):
        frozen_lifecycle_counts(tmp_path/"absent.sqlite",profile="ai_v1")
    with pytest.raises(FrozenLifecycleError):
        frozen_lifecycle_counts(tmp_path/"absent.sqlite",profile="guess")
