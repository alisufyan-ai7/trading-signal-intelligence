from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from trading_signal_intelligence.ai_v1.engine_v1_1 import (
    RUNTIME_VERSION,
)
from trading_signal_intelligence.ai_v1.mt5_rates_adapter_v1_1 import (
    read_synchronized_market_bars,
)
from trading_signal_intelligence.ai_v1.shadow_runtime_v1_1 import (
    DATABASE_PATHS,
    cycle_entity_id_v1_1,
    market_specs_v1_1,
)
from trading_signal_intelligence.models import Candle, Quote


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


class Clock:
    def __init__(self) -> None:
        self.value = 0.0

    def monotonic(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


def candle(
    ts: datetime,
    *,
    timeframe: str,
    closed: bool,
    symbol: str = "USTEC",
) -> Candle:
    return Candle(
        source="exness_mt5_demo",
        source_symbol=symbol,
        symbol="NASDAQ 100",
        timeframe=timeframe,
        timestamp_utc=ts,
        open=Decimal("100"),
        high=Decimal("101"),
        low=Decimal("99"),
        close=Decimal("100.5"),
        volume=Decimal("10"),
        volume_kind="tick_volume",
        spread=Decimal("1"),
        is_closed=closed,
    )


class FakeConnector:
    def __init__(self, *, scan: datetime) -> None:
        self.scan = scan
        self.calls = 0

    def latest_quote(self, source_symbol: str, canonical_symbol: str) -> Quote:
        return Quote(
            source="exness_mt5_demo",
            source_symbol=source_symbol,
            symbol=canonical_symbol,
            timestamp_utc=self.scan,
            bid=Decimal("100"),
            ask=Decimal("101"),
            last=Decimal("100.5"),
        )

    def bars_from_pos(
        self,
        source_symbol: str,
        canonical_symbol: str,
        timeframe: str,
        start_pos: int,
        count: int,
        *,
        current_bar_is_closed: bool = False,
    ) -> list[Candle]:
        if timeframe == "H1":
            self.calls += 1
            current = self.scan.replace(minute=0, second=0, microsecond=0)
            newest = (
                current - timedelta(hours=1)
                if self.calls == 1
                else current
            )
            return [
                candle(
                    newest - timedelta(hours=1),
                    timeframe="H1",
                    closed=True,
                ),
                candle(newest, timeframe="H1", closed=False),
            ]

        current_h4 = self.scan.replace(
            hour=(self.scan.hour // 4) * 4,
            minute=0,
            second=0,
            microsecond=0,
        )
        return [
            candle(
                current_h4 - timedelta(hours=4),
                timeframe="H4",
                closed=True,
            ),
            candle(current_h4, timeframe="H4", closed=False),
        ]


def test_v1_1_runtime_identity_and_separate_ledger_paths() -> None:
    assert RUNTIME_VERSION == "AI-v1.1"
    assert DATABASE_PATHS == {
        "XAUUSD": "data/ai_v1_1_xauusd.sqlite",
        "USTEC": "data/ai_v1_1_ustec.sqlite",
        "US30": "data/ai_v1_1_us30.sqlite",
    }
    specs = market_specs_v1_1(ROOT)
    assert specs["XAUUSD"].database_path.name == "ai_v1_1_xauusd.sqlite"
    assert specs["USTEC"].database_path.name == "ai_v1_1_ustec.sqlite"
    assert specs["US30"].database_path.name == "ai_v1_1_us30.sqlite"


def test_v1_1_entity_id_does_not_collide_with_v1_0() -> None:
    close = datetime(2026, 9, 30, 8, 0, tzinfo=UTC)
    assert cycle_entity_id_v1_1("USTEC", close) == (
        "AI-v1.1:USTEC:2026-09-30T08:00:00Z"
    )


def test_mt5_adapter_retries_stale_first_h1_snapshot() -> None:
    scan = datetime(2026, 9, 30, 8, 2, 10, tzinfo=UTC)
    clock = Clock()
    connector = FakeConnector(scan=scan)

    result = read_synchronized_market_bars(
        connector=connector,
        source_symbol="USTEC",
        canonical_symbol="NASDAQ 100",
        scan_started_utc=scan,
        h1_count=500,
        h4_count=200,
        monotonic=clock.monotonic,
        sleep=clock.sleep,
        max_wait_seconds=5,
        poll_interval_seconds=1,
    )

    assert result.synchronization.ready is True
    assert result.synchronization.attempts == 2
    assert result.synchronization.waited_seconds == 1.0
    assert result.h1_all[-1].timestamp_utc == datetime(
        2026, 9, 30, 8, 0, tzinfo=UTC
    )


def test_v1_1_adapter_has_no_provider_or_ledger_dependency() -> None:
    import trading_signal_intelligence.ai_v1.mt5_rates_adapter_v1_1 as module

    names = set(module.__dict__)
    assert "OpenAIResponsesAdapter" not in names
    assert "AILedger" not in names



def test_v1_1_stale_snapshot_skips_provider_and_v1_0_ledger(
    tmp_path: Path,
) -> None:
    from trading_signal_intelligence.ai_v1.engine_v1_1 import (
        process_inference_cycle_v1_1,
    )
    from trading_signal_intelligence.ai_v1.features import FeatureSnapshot
    from trading_signal_intelligence.ai_v1.ledger import AILedger

    class NeverCallAdapter:
        provider = "test"
        model_id = "test-model"
        parameters = {}

        def __init__(self) -> None:
            self.calls = 0

        def infer(self, **kwargs):
            self.calls += 1
            raise AssertionError("provider must not be called for stale data")

    feature_payload = {
        "feature_schema_version": "AI-v1.0",
        "source_symbol": "USTEC",
        "canonical_symbol": "NASDAQ 100",
        "source_bar_open_utc": "2026-09-30T07:00:00Z",
        "source_bar_close_utc": "2026-09-30T08:00:00Z",
        "inference_started_utc": "2026-09-30T08:05:01Z",
        "data_age_seconds": 301.0,
    }
    snapshot = FeatureSnapshot(payload=feature_payload, sha256="a" * 64)
    guardrails = {
        "max_data_age_seconds": 300,
    }

    v10 = AILedger(tmp_path / "ai_v1_ustec.sqlite")
    v11 = AILedger(tmp_path / "ai_v1_1_ustec.sqlite")
    adapter = NeverCallAdapter()

    result = process_inference_cycle_v1_1(
        ledger=v11,
        adapter=adapter,
        feature_snapshot=snapshot,
        policy_text="frozen",
        decision_schema={},
        guardrails=guardrails,
        active_signal_exists=False,
        recorded_at_utc=datetime(2026, 9, 30, 8, 5, 1, tzinfo=UTC),
    )

    assert result.status == "MISSED_INFERENCE"
    assert result.entity_id.startswith("AI-v1.1:USTEC:")
    assert result.terminal_record is not None
    assert result.terminal_record["payload"]["runtime_version"] == "AI-v1.1"
    assert result.terminal_record["payload"]["protocol_version"] == "AI-v1.0"
    assert result.terminal_record["payload"]["provider_call_made"] is False
    assert adapter.calls == 0
    assert v10.records() == []
    assert len(v11.records()) == 1
