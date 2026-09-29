from __future__ import annotations

from trading_signal_intelligence.ai_v1.historical_tick_boundary import (
    classify_tick_relation,
    summarize_cases,
)


def test_classify_tick_relation() -> None:
    assert classify_tick_relation(
        outcome="MISSED_INFERENCE",
        scan_offset_seconds=140.0,
        first_tick_offset_seconds=180.0,
        tick_history_available=True,
    ) == "missed_first_tick_after_scan"

    assert classify_tick_relation(
        outcome="INFERENCE",
        scan_offset_seconds=145.0,
        first_tick_offset_seconds=10.0,
        tick_history_available=True,
    ) == "valid_first_tick_before_or_at_scan"

    assert classify_tick_relation(
        outcome="MISSED_INFERENCE",
        scan_offset_seconds=140.0,
        first_tick_offset_seconds=None,
        tick_history_available=True,
    ) == "missed_no_tick_within_window"


def test_summary_supports_first_tick_mechanism() -> None:
    cases = (
        [{"classification": "missed_first_tick_after_scan"}] * 8
        + [{"classification": "missed_first_tick_before_or_at_scan"}] * 2
        + [{"classification": "valid_first_tick_before_or_at_scan"}] * 4
    )
    result = summarize_cases(cases)
    assert result["missed_cases"] == 10
    assert result["valid_cases"] == 4
    assert result["missed_support_fraction"] == 0.8
    assert result["valid_expected_fraction"] == 1.0
    assert result["diagnosis"] == "FIRST_TICK_AFTER_SCAN_MECHANISM_SUPPORTED"


def test_summary_does_not_overclaim_mixed_evidence() -> None:
    cases = (
        [{"classification": "missed_first_tick_after_scan"}] * 2
        + [{"classification": "missed_first_tick_before_or_at_scan"}] * 8
        + [{"classification": "valid_first_tick_before_or_at_scan"}] * 3
    )
    result = summarize_cases(cases)
    assert result["diagnosis"] == "FIRST_TICK_MECHANISM_NOT_CONFIRMED"
