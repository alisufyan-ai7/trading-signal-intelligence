from __future__ import annotations

import copy

import pytest
from fastapi import HTTPException

from trading_signal_intelligence.product.cloud_app import (
    _validate_snapshot,
    _with_public_miss_metrics,
)


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
    with pytest.raises(HTTPException):
        _validate_snapshot(payload)


def test_cloud_snapshot_rejects_v1_1_legacy_gate_count_mixing() -> None:
    payload = _snapshot()
    payload["ai_v1"]["runtime_version"] = "AI-v1.1"
    payload["ai_v1"]["legacy_lineage"] = {
        "runtime_version": "AI-v1.0",
        "gate_counts_carried_into_active_runtime": True,
    }
    with pytest.raises(HTTPException):
        _validate_snapshot(payload)


def test_cloud_snapshot_rejects_wrong_decision_protocol() -> None:
    payload = copy.deepcopy(_snapshot())
    payload["ai_v1"]["protocol_version"] = "AI-v9"
    with pytest.raises(HTTPException):
        _validate_snapshot(payload)



def test_cloud_snapshot_rejects_wrong_decision_protocol_version() -> None:
    payload = _snapshot()
    payload["ai_v1"]["decision_protocol_version"] = "AI-v9"
    with pytest.raises(HTTPException):
        _validate_snapshot(payload)


def test_public_miss_metrics_separate_no_tick_without_mutating_snapshot() -> None:
    ai_v1 = {
        "runtime_version": "AI-v1.1",
        "totals": {
            "valid_inferences": 177,
            "missed_inferences": 156,
            "errors": 0,
            "sync_operational_counts": {
                "no_current_h1_tick": 153,
            },
        },
    }
    original = copy.deepcopy(ai_v1)

    result = _with_public_miss_metrics(ai_v1)

    assert ai_v1 == original
    assert result["totals"]["missed_inferences"] == 156
    assert result["totals"]["no_current_h1_tick_count"] == 153
    assert result["totals"]["processing_miss_count"] == 3
    assert result["totals"]["processing_miss_denominator"] == 180
    assert result["totals"]["processing_miss_rate"] == 1 / 60
    assert "not missed trades" in result["operational_miss_notice"].lower()


def test_public_miss_metrics_handle_missing_counts_fail_safely() -> None:
    result = _with_public_miss_metrics({"runtime_version": "UNKNOWN"})

    assert result["totals"]["no_current_h1_tick_count"] == 0
    assert result["totals"]["processing_miss_count"] == 0
    assert result["totals"]["processing_miss_denominator"] == 0
    assert result["totals"]["processing_miss_rate"] == 0.0
