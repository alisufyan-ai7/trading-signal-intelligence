from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

from trading_signal_intelligence.ai_v1.expansion_v1_2 import (
    DATABASE_PATHS,
    DECISION_PROTOCOL_VERSION,
    MARKETS,
    RUNTIME_VERSION,
    expansion_market_specs,
    feature_schema_equivalence_report,
    preactivation_report_v1_2,
)
from trading_signal_intelligence.ai_v1.readiness_v1_2 import (
    probe_market_readiness_v1_2,
)
from trading_signal_intelligence.models import Candle, Quote


ROOT = Path(__file__).resolve().parents[1]
UTC = timezone.utc


def test_expansion_identity_and_isolated_paths() -> None:
    assert RUNTIME_VERSION == "AI-v1.2"
    assert DECISION_PROTOCOL_VERSION == "AI-v1.0"
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


def test_expansion_registry_mapping_is_exact() -> None:
    specs = expansion_market_specs(ROOT)
    assert specs["EURUSD"].canonical_symbol == "EUR/USD"
    assert specs["EURUSD"].digits == 5
    assert specs["EURUSD"].point_size == 0.00001

    assert specs["XAGUSD"].canonical_symbol == "XAG/USD"
    assert specs["XAGUSD"].digits == 3
    assert specs["XAGUSD"].point_size == 0.001

    assert specs["USOIL"].canonical_symbol == "WTI"
    assert specs["USOIL"].digits == 3
    assert specs["USOIL"].point_size == 0.001


def test_expansion_feature_schema_changes_only_allowlist_and_metadata() -> None:
    report = feature_schema_equivalence_report(ROOT)
    assert report[
        "equivalent_except_schema_metadata_and_source_symbol_allowlist"
    ] is True
    assert report["feature_schema_version_preserved"] is True
    assert report["base_source_symbol_enum"] == ["XAUUSD", "USTEC", "US30"]
    assert report["expansion_source_symbol_enum"] == [
        "EURUSD",
        "XAGUSD",
        "USOIL",
    ]


def test_expansion_static_preactivation_report_is_side_effect_free() -> None:
    before = {
        symbol: (ROOT / relative).exists()
        for symbol, relative in DATABASE_PATHS.items()
    }

    report = preactivation_report_v1_2(ROOT)

    after = {
        symbol: (ROOT / relative).exists()
        for symbol, relative in DATABASE_PATHS.items()
    }

    assert before == after
    assert report["preactivation_check"] == "PASS"
    assert report["runtime_version"] == "AI-v1.2"
    assert report["decision_protocol_version"] == "AI-v1.0"
    assert report["frozen_ai_v1_0_decision_lineage_match"] is True
    assert report["feature_formula_change"] is False
    assert report["decision_contract_change"] is False
    assert report["policy_change"] is False
    assert report["guard_numeric_semantics_change"] is False
    assert report["market_allowlist_change"] is True
    assert report["market_allowlist_change_is_version_isolated"] is True
    assert not any(report["expansion_ledger_paths_exist"].values())
    assert report["expansion_activation_anchors"] == []
    assert report["provider_call_made"] is False
    assert report["mt5_call_made"] is False
    assert report["ledger_write_performed"] is False
    assert report["activation_performed"] is False
    assert report["scheduler_changed"] is False
    assert report["broker_execution_enabled"] is False


def _candle(
    *,
    symbol: str,
    canonical: str,
    timeframe: str,
    timestamp: datetime,
    index: int,
    closed: bool,
    spread: str,
) -> Candle:
    base = Decimal("100") + Decimal(index) / Decimal("100")
    return Candle(
        source="exness_mt5_demo",
        source_symbol=symbol,
        symbol=canonical,
        timeframe=timeframe,
        timestamp_utc=timestamp,
        open=base,
        high=base + Decimal("0.30"),
        low=base - Decimal("0.30"),
        close=base + Decimal("0.05"),
        volume=Decimal(100 + (index % 17)),
        volume_kind="tick_volume",
        spread=Decimal(spread),
        is_closed=closed,
    )


class FakeReadyConnector:
    def __init__(
        self,
        *,
        symbol: str,
        canonical: str,
        scan: datetime,
        spread: str,
    ) -> None:
        self.symbol = symbol
        self.canonical = canonical
        self.scan = scan
        current_h1 = scan.replace(minute=0, second=0, microsecond=0)
        current_h4 = current_h1.replace(hour=(current_h1.hour // 4) * 4)

        self.h1 = [
            _candle(
                symbol=symbol,
                canonical=canonical,
                timeframe="H1",
                timestamp=current_h1 - timedelta(hours=499 - index),
                index=index,
                closed=index != 499,
                spread=spread,
            )
            for index in range(500)
        ]
        self.h4 = [
            _candle(
                symbol=symbol,
                canonical=canonical,
                timeframe="H4",
                timestamp=current_h4 - timedelta(hours=4 * (199 - index)),
                index=index,
                closed=index != 199,
                spread=spread,
            )
            for index in range(200)
        ]

    def latest_quote(self, source_symbol: str, canonical_symbol: str) -> Quote:
        assert source_symbol == self.symbol
        assert canonical_symbol == self.canonical
        return Quote(
            source="exness_mt5_demo",
            source_symbol=source_symbol,
            symbol=canonical_symbol,
            timestamp_utc=self.scan,
            bid=Decimal("100"),
            ask=Decimal("100.01"),
            last=Decimal("100.005"),
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
        assert start_pos == 0
        assert source_symbol == self.symbol
        assert canonical_symbol == self.canonical
        if timeframe == "H1":
            return list(self.h1[-count:])
        if timeframe == "H4":
            return list(self.h4[-count:])
        raise AssertionError(f"unexpected timeframe {timeframe}")


def test_each_expansion_market_can_build_unchanged_feature_formula_snapshot() -> None:
    scan = datetime(2026, 10, 6, 17, 2, 0, tzinfo=UTC)
    specs = expansion_market_specs(ROOT)
    spreads = {
        "EURUSD": "6",
        "XAGUSD": "20",
        "USOIL": "18",
    }

    for symbol in MARKETS:
        market = specs[symbol]
        connector = FakeReadyConnector(
            symbol=symbol,
            canonical=market.canonical_symbol,
            scan=scan,
            spread=spreads[symbol],
        )
        report = probe_market_readiness_v1_2(
            connector=connector,
            market=market,
            scan_started_utc=scan,
        )

        assert report["readiness"] == "READY"
        assert report["feature_snapshot_built"] is True
        assert report["feature_schema_version"] == "AI-v1.0"
        assert report["data_age_seconds"] == 120.0
        assert report["atr_14"] > 0
        assert report["spread_price"] >= 0
        assert report["spread_atr_fraction"] >= 0
        assert report["provider_call_made"] is False
        assert report["ledger_write_performed"] is False
        assert report["broker_execution_enabled"] is False


def test_live_probe_source_has_no_outreach_or_activation_path() -> None:
    text = (
        ROOT / "scripts" / "probe_ai_v1_2_market_readiness.py"
    ).read_text(encoding="utf-8")

    assert "symbol_select" not in text
    assert "OpenAIResponsesAdapter" not in text
    assert "AILedger" not in text
    assert "Register-ScheduledTask" not in text
    assert "activate_ai" not in text
