from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_signal_intelligence.ai_v1.features import build_feature_snapshot
from trading_signal_intelligence.ai_v1.guardrails import evaluate_guard
from trading_signal_intelligence.ai_v1.inference import run_inference
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.models import Candle


ROOT = Path(__file__).resolve().parents[1]
S02_DATABASES = [
    ROOT / "data" / "forward.sqlite",
    ROOT / "data" / "forward_ustec.sqlite",
    ROOT / "data" / "forward_us30.sqlite",
]


def file_sha256(path: Path) -> str | None:
    if not path.exists():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def s02_hashes() -> dict[str, str | None]:
    return {str(path.relative_to(ROOT)): file_sha256(path) for path in S02_DATABASES}


def candle(timeframe: str, ts: datetime, index: int, spread: float) -> Candle:
    step = 0.12 if timeframe == "H1" else 0.45
    close = 4000.0 + step * index + 0.15 * ((index % 7) - 3)
    open_ = close - 0.2
    high = max(open_, close) + 1.0 + 0.01 * (index % 5)
    low = min(open_, close) - 0.9 - 0.01 * (index % 3)
    return Candle(
        source="exness_mt5_demo",
        source_symbol="XAUUSD",
        symbol="XAU/USD",
        timeframe=timeframe,
        timestamp_utc=ts,
        open=Decimal(str(open_)),
        high=Decimal(str(high)),
        low=Decimal(str(low)),
        close=Decimal(str(close)),
        volume=Decimal(str(1000 + (index % 23) * 17)),
        volume_kind="tick",
        spread=Decimal(str(spread)),
        is_closed=True,
    )


@dataclass
class LocalSmokeAdapter:
    provider: str = "local-smoke"
    model_id: str = "no-provider-call"

    @property
    def parameters(self) -> dict[str, Any]:
        return {"mode": "deterministic_test"}

    def infer(
        self,
        *,
        policy_text: str,
        feature_snapshot: dict[str, Any],
        decision_schema: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        if not policy_text or not decision_schema:
            raise RuntimeError("frozen policy/schema not loaded")
        if feature_snapshot["feature_schema_version"] != "AI-v1.0":
            raise RuntimeError("unexpected feature schema version")
        return (
            {
                "protocol_version": "AI-v1.0",
                "decision": "BUY",
                "raw_confidence": 64,
                "regime": "TREND_UP",
                "stop_atr": 1.5,
                "tp1_r": 1.0,
                "tp2_r": 2.0,
                "rationale": "Synthetic foundation smoke.",
                "supporting_factors": ["trend_up"],
                "risk_factors": ["test_only"],
            },
            {
                "request_id": "local-smoke",
                "authorization": "must-not-be-retained",
            },
        )


def main() -> None:
    s02_before = s02_hashes()

    guardrails = json.loads(
        (ROOT / "config" / "ai_v1_guardrails.json").read_text(encoding="utf-8")
    )
    feature_schema = json.loads(
        (ROOT / "config" / "ai_v1_feature_schema.json").read_text(encoding="utf-8")
    )
    decision_schema = json.loads(
        (ROOT / "config" / "ai_v1_decision_schema.json").read_text(encoding="utf-8")
    )
    json.loads(
        (ROOT / "config" / "ai_v1_activation_schema.json").read_text(encoding="utf-8")
    )
    policy = (ROOT / "config" / "ai_v1_policy.txt").read_text(encoding="utf-8")

    if feature_schema["title"] != "SignalProof AI-v1 feature snapshot":
        raise RuntimeError("unexpected feature schema")
    if decision_schema["title"] != "SignalProof AI-v1 model decision":
        raise RuntimeError("unexpected decision schema")

    start = datetime(2026, 1, 1, tzinfo=timezone.utc)
    h1 = [candle("H1", start + timedelta(hours=i), i, 125.0) for i in range(420)]
    h4 = [candle("H4", start + timedelta(hours=4 * i), i, 125.0) for i in range(110)]
    inference_time = h1[-1].timestamp_utc + timedelta(hours=1, minutes=2)

    snapshot = build_feature_snapshot(
        h1_candles=h1,
        h4_candles=h4,
        point_size=0.001,
        inference_started_utc=inference_time,
        source_symbol="XAUUSD",
        canonical_symbol="XAU/USD",
    )

    inference = run_inference(
        adapter=LocalSmokeAdapter(),
        feature_snapshot=snapshot,
        policy_text=policy,
        decision_schema=decision_schema,
    )
    if "authorization" in inference.metadata:
        raise RuntimeError("sensitive inference metadata was retained")

    guard = evaluate_guard(
        decision_payload=inference.decision,
        feature_snapshot=snapshot.payload,
        guardrails=guardrails,
        active_signal_exists=False,
    )
    if not guard.publishable:
        raise RuntimeError(f"guard unexpectedly rejected smoke proposal: {guard.reasons}")

    now = datetime(2026, 9, 28, 7, 0, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as temp:
        ledger = AILedger(Path(temp) / "ai.sqlite")
        activation = ledger.append(
            record_type="ACTIVATION",
            entity_id="AI-v1.0:XAUUSD:ACTIVATION",
            effective_at_utc=now,
            recorded_at_utc=now,
            payload={"protocol_version": "AI-v1.0", "test_only": True},
        )
        record = ledger.append(
            record_type="INFERENCE",
            entity_id="AI-v1.0:XAUUSD:2026-09-28T08:00:00Z",
            effective_at_utc=now,
            recorded_at_utc=now,
            payload={
                "feature_snapshot_sha256": snapshot.sha256,
                "decision": inference.decision,
                "test_only": True,
            },
        )
        if record["previous_hash"] != activation["record_hash"]:
            raise RuntimeError("AI ledger hash chain failed")
        verification = ledger.verify()
        if not verification["valid"]:
            raise RuntimeError(f"AI ledger verification failed: {verification}")

        with sqlite3.connect(ledger.path) as connection:
            try:
                connection.execute(
                    "UPDATE ai_records SET entity_id='changed' WHERE sequence=1"
                )
            except sqlite3.DatabaseError:
                pass
            else:
                raise RuntimeError("AI ledger UPDATE protection failed")

    s02_after = s02_hashes()
    if s02_before != s02_after:
        raise RuntimeError(
            "S02 database hash changed during AI-v1 foundation smoke"
        )

    print(
        json.dumps(
            {
                "ai_v1_foundation_smoke": "PASS",
                "feature_snapshot_sha256": snapshot.sha256,
                "inference_adapter_exercised": True,
                "provider_call_made": False,
                "metadata_filter_passed": True,
                "guard_publishable": guard.publishable,
                "estimated_cost_r": guard.estimated_cost_r,
                "ledger_verified": True,
                "s02_database_hashes_unchanged": True,
                "broker_execution_enabled": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
