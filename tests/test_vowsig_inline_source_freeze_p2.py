"""Test exact VPS inline operator with disposable synthetic databases."""
from __future__ import annotations
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
from datetime import datetime,timezone
import pytest
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "vowsig_inline_capture",ROOT/"ops"/"handoffs"/"vowsig_original_source_freeze_inline_v0_1.py")
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def make_source(tmp_path):
    root=tmp_path/"trading-signal-intelligence"
    (root/"data").mkdir(parents=True)
    (root/"research"/"forward").mkdir(parents=True)
    private=tmp_path/"private"
    private.mkdir(mode=0o700)
    pins=[]
    markets={}
    when=datetime(2026,11,5,2,tzinfo=timezone.utc)
    for version,market,name,table,_,_ in module.FILES:
        ledger=ForwardLedger(root/"data"/name) if version=="S02-v0.1" else AILedger(root/"data"/name)
        kind=("MISSED_SIGNAL" if version=="S02-v0.1" else
              "ACTIVATION" if version=="AI-v1.3" else "NO_TRADE")
        row=ledger.append(record_type=kind,entity_id="test-"+market,
                          effective_at_utc=when,payload={"secret":"NEVER_EXPORT"})
        pins.append((version,market,name,table,1,row["record_hash"]))
        if version=="AI-v1.3":
            markets[market]={"record_hash":row["record_hash"],
                             "payload":{"secret":"NEVER_EXPORT"}}
    (root/module.ANCHOR).write_text(json.dumps({
        "public_signal_exposure_enabled":False,
        "broker_execution_enabled":False,"markets":markets
    }),encoding="utf-8")
    return root,private,tuple(pins)


def test_online_backup_twelve_stable_files_and_no_payload_leak(tmp_path):
    root,private,pins=make_source(tmp_path)
    original={name:hashlib.sha256((root/"data"/name).read_bytes()).hexdigest()
              for _,_,name,_,_,_ in pins}
    outcome=module.capture(root,private,rows=pins)
    assert outcome["independent_historical_profit_verified"] is False
    assert len(outcome["ledgers"])==12
    assert "NEVER_EXPORT" not in str(outcome)
    run=Path(outcome["run_dir"])
    assert hashlib.sha256((run/"manifest.preliminary.json").read_bytes()).hexdigest()==outcome["manifest_sha256"]
    assert all(x["self_consistent_full_chain"] for x in outcome["ledgers"])
    assert all(x["event_counts"]==({"MISSED_SIGNAL":1} if x["model_version"]=="S02-v0.1"
                          else {"ACTIVATION":1} if x["model_version"]=="AI-v1.3"
                          else {"NO_TRADE":1}) for x in outcome["ledgers"])
    assert {name:hashlib.sha256((root/"data"/name).read_bytes()).hexdigest()
            for _,_,name,_,_,_ in pins}==original


def test_prior_pin_mismatch_never_writes_successful_manifest(tmp_path):
    root,private,pins=make_source(tmp_path)
    changed=list(pins)
    first=list(changed[0])
    first[-1]="f"*64
    changed[0]=tuple(first)
    with pytest.raises(ValueError):
        module.capture(root,private,rows=tuple(changed))
    assert not list(private.glob("*/manifest.preliminary.json"))


def test_refuses_outside_destination(tmp_path):
    root,private,pins=make_source(tmp_path)
    with pytest.raises(ValueError):
        module.capture(root,root/"data",rows=pins)
    assert not list(private.iterdir())
