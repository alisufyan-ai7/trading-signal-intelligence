"""Disposable independent frozen-file recheck fixtures (never owner source)."""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import pytest
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger

FILE=Path(__file__).resolve().parents[1]/"ops"/"handoffs"/"vowsig_frozen_source_recheck_inline_v0_1.py"
spec=importlib.util.spec_from_file_location("vowsig_independent_freeze_recheck",FILE)
tool=importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def fixture(tmp_path, orphan=False):
    base=tmp_path/"OriginalLedgerEvidence-synthetic"
    run=base/"freeze-synthetic"
    run.mkdir(parents=True)
    pins={}
    manifest_rows=[]
    crypto={}
    when=datetime(2026,11,5,3,tzinfo=timezone.utc)
    for name,(version,market,table,_,_,_) in tool.PINNED.items():
        original=tmp_path/(name+"-original")
        ledger=ForwardLedger(original) if table=="forward_records" else AILedger(original)
        kind="MISSED_SIGNAL" if table=="forward_records" else "ACTIVATION" if version=="AI-v1.3" else "SIGNAL"
        first=ledger.append(record_type=kind,entity_id="synthetic-"+market,
                            effective_at_utc=when,
                            payload={"secret":"ORIGINAL_PRIVATE_ROWS_NOT_EMITTED"})
        if orphan and name=="forward.sqlite":
            ledger.append(record_type="EXIT",entity_id="never-signaled",
                          effective_at_utc=when,payload={"secret":"NEVER_EMIT"})
        if version=="AI-v1.3":
            crypto[market]=first["record_hash"]
        with sqlite3.connect(original) as source, sqlite3.connect(run/name) as target:
            source.backup(target)
        with sqlite3.connect(run/name) as con:
            rows=con.execute("SELECT sequence,record_type,record_hash FROM "+
                             table+" ORDER BY sequence").fetchall()
        chain=hashlib.sha256()
        counts={}
        for seq,kind,head in rows:
            chain.update(f"{seq}:{head}\n".encode())
            counts[kind]=counts.get(kind,0)+1
        count=len(rows)
        head=rows[-1][2]
        sha=tool._digest(run/name)
        pins[name]=(version,market,table,count,sha,head)
        manifest_rows.append({
            "model_version":version,"market":market,"private_file":name,
            "source_path":"data/"+name,"rows":count,"terminal_sequence":count,
            "frozen_file_sha256":sha,"terminal_record_hash":head,
            "event_counts":counts,"sequence_chain_sha256":chain.hexdigest(),
            "self_consistent_full_chain":True,"prior_observed_prefix_match":True,
        })
    manifest={
        "schema_version":1,
        "status":"PRIVATE_FROZEN_COPIES_SELF_VERIFIED_EXTERNAL_REVIEW_REQUIRED",
        "synchronized_all_markets_at_one_instant":False,
        "count":12,"ledgers":manifest_rows
    }
    (run/"manifest.preliminary.json").write_text(
        json.dumps(manifest,sort_keys=True,separators=(",",":")))
    return run,pins,tool._digest(run/"manifest.preliminary.json"),crypto


def test_matches_owner_exported_manifest_and_private_files(tmp_path):
    run,pins,sha,crypto=fixture(tmp_path)
    result=tool.recheck(run,pins=pins,manifest_sha=sha,crypto_hashes=crypto)
    assert result["sum_source_event_rows"]==12
    assert result["file_sha256_against_owner_record"]==12
    assert result["full_canonical_hash_chains_checked"]==12
    assert result["source_entity_lifecycle_holds"]==0
    assert result["crypto_k5_epoch_provenance_verified"] is False
    assert "ORIGINAL_PRIVATE_ROWS_NOT_EMITTED" not in str(result)


def test_wrong_external_pin_and_mutated_frozen_source_hold(tmp_path):
    run,pins,sha,crypto=fixture(tmp_path)
    with pytest.raises(tool.FrozenRecheckHold):
        tool.recheck(run,pins=pins,manifest_sha="f"*64,crypto_hashes=crypto)
    (run/"ai_v1_1_xauusd.sqlite").open("ab").write(b"tampered")
    with pytest.raises(tool.FrozenRecheckHold):
        tool.recheck(run,pins=pins,manifest_sha=sha,crypto_hashes=crypto)


def test_orphan_s02_exit_is_reported_as_lifecycle_hold_without_row_export(tmp_path):
    run,pins,sha,crypto=fixture(tmp_path,orphan=True)
    result=tool.recheck(run,pins=pins,manifest_sha=sha,crypto_hashes=crypto)
    assert result["source_entity_lifecycle_holds"]==1
    observed=next(x for x in result["ledgers"] if x["model_version"]=="S02-v0.1" and x["market"]=="XAUUSD")
    assert observed["orphan_exit"]==1
    assert observed["lifecycle_status"]=="HOLD_REVIEW"
    assert "never-signaled" not in str(result)


def test_duplicate_manifest_row_and_unapproved_kind_hold(tmp_path):
    run,pins,sha,crypto=fixture(tmp_path)
    manifest=run/"manifest.preliminary.json"
    content=json.loads(manifest.read_text())
    content["ledgers"][1]["private_file"]=content["ledgers"][0]["private_file"]
    manifest.write_text(json.dumps(content))
    newsha=tool._digest(manifest)
    with pytest.raises(tool.FrozenRecheckHold):
        tool.recheck(run,pins=pins,manifest_sha=newsha,crypto_hashes=crypto)
