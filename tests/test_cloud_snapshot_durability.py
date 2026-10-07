from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.verify_cloud_snapshot_durability import main


GOOD_HEALTH = {
    "ok": True,
    "launch_ready": True,
    "product": "VowSig Research Beta",
    "snapshot_pending": False,
    "snapshot_generated_at_utc": "2026-09-28T19:45:56+00:00",
    "snapshot_freshness": "fresh",
    "snapshot_age_seconds": 35,
}

GOOD_AI = {
    "runtime_version": "AI-v1.0",
    "decision_protocol_version": "AI-v1.0",
    "protocol_version": "AI-v1.0",
    "mode": "SHADOW_ONLY",
    "status": "forward_validation_in_progress",
    "generated_at_utc": "2026-09-28T19:45:51+00:00",
    "health": {
        "healthy": True,
        "broker_execution_disabled": True,
    },
    "totals": {
        "valid_inferences": 4,
        "signals": 1,
        "open_shadow_signals": 1,
        "completed_shadow_trades": 0,
        "missed_inferences": 6,
        "errors": 0,
    },
    "raw_market_data_included": False,
    "raw_feature_snapshots_included": False,
    "provider_request_metadata_included": False,
    "hidden_reasoning_included": False,
}


GOOD_VALIDATION = {
    "schema_version": 1,
    "programs": [
        {
            "program_id": "core-ai-shadow",
            "mode": "SHADOW_ONLY",
            "public_research_observability": True,
            "public_signal_exposure": True,
            "signal_details_included": False,
            "health": {"broker_execution_disabled": True},
            "gates": [
                {"gate_id": "A1"},
                {"gate_id": "A2"},
                {"gate_id": "A3"},
            ],
            "markets": [],
        },
        {
            "program_id": "market-expansion-1",
            "mode": "SHADOW_ONLY",
            "public_research_observability": True,
            "public_signal_exposure": False,
            "signal_details_included": False,
            "health": {"broker_execution_disabled": True},
            "gates": [
                {"gate_id": "X1"},
                {"gate_id": "X2"},
                {"gate_id": "X3"},
            ],
            "markets": [
                {"source_symbol": "EURUSD"},
                {"source_symbol": "XAGUSD"},
                {"source_symbol": "USOIL"},
            ],
        },
    ],
}


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _urlopen_factory(health, ai, markets, validation=GOOD_VALIDATION):
    def _urlopen(request, timeout=20.0):
        url = request.full_url
        if url.endswith("/api/health"):
            return _Response(health)
        if url.endswith("/api/ai/insights"):
            return _Response(ai)
        if url.endswith("/api/validation/programs"):
            return _Response(validation)
        if url.endswith("/api/markets"):
            return _Response(markets)
        raise AssertionError(url)

    return _urlopen


def test_durability_verifier_passes_good_public_contract(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(GOOD_HEALTH, GOOD_AI, [{"id": i} for i in range(9)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["cloud_snapshot_durability_check"] == "PASS"
    assert payload["market_count"] == 9
    assert payload["validation_program_count"] == 2
    assert payload["validation_program_ids"] == [
        "core-ai-shadow",
        "market-expansion-1",
    ]
    assert payload["broker_execution_disabled"] is True
    assert payload["snapshot_freshness"] == "fresh"
    assert payload["snapshot_age_seconds"] == 35
    assert payload["raw_market_data_included"] is False


def test_durability_verifier_fails_snapshot_pending(monkeypatch) -> None:
    pending = dict(GOOD_HEALTH)
    pending["launch_ready"] = False
    pending["snapshot_pending"] = True

    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(pending, GOOD_AI, [{"id": i} for i in range(9)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    with pytest.raises(SystemExit, match="launch-ready|pending"):
        main()


def test_durability_verifier_fails_stale_snapshot(monkeypatch) -> None:
    stale = dict(GOOD_HEALTH)
    stale["snapshot_freshness"] = "stale"
    stale["snapshot_age_seconds"] = 10_000

    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(stale, GOOD_AI, [{"id": i} for i in range(9)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    with pytest.raises(SystemExit, match="not fresh"):
        main()


def test_durability_verifier_fails_broker_boundary(monkeypatch) -> None:
    unsafe = json.loads(json.dumps(GOOD_AI))
    unsafe["health"]["broker_execution_disabled"] = False

    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(GOOD_HEALTH, unsafe, [{"id": i} for i in range(9)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    with pytest.raises(SystemExit, match="Broker execution boundary failed"):
        main()


def test_durability_verifier_fails_market_count(monkeypatch) -> None:
    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(GOOD_HEALTH, GOOD_AI, [{"id": i} for i in range(8)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    with pytest.raises(SystemExit, match="Expected 9 markets"):
        main()



def test_durability_verifier_passes_v1_1_with_separate_legacy_lineage(
    monkeypatch,
    capsys,
) -> None:
    ai = json.loads(json.dumps(GOOD_AI))
    ai["runtime_version"] = "AI-v1.1"
    ai["legacy_lineage"] = {
        "runtime_version": "AI-v1.0",
        "gate_counts_carried_into_active_runtime": False,
    }

    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(GOOD_HEALTH, ai, [{"id": i} for i in range(9)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    main()
    payload = json.loads(capsys.readouterr().out)
    assert payload["cloud_snapshot_durability_check"] == "PASS"
    assert payload["ai_runtime_version"] == "AI-v1.1"


def test_durability_verifier_rejects_v1_1_without_legacy_isolation(
    monkeypatch,
) -> None:
    ai = json.loads(json.dumps(GOOD_AI))
    ai["runtime_version"] = "AI-v1.1"
    ai["legacy_lineage"] = None

    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(GOOD_HEALTH, ai, [{"id": i} for i in range(9)]),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    with pytest.raises(SystemExit, match="legacy lineage"):
        main()



def test_durability_verifier_rejects_expansion_signal_exposure(
    monkeypatch,
) -> None:
    validation = json.loads(json.dumps(GOOD_VALIDATION))
    validation["programs"][1]["public_signal_exposure"] = True

    monkeypatch.setattr(
        "urllib.request.urlopen",
        _urlopen_factory(
            GOOD_HEALTH,
            GOOD_AI,
            [{"id": i} for i in range(9)],
            validation,
        ),
    )
    monkeypatch.setattr("sys.argv", ["verify_cloud_snapshot_durability.py"])

    with pytest.raises(SystemExit, match="signal exposure"):
        main()
