"""Synthetic twelve-ledger capture: full chain, prefix and privacy acceptance."""
from __future__ import annotations

import hashlib
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
import stat

import pytest

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.forward.ledger import ForwardLedger
from trading_signal_intelligence.product.accounts.source_inventory import SOURCES
from trading_signal_intelligence.product.accounts import private_source_freeze as freeze


def _setup(tmp_path,monkeypatch):
    repo=tmp_path/"trading-signal-intelligence"
    (repo/"data").mkdir(parents=True)
    (repo/"research"/"forward").mkdir(parents=True)
    private=tmp_path/"private"
    private.mkdir(mode=0o700)
    when=datetime(2026,11,5,2,tzinfo=timezone.utc)
    old={}
    anchor={"public_signal_exposure_enabled":False,
            "broker_execution_enabled":False,"markets":{}}
    for spec in SOURCES:
        path=repo/spec.relative_path
        ledger=ForwardLedger(path) if spec.program=="s02-forward" else AILedger(path)
        kind="MISSED_SIGNAL" if spec.program=="s02-forward" else "NO_TRADE"
        if spec.program=="crypto-expansion-1":
            kind="ACTIVATION"
        row=ledger.append(record_type=kind,entity_id="synthetic",
                          effective_at_utc=when,
                          payload={"private":"SYNTHETIC_SECRET_NEVER_EXPORT"})
        old[spec.relative_path]=(1,row["record_hash"])
        if spec.program=="crypto-expansion-1":
            anchor["markets"][spec.symbol]={
                "record_hash":row["record_hash"],
                "payload":{"private":"SYNTHETIC_SECRET_NEVER_EXPORT"}
            }
    (repo/freeze.CRYPTO_ANCHOR_PATH).write_text(
        json.dumps(anchor),encoding="utf-8"
    )
    monkeypatch.setattr(freeze,"OBSERVED_PREFIXES",old)
    return repo,private


def test_twelve_consistent_private_copies_with_prefix_chain_hash(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    originals={s.relative_path:hashlib.sha256(
        (repo/s.relative_path).read_bytes()).hexdigest() for s in SOURCES}
    result=freeze.capture_private_frozen_sources(repo,private)
    assert result["copy_count"]==12
    assert result["synchronized_twelve_market_point_in_time"] is False
    assert result["independent_external_source_pins_verified"] is False
    assert result["complete_historical_after_cost_performance_verified"] is False
    assert result["crypto_k5_epoch_provenance_verified"] is False
    assert result["raw_source_payloads_in_private_copies"] is True
    assert "SYNTHETIC_SECRET_NEVER_EXPORT" not in str(result)
    run=private/result["run_id"]
    manifest=run/"manifest.preliminary.json"
    assert hashlib.sha256(manifest.read_bytes()).hexdigest()==result["manifest_sha256"]
    for row in result["rows"]:
        f=run/row["private_copy_name"]
        assert f.is_file()
        assert hashlib.sha256(f.read_bytes()).hexdigest()==row["frozen_file_sha256"]
        assert row["prior_observation_prefix_match"] is True
        assert row["full_chain_self_consistent"] is True
        assert row["rows"]==1
    assert {s.relative_path:hashlib.sha256(
        (repo/s.relative_path).read_bytes()).hexdigest()
        for s in SOURCES}==originals


def test_source_prefix_changed_fails_closed_no_manifest(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    wrong=dict(freeze.OBSERVED_PREFIXES)
    wrong["data/ai_v1_1_xauusd.sqlite"]=(1,"f"*64)
    monkeypatch.setattr(freeze,"OBSERVED_PREFIXES",wrong)
    with pytest.raises(freeze.PrivateSourceFreezeError,match="INCOMPLETE"):
        freeze.capture_private_frozen_sources(repo,private)
    assert not list(private.glob("*/manifest.preliminary.json"))


def test_refuses_destination_inside_repo_and_missing_original(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    with pytest.raises(freeze.PrivateSourceFreezeError):
        freeze.capture_private_frozen_sources(repo,repo/"data")
    (repo/"data"/"ai_v1_1_xauusd.sqlite").unlink()
    with pytest.raises(freeze.PrivateSourceFreezeError):
        freeze.capture_private_frozen_sources(repo,private)
    assert list(private.iterdir())==[]


def test_crypto_anchor_mismatch_holds_private_manifest(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    anchor=repo/freeze.CRYPTO_ANCHOR_PATH
    data=json.loads(anchor.read_text())
    data["markets"]["ETHUSDT"]["record_hash"]="0"*64
    anchor.write_text(json.dumps(data))
    with pytest.raises(freeze.PrivateSourceFreezeError,match="INCOMPLETE"):
        freeze.capture_private_frozen_sources(repo,private)
    assert not list(private.glob("*/manifest.preliminary.json"))


def test_unrecognized_s02_event_rejected_without_export(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    path=repo/"data"/"forward.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("UPDATE forward_records SET record_type=record_type") if False else None
        db.execute("DROP TRIGGER forward_records_no_update")
        db.execute("UPDATE forward_records SET record_type='UNKNOWN_TYPE' WHERE sequence=1")
    with pytest.raises(freeze.PrivateSourceFreezeError):
        freeze.capture_private_frozen_sources(repo,private)
    assert not list(private.glob("*/manifest.preliminary.json"))


def test_separate_manifest_pin_recovers_same_frozen_set(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    snapshot=freeze.capture_private_frozen_sources(repo,private)
    run=private/snapshot["run_id"]
    verdict=freeze.verify_private_frozen_set(
        repo,run,externally_recorded_manifest_sha256=snapshot["manifest_sha256"])
    assert verdict["copy_count"]==12
    assert verdict["total_event_rows"]==12
    assert verdict["full_history_costs_rights_and_performance_verified"] is False
    assert verdict["independently_reviewed_manifest_pin_proven"] is False


def test_frozen_manifest_rejects_wrong_pin_and_modified_database(tmp_path,monkeypatch):
    repo,private=_setup(tmp_path,monkeypatch)
    snapshot=freeze.capture_private_frozen_sources(repo,private)
    run=private/snapshot["run_id"]
    with pytest.raises(freeze.PrivateSourceFreezeError):
        freeze.verify_private_frozen_set(repo,run,externally_recorded_manifest_sha256="f"*64)
    frozen=run/"ai_v1_1_xauusd.sqlite"
    frozen.chmod(0o600)
    with frozen.open("ab") as f:
        f.write(b"tampered")
    with pytest.raises(freeze.PrivateSourceFreezeError):
        freeze.verify_private_frozen_set(
            repo,run,externally_recorded_manifest_sha256=snapshot["manifest_sha256"])
