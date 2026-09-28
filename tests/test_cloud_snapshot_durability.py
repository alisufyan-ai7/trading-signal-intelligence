from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from scripts.verify_cloud_snapshot_durability import main


GOOD_HEALTH = {
    "ok": True,
    "launch_ready": True,
    "snapshot_pending": False,
    "snapshot_generated_at_utc": "2026-09-28T19:45:56+00:00",
}

GOOD_AI = {
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


class _Response:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def _urlopen_factory(health, ai, markets):
    def _urlopen(request, timeout=20.0):
        url = request.full_url
        if url.endswith("/api/health"):
            return _Response(health)
        if url.endswith("/api/ai/insights"):
            return _Response(ai)
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
    assert payload["broker_execution_disabled"] is True
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
