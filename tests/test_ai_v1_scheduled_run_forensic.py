from __future__ import annotations

import json

from trading_signal_intelligence.ai_v1.scheduled_run_forensic import (
    extract_run_summaries,
    extract_wrapper_results,
)


def test_extract_run_summary_from_mixed_log() -> None:
    payload = {
        "protocol_version": "AI-v1.0",
        "run_mode": "SHADOW_ONLY",
        "market_results": {
            "XAUUSD": {
                "scanned_at_utc": "2026-09-29T20:02:01+00:00",
                "actions": [],
            }
        },
        "failures": {"USTEC": "RuntimeError: sample"},
    }
    text = "noise\n" + json.dumps(payload, indent=2) + "\nmore noise"
    rows = extract_run_summaries(text)
    assert len(rows) == 1
    assert rows[0]["failures"]["USTEC"].startswith("RuntimeError")


def test_extract_wrapper_results() -> None:
    text = "run_exit=2 verify_exit=0\nrun_exit=0 verify_exit=0\n"
    rows = extract_wrapper_results(text)
    assert rows == [
        {"run_exit": 2, "verify_exit": 0},
        {"run_exit": 0, "verify_exit": 0},
    ]
