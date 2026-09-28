from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from trading_signal_intelligence.ai_v1.engine import process_inference_cycle
from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.ledger import AILedger


@dataclass
class Adapter:
    response: dict[str, Any]
    provider: str = "test"
    model_id: str = "test-model"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"temperature": 0}

    def infer(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
        decision_schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.response, {"request_id": "test"}


def guardrails() -> dict[str, Any]:
    return {
        "max_data_age_seconds": 300,
        "stop_atr_min": 1.0,
        "stop_atr_max": 3.0,
        "tp1_r_min": 0.75,
        "tp1_r_max": 2.0,
        "tp2_r_min": 1.5,
        "tp2_r_max": 4.0,
        "require_tp2_gt_tp1": True,
        "cost_multiplier": 1.25,
        "max_round_trip_cost_r": 0.15,
    }


def snapshot(age: float = 30.0) -> FeatureSnapshot:
    return FeatureSnapshot(
        payload={
            "source_symbol": "XAUUSD",
            "source_bar_open_utc": "2026-09-28T07:00:00Z",
            "source_bar_close_utc": "2026-09-28T08:00:00Z",
            "feature_schema_version": "AI-v1.0",
            "data_age_seconds": age,
            "atr_14": 10.0,
            "spread_price": 0.5,
        },
        sha256="a" * 64,
    )


def no_trade_response() -> dict[str, Any]:
    return {
        "protocol_version": "AI-v1.0",
        "decision": "NO_TRADE",
        "raw_confidence": 40,
        "regime": "MIXED",
        "stop_atr": None,
        "tp1_r": None,
        "tp2_r": None,
        "rationale": "Mixed evidence.",
        "supporting_factors": [],
        "risk_factors": ["mixed"],
    }


def buy_response() -> dict[str, Any]:
    return {
        "protocol_version": "AI-v1.0",
        "decision": "BUY",
        "raw_confidence": 65,
        "regime": "TREND_UP",
        "stop_atr": 1.5,
        "tp1_r": 1.0,
        "tp2_r": 2.0,
        "rationale": "Trend aligned.",
        "supporting_factors": ["trend"],
        "risk_factors": ["volatility"],
    }


def test_stale_cycle_skips_provider(tmp_path) -> None:
    ledger = AILedger(tmp_path / "ai.sqlite")
    adapter = Adapter(response=buy_response())
    called = {"value": False}

    original = adapter.infer

    def wrapped(**kwargs):
        called["value"] = True
        return original(**kwargs)

    adapter.infer = wrapped  # type: ignore[method-assign]

    result = process_inference_cycle(
        ledger=ledger,
        adapter=adapter,
        feature_snapshot=snapshot(age=301.0),
        policy_text="policy",
        decision_schema={"title": "schema"},
        guardrails=guardrails(),
        active_signal_exists=False,
        recorded_at_utc=datetime(2026, 9, 28, 8, 5, 1, tzinfo=timezone.utc),
    )

    assert result.status == "MISSED_INFERENCE"
    assert called["value"] is False
    assert ledger.counts_by_type() == {"MISSED_INFERENCE": 1}


def test_no_trade_cycle_appends_inference_and_abstention(tmp_path) -> None:
    ledger = AILedger(tmp_path / "ai.sqlite")
    result = process_inference_cycle(
        ledger=ledger,
        adapter=Adapter(response=no_trade_response()),
        feature_snapshot=snapshot(),
        policy_text="policy",
        decision_schema={"title": "schema"},
        guardrails=guardrails(),
        active_signal_exists=False,
        recorded_at_utc=datetime(2026, 9, 28, 8, 0, 30, tzinfo=timezone.utc),
    )

    assert result.status == "NO_TRADE"
    assert ledger.counts_by_type() == {"INFERENCE": 1, "NO_TRADE": 1}
    assert ledger.verify()["valid"] is True


def test_buy_cycle_can_be_approved_pending_entry(tmp_path) -> None:
    ledger = AILedger(tmp_path / "ai.sqlite")
    result = process_inference_cycle(
        ledger=ledger,
        adapter=Adapter(response=buy_response()),
        feature_snapshot=snapshot(),
        policy_text="policy",
        decision_schema={"title": "schema"},
        guardrails=guardrails(),
        active_signal_exists=False,
        recorded_at_utc=datetime(2026, 9, 28, 8, 0, 30, tzinfo=timezone.utc),
    )

    assert result.status == "APPROVED_PENDING_ENTRY"
    assert ledger.counts_by_type() == {"INFERENCE": 1}
    assert result.guard_result is not None
    assert result.guard_result.publishable is True
