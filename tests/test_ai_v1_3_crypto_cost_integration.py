from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from trading_signal_intelligence.ai_v1.crypto_cost_v1_3 import (
    CryptoCostPolicyError,
    CryptoExecutionContext,
    calculate_crypto_cost,
    load_crypto_cost_policy,
    validate_execution_context,
)
from trading_signal_intelligence.ai_v1.crypto_engine_v1_3 import (
    process_crypto_inference_cycle,
)
from trading_signal_intelligence.ai_v1.crypto_guardrails_v1_3 import (
    evaluate_crypto_guard,
)
from trading_signal_intelligence.ai_v1.crypto_signals_v1_3 import (
    append_crypto_signal_from_approved_inference,
)
from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.signals import evaluate_signal
from trading_signal_intelligence.models import Candle


ROOT = Path(__file__).resolve().parents[1]
COST_POLICY_PATH = ROOT / "config" / "ai_v1_3_crypto_cost_policy.json"


@dataclass
class Adapter:
    response: dict[str, Any]
    provider: str = "test"
    model_id: str = "test-model"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"reasoning_effort": "medium"}

    def infer(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
        decision_schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        return self.response, {
            "request_id": "crypto-test",
            "usage": {
                "input_tokens": 100,
                "output_tokens": 20,
                "total_tokens": 120,
            },
        }


def cost_policy() -> dict[str, Any]:
    return load_crypto_cost_policy(COST_POLICY_PATH)


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
        "max_round_trip_cost_r": 0.15,
        "entry_policy": "next_eligible_h1_open",
        "max_hold_h1_bars": 24,
        "tp1_position_fraction": 0.5,
        "tp2_position_fraction": 0.5,
        "move_stop_after_tp1": False,
    }


def buy_response(*, stop_atr: float = 2.0) -> dict[str, Any]:
    return {
        "protocol_version": "AI-v1.0",
        "decision": "BUY",
        "raw_confidence": 65,
        "regime": "TREND_UP",
        "stop_atr": stop_atr,
        "tp1_r": 1.0,
        "tp2_r": 2.0,
        "rationale": "Synthetic offline integration test.",
        "supporting_factors": ["trend"],
        "risk_factors": ["volatility"],
    }


def snapshot(
    *,
    symbol: str = "ETHUSDT",
    canonical: str = "ETH/USDT",
    atr: float = 10.0,
    age: float = 30.0,
) -> FeatureSnapshot:
    return FeatureSnapshot(
        payload={
            "feature_schema_version": "AI-crypto-v1.0",
            "source_symbol": symbol,
            "canonical_symbol": canonical,
            "source_bar_open_utc": "2026-10-08T21:00:00Z",
            "source_bar_close_utc": "2026-10-08T22:00:00Z",
            "data_age_seconds": age,
            "atr_14": atr,
            "spread_price": 0.01,
        },
        sha256="a" * 64,
    )


def execution_context(
    *,
    symbol: str = "ETHUSDT",
    midpoint: Decimal = Decimal(1000),
    spread: Decimal = Decimal("0.01"),
    observed_at: datetime | None = None,
) -> CryptoExecutionContext:
    half = spread / Decimal(2)
    return CryptoExecutionContext(
        source="binance_spot",
        source_symbol=symbol,
        observed_at_utc=observed_at
        or datetime(2026, 10, 8, 22, 0, 20, tzinfo=UTC),
        best_bid=midpoint - half,
        best_ask=midpoint + half,
    )


def candle(
    timestamp: datetime,
    *,
    symbol: str = "ETHUSDT",
    canonical: str = "ETH/USDT",
    open_: float,
    high: float,
    low: float,
    close: float,
) -> Candle:
    return Candle(
        source="binance_spot",
        source_symbol=symbol,
        symbol=canonical,
        timeframe="H1",
        timestamp_utc=timestamp,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(1000),
        volume_kind="base_asset_volume",
        spread=None,
        is_closed=True,
    )


def test_k1_btc_cost_diagnostic_matches_frozen_formula() -> None:
    policy = cost_policy()
    now = datetime(2026, 10, 8, 22, 4, 16, 723272, tzinfo=UTC)
    context = execution_context(
        symbol="BTCUSDT",
        midpoint=Decimal("81693.665"),
        spread=Decimal("0.01"),
        observed_at=datetime(2026, 10, 8, 22, 4, 14, 848295, tzinfo=UTC),
    )

    breakdown = calculate_crypto_cost(
        policy=policy,
        context=context,
        source_symbol="BTCUSDT",
        atr_14=535.8925734716352,
        stop_atr=2.0,
        now_utc=now,
        max_data_age_seconds=300,
    )

    assert float(breakdown.round_trip_fee_price) == pytest.approx(163.38733)
    assert float(breakdown.spread_crossing_price) == pytest.approx(0.01)
    assert float(breakdown.slippage_buffer_price) == pytest.approx(0.01)
    assert float(breakdown.total_cost_price) == pytest.approx(163.40733)
    assert float(breakdown.estimated_cost_r) == pytest.approx(
        0.152463, rel=1e-5
    )
    assert breakdown.passes_cost_guard is False


def test_execution_context_staleness_fails_closed() -> None:
    context = execution_context(
        observed_at=datetime(2026, 10, 8, 22, 0, 0, tzinfo=UTC)
    )

    with pytest.raises(CryptoCostPolicyError, match="outside 0..300"):
        validate_execution_context(
            context,
            source_symbol="ETHUSDT",
            now_utc=datetime(2026, 10, 8, 22, 6, 0, tzinfo=UTC),
            max_age_seconds=300,
        )


def test_crypto_guard_accepts_cost_below_frozen_015r_threshold() -> None:
    now = datetime(2026, 10, 8, 22, 0, 30, tzinfo=UTC)
    guard = evaluate_crypto_guard(
        decision_payload=buy_response(stop_atr=2.0),
        feature_snapshot=snapshot().payload,
        guardrails=guardrails(),
        cost_policy=cost_policy(),
        execution_context=execution_context(
            observed_at=now - timedelta(seconds=5)
        ),
        active_signal_exists=False,
        now_utc=now,
    )

    assert guard.publishable is True
    assert guard.reasons == ()
    assert guard.estimated_cost_r == pytest.approx(0.101)
    assert guard.cost_breakdown is not None
    assert guard.cost_breakdown.passes_cost_guard is True


def test_crypto_guard_rejects_cost_above_frozen_015r_threshold() -> None:
    now = datetime(2026, 10, 8, 22, 0, 30, tzinfo=UTC)
    guard = evaluate_crypto_guard(
        decision_payload=buy_response(stop_atr=1.0),
        feature_snapshot=snapshot().payload,
        guardrails=guardrails(),
        cost_policy=cost_policy(),
        execution_context=execution_context(
            observed_at=now - timedelta(seconds=5)
        ),
        active_signal_exists=False,
        now_utc=now,
    )

    assert guard.publishable is False
    assert "cost_too_high" in guard.reasons
    assert guard.estimated_cost_r == pytest.approx(0.202)


def test_crypto_engine_rejects_invalid_context_before_provider_call(
    tmp_path: Path,
) -> None:
    ledger = AILedger(tmp_path / "crypto.sqlite")
    adapter = Adapter(response=buy_response())
    called = {"value": False}
    original = adapter.infer

    def wrapped(**kwargs: Any) -> tuple[dict[str, Any], dict[str, Any]]:
        called["value"] = True
        return original(**kwargs)

    adapter.infer = wrapped  # type: ignore[method-assign]

    now = datetime(2026, 10, 8, 22, 0, 30, tzinfo=UTC)
    stale_context = execution_context(
        observed_at=now - timedelta(seconds=301)
    )

    result = process_crypto_inference_cycle(
        ledger=ledger,
        adapter=adapter,
        feature_snapshot=snapshot(),
        execution_context=stale_context,
        cost_policy=cost_policy(),
        policy_text="policy",
        decision_schema={"title": "schema"},
        guardrails=guardrails(),
        active_signal_exists=False,
        recorded_at_utc=now,
    )

    assert result.status == "ERROR"
    assert called["value"] is False
    assert result.terminal_record is not None
    payload = result.terminal_record["payload"]
    assert payload["stage"] == "crypto_execution_cost_context"
    assert payload["provider_call_made"] is False
    assert ledger.counts_by_type() == {"ERROR": 1}


def test_crypto_engine_freezes_cost_breakdown_in_inference(
    tmp_path: Path,
) -> None:
    ledger = AILedger(tmp_path / "crypto.sqlite")
    now = datetime(2026, 10, 8, 22, 0, 30, tzinfo=UTC)

    result = process_crypto_inference_cycle(
        ledger=ledger,
        adapter=Adapter(response=buy_response()),
        feature_snapshot=snapshot(),
        execution_context=execution_context(
            observed_at=now - timedelta(seconds=5)
        ),
        cost_policy=cost_policy(),
        policy_text="policy",
        decision_schema={"title": "schema"},
        guardrails=guardrails(),
        active_signal_exists=False,
        recorded_at_utc=now,
    )

    assert result.status == "APPROVED_PENDING_ENTRY"
    assert result.inference_record is not None
    payload = result.inference_record["payload"]
    assert payload["runtime_version"] == "AI-v1.3"
    assert payload["guard_publishable"] is True
    assert payload["crypto_execution_context"]["midpoint"] == pytest.approx(1000)
    assert payload["crypto_execution_context"]["spread_price"] == pytest.approx(
        0.01
    )
    assert len(payload["crypto_cost_policy_sha256"]) == 64
    cost = payload["crypto_cost_breakdown"]
    assert cost["total_cost_price"] == pytest.approx(2.02)
    assert cost["estimated_cost_r"] == pytest.approx(0.101)
    assert cost["passes_cost_guard"] is True
    assert payload["broker_execution_enabled"] is False
    assert payload["public_signal_exposure_enabled"] is False
    assert ledger.verify()["valid"] is True


def test_crypto_signal_and_lifecycle_use_frozen_cost_without_recalculation(
    tmp_path: Path,
) -> None:
    ledger = AILedger(tmp_path / "crypto.sqlite")
    now = datetime(2026, 10, 8, 22, 0, 30, tzinfo=UTC)
    result = process_crypto_inference_cycle(
        ledger=ledger,
        adapter=Adapter(response=buy_response()),
        feature_snapshot=snapshot(),
        execution_context=execution_context(
            observed_at=now - timedelta(seconds=5)
        ),
        cost_policy=cost_policy(),
        policy_text="policy",
        decision_schema={"title": "schema"},
        guardrails=guardrails(),
        active_signal_exists=False,
        recorded_at_utc=now,
    )
    assert result.status == "APPROVED_PENDING_ENTRY"

    entry = candle(
        datetime(2026, 10, 8, 22, 0, tzinfo=UTC),
        open_=1000,
        high=1001,
        low=999,
        close=1000,
    )
    signal = append_crypto_signal_from_approved_inference(
        ledger=ledger,
        entity_id=result.entity_id,
        entry_bar=entry,
        guardrails=guardrails(),
        recorded_at_utc=now,
    )

    signal_payload = signal["payload"]
    assert signal_payload["total_cost_price"] == pytest.approx(2.02)
    assert signal_payload["estimated_cost_r"] == pytest.approx(0.101)
    assert signal_payload["reference_midpoint"] == pytest.approx(1000)
    assert signal_payload["broker_execution_enabled"] is False
    assert signal_payload["public_signal_exposure_enabled"] is False

    bar1 = candle(
        datetime(2026, 10, 8, 22, 0, tzinfo=UTC),
        open_=1000,
        high=1021,
        low=995,
        close=1019,
    )
    bar2 = candle(
        datetime(2026, 10, 8, 23, 0, tzinfo=UTC),
        open_=1019,
        high=1041,
        low=1015,
        close=1040,
    )
    actions = evaluate_signal(
        ledger=ledger,
        entity_id=result.entity_id,
        closed_h1=[bar1, bar2],
        recorded_at_utc=datetime(2026, 10, 9, 0, 0, tzinfo=UTC),
    )

    assert [row["record_type"] for row in actions] == [
        "PARTIAL_EXIT",
        "EXIT",
    ]
    partial = actions[0]["payload"]
    final = actions[1]["payload"]

    assert partial["cost_contribution_r"] == pytest.approx(0.0505)
    assert final["cost_contribution_r"] == pytest.approx(0.0505)
    assert (
        partial["cost_contribution_r"] + final["cost_contribution_r"]
    ) == pytest.approx(0.101)
    assert final["total_combined_signal_net_r"] == pytest.approx(1.399)
    assert ledger.verify()["valid"] is True


def test_cost_policy_json_remains_machine_readable_and_frozen() -> None:
    raw = json.loads(COST_POLICY_PATH.read_text(encoding="utf-8"))
    assert raw["policy_version"] == "AI-v1.3-crypto-cost-v0.1"
    assert raw["activation_constraints"]["numeric_cost_policy_frozen"] is True
    assert raw["activation_constraints"]["broker_execution_enabled"] is False
