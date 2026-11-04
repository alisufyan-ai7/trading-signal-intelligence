"""Private original-ledger audit tests; synthetic append-only SQLite only."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from pathlib import Path
import sqlite3

import pytest

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger
from trading_signal_intelligence.product.accounts.source_ledger_audit import (
    SourceLedgerAuditError,audit_pinned_source,
)


def _build(tmp_path: Path, *, profile: str):
    file = tmp_path / (profile+".sqlite")
    ledger = AILedger(file) if profile == "ai_v1" else ForwardLedger(file)
    when = datetime(2026, 11, 4, 12, 0, tzinfo=timezone.utc)
    for kind, entity in (("ACTIVATION", "activation"), ("SIGNAL", "trade-01")):
        ledger.append(
            record_type=kind,
            entity_id=entity,
            effective_at_utc=when,
            recorded_at_utc=when,
            payload={"source_symbol":"XAUUSD","secret":"SYNTHETIC_NEVER_EXPORTED"},
        )
    head = ledger.head_hash()
    assert isinstance(head,str) and len(head)==64
    return file,head


@pytest.mark.parametrize("profile",("ai_v1","s02_forward"))
def test_read_only_pinned_hash_chain_for_core_and_s02(tmp_path,profile):
    file,head=_build(tmp_path,profile=profile)
    digest_before=hashlib.sha256(file.read_bytes()).hexdigest()
    evidence=audit_pinned_source(
        file, profile=profile,expected_head_sha256=head,expected_records=2,
    )
    assert evidence["status"]=="PINNED_CHAIN_VERIFIED"
    assert evidence["records"]==2 and evidence["head_sha256"]==head
    assert evidence["record_type_counts"]=={"ACTIVATION":1,"SIGNAL":1}
    assert evidence["source_rows_exported"] is False
    assert evidence["complete_historical_performance_verified"] is False
    assert evidence["source_costs_verified"] is False
    assert evidence["source_rights_verified"] is False
    assert "SYNTHETIC_NEVER_EXPORTED" not in str(evidence)
    assert hashlib.sha256(file.read_bytes()).hexdigest()==digest_before


def test_missing_wrong_count_or_unpinned_head_never_marks_verified(tmp_path):
    file,head=_build(tmp_path,profile="ai_v1")
    for n,h in ((1,head),(3,head),(2,"f"*64)):
        with pytest.raises(SourceLedgerAuditError):
            audit_pinned_source(file,profile="ai_v1",
                                expected_head_sha256=h,expected_records=n)
    with pytest.raises(SourceLedgerAuditError):
        audit_pinned_source(file,profile="unreviewed",
                            expected_head_sha256=head,expected_records=2)
    with pytest.raises(SourceLedgerAuditError):
        audit_pinned_source(file,profile="ai_v1",
                            expected_head_sha256="bad",expected_records=2)


def test_tampered_source_record_fails_external_chain_proof(tmp_path):
    file,head=_build(tmp_path,profile="ai_v1")
    with sqlite3.connect(file) as conn:
        conn.execute("DROP TRIGGER ai_records_no_update")
        conn.execute(
            "UPDATE ai_records SET payload_json=? WHERE sequence=1",
            ('{"fabricated":true}',),
        )
    with pytest.raises(SourceLedgerAuditError,match="hash mismatch"):
        audit_pinned_source(file,profile="ai_v1",
                            expected_head_sha256=head,expected_records=2)


def test_removed_sequence_and_symlink_refused_without_mutation(tmp_path):
    file,head=_build(tmp_path,profile="s02_forward")
    with sqlite3.connect(file) as conn:
        conn.execute("DROP TRIGGER forward_records_no_delete")
        conn.execute("DELETE FROM forward_records WHERE sequence=1")
    with pytest.raises(SourceLedgerAuditError):
        audit_pinned_source(file,profile="s02_forward",
                            expected_head_sha256=head,expected_records=2)
    symlink=tmp_path/"redirect.sqlite"
    symlink.symlink_to(file)
    with pytest.raises(SourceLedgerAuditError,match="non-symlink"):
        audit_pinned_source(symlink,profile="s02_forward",
                            expected_head_sha256=head,expected_records=2)
    missing=tmp_path/"absent.sqlite"
    with pytest.raises(SourceLedgerAuditError):
        audit_pinned_source(missing,profile="s02_forward",
                            expected_head_sha256=head,expected_records=2)
    assert not missing.exists()
