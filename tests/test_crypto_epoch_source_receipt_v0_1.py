"""EXP-034 synthetic tests. NO actual K5/VPS, providers, network, or secrets."""
from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

from trading_signal_intelligence.ai_v1.observability import _record_hash, verify_records
from trading_signal_intelligence.ai_v1.crypto_activation_v1_3 import DATABASE_PATHS
from trading_signal_intelligence.product.crypto_completed_epoch_v0_1 import (
    public_program_from_completed_epoch,
)
from trading_signal_intelligence.product.crypto_epoch_source_producer_v0_1 import (
    SourceEpochHeld, capture_completed_k5_epoch,
)
from trading_signal_intelligence.product.crypto_epoch_receipt_store_v0_1 import (
    ReceiptStoreHeld, stage_authenticated_epoch, consume_trusted_epoch,
)
from test_crypto_epoch_bridge_v0_1 import fixture as old_fixture, task as old_task

UTC = timezone.utc
CLOSE = datetime(2026, 10, 12, 10, tzinfo=UTC)
NOW = CLOSE + timedelta(minutes=6)
KEY = b"synthetic-test-only-key-material-NOT-A-PRODUCTION-SECRET"
SYMS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def _make_row(symbol, record_type, entity_id, sequence, previous):
    row = {
        "sequence": sequence, "record_id": f"{symbol}-{sequence}",
        "record_type": record_type, "entity_id": entity_id,
        "recorded_at_utc": NOW.isoformat(),
        "effective_at_utc": CLOSE.isoformat(),
        "payload": {"synthetic": True},
        "previous_hash": previous,
    }
    row["record_hash"] = _record_hash(row, previous)
    return row


def _source_fixture():
    report, _, _, _, _ = old_fixture()
    records = {}
    for sym in SYMS:
        entity = f"AI-v1.3:{sym}:{CLOSE.isoformat().replace('+00:00', 'Z')}"
        prev = None
        rows = []
        for i, (kind, id) in enumerate((
            ("ACTIVATION", f"activation-{sym}"),
            ("INFERENCE", entity),
            ("NO_TRADE", entity),
        ), 1):
            row = _make_row(sym, kind, id, i, prev)
            rows.append(row)
            prev = row["record_hash"]
        records[sym] = rows
        assert verify_records(rows)["valid"] is True
        info = report["markets"][sym]
        info["symbol"] = sym
        info["current_head_hash"] = rows[-1]["record_hash"]
        info["records"] = 3
        info["counts_by_type"] = {
            "ACTIVATION": 1, "INFERENCE": 1, "NO_TRADE": 1,
        }
    for name, gate in report["gates"].items():
        gate["gate"] = name
    return report, records


def _capture(tmp_path, *, report=None, records=None, task_mutator=None,
             second_batch_mutator=None, report_mutator=None):
    normal_report, normal_records = _source_fixture()
    report = copy.deepcopy(report if report is not None else normal_report)
    records = copy.deepcopy(records if records is not None else normal_records)
    batches = {"reads": 0, "probes": 0}

    def reader(path):
        sym = next(s for s in SYMS if path.as_posix().endswith(DATABASE_PATHS[s]))
        batches["reads"] += 1
        returned = copy.deepcopy(records[sym])
        if second_batch_mutator is not None and batches["reads"] > 3:
            second_batch_mutator(sym, returned)
        return returned

    def reporter(root, *, now_utc, include_scheduler, verify_upstream):
        assert root == tmp_path.resolve()
        assert include_scheduler is True and verify_upstream is True
        assert now_utc == NOW
        selected = copy.deepcopy(report)
        if report_mutator is not None:
            report_mutator(selected)
        return selected

    def probe():
        batches["probes"] += 1
        result = old_task()
        if task_mutator is not None:
            task_mutator(batches["probes"], result)
        return result

    gate_rules = {"C1": (100, 20, 0), "C2": (500, 50, 60),
                  "C3": (1000, 100, 120)}
    def fixed_gate_reader(_root):
        return {"valid": True, "gates": {
            k: {"valid_inferences": vals[0],
                "completed_shadow_trades": vals[1],
                "minimum_calendar_days": vals[2]}
            for k, vals in gate_rules.items()
        }}
    raw = capture_completed_k5_epoch(
        tmp_path, observed_at_utc=NOW,
        reader=reader, reporter=reporter, task_probe=probe,
        gate_reader=fixed_gate_reader,
    )
    return raw, batches


def test_real_repository_chain_verifier_and_source_report_sanitize(tmp_path):
    raw, counts = _capture(tmp_path)
    assert counts == {"reads": 6, "probes": 2}
    payload = json.loads(raw)
    assert payload["cycle_close_utc"] == CLOSE.isoformat()
    assert payload["crypto_program"]["program_id"] == "crypto-expansion-1"
    assert payload["crypto_program"]["public_signal_exposure"] is False
    assert payload["crypto_program"]["signal_details_included"] is False
    assert payload["crypto_program"]["totals"]["valid_inferences"] == 3
    for disallowed in (
        "payload_json", "ledger_path", "record_hash", "record_id",
        "activation_record_hash", "current_head_hash", "supporting_factors",
        "broker_account", "private_report",
    ):
        assert disallowed not in raw.decode()
    assert public_program_from_completed_epoch(
        raw, expected_sha256=hashlib.sha256(raw).hexdigest(), now=NOW
    )["status"] == "collecting"


def test_source_records_change_between_full_reads(tmp_path):
    def changed(sym, rows):
        if sym == "BTCUSDT":
            rows[0]["record_hash"] = "0" * 64
    with pytest.raises(SourceEpochHeld):
        _capture(tmp_path, second_batch_mutator=changed)



def test_valid_append_between_reads_holds_even_if_each_chain_is_valid(tmp_path):
    def append_valid(sym, rows):
        if sym != "BTCUSDT":
            return
        extra = _make_row(
            sym, "EXIT", "synthetic-earlier-signal", 4, rows[-1]["record_hash"]
        )
        rows.append(extra)
        assert verify_records(rows)["valid"] is True
    with pytest.raises(SourceEpochHeld):
        _capture(tmp_path, second_batch_mutator=append_valid)


def test_interrupted_receipt_commit_keeps_orphan_untrusted(monkeypatch, tmp_path):
    from trading_signal_intelligence.product import crypto_epoch_receipt_store_v0_1 as store
    raw, _ = _capture(tmp_path)
    def interrupted(_root, _filename, _raw):
        raise ReceiptStoreHeld("synthetic simulated receipt crash")
    monkeypatch.setattr(store, "_write_exclusive", interrupted)
    with pytest.raises(ReceiptStoreHeld, match="receipt crash"):
        stage_authenticated_epoch(
            tmp_path, raw_epoch=raw, signing_key=KEY, observation_utc=NOW,
        )
    assert len(list(tmp_path.glob("crypto-epoch-*.json"))) == 1
    assert not list(tmp_path.glob("*.receipt"))
    # An unsigned epoch is untrusted regardless of how valid its bytes look.


def test_missing_receipt_holds(tmp_path):
    raw, _ = _capture(tmp_path)
    with pytest.raises(FileNotFoundError):
        consume_trusted_epoch(
            tmp_path, receipt_filename="crypto-epoch-20261012T100000Z-" +
            "0"*64 + ".json.receipt",
            externally_pinned_receipt_sha256="0"*64,
            verification_key=KEY, observation_utc=NOW,
            external_last_accepted_cycle_close_utc=None,
        )

def test_task_running_after_read_holds(tmp_path):
    def mutate(n, task):
        if n == 2:
            task["State"] = "Running"
    with pytest.raises(SourceEpochHeld):
        _capture(tmp_path, task_mutator=mutate)


def test_report_changed_after_first_batch_holds(tmp_path):
    def mutate(report):
        report["markets"]["ETHUSDT"]["current_head_hash"] = "0" * 64
    with pytest.raises(SourceEpochHeld):
        _capture(tmp_path, report_mutator=mutate)


def test_frozen_gate_mismatch_holds(tmp_path):
    def mutate(report):
        report["gates"]["C2"]["valid_inferences"]["required"] = 3
    # Independent frozen config still says 500 valid inferences for C2.
    with pytest.raises(SourceEpochHeld):
        _capture(tmp_path, report_mutator=mutate)


def test_explicit_untrusted_clock_holds(tmp_path):
    report, rows = _source_fixture()
    with pytest.raises(SourceEpochHeld):
        capture_completed_k5_epoch(
            tmp_path, observed_at_utc=NOW.replace(tzinfo=None),
            reader=lambda _: [], reporter=lambda *_a, **_k: report,
            task_probe=old_task,
        )


def test_trusted_receipt_roundtrip_and_no_secret_leakage(tmp_path):
    raw, _ = _capture(tmp_path)
    candidate = stage_authenticated_epoch(
        tmp_path, raw_epoch=raw, signing_key=KEY, observation_utc=NOW,
    )
    assert set(candidate) == {
        "epoch_filename", "epoch_sha256", "receipt_filename",
        "receipt_sha256", "cycle_close_utc",
    }
    receipt_raw = (tmp_path / candidate["receipt_filename"]).read_bytes()
    assert KEY not in receipt_raw and KEY not in raw
    assert b"ledger_head_sha256" not in receipt_raw
    program = consume_trusted_epoch(
        tmp_path,
        receipt_filename=candidate["receipt_filename"],
        externally_pinned_receipt_sha256=candidate["receipt_sha256"],
        verification_key=KEY, observation_utc=NOW,
        external_last_accepted_cycle_close_utc=None,
    )
    assert program["totals"]["valid_inferences"] == 3
    assert program["public_signal_exposure"] is False


def test_receipt_tamper_bad_pin_wrong_key_and_rollback_hold(tmp_path):
    raw, _ = _capture(tmp_path)
    candidate = stage_authenticated_epoch(
        tmp_path, raw_epoch=raw, signing_key=KEY, observation_utc=NOW,
    )
    params = dict(
        directory=tmp_path,
        receipt_filename=candidate["receipt_filename"],
        externally_pinned_receipt_sha256=candidate["receipt_sha256"],
        verification_key=KEY, observation_utc=NOW,
        external_last_accepted_cycle_close_utc=None,
    )
    with pytest.raises(ReceiptStoreHeld):
        consume_trusted_epoch(**{**params, "externally_pinned_receipt_sha256": "a"*64})
    with pytest.raises(Exception):
        consume_trusted_epoch(**{**params, "verification_key": b"wrong-key" * 5})
    with pytest.raises(ReceiptStoreHeld):
        consume_trusted_epoch(**{**params,
            "external_last_accepted_cycle_close_utc": CLOSE.isoformat()})
    receipt = tmp_path / candidate["receipt_filename"]
    receipt.write_bytes(receipt.read_bytes() + b" ")
    with pytest.raises(ReceiptStoreHeld):
        consume_trusted_epoch(**params)


def test_same_epoch_cannot_overwrite_and_orphan_never_validates(tmp_path):
    raw, _ = _capture(tmp_path)
    candidate = stage_authenticated_epoch(
        tmp_path, raw_epoch=raw, signing_key=KEY, observation_utc=NOW,
    )
    with pytest.raises(Exception):
        stage_authenticated_epoch(
            tmp_path, raw_epoch=raw, signing_key=KEY, observation_utc=NOW,
        )
    # Orphaned files or arbitrary latest-directory scans are NOT consumed;
    # the trusted receipt name+digest must be given explicitly.
    (tmp_path / candidate["receipt_filename"]).unlink()
    with pytest.raises(FileNotFoundError):
        consume_trusted_epoch(
            tmp_path, receipt_filename=candidate["receipt_filename"],
            externally_pinned_receipt_sha256=candidate["receipt_sha256"],
            verification_key=KEY, observation_utc=NOW,
            external_last_accepted_cycle_close_utc=None,
        )


def test_stale_receipt_never_becomes_current(tmp_path):
    raw, _ = _capture(tmp_path)
    candidate = stage_authenticated_epoch(
        tmp_path, raw_epoch=raw, signing_key=KEY, observation_utc=NOW,
    )
    with pytest.raises(Exception):
        consume_trusted_epoch(
            tmp_path, receipt_filename=candidate["receipt_filename"],
            externally_pinned_receipt_sha256=candidate["receipt_sha256"],
            verification_key=KEY,
            observation_utc=NOW + timedelta(hours=3),
            external_last_accepted_cycle_close_utc=None,
        )
