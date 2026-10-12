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
            "status": "collecting",
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
    "four_programs", "unsafe_exposure", "signal_details",
    "crypto_running", "bad_market", "bad_gate", "unverified_market",
    "private_signal", "stale_snapshot", "unhealthy_core",
])
def test_public_contract_rejects_unsafe_crypto(monkeypatch, defect):
    _no_network_validators(monkeypatch)
    data = _candidate()
    c = data["validation_programs"][2]
    if defect == "four_programs":
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
    # Deliberately exercise the FUTURE crypto branch under an offline-only
    # simulated interlock. Production has no K5 writer interlock and fails closed.
    monkeypatch.setattr(guard, "CRYPTO_WRITER_INTERLOCK_READY", True)
    monkeypatch.setattr(guard, "require_crypto_writer_interlock", lambda _: None)
    calls = []
    data = tmp_path / "data"
    data.mkdir()
    (data / "public_snapshot.json").write_text("OLD-SNAPSHOT")
    monkeypatch.setattr(guard, "probe_k5", lambda: _task())
    monkeypatch.setattr(guard, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda _: {"BTCUSDT": "digest"})
    def fail(argv, root, *, timeout):
        calls.append(Path(argv[2]).name)
        raise guard.PublicationHeld("simulated export failure")
    monkeypatch.setattr(guard, "run_checked", fail)
    with pytest.raises(guard.PublicationHeld, match="export failure"):
        guard.publish_locked(tmp_path)
    assert calls == ["export_guarded_full_v0_1.py", "export_guarded_core_expansion_v0_2.py"]
    assert (data / "public_snapshot.json").read_text() == "OLD-SNAPSHOT"


def test_crypto_ledger_change_falls_back_to_fresh_core_expansion(monkeypatch, tmp_path):
    # Deliberately exercise the FUTURE crypto branch under an offline-only
    # simulated interlock. Production has no K5 writer interlock and fails closed.
    monkeypatch.setattr(guard, "CRYPTO_WRITER_INTERLOCK_READY", True)
    monkeypatch.setattr(guard, "require_crypto_writer_interlock", lambda _: None)
    data = tmp_path / "data"
    data.mkdir()
    calls = []
    monkeypatch.setattr(guard, "probe_k5", lambda: _task())
    monkeypatch.setattr(guard, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    state = iter([{"BTCUSDT": "old"}, {"BTCUSDT": "new"}])
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda _: next(state))

    def run(argv, root, *, timeout):
        name = Path(argv[2]).name
        calls.append(name)
        if name == "export_guarded_full_v0_1.py":
            Path(argv[-1]).write_text(json.dumps(_candidate()), encoding="utf-8")
        elif name == "export_guarded_core_expansion_v0_2.py":
            two = _candidate()
            two["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(two), encoding="utf-8")

    monkeypatch.setattr(guard, "run_checked", run)
    guard.publish_locked(tmp_path)
    assert calls == [
        "export_guarded_full_v0_1.py",
        "export_guarded_core_expansion_v0_2.py",
        "push_public_snapshot.py",
    ]
    accepted = json.loads((data / "public_snapshot.json").read_text(encoding="utf-8"))
    assert [p["program_id"] for p in accepted["validation_programs"]] == [
        "core-ai-shadow", "market-expansion-1",
    ]
    assert len(list((data / guard.HISTORY_NAME).glob("*.accepted"))) == 1


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
    assert 'if not "%VOWSIG_GUARDED_PUBLISH_ENABLED%"=="1" exit /b 31' in cmd
    assert cmd.index('VOWSIG_GUARDED_PUBLISH_ENABLED') < cmd.index('scripts\\notify_forward_events.py')


def test_failed_cloud_push_preserves_previous_local_snapshot(monkeypatch, tmp_path):
    # Deliberately exercise the FUTURE crypto branch under an offline-only
    # simulated interlock. Production has no K5 writer interlock and fails closed.
    monkeypatch.setattr(guard, "CRYPTO_WRITER_INTERLOCK_READY", True)
    monkeypatch.setattr(guard, "require_crypto_writer_interlock", lambda _: None)
    data = tmp_path / "data"
    data.mkdir()
    old = data / "public_snapshot.json"
    old.write_text("IMMUTABLE-OLD-SNAPSHOT", encoding="utf-8")
    calls = []
    monkeypatch.setattr(guard, "probe_k5", lambda: _task())
    monkeypatch.setattr(guard, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda _: {"BTCUSDT": "unchanged"})
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)

    def mock_run(argv, root, *, timeout):
        calls.append(Path(argv[2]).name)
        if Path(argv[2]).name == "export_guarded_full_v0_1.py":
            Path(argv[-1]).write_text(json.dumps(_candidate()), encoding="utf-8")
        elif Path(argv[2]).name == "push_public_snapshot.py":
            raise guard.PublicationHeld("mock cloud push failed")

    monkeypatch.setattr(guard, "run_checked", mock_run)
    with pytest.raises(guard.PublicationHeld, match="cloud push failed"):
        guard.publish_locked(tmp_path)
    assert calls == ["export_guarded_full_v0_1.py", "push_public_snapshot.py"]
    assert old.read_text(encoding="utf-8") == "IMMUTABLE-OLD-SNAPSHOT"


def test_successful_mock_push_atomically_updates_local_snapshot(monkeypatch, tmp_path):
    # Deliberately exercise the FUTURE crypto branch under an offline-only
    # simulated interlock. Production has no K5 writer interlock and fails closed.
    monkeypatch.setattr(guard, "CRYPTO_WRITER_INTERLOCK_READY", True)
    monkeypatch.setattr(guard, "require_crypto_writer_interlock", lambda _: None)
    data = tmp_path / "data"
    data.mkdir()
    calls = []
    monkeypatch.setattr(guard, "probe_k5", lambda: _task())
    monkeypatch.setattr(guard, "validate_k5_finished", lambda *_: None)
    monkeypatch.setattr(guard, "crypto_fingerprints", lambda _: {"BTCUSDT": "unchanged"})
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    def mock_run(argv, root, *, timeout):
        calls.append(Path(argv[2]).name)
        if Path(argv[2]).name == "export_guarded_full_v0_1.py":
            Path(argv[-1]).write_text(json.dumps(_candidate()), encoding="utf-8")
    monkeypatch.setattr(guard, "run_checked", mock_run)
    guard.publish_locked(tmp_path)
    assert calls == ["export_guarded_full_v0_1.py", "push_public_snapshot.py"]
    assert json.loads((data / "public_snapshot.json").read_text(encoding="utf-8"))["validation_programs"][2]["program_id"] == "crypto-expansion-1"


def test_running_k5_still_publishes_fresh_core_expansion(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    calls = []
    monkeypatch.setattr(guard, "probe_k5", lambda: _task(state="Running"))
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    def run(argv, root, *, timeout):
        name = Path(argv[2]).name
        calls.append(name)
        if name == "export_guarded_core_expansion_v0_2.py":
            fresh = _candidate()
            fresh["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(fresh), encoding="utf-8")
    monkeypatch.setattr(guard, "run_checked", run)
    guard.publish_locked(tmp_path)
    assert calls == ["export_guarded_core_expansion_v0_2.py", "push_public_snapshot.py"]
    stored = json.loads((data / "public_snapshot.json").read_text(encoding="utf-8"))
    assert {p["program_id"] for p in stored["validation_programs"]} == guard.BASE_PROGRAMS


def test_delayed_crypto_is_explicitly_labeled_and_original_time_preserved(monkeypatch, tmp_path):
    _no_network_validators(monkeypatch)
    (tmp_path / "data").mkdir()
    original = _candidate()
    # The fixture's crypto row was independently healthy and current.
    crypto = original["validation_programs"][2]
    crypto["status"] = "collecting"
    encoded = json.dumps(original).encode("utf-8")
    archive, receipt = guard._pending_archive(tmp_path, original, encoded)
    guard._accept_archive(archive, receipt, encoded)
    later = NOW + timedelta(minutes=61)
    delayed = guard._last_accepted_crypto(tmp_path, later)
    assert delayed["data_freshness"] == "delayed"
    assert delayed["status"] == "delayed"
    assert "DELAYED" in delayed["title"]
    assert delayed["last_verified_snapshot_at_utc"] == NOW.isoformat()
    assert delayed["health"]["healthy"] is False
    assert delayed["health"]["scheduler_healthy"] is False
    fresh = _candidate()
    fresh["generated_at_utc"] = later.isoformat()
    fresh["validation_programs"][2] = delayed
    guard.validate_candidate(fresh, later)
    stale_dressed_as_fresh = copy.deepcopy(fresh)
    stale_dressed_as_fresh["validation_programs"][2]["title"] = "Crypto AI Shadow Validation"
    with pytest.raises(guard.PublicationHeld):
        guard.validate_candidate(stale_dressed_as_fresh, later)


def test_legacy_public_schema_delayed_archive_is_skipped_before_current(monkeypatch, tmp_path):
    """EXP034: accepted legacy DELAYED archives must not block new CURRENT source."""
    _no_network_validators(monkeypatch)
    (tmp_path / "data").mkdir()
    accepted = _candidate()
    generated = NOW - timedelta(minutes=60)
    observed = generated - timedelta(minutes=10)
    accepted["generated_at_utc"] = generated.isoformat()
    crypto = accepted["validation_programs"][2]
    crypto["status"] = "delayed"
    crypto["title"] = (
        "Crypto AI Shadow Validation — DELAYED "
        f"(last verified {observed.isoformat()} UTC)"
    )
    crypto["health"]["healthy"] = False
    crypto["health"]["scheduler_healthy"] = False
    assert "data_freshness" not in crypto
    assert "last_verified_snapshot_at_utc" not in crypto

    raw = json.dumps(accepted).encode("utf-8")
    archive, receipt = guard._pending_archive(tmp_path, accepted, raw)
    guard._accept_archive(archive, receipt, raw)

    # Legacy archived crypto is validated for hash, status and historical
    # provenance, then intentionally skipped as a *current* predecessor.
    # Previously it raised "historic crypto was not independently verified"
    # for every owner-pinned schema-v1 DELAYED archive.
    assert guard._last_accepted_crypto(tmp_path, NOW) is None
    assert archive.read_bytes() == raw
    assert receipt.is_file()


def test_corrupt_crypto_archive_never_blocks_fresh_core_expansion(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    archive_folder = data / guard.HISTORY_NAME
    archive_folder.mkdir()
    # Invalid receipt means cache cannot be trusted; core/expansion still advances.
    (archive_folder / ("snapshot-20261010T130509Z-" + "0" * 64 + ".json.accepted")).write_text(
        "CORRUPT-RECEIPT", encoding="utf-8"
    )
    monkeypatch.setattr(guard, "probe_k5", lambda: _task(state="Running"))
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    calls = []
    def run(argv, root, *, timeout):
        name = Path(argv[2]).name
        calls.append(name)
        if name == "export_guarded_core_expansion_v0_2.py":
            fresh = _candidate()
            fresh["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(fresh), encoding="utf-8")
    monkeypatch.setattr(guard, "run_checked", run)
    guard.publish_locked(tmp_path)
    assert calls == ["export_guarded_core_expansion_v0_2.py", "push_public_snapshot.py"]
    assert len(json.loads((data / "public_snapshot.json").read_text())["validation_programs"]) == 2


def test_failed_cloud_post_never_generates_accepted_archive_receipt(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    monkeypatch.setattr(guard, "probe_k5", lambda: _task(state="Running"))
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)
    def run(argv, root, *, timeout):
        name = Path(argv[2]).name
        if name == "export_guarded_core_expansion_v0_2.py":
            fresh = _candidate()
            fresh["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(fresh), encoding="utf-8")
        if name == "push_public_snapshot.py":
            raise guard.PublicationHeld("mock HTTP failure")
    monkeypatch.setattr(guard, "run_checked", run)
    with pytest.raises(guard.PublicationHeld):
        guard.publish_locked(tmp_path)
    assert not list((data / guard.HISTORY_NAME).glob("*.accepted"))
    assert not (data / "public_snapshot.json").exists()


def test_archived_history_is_exclusive_and_cannot_be_overwritten(tmp_path):
    (tmp_path / "data").mkdir()
    snapshot = _candidate()
    raw = json.dumps(snapshot).encode("utf-8")
    first, receipt = guard._pending_archive(tmp_path, snapshot, raw)
    guard._accept_archive(first, receipt, raw)
    before = first.read_bytes()
    with pytest.raises(guard.PublicationHeld, match="collision"):
        guard._pending_archive(tmp_path, snapshot, raw)
    assert first.read_bytes() == before


def test_independent_exporter_builds_new_core_expansion_without_crypto(monkeypatch, tmp_path):
    """No K5 gate, no old public snapshot and no crypto report builder."""
    script = ROOT / "scripts/export_guarded_core_expansion_v0_2.py"
    spec = importlib.util.spec_from_file_location("guarded_core_export_v0_2", script)
    assert spec and spec.loader
    export = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(export)

    def status_rows():
        return [{
            "source_symbol": "EURUSD", "canonical_symbol": "EUR/USD",
            "asset_class": "forex", "product_status": "live_signal_market",
            "evidence_status": "verified", "forward": {
                "state": "live", "ledger_valid": True,
            },
        }]
    monkeypatch.setattr(export, "market_statuses", status_rows)
    monkeypatch.setattr(export, "public_signal_history", lambda market, limit: [])
    monkeypatch.setattr(export, "operational_event_counts", lambda market: {})
    monkeypatch.setattr(export, "health", lambda: {"live_signal_markets": 9})
    monkeypatch.setattr(export, "evidence_summary", lambda: {"markets": {}})
    monkeypatch.setattr(export, "build_public_ai_insights",
                        lambda root: {"publish_allowed": True, "protocol_version": "AI-v1.0"})
    monkeypatch.setattr(export, "v1_1_state", lambda root: {"any_state": True})
    programs = _candidate()["validation_programs"][:2]
    monkeypatch.setattr(export, "build_core_expansion_programs", lambda root: programs)
    snapshot = export.build_core_expansion_snapshot(tmp_path)
    assert [p["program_id"] for p in snapshot["validation_programs"]] == [
        "core-ai-shadow", "market-expansion-1"
    ]
    assert snapshot["markets"][0]["signals"] == []
    assert snapshot["markets"][0]["operational_event_counts"] == {}
    assert snapshot["raw_market_data_included"] is False
    assert isinstance(snapshot["generated_at_utc"], str)


def test_unsafe_nested_private_crypto_field_rejected(monkeypatch):
    _no_network_validators(monkeypatch)
    payload = _candidate()
    payload["validation_programs"][2]["status"] = "collecting"
    payload["validation_programs"][2]["markets"][0]["entry_price"] = 199.50
    with pytest.raises(guard.PublicationHeld, match="private"):
        guard.validate_candidate(payload, NOW)


def test_core_expansion_fallback_not_allowed_if_base_unhealthy(monkeypatch):
    _no_network_validators(monkeypatch)
    payload = _candidate()
    payload["validation_programs"].pop()
    payload["validation_programs"][0]["health"]["healthy"] = False
    with pytest.raises(guard.PublicationHeld, match="unhealthy"):
        guard.validate_candidate(payload, NOW)


def test_archival_filename_matches_exact_accepted_receipt(tmp_path):
    (tmp_path / "data").mkdir()
    payload = _candidate()
    raw = json.dumps(payload).encode("utf-8")
    archive, receipt = guard._pending_archive(tmp_path, payload, raw)
    guard._accept_archive(archive, receipt, raw)
    assert guard.ARCHIVE_RE.fullmatch(receipt.name) is not None
    assert archive.read_bytes() == raw

def test_safe_two_program_fallback_is_explicitly_allowed(monkeypatch):
    _no_network_validators(monkeypatch)
    data = _candidate()
    data["validation_programs"].pop()
    guard.validate_candidate(data, NOW)
    assert {p["program_id"] for p in data["validation_programs"]} == guard.BASE_PROGRAMS


def test_uncoordinated_default_never_uses_crypto_or_old_crypto_archive(monkeypatch, tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    calls = []
    # Any attempt to inspect K5 must fail: safe base-only must not need it.
    monkeypatch.setattr(guard, "probe_k5", lambda: pytest.fail("K5 probed without interlock"))
    monkeypatch.setattr(guard, "crypto_fingerprints",
                        lambda _: pytest.fail("crypto ledgers accessed without interlock"))
    monkeypatch.setattr(guard, "_last_accepted_crypto",
                        lambda *_: pytest.fail("old crypto cache attached without interlock"))
    monkeypatch.setattr(guard, "validate_candidate", lambda *_: None)

    def offline_run(argv, root, *, timeout):
        name = Path(argv[2]).name
        calls.append(name)
        if name == "export_guarded_core_expansion_v0_2.py":
            row = _candidate()
            row["validation_programs"].pop()
            Path(argv[-1]).write_text(json.dumps(row), encoding="utf-8")
        elif name == "push_public_snapshot.py":
            assert json.loads(Path(argv[-1]).read_text())["validation_programs"][-1][
                "program_id"
            ] == "market-expansion-1"

    monkeypatch.setattr(guard, "run_checked", offline_run)
    guard.publish_locked(tmp_path)
    assert calls == ["export_guarded_core_expansion_v0_2.py", "push_public_snapshot.py"]
    assert {
        p["program_id"] for p in json.loads(
            (data / "public_snapshot.json").read_text(encoding="utf-8")
        )["validation_programs"]
    } == guard.BASE_PROGRAMS


def test_accidental_crypto_flag_flip_fails_closed_even_before_k5(monkeypatch, tmp_path):
    (tmp_path / "data").mkdir()
    monkeypatch.setattr(guard, "CRYPTO_WRITER_INTERLOCK_READY", True)
    monkeypatch.setattr(guard, "probe_k5", lambda: pytest.fail("K5 should not be probed"))
    with pytest.raises(guard.PublicationHeld, match="not implemented"):
        guard.publish_locked(tmp_path)
    assert not (tmp_path / "data" / "public_snapshot.json").exists()
    assert not (tmp_path / "data" / guard.HISTORY_NAME).exists()


def test_writer_interlock_absent_is_the_released_default():
    assert guard.CRYPTO_WRITER_INTERLOCK_READY is False
    with pytest.raises(guard.PublicationHeld, match="not implemented"):
        guard.require_crypto_writer_interlock(ROOT)
