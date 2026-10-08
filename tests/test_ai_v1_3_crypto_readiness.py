from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Self

import pytest

from trading_signal_intelligence.ai_v1.crypto_readiness_v1_3 import (
    CANONICAL_SYMBOLS,
    MARKETS,
    CryptoMarketReadinessInput,
    CryptoReadinessError,
    evaluate_batch_readiness,
    evaluate_market_readiness,
)
from trading_signal_intelligence.connectors import binance as binance_module
from trading_signal_intelligence.connectors.binance import BinanceSpotConnector
from trading_signal_intelligence.models import Candle, Quote


class _FakeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = json.dumps(payload).encode("utf-8")

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _candle(
    *,
    symbol: str,
    canonical: str,
    timeframe: str,
    timestamp: datetime,
    index: int,
) -> Candle:
    base = Decimal(100) + Decimal(index) * Decimal("0.10")
    wiggle = Decimal((index % 7) - 3) * Decimal("0.01")
    close = base + wiggle
    return Candle(
        source="binance_spot",
        source_symbol=symbol,
        symbol=canonical,
        timeframe=timeframe,
        timestamp_utc=timestamp,
        open=base,
        high=max(base, close) + Decimal("0.25"),
        low=min(base, close) - Decimal("0.25"),
        close=close,
        volume=Decimal(1000) + Decimal(index % 13),
        volume_kind="base_asset_volume",
        spread=None,
        is_closed=True,
    )


def _market_input(
    symbol: str,
    *,
    latest_h1_open: datetime,
    quote_spread: Decimal = Decimal("0.10"),
) -> CryptoMarketReadinessInput:
    canonical = CANONICAL_SYMBOLS[symbol]

    h1_start = latest_h1_open - timedelta(hours=500)
    h1 = [
        _candle(
            symbol=symbol,
            canonical=canonical,
            timeframe="H1",
            timestamp=h1_start + timedelta(hours=i),
            index=i,
        )
        for i in range(501)
    ]

    latest_h4_open = latest_h1_open.replace(
        hour=(latest_h1_open.hour // 4) * 4,
    )
    if latest_h4_open + timedelta(hours=4) > latest_h1_open + timedelta(hours=1):
        latest_h4_open -= timedelta(hours=4)

    h4_start = latest_h4_open - timedelta(hours=4 * 199)
    h4 = [
        _candle(
            symbol=symbol,
            canonical=canonical,
            timeframe="H4",
            timestamp=h4_start + timedelta(hours=4 * i),
            index=i,
        )
        for i in range(200)
    ]

    bid = Decimal("120.00")
    quote = Quote(
        source="binance_spot",
        source_symbol=symbol,
        symbol=canonical,
        timestamp_utc=latest_h1_open + timedelta(hours=1, seconds=20),
        bid=bid,
        ask=bid + quote_spread,
    )
    return CryptoMarketReadinessInput(
        source_symbol=symbol,
        canonical_symbol=canonical,
        h1_candles=h1,
        h4_candles=h4,
        quote=quote,
    )


def test_binance_book_ticker_is_read_only_quote_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "symbol": "BTCUSDT",
        "bidPrice": "60000.10",
        "bidQty": "1.2",
        "askPrice": "60000.30",
        "askQty": "0.8",
    }
    monkeypatch.setattr(
        binance_module,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(payload),
    )

    quote = BinanceSpotConnector().book_ticker("BTCUSDT", "BTC/USDT")

    assert quote.source == "binance_spot"
    assert quote.source_symbol == "BTCUSDT"
    assert quote.symbol == "BTC/USDT"
    assert quote.bid == Decimal("60000.10")
    assert quote.ask == Decimal("60000.30")
    assert quote.spread == Decimal("0.20")
    assert quote.timestamp_utc.tzinfo is not None


def test_binance_book_ticker_rejects_crossed_book(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = {
        "symbol": "BTCUSDT",
        "bidPrice": "60000.30",
        "bidQty": "1.2",
        "askPrice": "60000.10",
        "askQty": "0.8",
    }
    monkeypatch.setattr(
        binance_module,
        "urlopen",
        lambda *args, **kwargs: _FakeResponse(payload),
    )

    with pytest.raises(ValueError, match="best ask"):
        BinanceSpotConnector().book_ticker("BTCUSDT", "BTC/USDT")


def test_crypto_market_readiness_builds_feature_from_top_of_book_spread() -> None:
    latest_open = datetime(2026, 10, 8, 20, 0, tzinfo=UTC)
    batch_time = datetime(2026, 10, 8, 21, 1, tzinfo=UTC)

    result = evaluate_market_readiness(
        _market_input("BTCUSDT", latest_h1_open=latest_open),
        batch_frozen_at_utc=batch_time,
    )

    assert result["readiness"] == "READY"
    assert result["closed_h1_bars"] == 500
    assert result["closed_h4_bars"] == 200
    assert result["h1_interval_gaps"] == 0
    assert result["h4_interval_gaps"] == 0
    assert result["saturday_closed_h1_bars"] > 0
    assert result["sunday_closed_h1_bars"] > 0
    assert result["volume_kind"] == "base_asset_volume"
    assert result["spread_price"] == "0.10"
    assert result["feature_snapshot"]["spread_price"] == pytest.approx(0.10)
    assert result["feature_snapshot"]["data_age_seconds"] == pytest.approx(60)
    assert result["numeric_fee_policy_frozen"] is False
    assert result["all_in_round_trip_cost_policy_frozen"] is False
    assert result["activation_ready"] is False
    assert (
        result["activation_blocker"]
        == "numeric_crypto_execution_cost_policy_not_frozen"
    )
    assert result["provider_call_made"] is False
    assert result["ledger_write_performed"] is False
    assert result["broker_execution_enabled"] is False


def test_crypto_batch_requires_common_h1_close_and_preserves_blocker() -> None:
    latest_open = datetime(2026, 10, 8, 20, 0, tzinfo=UTC)
    batch_time = datetime(2026, 10, 8, 21, 1, tzinfo=UTC)
    inputs = {
        symbol: _market_input(symbol, latest_h1_open=latest_open)
        for symbol in MARKETS
    }

    report = evaluate_batch_readiness(
        inputs,
        batch_frozen_at_utc=batch_time,
    )

    assert report["k1_market_readiness"] == "PASS"
    assert (
        report["activation_readiness"]
        == "BLOCKED_NUMERIC_COST_POLICY_NOT_FROZEN"
    )
    assert report["common_source_bar_close_utc"].startswith("2026-10-08T21:00:00")
    assert report["provider_call_made"] is False
    assert report["ledger_write_performed"] is False
    assert report["scheduler_changed"] is False
    assert report["public_signal_exposure_enabled"] is False
    assert report["broker_execution_enabled"] is False


def test_crypto_readiness_fails_closed_when_latest_h1_is_stale() -> None:
    latest_open = datetime(2026, 10, 8, 20, 0, tzinfo=UTC)
    stale_batch_time = datetime(2026, 10, 8, 21, 6, tzinfo=UTC)

    with pytest.raises(CryptoReadinessError, match="outside 0..300"):
        evaluate_market_readiness(
            _market_input("BTCUSDT", latest_h1_open=latest_open),
            batch_frozen_at_utc=stale_batch_time,
        )
