"""Read-only source inventory tests. All SQLite files are disposable synthetic data."""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
import sqlite3

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger
from trading_signal_intelligence.product.accounts.source_inventory import (
    SOURCES,inventory_expected_sources,
)


def test_twelve_authoritative_source_paths_including_crypto_and_s02():
    assert len(SOURCES)==12
    assert len({x.relative_path for x in SOURCES})==12
    assert {x.symbol for x in SOURCES if x.model_version=="AI-v1.3"}=={
        "BTCUSDT","ETHUSDT","SOLUSDT",
    }
    assert all(x.relative_path.startswith("data/") for x in SOURCES)
    assert all(x.table in ("ai_records","forward_records") for x in SOURCES)


def test_inventory_is_pinned_to_real_repo_ledger_path_contracts():
    import ast
    import json
    root=Path(__file__).resolve().parents[1]
    files=(
        ("AI-v1.1","ai_v1/shadow_runtime_v1_1.py"),
        ("AI-v1.2.1","ai_v1/shadow_runtime_v1_2_1.py"),
        ("AI-v1.3","ai_v1/crypto_activation_v1_3.py"),
    )
    for version,relative in files:
        path=root/"src"/"trading_signal_intelligence"/relative
        module=ast.parse(path.read_text(encoding="utf-8"))
        assignments=[x for x in module.body
                     if isinstance(x,ast.Assign) and
                     any(isinstance(t,ast.Name) and t.id=="DATABASE_PATHS"
                         for t in x.targets)]
        assert len(assignments)==1
        expected=ast.literal_eval(assignments[0].value)
        actual={s.symbol:s.relative_path for s in SOURCES if s.model_version==version}
        assert actual==expected
    launch=json.loads((root/"config"/"launch_universe.json").read_text(encoding="utf-8"))
    expected={m["source_symbol"]:m["forward_database"]
              for m in launch["live_signal_markets"]}
    actual={s.symbol:s.relative_path for s in SOURCES if s.program=="s02-forward"}
    assert actual==expected


def test_inventory_only_reads_existing_original_source_database(tmp_path):
    data=tmp_path/"data"
    data.mkdir()
    root=tmp_path
    ai=data/"ai_v1_1_xauusd.sqlite"
    s02=data/"forward.sqlite"
    now=datetime(2026,11,4,18,tzinfo=timezone.utc)
    ledger=AILedger(ai)
    r=ledger.append(record_type="NO_TRADE",entity_id="synthetic-abstain",
                    effective_at_utc=now,
                    payload={"secret":"SHOULD_NOT_LEAK"})
    forward=ForwardLedger(s02)
    forward.append(record_type="ACTIVATION",entity_id="synthetic-activation",
                   effective_at_utc=now,
                   payload={"entry":"ALSO_SHOULD_NOT_LEAK"})
    before={
        "ai":hashlib.sha256(ai.read_bytes()).hexdigest(),
        "s02":hashlib.sha256(s02.read_bytes()).hexdigest(),
    }
    result=inventory_expected_sources(root)
    assert result["expected_ledger_files"]==12
    assert result["observed_nonempty_ledger_files"]==2
    assert result["missing_or_unreadable_ledger_files"]==10
    assert result["all_original_sources_independently_verified"] is False
    assert result["crypto_k5_provenance_verified"] is False
    assert result["historical_net_r_verified"] is False
    assert result["contains_raw_source_records"] is False
    rows={x["relative_path"]:x for x in result["ledgers"]}
    assert rows["data/ai_v1_1_xauusd.sqlite"]["status"]=="OBSERVED_UNFROZEN"
    assert rows["data/ai_v1_1_xauusd.sqlite"]["record_count"]==1
    assert rows["data/ai_v1_1_xauusd.sqlite"]["last_record_hash"]==r["record_hash"]
    assert rows["data/ai_v1_1_xauusd.sqlite"]["event_counts"]["NO_TRADE"]==1
    assert rows["data/forward.sqlite"]["record_count"]==1
    assert rows["data/ai_v1_3_btcusdt.sqlite"]["status"]=="MISSING"
    assert "SHOULD_NOT_LEAK" not in str(result)
    assert "ALSO_SHOULD_NOT_LEAK" not in str(result)
    assert hashlib.sha256(ai.read_bytes()).hexdigest()==before["ai"]
    assert hashlib.sha256(s02.read_bytes()).hexdigest()==before["s02"]


def test_refuses_symlink_and_invalid_ledger_head(tmp_path):
    data=tmp_path/"data"
    data.mkdir()
    outside=tmp_path/"outside.sqlite"
    AILedger(outside)
    link=data/"ai_v1_1_xauusd.sqlite"
    link.symlink_to(outside)
    r=inventory_expected_sources(tmp_path)
    rows={x["relative_path"]:x for x in r["ledgers"]}
    assert rows["data/ai_v1_1_xauusd.sqlite"]["status"]=="SYMLINK_REFUSED"
    link.unlink()
    ledger=AILedger(link)
    now=datetime(2026,11,4,18,tzinfo=timezone.utc)
    ledger.append(record_type="ERROR",entity_id="failure",
                  effective_at_utc=now,payload={"synthetic":True})
    with sqlite3.connect(link) as conn:
        conn.execute("DROP TRIGGER ai_records_no_update")
        conn.execute("UPDATE ai_records SET record_hash='corrupt' WHERE sequence=1")
    s=inventory_expected_sources(tmp_path)
    rows={x["relative_path"]:x for x in s["ledgers"]}
    assert rows["data/ai_v1_1_xauusd.sqlite"]["status"]=="READ_ONLY_SOURCE_UNAVAILABLE"


def test_missing_originals_not_created_and_no_directory_glob(tmp_path):
    data=tmp_path/"data"
    data.mkdir()
    arbitrary=data/"unrelated-customer.sqlite"
    arbitrary.write_bytes(b"FAKE CUSTOMER DB")
    inventory=inventory_expected_sources(tmp_path)
    assert inventory["observed_nonempty_ledger_files"]==0
    assert inventory["missing_or_unreadable_ledger_files"]==12
    assert arbitrary.read_bytes()==b"FAKE CUSTOMER DB"
    assert not (data/"ai_v1_1_xauusd.sqlite").exists()
    assert "unrelated-customer.sqlite" not in str(inventory)


def test_empty_ledger_does_not_count_as_missing_or_unreadable(tmp_path):
    data=tmp_path/"data"
    data.mkdir()
    AILedger(data/"ai_v1_1_xauusd.sqlite")
    result=inventory_expected_sources(tmp_path)
    assert result["observed_nonempty_ledger_files"]==0
    assert result["empty_ledger_files"]==1
    assert result["missing_or_unreadable_ledger_files"]==11
    assert result["other_event_type_rows"]==0
    row=next(x for x in result["ledgers"] if x["symbol"]=="XAUUSD" and x["model_version"]=="AI-v1.1")
    assert row["status"]=="EMPTY_LEDGER"
    assert row["record_count"]==0
    assert row["other_event_type_rows"]==0


def test_unrecognized_event_type_is_counted_without_leaking_name(tmp_path):
    data=tmp_path/"data"
    data.mkdir()
    path=data/"ai_v1_1_xauusd.sqlite"
    now=datetime(2026,11,4,18,tzinfo=timezone.utc)
    valid=AILedger(path).append(
        record_type="NO_TRADE",entity_id="synthetic-known",
        effective_at_utc=now,payload={"synthetic":True},
    )
    with sqlite3.connect(path) as conn:
        conn.execute(
            """INSERT INTO ai_records
               (record_id,record_type,entity_id,recorded_at_utc,
                effective_at_utc,payload_json,previous_hash,record_hash)
               VALUES (?,?,?,?,?,?,?,?)""",
            ("unexpected-row","SYNTHETIC_UNEXPECTED_KIND","synthetic-private",
             now.isoformat(),now.isoformat(),"{}",valid["record_hash"],"b"*64),
        )
    result=inventory_expected_sources(tmp_path)
    row=next(x for x in result["ledgers"] if x["symbol"]=="XAUUSD" and x["model_version"]=="AI-v1.1")
    assert result["observed_nonempty_ledger_files"]==1
    assert result["other_event_type_rows"]==1
    assert row["record_count"]==2
    assert row["event_counts"]["NO_TRADE"]==1
    assert row["other_event_type_rows"]==1
    assert "SYNTHETIC_UNEXPECTED_KIND" not in str(result)
    assert "synthetic-private" not in str(result)
