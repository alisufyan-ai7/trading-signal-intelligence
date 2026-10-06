from __future__ import annotations

from pathlib import Path

from trading_signal_intelligence.ai_v1.expansion_v1_2 import (
    review_gates_report,
)
from trading_signal_intelligence.ai_v1.observability_v1_2 import (
    TASK_NAME,
)


ROOT = Path(__file__).resolve().parents[1]


def test_v1_2_observability_uses_distinct_scheduler_identity() -> None:
    assert TASK_NAME == "VowSig AI-v1.2 Expansion Shadow Scan"
    assert TASK_NAME != "SignalProof AI-v1.1 Shadow Scan"


def test_v1_2_observability_gates_are_x1_x2_x3() -> None:
    report = review_gates_report(ROOT)
    assert report["valid"] is True
    gates = report["gates"]
    assert set(gates) == {"X1", "X2", "X3"}
    assert gates["X1"]["valid_inferences"] == 100
    assert gates["X1"]["completed_shadow_trades"] == 20
    assert gates["X1"]["minimum_calendar_days"] == 0
    assert gates["X2"]["valid_inferences"] == 500
    assert gates["X2"]["completed_shadow_trades"] == 50
    assert gates["X2"]["minimum_calendar_days"] == 60
    assert gates["X3"]["valid_inferences"] == 1000
    assert gates["X3"]["completed_shadow_trades"] == 100
    assert gates["X3"]["minimum_calendar_days"] == 120


def test_v1_2_observability_preserves_processing_miss_semantics() -> None:
    text = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "observability_v1_2.py"
    ).read_text(encoding="utf-8")

    assert 'no_current_h1_tick = missed_reason_counts.get(' in text
    assert "processing_miss_count = missed - no_current_h1_tick" in text
    assert (
        '"processing_miss_rate_excluding_no_current_h1_tick"'
        in text
    )


def test_v1_2_observability_requires_per_market_reporting() -> None:
    text = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "observability_v1_2.py"
    ).read_text(encoding="utf-8")

    assert '"per_market_reporting_required": True' in text
    assert '"markets": markets' in text
    assert '"public_exposure_disabled": public_disabled' in text
    assert '"broker_execution_disabled": broker_disabled' in text
