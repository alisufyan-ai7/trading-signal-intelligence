"""Synthetic-only source bridge and signed publisher-preview tests."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from trading_signal_intelligence.product.crypto_epoch_bridge_v0_1 import (
    EpochBridgeHeld, prepare_verified_epoch, signed_receipt, verify_receipt,
    attach_current_crypto_preview,
)
from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
    public_program_from_completed_epoch,
)
from test_crypto_completed_epoch_v0_1 import program

CLOSE = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
AT = CLOSE + timedelta(minutes=6)
LAST = CLOSE + timedelta(minutes=3)
NEXT = CLOSE + timedelta(hours=1, minutes=3)
KEY = b"fixture-only-cryptographic-key-not-a-secret-987"
MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def task():
    return {"TaskName": "VowSig AI-v1.3 Crypto Shadow Scan", "State": "Ready",
            "LastTaskResult": 0, "LastRunTime": LAST.isoformat(),
            "NextRunTime": NEXT.isoformat()}


def fixture():
    records, markets = {}, {}
    for sym in MARKETS:
        entity = f"AI-v1.3:{sym}:{CLOSE.isoformat().replace('+00:00', 'Z')}"
        rows = [{"record_type": "ACTIVATION", "entity_id": "activation",
                 "record_hash": hashlib.sha256((sym + 'activation').encode()).hexdigest()}]
        for kind in ("INFERENCE", "NO_TRADE"):
            rows.append({"record_type": kind, "entity_id": entity,
                         "record_hash": hashlib.sha256((sym + kind).encode()).hexdigest()})
        records[sym] = rows
        markets[sym] = {"ledger_verification": {"valid": True},
                        "activation_anchor_match": True,
                        "current_head_hash": rows[-1]["record_hash"],
                        "records": len(rows),
                        "counts_by_type": {"ACTIVATION": 1, "INFERENCE": 1, "NO_TRADE": 1},
                        "valid_inferences": 1, "completed_shadow_trades": 0,
                        "open_signals": 0, "latest_recorded_at_utc": AT.isoformat()}
    report = {"runtime_version": "AI-v1.3", "decision_protocol_version": "AI-v1.0",
              "program_id": "crypto-expansion-1", "mode": "READ_ONLY",
              "generated_at_utc": AT.isoformat(),
              "scheduler": {"healthy": True, "task_name": task()["TaskName"],
                            "state": "Ready", "last_task_result": 0,
                            "last_run_time": LAST.isoformat()},
              "health": dict.fromkeys(("healthy", "ledgers_valid",
                  "activation_anchor_matches_ledgers", "crypto_artifacts_valid",
                  "activation_anchor_upstream_valid", "scheduler_healthy",
                  "public_signal_exposure_disabled", "broker_execution_disabled"), True),
              "activation": {"public_signal_exposure_enabled": False,
                             "broker_execution_enabled": False,
                             "backfill_prior_missed": False},
              "markets": markets,
              "gates": {g: {"eligible": False,
                      "valid_inferences": {"current": 3, "required": n, "met": 3>=n},
                      "completed_shadow_trades": {"current": 0, "required": trades, "met": False},
                      "minimum_calendar_days": days,
                      "calendar_days_remaining": days,
                      "calendar_requirement_met": days==0}
                       for g, n, trades, days in (
                           ("C1", 100, 20, 0), ("C2", 500, 50, 60), ("C3", 1000, 100, 120))},
              "totals": {"valid_inferences": 3, "completed_shadow_trades": 0,
                         "open_shadow_signals": 0}}
    public = program()
    for m in public["markets"]:
        m["valid_inferences"] = 1
        m["no_trade"] = 1
        m["latest_recorded_at_utc"] = AT.isoformat()
    for gate, n, trades, days in (
        ("C1", 100, 20, 0), ("C2", 500, 50, 60), ("C3", 1000, 100, 120)
    ):
        target = next(g for g in public["gates"] if g["gate_id"] == gate)
        target["requirements"] = [
            {"metric": "valid_inferences", "current": 3, "required": n, "met": False},
            {"metric": "completed_shadow_trades", "current": 0,
             "required": trades, "met": False},
        ]
        if days:
            target["requirements"].append({"metric": "calendar_days",
                 "current": 0, "required": days, "met": False})
    public["totals"]["valid_inferences"] = 3
    public["totals"]["no_trade"] = 3
    return report, records, public, task(), task()


def produce(f):
    report, records, public, before, after = f
    return prepare_verified_epoch(
        report=report, private_records=records, public_program=public,
        task_before=before, task_after=after, cycle_close_utc=CLOSE.isoformat(),
        captured_at_utc=AT.isoformat(), verify_chain=lambda rows: {"valid": True})


def base():
    return {"generated_at_utc": AT.isoformat(),
            "validation_programs": [{"program_id": x} for x in (
                "core-ai-shadow", "market-expansion-1")],
            "markets": [{"canonical_symbol": "XAU/USD"}]}


def test_verified_k5_report_records_epoch_then_hmac_publication():
    raw = produce(fixture())
    doc = json.loads(raw)
    assert doc["cycle_close_utc"] == CLOSE.isoformat()
    assert '"activation":' not in raw.decode()
    assert all(x["record_hash"] not in raw.decode() for rows in fixture()[1].values() for x in rows)
    receipt = signed_receipt(raw, key=KEY)
    assert verify_receipt(receipt, key=KEY)["epoch_sha256"] == hashlib.sha256(raw).hexdigest()
    original = base()
    published = attach_current_crypto_preview(
        base_snapshot=original, raw_epoch=raw, raw_receipt=receipt,
        key=KEY, now=AT, last_accepted_cycle_close_utc=None,
        verify_public=lambda p: None)
    assert len(published["validation_programs"]) == 3
    assert published["validation_programs"][2]["status"] == "collecting"
    assert published["validation_programs"][2]["public_signal_exposure"] is False
    assert original == base()  # no mutation


@pytest.mark.parametrize("change", [
    lambda f: f[4].update(State="Running"),
    lambda f: f[4].update(LastTaskResult=1),
    lambda f: f[4].update(LastRunTime=(LAST + timedelta(minutes=1)).isoformat()),
    lambda f: f[0]["health"].update(activation_anchor_upstream_valid=False),
    lambda f: f[0]["activation"].update(public_signal_exposure_enabled=True),
    lambda f: f[1]["SOLUSDT"].pop(),
    lambda f: f[1]["ETHUSDT"][-1].update(record_type="ERROR"),
    lambda f: f[1]["BTCUSDT"][-1].update(entity_id="older-cycle"),
    lambda f: f[0]["markets"]["SOLUSDT"].update(current_head_hash="0" * 64),
    lambda f: f[2]["markets"][0].update(valid_inferences=4),
    lambda f: f[0]["scheduler"].update(healthy=False),
    lambda f: f[0]["totals"].update(valid_inferences=99),
    lambda f: f[2]["gates"][0]["requirements"][0].update(required=10),
    lambda f: f[2]["gates"][1]["requirements"][2].update(current=60),
    lambda f: f[2]["markets"][0].update(latest_recorded_at_utc="fake"),
])
def test_bridge_refuses_inconsistent_k5_evidence(change):
    f = list(fixture())
    change(f)
    with pytest.raises(EpochBridgeHeld):
        produce(f)


def test_bridge_rejects_explicit_bad_hash_chain():
    report, records, public, b, a = fixture()
    with pytest.raises(EpochBridgeHeld):
        prepare_verified_epoch(report=report, private_records=records,
            public_program=public, task_before=b, task_after=a,
            cycle_close_utc=CLOSE.isoformat(), captured_at_utc=AT.isoformat(),
            verify_chain=lambda rows: {"valid": False})


def test_receipt_key_separation_wrong_key_and_tampering():
    raw = produce(fixture())
    receipt = signed_receipt(raw, key=KEY)
    with pytest.raises(EpochBridgeHeld):
        verify_receipt(receipt, key=b"x" * 32)
    corrupted = receipt.replace(b"crypto-epoch-", b"crypto-ep0ch-", 1)
    with pytest.raises(EpochBridgeHeld):
        verify_receipt(corrupted, key=KEY)


def test_stale_crypto_and_replayed_previous_cycle_preserve_fresh_base():
    raw = produce(fixture())
    receipt = signed_receipt(raw, key=KEY)
    for now, last_cycle in (
        (AT+timedelta(hours=2), None),
        (AT, (CLOSE+timedelta(hours=1)).isoformat()),
    ):
        result = attach_current_crypto_preview(base_snapshot=base(), raw_epoch=raw,
            raw_receipt=receipt, key=KEY, now=now,
            last_accepted_cycle_close_utc=last_cycle, verify_public=lambda p: None)
        assert result == base()


def test_failing_full_public_validator_falls_back_without_publishing_crypto():
    raw = produce(fixture())
    receipt = signed_receipt(raw, key=KEY)
    def reject(_):
        raise ValueError("synthetic complete guard denies")
    result = attach_current_crypto_preview(base_snapshot=base(), raw_epoch=raw,
        raw_receipt=receipt, key=KEY, now=AT,
        last_accepted_cycle_close_utc=None, verify_public=reject)
    assert result == base()


def test_unverified_private_data_never_hidden_in_cryptographic_receipt():
    raw = produce(fixture())
    receipt = signed_receipt(raw, key=KEY)
    assert len(receipt) < 1024
    assert b'current_head_hash' not in receipt
    assert b'provider' not in receipt
    assert b'entry' not in receipt
    assert b'ledger_head_sha256' not in receipt


def test_wrong_base_fails_closed_before_crypto_merge():
    raw = produce(fixture())
    receipt = signed_receipt(raw, key=KEY)
    wrong = base()
    wrong["validation_programs"] = [{"program_id": "crypto-expansion-1"}]
    with pytest.raises(EpochBridgeHeld):
        attach_current_crypto_preview(base_snapshot=wrong, raw_epoch=raw,
            raw_receipt=receipt, key=KEY, now=AT,
            last_accepted_cycle_close_utc=None, verify_public=lambda p: None)
