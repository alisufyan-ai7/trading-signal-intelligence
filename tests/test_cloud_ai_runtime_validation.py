from __future__ import annotations

import copy

import pytest
from fastapi import HTTPException

from trading_signal_intelligence.product.cloud_app import _validate_snapshot


def _snapshot() -> dict:
    return {
        "schema_version": 1,
        "raw_market_data_included": False,
        "markets": [],
        "health": {},
        "ai_v1": {
            "schema_version": 1,
            "runtime_version": "AI-v1.0",
            "decision_protocol_version": "AI-v1.0",
            "protocol_version": "AI-v1.0",
            "mode": "SHADOW_ONLY",
            "status": "forward_validation_in_progress",
            "health": {"healthy": True},
            "raw_market_data_included": False,
            "raw_feature_snapshots_included": False,
            "provider_request_metadata_included": False,
            "hidden_reasoning_included": False,
        },
    }


def test_cloud_snapshot_accepts_explicit_v1_0_runtime() -> None:
    _validate_snapshot(_snapshot())


def test_cloud_snapshot_accepts_v1_1_with_separate_legacy_lineage() -> None:
    payload = _snapshot()
    payload["ai_v1"]["runtime_version"] = "AI-v1.1"
    payload["ai_v1"]["legacy_lineage"] = {
        "runtime_version": "AI-v1.0",
        "gate_counts_carried_into_active_runtime": False,
    }
    _validate_snapshot(payload)


def test_cloud_snapshot_rejects_ambiguous_active_runtime() -> None:
    payload = _snapshot()
    payload["ai_v1"]["runtime_version"] = "UNKNOWN"
    with pytest.raises(HTTPException, match=""):
        _validate_snapshot(payload)


def test_cloud_snapshot_rejects_v1_1_legacy_gate_count_mixing() -> None:
    payload = _snapshot()
    payload["ai_v1"]["runtime_version"] = "AI-v1.1"
    payload["ai_v1"]["legacy_lineage"] = {
        "runtime_version": "AI-v1.0",
        "gate_counts_carried_into_active_runtime": True,
    }
    with pytest.raises(HTTPException, match=""):
        _validate_snapshot(payload)


def test_cloud_snapshot_rejects_wrong_decision_protocol() -> None:
    payload = copy.deepcopy(_snapshot())
    payload["ai_v1"]["protocol_version"] = "AI-v9"
    with pytest.raises(HTTPException, match=""):
        _validate_snapshot(payload)
