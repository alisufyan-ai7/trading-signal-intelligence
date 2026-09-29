from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.rates_cache_correlation import (
    extract_probe_accesses,
    extract_s02_secondary_scans,
    summarize_correlation,
)


def test_extract_s02_secondary_scans() -> None:
    text = "\n".join(
        [
            json.dumps(
                {
                    "scanned_at_utc": "2026-09-29T19:03:10+00:00",
                    "test_entity": "S02-v0.1:USTEC:SECONDARY",
                    "actions": [],
                }
            ),
            json.dumps(
                {
                    "scanned_at_utc": "2026-09-29T19:03:20+00:00",
                    "test_entity": "S02-v0.1:US30:SECONDARY",
                    "actions": [],
                }
            ),
        ]
    )
    result = extract_s02_secondary_scans(text)
    assert result["USTEC"] == [
        datetime(2026, 9, 29, 19, 3, 10, tzinfo=timezone.utc)
    ]
    assert result["US30"] == [
        datetime(2026, 9, 29, 19, 3, 20, tzinfo=timezone.utc)
    ]


def test_extract_probe_accesses(tmp_path: Path) -> None:
    path = tmp_path / "ai_v1_index_h1_boundary_probe_20260929T200000Z.jsonl"
    path.write_text(
        json.dumps(
            {
                "symbol": "USTEC",
                "observed_at_utc": "2026-09-29T20:01:50Z",
            }
        )
        + "\n"
        + json.dumps(
            {
                "symbol": "US30",
                "observed_at_utc": "2026-09-29T20:01:51Z",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    result = extract_probe_accesses(tmp_path)
    assert len(result["USTEC"]) == 1
    assert len(result["US30"]) == 1


def test_summary_reports_correlation_without_causation() -> None:
    cases = [
        {
            "outcome": "INFERENCE",
            "known_pre_ai_same_hour_access": True,
            "probe_pre_ai_access_count": 1,
            "s02_pre_ai_same_hour_count": 0,
            "nearest_prior_s02_scan_utc": "2026-09-29T19:03:00Z",
        },
        {
            "outcome": "MISSED_INFERENCE",
            "known_pre_ai_same_hour_access": False,
            "probe_pre_ai_access_count": 0,
            "s02_pre_ai_same_hour_count": 0,
            "nearest_prior_s02_scan_utc": "2026-09-29T19:03:00Z",
        },
    ]
    result = summarize_correlation(cases)
    assert result["valid_cycles"] == 1
    assert result["missed_cycles"] == 1
    assert result["valid_known_pre_ai_same_hour_fraction"] == 1.0
    assert result["missed_known_pre_ai_same_hour_fraction"] == 0.0
    assert "Correlation only" in result["interpretation"]
