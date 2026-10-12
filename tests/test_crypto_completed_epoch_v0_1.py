"""Offline/synthetic completed-cycle crypto handoff tests; no providers/SQLite."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
    CompletedEpochRejected, create_completed_epoch_bytes,
    public_program_from_completed_epoch, publish_immutable_epoch,
    read_immutable_epoch,
)

AT = datetime(2026, 10, 12, 10, 5, tzinfo=timezone.utc)
CLOSE = datetime(2026, 10, 12, 10, 0, tzinfo=timezone.utc)
SYMBOLS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def program():
    return {
        "schema_version": 1, "program_id": "crypto-expansion-1",
        "title": "Crypto AI Shadow Validation", "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0", "mode": "SHADOW_ONLY",
        "status": "collecting", "public_research_observability": True,
        "public_signal_exposure": False, "signal_details_included": False,
        "health": {"healthy": True, "ledgers_valid": True,
                   "scheduler_healthy": True, "broker_execution_disabled": True},
        "totals": {"valid_inferences": 9, "completed_shadow_trades": 0,
                   "open_shadow_signals": 0, "signals": 0, "no_trade": 9,
                   "rejected_inferences": 0, "missed_inferences": 0, "errors": 0},
        "gates": [{"gate_id": x, "eligible": False, "requirements": []}
                  for x in ("C1", "C2", "C3")],
        "markets": [{
            "source_symbol": x, "canonical_symbol": x.replace("USDT", "/USDT"),
            "ledger_valid": True, "activation_anchor_match": True,
            "valid_inferences": 3, "completed_shadow_trades": 0, "signals": 0,
            "open_signals": 0, "no_trade": 3, "rejected_inferences": 0,
            "missed_inferences": 0, "errors": 0,
            "latest_recorded_at_utc": AT.isoformat(),
        } for x in SYMBOLS],
        "raw_market_data_included": False, "raw_feature_snapshots_included": False,
        "provider_request_metadata_included": False, "hidden_reasoning_included": False,
    }


def proofs():
    return {x: {"source_bar_close_utc": CLOSE.isoformat(),
                "terminal_record_type": "NO_TRADE",
                "ledger_head_sha256": hashlib.sha256(x.encode()).hexdigest()}
            for x in SYMBOLS}


def payload(crypto=None, evidence=None, cycle=None, captured=None):
    raw = create_completed_epoch_bytes(
        crypto_program=program() if crypto is None else crypto,
        cycle_close_utc=CLOSE.isoformat() if cycle is None else cycle,
        captured_at_utc=AT.isoformat() if captured is None else captured,
        terminal_proofs=proofs() if evidence is None else evidence,
    )
    return raw, hashlib.sha256(raw).hexdigest()


def test_complete_three_market_epoch_round_trip_and_private_proof_omission(tmp_path):
    raw, sha = payload()
    encoded = json.loads(raw)
    assert encoded["cycle_close_utc"] == CLOSE.isoformat()
    assert len(raw) < 65536
    assert "ledger_head_sha256" not in raw.decode()
    for x in proofs().values():
        assert x["ledger_head_sha256"] not in raw.decode()
    assert set(encoded) == {"schema_version", "cycle_close_utc", "captured_at_utc",
                            "cohort_commitment_sha256", "crypto_program"}
    directory = tmp_path / "spool"
    directory.mkdir()
    path, written_sha = publish_immutable_epoch(directory, raw)
    assert written_sha == sha and path.is_file()
    result = read_immutable_epoch(path, expected_sha256=sha, now=AT + timedelta(minutes=1))
    assert result == program() and result["public_signal_exposure"] is False


@pytest.mark.parametrize("mutate", [
    lambda p: p.pop("SOLUSDT"),
    lambda p: p["BTCUSDT"].update(source_bar_close_utc=(CLOSE-timedelta(hours=1)).isoformat()),
    lambda p: p["BTCUSDT"].update(terminal_record_type="INFERENCE"),
    lambda p: p["ETHUSDT"].update(terminal_record_type="ERROR"),
    lambda p: p["SOLUSDT"].update(ledger_head_sha256="abc"),
    lambda p: p["SOLUSDT"].update(extra_private_field="not safe"),
])
def test_incomplete_mixed_or_unproven_terminal_cycles_hold(mutate):
    p = proofs()
    mutate(p)
    with pytest.raises(CompletedEpochRejected):
        payload(evidence=p)


@pytest.mark.parametrize("delta", [-1, 21, 65])
def test_capture_must_follow_exact_recent_h1_close(delta):
    with pytest.raises(CompletedEpochRejected):
        payload(captured=(CLOSE+timedelta(minutes=delta)).isoformat())


def test_not_current_after_90_minutes_or_in_future():
    raw, sha = payload()
    for when in (AT-timedelta(seconds=1), AT+timedelta(minutes=90)):
        with pytest.raises(CompletedEpochRejected):
            public_program_from_completed_epoch(raw, expected_sha256=sha, now=when)


def test_reject_rollback_even_when_hash_is_valid():
    raw, sha = payload()
    with pytest.raises(CompletedEpochRejected):
        public_program_from_completed_epoch(raw, expected_sha256=sha, now=AT,
            last_published_cycle_close_utc=(CLOSE+timedelta(hours=1)).isoformat())


def test_missing_bad_digest_and_tamper_hold():
    raw, sha = payload()
    for candidate, digest in ((raw, ""), (raw, "a" * 64), (raw+b" ", sha)):
        with pytest.raises(CompletedEpochRejected):
            public_program_from_completed_epoch(candidate, expected_sha256=digest, now=AT)


@pytest.mark.parametrize("unsafe", [
    lambda p: p.update(public_signal_exposure=True),
    lambda p: p.update(recent_decisions=[{"direction": "BUY"}]),
    lambda p: p["markets"].pop(),
    lambda p: p["totals"].update(no_trade=100),
    lambda p: p["health"].update(broker_execution_disabled=False),
])
def test_reject_unsafe_public_program(unsafe):
    crypto = program()
    unsafe(crypto)
    with pytest.raises(CompletedEpochRejected):
        payload(crypto=crypto)


def test_spool_never_overwrites_existing_immutable_file(tmp_path):
    raw, _ = payload()
    publish_immutable_epoch(tmp_path, raw)
    with pytest.raises(CompletedEpochRejected, match="already exists"):
        publish_immutable_epoch(tmp_path, raw)
    assert len(list(tmp_path.glob("crypto-epoch-*.json"))) == 1


def test_spool_rejects_symlink(tmp_path):
    raw, _ = payload()
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(real, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks unavailable")
    with pytest.raises(CompletedEpochRejected):
        publish_immutable_epoch(link, raw)


def test_reject_duplicate_json_keys_even_with_correct_digest():
    raw, _ = payload()
    text = raw.decode().replace('"schema_version":1', '"schema_version":1,"schema_version":1', 1)
    attack = text.encode()
    with pytest.raises(CompletedEpochRejected):
        public_program_from_completed_epoch(attack,
            expected_sha256=hashlib.sha256(attack).hexdigest(), now=AT)
