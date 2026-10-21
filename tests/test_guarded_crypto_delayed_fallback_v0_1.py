"""Synthetic-only EXP034 HOLD recovery: preserve last accepted PUBLIC counts.

No Windows tasks, private crypto ledgers, providers, HTTP calls, or broker use.
The production writer interlock must remain disabled.
"""
from __future__ import annotations

import copy
import json
from datetime import timedelta

import pytest

from test_guarded_crypto_current_aggregate_v0_1 import (
    AT, _mock_publish_base, fixture, guard, produce,
)


def _program():
    return json.loads(produce(fixture()))["crypto_program"]


def _accepted(tmp_path, created, crypto, *, delayed=False):
    candidate = copy.deepcopy(crypto)
    if delayed:
        original = created - timedelta(minutes=1)
        candidate["status"] = "delayed"
        candidate["title"] = (
            "Crypto AI Shadow Validation — DELAYED "
            f"(last verified {original.isoformat()} UTC)"
        )
        candidate["health"]["healthy"] = False
        candidate["health"]["scheduler_healthy"] = False
    payload = {
        "generated_at_utc": created.isoformat(),
        "validation_programs": [
            {"program_id": "core-ai-shadow"},
            {"program_id": "market-expansion-1"},
            candidate,
        ],
    }
    raw = json.dumps(payload, sort_keys=True).encode("utf-8")
    archive, receipt = guard._pending_archive(tmp_path, payload, raw)
    guard._accept_archive(archive, receipt, raw)
    return archive, receipt


def test_crypto_hold_uses_newest_sha_accepted_current_not_older_delayed(
    monkeypatch, tmp_path, capsys,
):
    calls = _mock_publish_base(tmp_path, monkeypatch)
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setenv("VOWSIG_CRYPTO_ASOF_ENABLED", "1")
    # A previous successful CURRENT archive followed by a deliberate crypto
    # HOLD which published the frozen older DELAYED card.
    program = _program()
    older_time = AT - timedelta(minutes=11)
    archive, receipt = _accepted(tmp_path, older_time, program)
    _accepted(tmp_path, AT - timedelta(minutes=8), program, delayed=True)
    monkeypatch.setattr(
        guard, "_try_source_attested_crypto_aggregate", lambda *_: None,
    )
    from trading_signal_intelligence.product import crypto_asof_seal_v0_1
    monkeypatch.setattr(
        crypto_asof_seal_v0_1, "load_pinned_asof_program",
        lambda *_: pytest.fail("older October 11 seal must not replace newer accepted counts"),
    )

    guard.publish_locked(tmp_path)
    result = json.loads(
        (tmp_path / "data/public_snapshot.json").read_text(encoding="utf-8")
    )
    crypto = result["validation_programs"][-1]
    assert crypto["program_id"] == "crypto-expansion-1"
    assert crypto["status"] == "delayed"
    assert crypto["data_freshness"] == "delayed"
    assert crypto["last_verified_snapshot_at_utc"] == older_time.isoformat()
    assert older_time.isoformat() in crypto["title"]
    assert crypto["totals"] == program["totals"]
    assert crypto["health"]["healthy"] is False
    assert crypto["health"]["scheduler_healthy"] is False
    assert crypto["health"]["broker_execution_disabled"] is True
    assert crypto["public_signal_exposure"] is False
    assert crypto["signal_details_included"] is False
    assert calls == [
        "export_guarded_core_expansion_v0_2.py", "push_public_snapshot.py",
    ]
    assert archive.is_file() and receipt.is_file()
    assert "CRYPTO_DELAYED_SOURCE=VERIFIED_ACCEPTED_CURRENT" in capsys.readouterr().out
    assert guard.CRYPTO_WRITER_INTERLOCK_READY is False


def test_tampered_current_receipt_falls_back_to_original_seal(
    monkeypatch, tmp_path, capsys,
):
    calls = _mock_publish_base(tmp_path, monkeypatch)
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setenv("VOWSIG_CRYPTO_ASOF_ENABLED", "1")
    program = _program()
    _, receipt = _accepted(tmp_path, AT - timedelta(minutes=10), program)
    receipt.write_text("TAMPERED", encoding="utf-8")
    monkeypatch.setattr(
        guard, "_try_source_attested_crypto_aggregate", lambda *_: None,
    )
    old = copy.deepcopy(program)
    old["status"] = "delayed"
    old["title"] = (
        "Crypto AI Shadow Validation — DELAYED "
        "(last verified 2026-10-11T12:07:21+00:00 UTC)"
    )
    old["health"]["healthy"] = False
    old["health"]["scheduler_healthy"] = False
    from trading_signal_intelligence.product import crypto_asof_seal_v0_1
    monkeypatch.setattr(
        crypto_asof_seal_v0_1, "load_pinned_asof_program", lambda *_: old,
    )
    guard.publish_locked(tmp_path)
    result = json.loads(
        (tmp_path / "data/public_snapshot.json").read_text(encoding="utf-8")
    )
    assert result["validation_programs"][-1]["status"] == "delayed"
    assert result["validation_programs"][-1]["title"] == old["title"]
    output = capsys.readouterr().out
    assert "CRYPTO_DELAYED_ACCEPTED_HISTORY=HELD" in output
    assert "CRYPTO_DELAYED_SOURCE=PINNED_ORIGINAL_SEAL" in output
    assert "TAMPERED" not in output
    assert calls.count("push_public_snapshot.py") == 1


def test_crypto_opt_in_off_never_reads_accepted_history(monkeypatch, tmp_path):
    calls = _mock_publish_base(tmp_path, monkeypatch)
    monkeypatch.delenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", raising=False)
    monkeypatch.delenv("VOWSIG_CRYPTO_ASOF_ENABLED", raising=False)
    monkeypatch.setattr(
        guard, "_last_accepted_crypto",
        lambda *_: pytest.fail("accepted crypto archive read while opt-in off"),
    )
    monkeypatch.setattr(
        guard, "_try_source_attested_crypto_aggregate", lambda *_: None,
    )
    guard.publish_locked(tmp_path)
    result = json.loads(
        (tmp_path / "data/public_snapshot.json").read_text(encoding="utf-8")
    )
    assert len(result["validation_programs"]) == 2
    assert calls.count("push_public_snapshot.py") == 1


def test_source_failure_log_only_contains_fixed_stage(monkeypatch, tmp_path, capsys):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    secret = "SECRET_PRIVATE_LEDGER_ROW_AND_PATH"
    def fail(*a, **k):
        raise ValueError(secret)
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1, "capture_completed_k5_epoch", fail,
    )
    assert guard._try_source_attested_crypto_aggregate(tmp_path, AT) is None
    output = capsys.readouterr().out
    assert "CRYPTO_CURRENT_AGGREGATE=HELD" in output
    assert "CRYPTO_CURRENT_HOLD_STAGE=SOURCE_CAPTURE" in output
    assert secret not in output


def test_invalid_epoch_reports_bounded_stage_not_private_bytes(
    monkeypatch, tmp_path, capsys,
):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1,
        "capture_completed_k5_epoch", lambda *a, **k: b'NOT-A-VALID-EPOCH',
    )
    assert guard._try_source_attested_crypto_aggregate(tmp_path, AT) is None
    output = capsys.readouterr().out
    assert "CRYPTO_CURRENT_HOLD_STAGE=EPOCH_VALIDATION" in output
    assert "NOT-A-VALID-EPOCH" not in output


def test_accepted_history_failure_reports_bounded_stage(
    monkeypatch, tmp_path, capsys,
):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1,
        "capture_completed_k5_epoch", lambda *a, **k: produce(fixture()),
    )
    monkeypatch.setattr(
        guard, "_last_accepted_crypto",
        lambda *_: (_ for _ in ()).throw(ValueError("SENSITIVE_HISTORY_PATH")),
    )
    assert guard._try_source_attested_crypto_aggregate(tmp_path, AT) is None
    output = capsys.readouterr().out
    assert "CRYPTO_CURRENT_HOLD_STAGE=ACCEPTED_HISTORY" in output
    assert "SENSITIVE_HISTORY_PATH" not in output


def test_count_regression_reports_bounded_stage(monkeypatch, tmp_path, capsys):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1,
        "capture_completed_k5_epoch", lambda *a, **k: produce(fixture()),
    )
    previous = _program()
    previous["last_verified_snapshot_at_utc"] = (
        AT - timedelta(minutes=70)
    ).isoformat()
    previous["markets"][0]["valid_inferences"] += 1
    monkeypatch.setattr(guard, "_last_accepted_crypto", lambda *_: previous)
    assert guard._try_source_attested_crypto_aggregate(tmp_path, AT) is None
    output = capsys.readouterr().out
    assert "CRYPTO_CURRENT_HOLD_STAGE=NON_REGRESSION" in output
    assert "Traceback" not in output
