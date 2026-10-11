"""Synthetic-only as-of crypto publication tests: no VPS/provider/network IO."""
from __future__ import annotations

import copy
import hashlib
import importlib.util
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from trading_signal_intelligence.product.crypto_asof_seal_v0_1 import (
    AsOfSealRejected, SEAL_NAME, asof_program_from_seal_bytes,
    load_pinned_asof_program, seal_from_verified_snapshot,
)

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
SPEC = importlib.util.spec_from_file_location(
    "guarded_asof_under_test", SCRIPTS / "guarded_product_publish_v0_1.py")
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)
AT = datetime(2026, 10, 11, 10, 0, tzinfo=timezone.utc)
MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")


def _crypto():
    return {
        "schema_version": 1, "program_id": "crypto-expansion-1",
        "title": "Crypto AI Shadow Validation",
        "runtime_version": "AI-v1.3",
        "decision_protocol_version": "AI-v1.0",
        "mode": "SHADOW_ONLY", "status": "collecting",
        "public_research_observability": True,
        "public_signal_exposure": False, "signal_details_included": False,
        "health": {
            "healthy": True, "ledgers_valid": True,
            "scheduler_healthy": True, "broker_execution_disabled": True,
        },
        "totals": {
            "valid_inferences": 9, "completed_shadow_trades": 0,
            "open_shadow_signals": 0, "signals": 0, "no_trade": 9,
            "rejected_inferences": 0, "missed_inferences": 0, "errors": 0,
        },
        "gates": [
            {"gate_id": gate, "eligible": False, "requirements": []}
            for gate in ("C1", "C2", "C3")
        ],
        "markets": [
            {
                "source_symbol": sym, "canonical_symbol": sym.replace("USDT", "/USDT"),
                "ledger_valid": True, "activation_anchor_match": True,
                "valid_inferences": 3, "completed_shadow_trades": 0,
                "signals": 0, "open_signals": 0, "no_trade": 3,
                "rejected_inferences": 0, "missed_inferences": 0,
                "errors": 0, "latest_recorded_at_utc": AT.isoformat(),
            }
            for sym in MARKETS
        ],
        "raw_market_data_included": False,
        "raw_feature_snapshots_included": False,
        "provider_request_metadata_included": False,
        "hidden_reasoning_included": False,
    }


def _snapshot():
    base = []
    for id_ in ("core-ai-shadow", "market-expansion-1"):
        p = _crypto()
        p["program_id"] = id_
        p["runtime_version"] = "AI-v1.1" if id_ == "core-ai-shadow" else "AI-v1.2.1"
        p["markets"] = []
        p["gates"] = []
        base.append(p)
    return {
        "generated_at_utc": AT.isoformat(),
        "validation_programs": base + [_crypto()],
    }


def _seal(tmp_path):
    raw = seal_from_verified_snapshot(_snapshot(), AT + timedelta(seconds=1))
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / "data").mkdir()
    file = tmp_path / "data" / SEAL_NAME
    file.write_bytes(raw)
    return raw, hashlib.sha256(raw).hexdigest(), file


def test_asof_seal_schema_v1_and_history_label(tmp_path):
    raw, sha, _ = _seal(tmp_path)
    val = load_pinned_asof_program(tmp_path, AT + timedelta(hours=2), sha)
    assert val["status"] == "delayed"
    assert "DELAYED" in val["title"] and AT.isoformat() in val["title"]
    assert val["health"]["healthy"] is False
    assert val["health"]["scheduler_healthy"] is False
    assert val["health"]["ledgers_valid"] is True
    assert not {"data_freshness", "last_verified_snapshot_at_utc"}.intersection(val)
    assert len(raw) < 65536
    # Validate against the repo's frozen field contract and installed
    # public-API validator. Native Windows venv does not include jsonschema.
    from trading_signal_intelligence.product.cloud_app import _validate_validation_programs
    schema = json.loads(
        (ROOT / "config/public_validation_program_schema_v1.json").read_text(
            encoding="utf-8"
        )
    )
    assert schema["additionalProperties"] is False
    assert set(val) == set(schema["required"]) == set(schema["properties"])
    health = schema["properties"]["health"]
    assert health["additionalProperties"] is False
    assert set(val["health"]) == set(health["required"])
    assert val["schema_version"] == schema["properties"]["schema_version"]["const"]
    assert val["mode"] == schema["properties"]["mode"]["const"]
    assert val["signal_details_included"] is False
    assert val["public_signal_exposure"] is False
    assert val["health"]["broker_execution_disabled"] is True
    assert len(val["markets"]) == 3
    assert len(val["gates"]) == 3
    _validate_validation_programs({
        "validation_programs_schema_version": 1,
        "validation_programs": [val],
    })


@pytest.mark.parametrize("alter", [
    "bad_digest", "missing_digest", "tampered_bytes", "symlink",
    "unsafe_payload", "unhealthy", "missing_market", "missing_gate",
    "exposed_signals", "new_field", "bad_time", "wrong_provenance",
    "wrong_counts", "boolean_count", "market_extra_field", "gate_extra_field",
])
def test_asof_seal_rejects_bad_evidence(tmp_path, alter):
    snap = _snapshot()
    crypto = snap["validation_programs"][2]
    if alter == "unsafe_payload":
        crypto["recent_decisions"] = [{"direction": "BUY"}]
    elif alter == "unhealthy":
        crypto["health"]["healthy"] = False
    elif alter == "missing_market":
        crypto["markets"].pop()
    elif alter == "missing_gate":
        crypto["gates"].pop()
    elif alter == "exposed_signals":
        crypto["public_signal_exposure"] = True
    elif alter == "new_field":
        crypto["unreviewed_public_field"] = True
    elif alter == "wrong_counts":
        crypto["totals"]["no_trade"] = 123
    elif alter == "boolean_count":
        crypto["markets"][0]["no_trade"] = True
    elif alter == "market_extra_field":
        crypto["markets"][0]["private_note"] = "bad"
    elif alter == "gate_extra_field":
        crypto["gates"][0]["hidden_evidence"] = "bad"
    elif alter == "bad_time":
        snap["generated_at_utc"] = "yesterday"
    elif alter == "wrong_provenance":
        crypto["program_id"] = "other-crypto"
    if alter in {
        "unsafe_payload", "unhealthy", "missing_market", "missing_gate",
        "exposed_signals", "new_field", "bad_time", "wrong_provenance",
        "wrong_counts", "boolean_count", "market_extra_field", "gate_extra_field",
    }:
        with pytest.raises(AsOfSealRejected):
            seal_from_verified_snapshot(snap, AT + timedelta(seconds=1))
        return
    raw, sha, f = _seal(tmp_path)
    if alter == "bad_digest":
        sha = "a" * 64
    elif alter == "missing_digest":
        sha = ""
    elif alter == "tampered_bytes":
        f.write_bytes(raw + b" ")
    elif alter == "symlink":
        f.unlink()
        try:
            f.symlink_to(tmp_path / "elsewhere")
        except (OSError, NotImplementedError):
            pytest.skip("symlinks unavailable")
    with pytest.raises((AsOfSealRejected, FileNotFoundError)):
        load_pinned_asof_program(tmp_path, AT + timedelta(hours=1), sha)


def test_label_cannot_pretend_to_be_current(monkeypatch):
    import push_public_snapshot
    from trading_signal_intelligence.product import cloud_app
    monkeypatch.setattr(push_public_snapshot, "_validate_snapshot_for_push", lambda _: None)
    monkeypatch.setattr(cloud_app, "_validate_snapshot", lambda _: None)
    payload = _snapshot()
    raw = seal_from_verified_snapshot(payload, AT + timedelta(seconds=1))
    payload["generated_at_utc"] = (AT + timedelta(hours=1)).isoformat()
    payload["validation_programs"][2] = asof_program_from_seal_bytes(
        raw, AT + timedelta(hours=1))
    guard.validate_candidate(payload, AT + timedelta(hours=1))
    malformed = copy.deepcopy(payload)
    malformed["validation_programs"][2]["title"] = "Crypto AI Shadow Validation"
    with pytest.raises(guard.PublicationHeld):
        guard.validate_candidate(malformed, AT + timedelta(hours=1))
    future = copy.deepcopy(payload)
    future["validation_programs"][2]["title"] = (
        "Crypto AI Shadow Validation — DELAYED "
        f"(last verified {(AT + timedelta(hours=4)).isoformat()} UTC)"
    )
    with pytest.raises(guard.PublicationHeld):
        guard.validate_candidate(future, AT + timedelta(hours=1))
    unsafe = copy.deepcopy(payload)
    unsafe["validation_programs"][2]["recent_decisions"] = []
    with pytest.raises(guard.PublicationHeld):
        guard.validate_candidate(unsafe, AT + timedelta(hours=1))


def test_capture_is_disabled_until_explicit_owner_gate(monkeypatch, tmp_path):
    import capture_crypto_research_asof_v0_1 as capture
    monkeypatch.delenv(capture.ENABLE, raising=False)
    with pytest.raises(RuntimeError, match="capture activation"):
        capture.produce_one_seal(tmp_path)
    assert not (tmp_path / "data").exists()


def test_guard_default_never_reads_crypto_or_attaches_seal(monkeypatch, tmp_path):
    (tmp_path / "data").mkdir()
    _seal_dir = tmp_path / "seal-candidate"
    _, sha, file = _seal(_seal_dir)  # distinct fake repo path, no prod
    (tmp_path / "data" / SEAL_NAME).write_bytes(file.read_bytes())
    monkeypatch.delenv("VOWSIG_CRYPTO_ASOF_ENABLED", raising=False)
    monkeypatch.setenv("VOWSIG_CRYPTO_ASOF_SHA256", sha)
    monkeypatch.setattr(guard, "probe_k5", lambda: pytest.fail("K5 probed"))
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda *_: pytest.fail("ledger read"))
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    monkeypatch.setattr(guard, "_verify_current_expansion_claim", lambda *_: None)

    def run(argv, root, *, timeout):
        if Path(argv[2]).name == "export_guarded_core_expansion_v0_2.py":
            p = _snapshot()
            p["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(p))
    monkeypatch.setattr(guard, "run_checked", run)
    guard.publish_locked(tmp_path)
    result = json.loads((tmp_path / "data/public_snapshot.json").read_text())
    assert len(result["validation_programs"]) == 2


@pytest.mark.parametrize("valid_pin", [True, False])
def test_guard_opt_in_publishes_only_pinned_delayed_aggregates(
    monkeypatch, tmp_path, valid_pin
):
    # Sample age must be historical relative to wall-clock in every timezone.
    # Do not hardcode a fixed-time sample that might still be in the future.
    observed = datetime.now(timezone.utc) - timedelta(minutes=2)
    snapshot = _snapshot()
    snapshot["generated_at_utc"] = observed.isoformat()
    raw = seal_from_verified_snapshot(snapshot, observed + timedelta(seconds=1))
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / SEAL_NAME).write_bytes(raw)
    digest = hashlib.sha256(raw).hexdigest()
    monkeypatch.setenv("VOWSIG_CRYPTO_ASOF_ENABLED", "1")
    monkeypatch.setenv("VOWSIG_CRYPTO_ASOF_SHA256",
                       digest if valid_pin else "a" * 64)
    monkeypatch.setattr(guard, "probe_k5", lambda: pytest.fail("K5 probed"))
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda *_: pytest.fail("ledger read"))
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    monkeypatch.setattr(guard, "_verify_current_expansion_claim", lambda *_: None)

    def run(argv, root, *, timeout):
        assert Path(argv[2]).name != "export_guarded_full_v0_1.py"
        if Path(argv[2]).name == "export_guarded_core_expansion_v0_2.py":
            p = _snapshot()
            p["generated_at_utc"] = (AT + timedelta(hours=1)).isoformat()
            p["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(p))
    # Code uses the real wall clock; seal source date is in past, accepted.
    monkeypatch.setattr(guard, "run_checked", run)
    guard.publish_locked(tmp_path)
    result = json.loads((tmp_path / "data/public_snapshot.json").read_text())
    assert len(result["validation_programs"]) == (3 if valid_pin else 2)
    if valid_pin:
        c = result["validation_programs"][2]
        assert c["status"] == "delayed"
        assert "DELAYED" in c["title"]
        assert c["health"]["healthy"] is False
        assert c["public_signal_exposure"] is False
        assert set(c) == set(_crypto())
    else:
        assert {p["program_id"] for p in result["validation_programs"]} == guard.BASE_PROGRAMS


def test_duplicate_seal_json_keys_rejected():
    duplicate = (
        b'{"seal_schema_version":1,"seal_schema_version":1,'
        b'"source_snapshot_generated_at_utc":"2026-10-11T10:00:00+00:00",'
        b'"crypto_program":{}}'
    )
    with pytest.raises(AsOfSealRejected):
        asof_program_from_seal_bytes(duplicate, AT + timedelta(hours=1))


def _capture_mocks(monkeypatch, capture):
    monkeypatch.setattr(capture, "probe_k5", lambda: {"State": "Ready"})
    monkeypatch.setattr(capture, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(capture, "ensure_stable_k5", lambda *_: None)
    monkeypatch.setattr(
        capture, "crypto_fingerprints",
        lambda *_: {name: "same" for name in MARKETS},
    )
    monkeypatch.setattr(
        capture, "nine_ledger_fingerprints",
        lambda *_: {"nine-governed-ledgers": "same"},
    )
    monkeypatch.setattr(
        capture, "build_three_program_observation",
        lambda *_: _snapshot(),
    )


def test_one_shot_capture_only_on_mock_verified_reports(monkeypatch, tmp_path):
    import capture_crypto_research_asof_v0_1 as capture
    (tmp_path / "data").mkdir()
    monkeypatch.setenv(capture.ENABLE, "1")
    _capture_mocks(monkeypatch, capture)
    digest = capture.produce_one_seal(tmp_path)
    data = (tmp_path / "data" / SEAL_NAME).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest
    assert asof_program_from_seal_bytes(data, datetime.now(timezone.utc))
    assert set(json.loads(data)) == {
        "seal_schema_version", "source_snapshot_generated_at_utc",
        "crypto_program",
    }
    assert b"forward.sqlite" not in data
    assert b"research.sqlite" not in data
    with pytest.raises(RuntimeError, match="overwrite"):
        capture.produce_one_seal(tmp_path)


def test_source_drift_during_mock_capture_refuses_seal(monkeypatch, tmp_path):
    import capture_crypto_research_asof_v0_1 as capture
    (tmp_path / "data").mkdir()
    monkeypatch.setenv(capture.ENABLE, "1")
    _capture_mocks(monkeypatch, capture)
    states = iter([
        {"BTCUSDT": "original"}, {"BTCUSDT": "changed"},
    ])
    monkeypatch.setattr(capture, "crypto_fingerprints", lambda *_: next(states))
    with pytest.raises(RuntimeError, match="crypto ledger chain changed"):
        capture.produce_one_seal(tmp_path)
    assert not (tmp_path / "data" / SEAL_NAME).exists()


def test_nine_ledger_drift_during_mock_capture_refuses_seal(
    monkeypatch, tmp_path
):
    import capture_crypto_research_asof_v0_1 as capture
    (tmp_path / "data").mkdir()
    monkeypatch.setenv(capture.ENABLE, "1")
    _capture_mocks(monkeypatch, capture)
    states = iter([
        {"nine": "before"}, {"nine": "after"},
    ])
    monkeypatch.setattr(
        capture, "nine_ledger_fingerprints",
        lambda *_: next(states),
    )
    with pytest.raises(RuntimeError, match="active AI ledger changed"):
        capture.produce_one_seal(tmp_path)
    assert not (tmp_path / "data" / SEAL_NAME).exists()


def test_builder_reads_three_programs_only_no_public_snapshot(
    monkeypatch, tmp_path
):
    import capture_crypto_research_asof_v0_1 as capture
    seen = []
    programs = _snapshot()["validation_programs"]
    monkeypatch.setattr(
        capture, "_verify_crypto_validation_adapter_source",
        lambda *_: seen.append("adapter"),
    )
    monkeypatch.setattr(
        capture, "build_core_expansion_programs",
        lambda *_: (seen.append("core_expansion") or programs[:2]),
    )
    monkeypatch.setattr(
        capture, "build_crypto_public_validation_program",
        lambda *args, **kwargs: (
            seen.append("crypto") or programs[2]
        ),
    )
    monkeypatch.setattr(
        capture, "_verify_current_expansion_claim",
        lambda *_: seen.append("registry_compat"),
    )
    payload = capture.build_three_program_observation(tmp_path)
    assert seen == [
        "adapter", "core_expansion", "crypto", "registry_compat",
    ]
    assert len(payload["validation_programs"]) == 3
    assert set(p["program_id"] for p in payload["validation_programs"]) == {
        "core-ai-shadow", "market-expansion-1", "crypto-expansion-1",
    }
    # The former full exporter inspected S02 and other databases. Make its
    # absence an explicit release invariant.
    import inspect
    source = inspect.getsource(capture)
    assert "from export_guarded_full_v0_1 import" not in source
    assert "build_guarded_full_snapshot(" not in source
    assert "build_core_expansion_snapshot(" not in source


@pytest.mark.parametrize("bad_program", [
    "unsafe_entry", "crypto_public_exposure", "unhealthy",
    "missing_crypto_market", "unexpected_cohort",
])
def test_builder_rejects_unqualified_synthetic_program(
    monkeypatch, tmp_path, bad_program
):
    import capture_crypto_research_asof_v0_1 as capture
    programs = _snapshot()["validation_programs"]
    crypto = programs[2]
    if bad_program == "unsafe_entry":
        crypto["markets"][0]["entry_price"] = 1234
    elif bad_program == "crypto_public_exposure":
        crypto["public_signal_exposure"] = True
    elif bad_program == "unhealthy":
        crypto["health"]["healthy"] = False
    elif bad_program == "missing_crypto_market":
        crypto["markets"].pop()
    elif bad_program == "unexpected_cohort":
        crypto["program_id"] = "unregistered"
    monkeypatch.setattr(
        capture, "_verify_crypto_validation_adapter_source", lambda *_: None,
    )
    monkeypatch.setattr(
        capture, "build_core_expansion_programs", lambda *_: programs[:2],
    )
    monkeypatch.setattr(
        capture, "build_crypto_public_validation_program",
        lambda *args, **kwargs: crypto,
    )
    monkeypatch.setattr(
        capture, "_verify_current_expansion_claim", lambda *_: None,
    )
    with pytest.raises(RuntimeError):
        capture.build_three_program_observation(tmp_path)


def test_nine_ledger_guard_fingerprints_exact_paths(tmp_path):
    import capture_crypto_research_asof_v0_1 as capture
    for rel in capture.ACTIVE_AI_LEDGER_PATHS:
        file = tmp_path / rel
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"synthetic metadata only; not SQLite content")
    fingerprints = capture.nine_ledger_fingerprints(tmp_path)
    assert len(fingerprints) == 9
    assert set(fingerprints) == set(capture.ACTIVE_AI_LEDGER_PATHS)
    for rel in fingerprints:
        assert fingerprints[rel][2] == hashlib.sha256(
            (tmp_path / rel).read_bytes()
        ).hexdigest()
    # Any sidecar means possible writer activity; refuse even clean content.
    sidecar = tmp_path / (capture.ACTIVE_AI_LEDGER_PATHS[0] + "-wal")
    sidecar.write_bytes(b"synthetic WAL")
    with pytest.raises(RuntimeError, match="sidecar"):
        capture.nine_ledger_fingerprints(tmp_path)
    sidecar.unlink()
    # Reject unexpected source changes instead of certifying evidence.
    (tmp_path / capture.ACTIVE_AI_LEDGER_PATHS[1]).write_bytes(b"")
    with pytest.raises(RuntimeError, match="unsafe active AI ledger"):
        capture.nine_ledger_fingerprints(tmp_path)
