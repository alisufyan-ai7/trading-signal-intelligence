from __future__ import annotations

from datetime import datetime, timezone

from trading_signal_intelligence.ai_v1.mt5_boundary_probe import (
    next_hour_boundary,
    summarize_observations,
)


def test_next_hour_boundary() -> None:
    now = datetime(2026, 9, 29, 18, 43, 12, tzinfo=timezone.utc)
    assert next_hour_boundary(now) == datetime(
        2026, 9, 29, 19, 0, 0, tzinfo=timezone.utc
    )


def test_summary_detects_index_row_after_nominal_scheduler() -> None:
    boundary = datetime(2026, 9, 29, 19, 0, 0, tzinfo=timezone.utc)
    observations = [
        {
            "symbol": "XAUUSD",
            "observed_at_utc": "2026-09-29T19:00:10Z",
            "seconds_from_boundary": 10.0,
            "read_ok": True,
            "boundary_row_present": True,
            "latest_h1_open_utc": "2026-09-29T19:00:00Z",
            "latest_tick_utc": "2026-09-29T19:00:09Z",
        },
        {
            "symbol": "USTEC",
            "observed_at_utc": "2026-09-29T19:02:00Z",
            "seconds_from_boundary": 120.0,
            "read_ok": True,
            "boundary_row_present": False,
            "latest_h1_open_utc": "2026-09-29T18:00:00Z",
            "latest_tick_utc": "2026-09-29T18:59:50Z",
        },
        {
            "symbol": "USTEC",
            "observed_at_utc": "2026-09-29T19:02:40Z",
            "seconds_from_boundary": 160.0,
            "read_ok": True,
            "boundary_row_present": True,
            "latest_h1_open_utc": "2026-09-29T19:00:00Z",
            "latest_tick_utc": "2026-09-29T19:02:39Z",
        },
        {
            "symbol": "US30",
            "observed_at_utc": "2026-09-29T19:02:00Z",
            "seconds_from_boundary": 120.0,
            "read_ok": True,
            "boundary_row_present": False,
            "latest_h1_open_utc": "2026-09-29T18:00:00Z",
            "latest_tick_utc": "2026-09-29T18:59:48Z",
        },
        {
            "symbol": "US30",
            "observed_at_utc": "2026-09-29T19:03:10Z",
            "seconds_from_boundary": 190.0,
            "read_ok": True,
            "boundary_row_present": True,
            "latest_h1_open_utc": "2026-09-29T19:00:00Z",
            "latest_tick_utc": "2026-09-29T19:03:09Z",
        },
    ]

    result = summarize_observations(observations, boundary_utc=boundary)

    assert result["markets"]["XAUUSD"]["first_boundary_row_seen_offset_seconds"] == 10.0
    assert result["markets"]["USTEC"]["first_boundary_row_seen_offset_seconds"] == 160.0
    assert result["markets"]["US30"]["first_boundary_row_seen_offset_seconds"] == 190.0
    assert result["markets"]["USTEC"]["first_seen_after_nominal_scheduler_120s"] is True
    assert result["markets"]["US30"]["first_seen_after_nominal_scheduler_120s"] is True
    assert result["markets"]["USTEC"][
        "closest_observation_to_scheduler_120s"
    ]["boundary_row_present"] is False
    assert result["markets"]["US30"][
        "closest_observation_to_scheduler_120s"
    ]["boundary_row_present"] is False
    assert result["comparison"]["ustec_minus_xau_seconds"] == 150.0
    assert result["comparison"]["us30_minus_xau_seconds"] == 180.0
    assert result["provider_call_made"] is False
    assert result["ledger_write_made"] is False
    assert result["broker_order_made"] is False
    assert result["symbol_selection_made"] is False


def test_summary_handles_boundary_row_not_seen() -> None:
    boundary = datetime(2026, 9, 29, 19, 0, 0, tzinfo=timezone.utc)
    observations = [
        {
            "symbol": "USTEC",
            "observed_at_utc": "2026-09-29T19:02:00Z",
            "seconds_from_boundary": 120.0,
            "read_ok": True,
            "boundary_row_present": False,
            "latest_h1_open_utc": "2026-09-29T18:00:00Z",
            "latest_tick_utc": "2026-09-29T18:59:50Z",
        }
    ]

    result = summarize_observations(observations, boundary_utc=boundary)
    assert result["markets"]["USTEC"]["first_boundary_row_seen_at_utc"] is None
    assert result["markets"]["USTEC"][
        "first_boundary_row_seen_offset_seconds"
    ] is None
