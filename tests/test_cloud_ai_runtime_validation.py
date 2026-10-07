from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from trading_signal_intelligence.product.cloud_app import (
    SNAPSHOT_DELAYED_AFTER_SECONDS,
    SNAPSHOT_STALE_AFTER_SECONDS,
    _snapshot_freshness,
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


def test_public_miss_metrics_bound_no_tick_to_raw_missed_count() -> None:
    result = _with_public_miss_metrics(
        {
            "totals": {
                "valid_inferences": 10,
                "missed_inferences": 2,
                "errors": 0,
                "sync_operational_counts": {
                    "no_current_h1_tick": 5,
                },
            }
        }
    )

    assert result["totals"]["no_current_h1_tick_count"] == 2
    assert result["totals"]["processing_miss_count"] == 0
    assert result["totals"]["processing_miss_denominator"] == 10
    assert result["totals"]["processing_miss_rate"] == 0.0


def test_snapshot_freshness_classifies_fresh_delayed_and_stale() -> None:
    now = datetime(2026, 10, 8, 0, 0, tzinfo=timezone.utc)

    fresh = _snapshot_freshness(
        (now - timedelta(seconds=SNAPSHOT_DELAYED_AFTER_SECONDS - 1)).isoformat(),
        now=now,
    )
    delayed = _snapshot_freshness(
        (now - timedelta(seconds=SNAPSHOT_DELAYED_AFTER_SECONDS)).isoformat(),
        now=now,
    )
    stale = _snapshot_freshness(
        (now - timedelta(seconds=SNAPSHOT_STALE_AFTER_SECONDS)).isoformat(),
        now=now,
    )

    assert fresh["snapshot_freshness"] == "fresh"
    assert delayed["snapshot_freshness"] == "delayed"
    assert stale["snapshot_freshness"] == "stale"
    assert fresh["snapshot_age_seconds"] == SNAPSHOT_DELAYED_AFTER_SECONDS - 1
    assert delayed["snapshot_age_seconds"] == SNAPSHOT_DELAYED_AFTER_SECONDS
    assert stale["snapshot_age_seconds"] == SNAPSHOT_STALE_AFTER_SECONDS


def test_snapshot_freshness_handles_invalid_timestamp_without_false_freshness() -> None:
    assert _snapshot_freshness(None) == {
        "snapshot_age_seconds": None,
        "snapshot_freshness": "unknown",
    }
    assert _snapshot_freshness("not-a-time") == {
        "snapshot_age_seconds": None,
        "snapshot_freshness": "unknown",
    }
