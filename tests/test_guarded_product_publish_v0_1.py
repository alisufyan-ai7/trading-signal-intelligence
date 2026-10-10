"""Mock-only guard regression tests: no VPS jobs, network, or ledger mutation."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/guarded_product_publish_v0_1.py"
SPEC = importlib.util.spec_from_file_location("guarded_product_publish_v0_1", SCRIPT)
assert SPEC and SPEC.loader
guard = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(guard)

NOW = datetime(2026, 10, 10, 13, 5, 9, tzinfo=timezone.utc)


def _task(*, state="Ready", result=0, age_seconds=65):
    return {
        "TaskName": guard.K5_TASK,
        "State": state,
        "LastTaskResult": result,
        "LastRunTime": (NOW - timedelta(seconds=age_seconds)).isoformat(),
        "NextRunTime": (NOW + timedelta(minutes=59)).isoformat(),
    }


def _candidate():
    programs = []
    for ident in ("core-ai-shadow", "market-expansion-1", "crypto-expansion-1"):
        programs.append({
            "program_id": ident,
            "runtime_version": "AI-v1.3" if ident == "crypto-expansion-1" else "AI-v1.1",
            "mode": "SHADOW_ONLY",
            "public_research_observability": True,
            "public_signal_exposure": ident == "core-ai-shadow",
            "signal_details_included": False,
            "health": {
                "healthy": True, "ledgers_valid": True,
                "scheduler_healthy": True,
                "broker_execution_disabled": True,
            },
            "markets": [
                {"source_symbol": sym, "ledger_valid": True, "activation_anchor_match": True}
                for sym in guard.MARKETS
            ] if ident == "crypto-expansion-1" else [],
            "gates": [{"gate_id": g} for g in ("C1", "C2", "C3")]
            if ident == "crypto-expansion-1" else [],
        })
    return {"generated_at_utc": NOW.isoformat(), "validation_programs": programs}


@pytest.mark.parametrize("state,result,age", [
    ("Running", 0, 65), ("Ready", 1, 65), ("Disabled", 0, 65),
    ("Ready", 0, 4000), ("Ready", 0, -10),
])
def test_k5_incomplete_or_stale_held(state, result, age):
    with pytest.raises(guard.PublicationHeld):
        guard.validate_k5_finished(
            _task(state=state, result=result, age_seconds=age), NOW
        )


def test_completed_recent_k5_accepted():
    assert guard.validate_k5_finished(_task(), NOW)


def test_last_task_result_must_be_int_not_true():
    value = _task()
    value["LastTaskResult"] = True
    with pytest.raises(guard.PublicationHeld):
        guard.validate_k5_finished(value, NOW)


def test_k5_state_change_during_export_rejected():
    with pytest.raises(guard.PublicationHeld, match="changed"):
        guard.ensure_stable_k5(_task(), _task(age_seconds=45), NOW)


def test_k5_timestamp_must_include_timezone():
    value = _task()
    value["LastRunTime"] = "2026-10-10T13:04:04"
    with pytest.raises(guard.PublicationHeld):
        guard.validate_k5_finished(value, NOW)


def _no_network_validators(monkeypatch):
    from trading_signal_intelligence.product import cloud_app
    monkeypatch.setattr(cloud_app, "_validate_snapshot", lambda _: None)
    # Production imports this module by name from the scripts directory.
    import sys
    sys.path.insert(0, str(ROOT / "scripts"))
    from push_public_snapshot import _validate_snapshot_for_push
    import push_public_snapshot
    monkeypatch.setattr(push_public_snapshot, "_validate_snapshot_for_push", lambda _: None)


def test_safe_three_program_contract(monkeypatch):
    _no_network_validators(monkeypatch)
    guard.validate_candidate(_candidate(), NOW)


@pytest.mark.parametrize("defect", [
    "no_crypto", "four_programs", "unsafe_exposure", "signal_details",
    "crypto_running", "bad_market", "bad_gate", "unverified_market",
    "private_signal", "stale_snapshot", "unhealthy_core",
])
def test_public_contract_rejects_unsafe_crypto(monkeypatch, defect):
    _no_network_validators(monkeypatch)
    data = _candidate()
    c = data["validation_programs"][2]
    if defect == "no_crypto":
        data["validation_programs"].pop()
    elif defect == "four_programs":
        data["validation_programs"].append(copy.deepcopy(c))
    elif defect == "unsafe_exposure":
        c["public_signal_exposure"] = True
    elif defect == "signal_details":
        c["signal_details_included"] = True
    elif defect == "crypto_running":
        c["health"]["scheduler_healthy"] = False
    elif defect == "bad_market":
        c["markets"].pop()
    elif defect == "bad_gate":
        c["gates"].pop()
    elif defect == "unverified_market":
        c["markets"][0]["ledger_valid"] = False
    elif defect == "private_signal":
        c["recent_decisions"] = []
    elif defect == "stale_snapshot":
        data["generated_at_utc"] = (NOW - timedelta(hours=1)).isoformat()
    elif defect == "unhealthy_core":
        data["validation_programs"][0]["health"]["healthy"] = False
    with pytest.raises(guard.PublicationHeld):
        guard.validate_candidate(data, NOW)


def test_failed_export_does_not_push_old_snapshot(monkeypatch, tmp_path):
    calls = []
    (tmp_path / "public_snapshot.json").write_text("OLD-SNAPSHOT")
    monkeypatch.setattr(guard, "probe_k5", lambda: _task())
    monkeypatch.setattr(guard, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda _: {"BTCUSDT": "digest"})
    def fail(argv, root, *, timeout):
        calls.append(Path(argv[2]).name)
        raise guard.PublicationHeld("simulated export failure")
    monkeypatch.setattr(guard, "run_checked", fail)
    with pytest.raises(guard.PublicationHeld, match="export failure"):
        guard.publish_locked(tmp_path)
    assert calls == ["export_public_snapshot.py"]
    assert (tmp_path / "public_snapshot.json").read_text() == "OLD-SNAPSHOT"


def test_crypto_ledger_change_blocks_push(monkeypatch, tmp_path):
    calls = []
    monkeypatch.setattr(guard, "probe_k5", lambda: _task())
    monkeypatch.setattr(guard, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    state = iter([{"BTCUSDT": "old"}, {"BTCUSDT": "new"}])
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda _: next(state))
    def run(argv, root, *, timeout):
        name = Path(argv[2]).name
        calls.append(name)
        if name == "export_public_snapshot.py":
            Path(argv[-1]).write_text(json.dumps(_candidate()), encoding="utf-8")
    monkeypatch.setattr(guard, "run_checked", run)
    with pytest.raises(guard.PublicationHeld, match="ledger changed"):
        guard.publish_locked(tmp_path)
    assert calls == ["export_public_snapshot.py"]
    assert not (tmp_path / "public_snapshot.json").exists()


def test_disabled_by_default_without_cutover(tmp_path, monkeypatch):
    monkeypatch.delenv("VOWSIG_GUARDED_PUBLISH_ENABLED", raising=False)
    with pytest.raises(guard.PublicationHeld, match="cutover"):
        guard.run_guarded(tmp_path)
    assert not (tmp_path / "data").exists()


def test_dormant_wrapper_runs_alerts_independently():
    cmd = (ROOT / "scripts/run_product_publish_guarded_v0_1.cmd").read_text(encoding="utf-8")
    assert 'scripts\\notify_forward_events.py' in cmd
    assert 'scripts\\guarded_product_publish_v0_1.py' in cmd
    assert cmd.index('scripts\\notify_forward_events.py') < cmd.index('scripts\\guarded_product_publish_v0_1.py')
    assert 'if not "!ALERT_EXIT!"=="0" exit /b !ALERT_EXIT!' in cmd
