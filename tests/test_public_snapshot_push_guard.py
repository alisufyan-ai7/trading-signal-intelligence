from __future__ import annotations

import pytest

from scripts.push_public_snapshot import _validate_snapshot_for_push


def test_normal_snapshot_is_publishable() -> None:
    payload = {
        "raw_market_data_included": False,
        "ai_v1": {
            "runtime_version": "AI-v1.0",
            "status": "forward_validation_in_progress",
        },
    }
    _validate_snapshot_for_push(payload)


def test_partial_v1_1_transition_snapshot_is_not_publishable() -> None:
    payload = {
        "raw_market_data_included": False,
        "ai_v1": {
            "runtime_version": "UNAVAILABLE",
            "status": "temporarily_unavailable",
            "publish_allowed": False,
            "transition_blocked": True,
        },
    }
    with pytest.raises(SystemExit, match="last good cloud snapshot"):
        _validate_snapshot_for_push(payload)


def test_raw_market_data_is_never_publishable() -> None:
    payload = {
        "raw_market_data_included": True,
        "ai_v1": {
            "runtime_version": "AI-v1.0",
        },
    }
    with pytest.raises(SystemExit, match="raw market data"):
        _validate_snapshot_for_push(payload)
