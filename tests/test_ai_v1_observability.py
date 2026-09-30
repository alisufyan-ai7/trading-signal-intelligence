from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

import trading_signal_intelligence.ai_v1.observability as observability
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.observability import (
    DATABASE_PATHS,
    MARKETS,
    ObservabilityError,
    _gate,
    build_report,
    read_records_read_only,
    verify_anchor_upstream,
    verify_records,
)


ACTIVATED = datetime(2026, 9, 28, 15, 56, 16, tzinfo=timezone.utc)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _seed_activation(repo_root: Path) -> dict[str, dict]:
    anchored: dict[str, dict] = {}
    for symbol in MARKETS:
        ledger = AILedger(repo_root / DATABASE_PATHS[symbol])
        record = ledger.append(
            record_type="ACTIVATION",
            entity_id=f"AI-v1.0:{symbol}:ACTIVATION",
            effective_at_utc=ACTIVATED,
            recorded_at_utc=ACTIVATED,
            payload={
                "protocol_version": "AI-v1.0",
                "market": symbol,
                "activated_at_utc": ACTIVATED.isoformat(),
                "broker_execution_enabled": False,
            },
        )
        anchored[symbol] = {
            "record_hash": record["record_hash"],
            "payload": record["payload"],
        }
    return anchored


def _write_anchor(repo_root: Path, markets: dict[str, dict]) -> None:
    forward = repo_root / "research" / "forward"
    forward.mkdir(parents=True, exist_ok=True)
    (forward / "AI-v1-activation-2026-09-28T155616Z.json").write_text(
        json.dumps(
            {
                "protocol_version": "AI-v1.0",
                "status": "TEST",
                "activated_at_utc": ACTIVATED.isoformat(),
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "artifact_hashes": {},
                "markets": markets,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def _append_example_evidence(repo_root: Path) -> None:
    at = ACTIVATED + timedelta(hours=2)

    xau = AILedger(repo_root / DATABASE_PATHS["XAUUSD"])
    xau_entity = "AI-v1.0:XAUUSD:2026-09-28T17:00:00Z"
    xau.append(
        record_type="INFERENCE",
        entity_id=xau_entity,
        effective_at_utc=at,
        recorded_at_utc=at,
        payload={"normalized_decision": {"decision": "BUY"}},
    )
    xau.append(
        record_type="SIGNAL",
        entity_id=xau_entity,
        effective_at_utc=at,
        recorded_at_utc=at,
        payload={"direction": "BUY", "broker_execution_enabled": False},
    )
    xau.append(
        record_type="PARTIAL_EXIT",
        entity_id=xau_entity,
        effective_at_utc=at + timedelta(hours=1),
        recorded_at_utc=at + timedelta(hours=1),
        payload={"trigger_reason": "TP1", "net_contribution_r": 0.45},
    )
    xau.append(
        record_type="EXIT",
        entity_id=xau_entity,
        effective_at_utc=at + timedelta(hours=2),
        recorded_at_utc=at + timedelta(hours=2),
        payload={
            "reason": "TP2",
            "bars_held": 2,
            "total_combined_signal_net_r": 1.35,
        },
    )

    ustec = AILedger(repo_root / DATABASE_PATHS["USTEC"])
    ustec_entity = "AI-v1.0:USTEC:2026-09-28T17:00:00Z"
    ustec.append(
        record_type="INFERENCE",
        entity_id=ustec_entity,
        effective_at_utc=at,
        recorded_at_utc=at,
        payload={"normalized_decision": {"decision": "NO_TRADE"}},
    )
    ustec.append(
        record_type="NO_TRADE",
        entity_id=ustec_entity,
        effective_at_utc=at,
        recorded_at_utc=at,
        payload={"normalized_decision": {"decision": "NO_TRADE"}},
    )

    us30 = AILedger(repo_root / DATABASE_PATHS["US30"])
    us30.append(
        record_type="MISSED_INFERENCE",
        entity_id="AI-v1.0:US30:2026-09-28T17:00:00Z",
        effective_at_utc=at,
        recorded_at_utc=at,
        payload={
            "reason": "scheduler_gap_or_stale_at_discovery",
            "provider_call_made": False,
        },
    )


def test_read_only_reader_does_not_create_missing_database(tmp_path) -> None:
    missing = tmp_path / "missing.sqlite"
    try:
        read_records_read_only(missing)
    except ObservabilityError:
        pass
    else:
        raise AssertionError("missing read-only ledger must fail closed")
    assert not missing.exists()


def test_observability_report_is_read_only_and_counts_evidence(tmp_path) -> None:
    markets = _seed_activation(tmp_path)
    _write_anchor(tmp_path, markets)
    _append_example_evidence(tmp_path)

    s02 = tmp_path / "data" / "s02_forward_control.sqlite"
    s02.write_bytes(b"S02 must remain untouched")

    before = {
        symbol: _sha256(tmp_path / DATABASE_PATHS[symbol]) for symbol in MARKETS
    }
    s02_before = _sha256(s02)

    report = build_report(
        tmp_path,
        now_utc=ACTIVATED + timedelta(days=1),
        include_scheduler=False,
        verify_upstream=False,
    )

    after = {
        symbol: _sha256(tmp_path / DATABASE_PATHS[symbol]) for symbol in MARKETS
    }
    assert before == after
    assert _sha256(s02) == s02_before

    assert report["mode"] == "READ_ONLY"
    assert report["health"]["healthy"] is True
    assert report["health"]["broker_execution_disabled"] is True
    assert report["totals"]["valid_inferences"] == 2
    assert report["totals"]["completed_shadow_trades"] == 1
    assert report["totals"]["missed_inferences"] == 1
    assert (
        report["totals"]["performance_observational_only"]["cumulative_net_r"]
        == 1.35
    )
    assert report["markets"]["XAUUSD"]["lifecycle"]["tp1_partial_count"] == 1
    assert report["markets"]["XAUUSD"]["lifecycle"]["tp2_exit_count"] == 1
    assert report["gates"]["A1"]["eligible"] is False


def test_hash_chain_tamper_is_reported_invalid(tmp_path) -> None:
    markets = _seed_activation(tmp_path)
    _write_anchor(tmp_path, markets)
    _append_example_evidence(tmp_path)

    path = tmp_path / DATABASE_PATHS["XAUUSD"]
    with sqlite3.connect(path) as connection:
        connection.execute("DROP TRIGGER ai_records_no_update")
        connection.execute(
            """
            UPDATE ai_records
            SET payload_json = ?
            WHERE record_type = 'INFERENCE'
            """,
            ('{"tampered":true}',),
        )
        connection.commit()

    verification = verify_records(read_records_read_only(path))
    assert verification["valid"] is False
    assert verification["reason"] == "record_hash_mismatch"

    report = build_report(
        tmp_path,
        now_utc=ACTIVATED + timedelta(days=1),
        include_scheduler=False,
        verify_upstream=False,
    )
    assert report["health"]["healthy"] is False
    assert report["health"]["ledgers_valid"] is False


def test_calendar_gates_are_frozen_to_activation_date() -> None:
    before_a2 = _gate(
        "A2",
        500,
        50,
        500,
        50,
        ACTIVATED + timedelta(days=59, hours=23),
        ACTIVATED,
        60,
    )
    at_a2 = _gate(
        "A2",
        500,
        50,
        500,
        50,
        ACTIVATED + timedelta(days=60),
        ACTIVATED,
        60,
    )
    at_a3 = _gate(
        "A3",
        1000,
        100,
        1000,
        100,
        ACTIVATED + timedelta(days=120),
        ACTIVATED,
        120,
    )

    assert before_a2["eligible"] is False
    assert at_a2["eligible"] is True
    assert at_a2["calendar_eligible_at_utc"].startswith("2026-11-27")
    assert at_a3["eligible"] is True
    assert at_a3["calendar_eligible_at_utc"].startswith("2027-01-26")



def test_verify_anchor_upstream_uses_clean_git_blobs_not_worktree_bytes(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact = tmp_path / "research" / "forward" / "retired.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b'{"ok": true}\r\n')

    head = "1" * 40
    upstream = "2" * 40
    committed = b'{"ok": true}\n'

    def fake_check_output(command, **kwargs):
        if command == ["git", "rev-parse", "HEAD"]:
            return head + "\n"
        if command == ["git", "rev-parse", "@{u}"]:
            return upstream + "\n"
        if command[:4] == [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
        ]:
            return ""
        if command == ["git", "show", f"{head}:research/forward/retired.json"]:
            return committed
        if command == [
            "git",
            "show",
            f"{upstream}:research/forward/retired.json",
        ]:
            return committed
        raise AssertionError(command)

    monkeypatch.setattr(observability.subprocess, "check_output", fake_check_output)

    result = verify_anchor_upstream(tmp_path, artifact)

    assert result["valid"] is True
    assert result["head_commit"] == head
    assert result["upstream_commit"] == upstream
    assert result["head_sha256"] == hashlib.sha256(committed).hexdigest()
    assert result["upstream_sha256"] == hashlib.sha256(committed).hexdigest()
    assert hashlib.sha256(artifact.read_bytes()).hexdigest() != result["head_sha256"]


def test_verify_anchor_upstream_rejects_dirty_local_artifact(
    tmp_path: Path,
    monkeypatch,
) -> None:
    artifact = tmp_path / "research" / "forward" / "retired.json"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_text("{}\n", encoding="utf-8")

    head = "1" * 40
    upstream = "2" * 40

    def fake_check_output(command, **kwargs):
        if command == ["git", "rev-parse", "HEAD"]:
            return head + "\n"
        if command == ["git", "rev-parse", "@{u}"]:
            return upstream + "\n"
        if command[:4] == [
            "git",
            "status",
            "--porcelain",
            "--untracked-files=no",
        ]:
            return " M research/forward/retired.json\n"
        raise AssertionError(command)

    monkeypatch.setattr(observability.subprocess, "check_output", fake_check_output)

    result = verify_anchor_upstream(tmp_path, artifact)

    assert result["valid"] is False
    assert result["reason"] == "local_artifact_not_clean"
    assert result["head_commit"] == head
    assert result["upstream_commit"] == upstream
