"""Synthetic-only guarded publisher current-crypto aggregate integration tests.

No real K5 files, provider calls, live Task Scheduler or network. No source
reads unless the explicit opt-in switch is enabled, and the public result
must always come from a sealed in-memory aggregate.
"""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
from datetime import timedelta
from pathlib import Path

from test_crypto_epoch_bridge_v0_1 import AT, fixture, produce

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "guarded_product_publish_crypto_current_tests",
    ROOT / "scripts" / "guarded_product_publish_v0_1.py",
)
assert SPEC is not None and SPEC.loader is not None
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)


def test_disabled_by_default_never_touches_private_k5(monkeypatch, tmp_path):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    monkeypatch.delenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", raising=False)
    def forbidden(*args, **kwargs):
        raise AssertionError("private K5 source accessed with switch disabled")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1, "capture_completed_k5_epoch", forbidden,
    )
    assert guard._try_source_attested_crypto_aggregate(tmp_path, AT) is None


def test_source_attested_in_memory_crypto_passes_only_aggregate(monkeypatch, tmp_path):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    raw = produce(fixture())
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1,
        "capture_completed_k5_epoch", lambda *a, **k: raw,
    )
    monkeypatch.setattr(guard, "_last_accepted_crypto", lambda *_: None)
    program = guard._try_source_attested_crypto_aggregate(tmp_path, AT)
    assert program is not None
    assert program["program_id"] == "crypto-expansion-1"
    assert program["status"] == "collecting"
    assert program["public_signal_exposure"] is False
    assert program["signal_details_included"] is False
    assert [m["source_symbol"] for m in program["markets"]] == [
        "BTCUSDT", "ETHUSDT", "SOLUSDT",
    ]
    encoded = json.dumps(program).lower()
    assert all(term not in encoded for term in (
        '"entry":', '"stop_loss":', '"direction":', '"rationale":',
        '"shadow_signals":', '"provider_payload":',
    ))


def test_previous_accepted_counters_never_regress(monkeypatch, tmp_path):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    raw = produce(fixture())
    current = json.loads(raw)["crypto_program"]
    previous = copy.deepcopy(current)
    previous["last_verified_snapshot_at_utc"] = (
        AT - timedelta(minutes=90)
    ).isoformat()
    previous["markets"][0]["valid_inferences"] += 1
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1,
        "capture_completed_k5_epoch", lambda *a, **k: raw,
    )
    monkeypatch.setattr(guard, "_last_accepted_crypto", lambda *_: previous)
    assert guard._try_source_attested_crypto_aggregate(tmp_path, AT) is None


def test_stale_epoch_fails_closed_without_current_crypto(monkeypatch, tmp_path):
    from trading_signal_intelligence.product import crypto_epoch_source_producer_v0_1
    raw = produce(fixture())
    monkeypatch.setenv("VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", "1")
    monkeypatch.setattr(
        crypto_epoch_source_producer_v0_1,
        "capture_completed_k5_epoch", lambda *a, **k: raw,
    )
    monkeypatch.setattr(guard, "_last_accepted_crypto", lambda *_: None)
    assert guard._try_source_attested_crypto_aggregate(
        tmp_path, AT + timedelta(hours=2)
    ) is None


def _mock_publish_base(tmp_path, monkeypatch):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(guard, "CRYPTO_WRITER_INTERLOCK_READY", False)
    monkeypatch.delenv("VOWSIG_CRYPTO_ASOF_ENABLED", raising=False)
    calls = []
    def mock_commands(argv, root, *, timeout):
        name = Path(argv[2]).name
        calls.append(name)
        if name == "export_guarded_core_expansion_v0_2.py":
            base = {
                "generated_at_utc": AT.isoformat(),
                "validation_programs": [
                    {"program_id": "core-ai-shadow"},
                    {"program_id": "market-expansion-1"},
                ],
                "markets": [],
            }
            Path(argv[-1]).write_text(json.dumps(base), encoding="utf-8")
    monkeypatch.setattr(guard, "run_checked", mock_commands)
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    monkeypatch.setattr(guard, "_verify_current_expansion_claim", lambda *_: None)
    return calls


def test_single_publish_current_candidate_archived_after_mock_accept(monkeypatch, tmp_path):
    calls = _mock_publish_base(tmp_path, monkeypatch)
    crypto = json.loads(produce(fixture()))["crypto_program"]
    monkeypatch.setattr(
        guard, "_try_source_attested_crypto_aggregate", lambda *_: crypto,
    )
    guard.publish_locked(tmp_path)
    assert calls == [
        "export_guarded_core_expansion_v0_2.py",
        "push_public_snapshot.py",
    ]
    stored = json.loads((tmp_path / "data/public_snapshot.json").read_text())
    assert len(stored["validation_programs"]) == 3
    assert stored["validation_programs"][-1]["status"] == "collecting"
    assert list((tmp_path / "data" / guard.HISTORY_NAME).glob("*.accepted"))


def test_crypto_source_hold_still_pushes_base_once(monkeypatch, tmp_path):
    calls = _mock_publish_base(tmp_path, monkeypatch)
    monkeypatch.setattr(
        guard, "_try_source_attested_crypto_aggregate", lambda *_: None,
    )
    guard.publish_locked(tmp_path)
    assert calls == [
        "export_guarded_core_expansion_v0_2.py",
        "push_public_snapshot.py",
    ]
    stored = json.loads((tmp_path / "data/public_snapshot.json").read_text())
    assert {p["program_id"] for p in stored["validation_programs"]} == {
        "core-ai-shadow", "market-expansion-1",
    }


def test_crypto_current_never_mutates_frozen_writer_interlock():
    assert guard.CRYPTO_WRITER_INTERLOCK_READY is False
    assert guard.require_crypto_writer_interlock.__name__ == "require_crypto_writer_interlock"
