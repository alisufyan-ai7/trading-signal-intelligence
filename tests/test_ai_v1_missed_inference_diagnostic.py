from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.missed_inference_diagnostic import (
    _delay_bucket,
    _diagnosis,
    _market_summary,
    _same_close_comparison,
)
from trading_signal_intelligence.ai_v1.observability import read_records_read_only


def _append(
    ledger: AILedger,
    *,
    record_type: str,
    symbol: str,
    close: datetime,
    recorded: datetime,
    payload: dict,
) -> None:
    ledger.append(
        record_type=record_type,
        entity_id=f"AI-v1.0:{symbol}:{close.isoformat()}",
        effective_at_utc=close,
        recorded_at_utc=recorded,
        payload=payload,
    )


def test_delay_bucket_distinguishes_fresh_and_one_hour_late() -> None:
    assert _delay_bucket(120.0) == "fresh_le_300s"
    assert _delay_bucket(301.0) == "late_5_to_30m"
    assert _delay_bucket(3700.0) == "late_about_1h"
    assert _delay_bucket(9100.0) == "late_over_150m"


def test_market_summary_reports_missed_reason_and_delay(tmp_path: Path) -> None:
    path = tmp_path / "ledger.sqlite"
    ledger = AILedger(path)
    close = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)

    _append(
        ledger,
        record_type="MISSED_INFERENCE",
        symbol="USTEC",
        close=close,
        recorded=close + timedelta(seconds=3720),
        payload={
            "source_symbol": "USTEC",
            "source_bar_close_utc": close.isoformat().replace("+00:00", "Z"),
            "detected_at_utc": (close + timedelta(seconds=3720)).isoformat(),
            "data_age_seconds": 3720.0,
            "max_data_age_seconds": 300.0,
            "reason": "scheduler_gap_or_stale_at_discovery",
        },
    )

    records = read_records_read_only(path)
    result = _market_summary("USTEC", records)

    assert result["missed_inferences"] == 1
    assert result["missed_reason_counts"] == {
        "scheduler_gap_or_stale_at_discovery": 1
    }
    assert result["missed_delay_bucket_counts"] == {"late_about_1h": 1}
    assert result["missed_about_one_hour_late_fraction"] == 1.0


def test_cross_market_comparison_detects_xau_fresh_same_close(tmp_path: Path) -> None:
    close = datetime(2026, 9, 29, 10, 0, tzinfo=timezone.utc)
    records_by_market = {}

    for symbol in ("XAUUSD", "USTEC", "US30"):
        path = tmp_path / f"{symbol}.sqlite"
        ledger = AILedger(path)
        if symbol == "XAUUSD":
            _append(
                ledger,
                record_type="INFERENCE",
                symbol=symbol,
                close=close,
                recorded=close + timedelta(seconds=120),
                payload={
                    "source_symbol": symbol,
                    "source_bar_close_utc": close.isoformat().replace("+00:00", "Z"),
                },
            )
        else:
            _append(
                ledger,
                record_type="MISSED_INFERENCE",
                symbol=symbol,
                close=close,
                recorded=close + timedelta(seconds=3720),
                payload={
                    "source_symbol": symbol,
                    "source_bar_close_utc": close.isoformat().replace("+00:00", "Z"),
                    "data_age_seconds": 3720.0,
                    "reason": "scheduler_gap_or_stale_at_discovery",
                },
            )
        records_by_market[symbol] = read_records_read_only(path)

    result = _same_close_comparison(records_by_market)
    assert result["index_missed_cycles"] == 2
    assert result["xauusd_inference_same_close_count"] == 2
    assert result["xauusd_inference_same_close_fraction"] == 1.0


def test_diagnosis_requires_pattern_not_single_miss() -> None:
    markets = {
        "XAUUSD": {"missed_inferences": 0, "missed_reason_counts": {}, "missed_delay_bucket_counts": {}},
        "USTEC": {
            "missed_inferences": 5,
            "missed_reason_counts": {"scheduler_gap_or_stale_at_discovery": 5},
            "missed_delay_bucket_counts": {"late_about_1h": 4, "late_5_to_30m": 1},
        },
        "US30": {
            "missed_inferences": 5,
            "missed_reason_counts": {"scheduler_gap_or_stale_at_discovery": 5},
            "missed_delay_bucket_counts": {"late_about_1h": 5},
        },
    }
    sync = {
        "xauusd_inference_same_close_fraction": 0.8,
    }
    result = _diagnosis(markets, sync)
    assert result["classification"] == "CONSISTENT_WITH_LATE_INDEX_BAR_DISCOVERY"
    assert result["decision_affecting_change_made"] is False
