from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.engine_v1_2 import (
    RUNTIME_VERSION,
    process_inference_cycle_v1_2,
)
from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
from trading_signal_intelligence.ai_v1.ledger import AILedger
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_2 import (
    DATABASE_PATHS,
    MARKETS,
    cycle_entity_id_v1_2,
    market_specs_v1_2,
)


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def test_v1_2_runtime_identity_and_separate_ledger_paths() -> None:
    assert RUNTIME_VERSION == "AI-v1.2"
    assert MARKETS == ("EURUSD", "XAGUSD", "USOIL")
    assert DATABASE_PATHS == {
        "EURUSD": "data/ai_v1_2_eurusd.sqlite",
        "XAGUSD": "data/ai_v1_2_xagusd.sqlite",
        "USOIL": "data/ai_v1_2_usoil.sqlite",
    }
    assert set(DATABASE_PATHS.values()).isdisjoint(
        {
            "data/ai_v1_1_xauusd.sqlite",
            "data/ai_v1_1_ustec.sqlite",
            "data/ai_v1_1_us30.sqlite",
        }
    )

    specs = market_specs_v1_2(ROOT)
    assert specs["EURUSD"].database_path.name == "ai_v1_2_eurusd.sqlite"
    assert specs["XAGUSD"].database_path.name == "ai_v1_2_xagusd.sqlite"
    assert specs["USOIL"].database_path.name == "ai_v1_2_usoil.sqlite"


def test_v1_2_entity_id_is_runtime_isolated() -> None:
    close = datetime(2026, 10, 7, 1, 0, tzinfo=UTC)
    assert cycle_entity_id_v1_2("EURUSD", close) == (
        "AI-v1.2:EURUSD:2026-10-07T01:00:00Z"
    )


class NeverCallAdapter:
    provider = "test"
    model_id = "test-model"
    parameters = {}

    def __init__(self) -> None:
        self.calls = 0

    def infer(self, **kwargs):
        self.calls += 1
        raise AssertionError("provider must not be called for stale data")


def test_v1_2_stale_snapshot_skips_provider_and_ai_v1_1_ledgers(
    tmp_path: Path,
) -> None:
    feature_payload = {
        "feature_schema_version": "AI-v1.0",
        "source_symbol": "EURUSD",
        "canonical_symbol": "EUR/USD",
        "source_bar_open_utc": "2026-10-07T00:00:00Z",
        "source_bar_close_utc": "2026-10-07T01:00:00Z",
        "inference_started_utc": "2026-10-07T01:05:01Z",
        "data_age_seconds": 301.0,
    }
    snapshot = FeatureSnapshot(payload=feature_payload, sha256="a" * 64)
    guardrails = {"max_data_age_seconds": 300}

    parallel = AILedger(tmp_path / "ai_v1_1_xauusd.sqlite")
    expansion = AILedger(tmp_path / "ai_v1_2_eurusd.sqlite")
    adapter = NeverCallAdapter()

    result = process_inference_cycle_v1_2(
        ledger=expansion,
        adapter=adapter,
        feature_snapshot=snapshot,
        policy_text="frozen",
        decision_schema={},
        guardrails=guardrails,
        active_signal_exists=False,
        recorded_at_utc=datetime(2026, 10, 7, 1, 5, 1, tzinfo=UTC),
    )

    assert result.status == "MISSED_INFERENCE"
    assert result.entity_id.startswith("AI-v1.2:EURUSD:")
    assert result.terminal_record is not None
    assert result.terminal_record["payload"]["runtime_version"] == "AI-v1.2"
    assert result.terminal_record["payload"]["protocol_version"] == "AI-v1.0"
    assert result.terminal_record["payload"]["provider_call_made"] is False
    assert adapter.calls == 0
    assert parallel.records() == []
    assert len(expansion.records()) == 1
