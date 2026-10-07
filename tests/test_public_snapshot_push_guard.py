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



def _validation_program() -> dict:
    return {
        "schema_version": 1,
        "program_id": "market-expansion-1",
        "mode": "SHADOW_ONLY",
        "public_research_observability": True,
        "public_signal_exposure": False,
        "signal_details_included": False,
        "health": {"broker_execution_disabled": True},
        "gates": [],
        "markets": [],
        "raw_market_data_included": False,
        "raw_feature_snapshots_included": False,
        "provider_request_metadata_included": False,
        "hidden_reasoning_included": False,
    }


def test_validation_program_snapshot_is_publishable() -> None:
    payload = {
        "raw_market_data_included": False,
        "ai_v1": {
            "runtime_version": "AI-v1.1",
            "status": "forward_validation_in_progress",
        },
        "validation_programs_schema_version": 1,
        "validation_programs": [_validation_program()],
    }
    _validate_snapshot_for_push(payload)


def test_validation_program_broker_boundary_fails_closed() -> None:
    program = _validation_program()
    program["health"]["broker_execution_disabled"] = False
    payload = {
        "raw_market_data_included": False,
        "validation_programs_schema_version": 1,
        "validation_programs": [program],
    }

    with pytest.raises(SystemExit, match="broker boundary"):
        _validate_snapshot_for_push(payload)


def test_research_only_program_rejects_signal_detail_payload() -> None:
    program = _validation_program()
    program["shadow_signals"] = [{"direction": "BUY"}]
    payload = {
        "raw_market_data_included": False,
        "validation_programs_schema_version": 1,
        "validation_programs": [program],
    }

    with pytest.raises(SystemExit, match="forbidden signal field"):
        _validate_snapshot_for_push(payload)
