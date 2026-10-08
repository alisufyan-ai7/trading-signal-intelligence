from __future__ import annotations

import math
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

from trading_signal_intelligence.ai_v1.features import (
    FeatureSnapshotError,
    build_feature_snapshot,
)
from trading_signal_intelligence.connectors.binance import BinanceSpotConnector
from trading_signal_intelligence.models import Candle, Quote


RUNTIME_VERSION = "AI-v1.3"
DECISION_PROTOCOL_VERSION = "AI-v1.0"
SOURCE_NAME = "binance_spot"
MAX_DATA_AGE_SECONDS = 300

MARKETS = ("BTCUSDT", "ETHUSDT", "SOLUSDT")

CANONICAL_SYMBOLS = {
    "BTCUSDT": "BTC/USDT",
    "ETHUSDT": "ETH/USDT",
    "SOLUSDT": "SOL/USDT",
}


class CryptoReadinessError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class CryptoMarketReadinessInput:
    source_symbol: str
    canonical_symbol: str
    h1_candles: list[Candle]
    h4_candles: list[Candle]
    quote: Quote


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise CryptoReadinessError("timestamp must be timezone-aware")
    return value.astimezone(timezone.utc)


def _closed_sorted_unique(
    candles: list[Candle],
    *,
    timeframe: str,
) -> list[Candle]:
    selected = [
        candle
        for candle in candles
        if candle.is_closed and candle.timeframe.upper() == timeframe.upper()
    ]
    selected.sort(key=lambda candle: candle.timestamp_utc)
    timestamps = [candle.timestamp_utc for candle in selected]
    if len(set(timestamps)) != len(timestamps):
        raise CryptoReadinessError(f"duplicate {timeframe} timestamps")
    return selected


def _gap_count(candles: list[Candle], *, expected_seconds: int) -> int:
    count = 0
    for left, right in zip(candles, candles[1:]):
        delta = (right.timestamp_utc - left.timestamp_utc).total_seconds()
        if delta != expected_seconds:
            count += 1
    return count


def _weekend_counts(candles: list[Candle]) -> dict[str, int]:
    saturday = sum(c.timestamp_utc.weekday() == 5 for c in candles)
    sunday = sum(c.timestamp_utc.weekday() == 6 for c in candles)
    return {
        "saturday_closed_h1_bars": saturday,
        "sunday_closed_h1_bars": sunday,
    }


def _spread_price(quote: Quote) -> Decimal:
    if quote.bid is None or quote.ask is None:
        raise CryptoReadinessError("top-of-book bid/ask unavailable")
    if quote.bid <= 0 or quote.ask <= 0:
        raise CryptoReadinessError("top-of-book bid/ask must be positive")
    if quote.ask < quote.bid:
        raise CryptoReadinessError("top-of-book ask is below bid")
    spread = quote.ask - quote.bid
    if spread < 0:
        raise CryptoReadinessError("top-of-book spread cannot be negative")
    return spread


def _inject_latest_spread_price(
    candles: list[Candle],
    *,
    spread_price: Decimal,
) -> list[Candle]:
    """Compatibility-only adapter for the frozen AI-v1 price formulas.

    AI-v1's feature builder expects Candle.spread in point units and multiplies
    by point_size. Crypto readiness supplies a direct price-unit top-of-book
    spread, so this wrapper uses point_size=1.0 and injects the exact price-unit
    spread into only the latest completed H1 candle.

    This is readiness evidence, not the final activation/runtime schema.
    """

    if not candles:
        raise CryptoReadinessError("completed H1 candles required")
    result = list(candles)
    result[-1] = replace(result[-1], spread=spread_price)
    return result


def collect_market_input(
    *,
    connector: BinanceSpotConnector,
    source_symbol: str,
    canonical_symbol: str,
    h1_count: int = 500,
    h4_count: int = 200,
) -> CryptoMarketReadinessInput:
    h1 = connector.klines(
        source_symbol,
        canonical_symbol,
        "H1",
        limit=min(h1_count + 1, 1000),
    )
    h4 = connector.klines(
        source_symbol,
        canonical_symbol,
        "H4",
        limit=min(h4_count + 1, 1000),
    )
    quote = connector.book_ticker(source_symbol, canonical_symbol)
    return CryptoMarketReadinessInput(
        source_symbol=source_symbol,
        canonical_symbol=canonical_symbol,
        h1_candles=h1,
        h4_candles=h4,
        quote=quote,
    )


def evaluate_market_readiness(
    market: CryptoMarketReadinessInput,
    *,
    batch_frozen_at_utc: datetime,
    h1_required: int = 500,
    h4_required: int = 200,
    max_data_age_seconds: int = MAX_DATA_AGE_SECONDS,
) -> dict[str, Any]:
    batch_frozen_at_utc = _utc(batch_frozen_at_utc)

    h1 = _closed_sorted_unique(market.h1_candles, timeframe="H1")
    h4 = _closed_sorted_unique(market.h4_candles, timeframe="H4")
    if len(h1) < h1_required:
        raise CryptoReadinessError(
            f"{market.source_symbol}: need {h1_required} closed H1 bars; got {len(h1)}"
        )
    if len(h4) < h4_required:
        raise CryptoReadinessError(
            f"{market.source_symbol}: need {h4_required} closed H4 bars; got {len(h4)}"
        )

    h1 = h1[-h1_required:]
    h4 = h4[-h4_required:]

    h1_gaps = _gap_count(h1, expected_seconds=3600)
    h4_gaps = _gap_count(h4, expected_seconds=4 * 3600)
    if h1_gaps:
        raise CryptoReadinessError(
            f"{market.source_symbol}: H1 history contains {h1_gaps} interval gaps"
        )
    if h4_gaps:
        raise CryptoReadinessError(
            f"{market.source_symbol}: H4 history contains {h4_gaps} interval gaps"
        )

    weekend = _weekend_counts(h1)
    if weekend["saturday_closed_h1_bars"] == 0:
        raise CryptoReadinessError(
            f"{market.source_symbol}: no Saturday H1 bars in readiness window"
        )
    if weekend["sunday_closed_h1_bars"] == 0:
        raise CryptoReadinessError(
            f"{market.source_symbol}: no Sunday H1 bars in readiness window"
        )

    latest_h1 = h1[-1]
    source_bar_close_utc = _utc(latest_h1.timestamp_utc).replace(
        microsecond=0
    )
    source_bar_close_utc = source_bar_close_utc.replace(tzinfo=timezone.utc)
    source_bar_close_utc = source_bar_close_utc + timedelta(hours=1)
    data_age_seconds = (batch_frozen_at_utc - source_bar_close_utc).total_seconds()
    if data_age_seconds < 0 or data_age_seconds > max_data_age_seconds:
        raise CryptoReadinessError(
            f"{market.source_symbol}: latest completed H1 age "
            f"{data_age_seconds:.3f}s outside 0..{max_data_age_seconds}"
        )

    quote_time = _utc(market.quote.timestamp_utc)
    quote_age_seconds = (batch_frozen_at_utc - quote_time).total_seconds()
    if quote_age_seconds < 0:
        quote_age_seconds = 0.0
    if quote_age_seconds > max_data_age_seconds:
        raise CryptoReadinessError(
            f"{market.source_symbol}: top-of-book age "
            f"{quote_age_seconds:.3f}s exceeds {max_data_age_seconds}"
        )

    spread_price = _spread_price(market.quote)
    h1_with_spread = _inject_latest_spread_price(
        h1,
        spread_price=spread_price,
    )

    try:
        feature = build_feature_snapshot(
            h1_candles=h1_with_spread,
            h4_candles=h4,
            point_size=1.0,
            inference_started_utc=batch_frozen_at_utc,
            source_symbol=market.source_symbol,
            canonical_symbol=market.canonical_symbol,
        )
    except FeatureSnapshotError as exc:
        raise CryptoReadinessError(
            f"{market.source_symbol}: feature construction failed: {exc}"
        ) from exc

    payload = feature.payload
    spread_from_feature = float(payload["spread_price"])
    if not math.isclose(
        spread_from_feature,
        float(spread_price),
        rel_tol=1e-12,
        abs_tol=1e-12,
    ):
        raise CryptoReadinessError(
            f"{market.source_symbol}: feature spread does not match top-of-book spread"
        )

    if any(candle.volume_kind != "base_asset_volume" for candle in h1):
        raise CryptoReadinessError(
            f"{market.source_symbol}: H1 volume semantics are not base_asset_volume"
        )
    if any(candle.volume_kind != "base_asset_volume" for candle in h4):
        raise CryptoReadinessError(
            f"{market.source_symbol}: H4 volume semantics are not base_asset_volume"
        )

    midpoint = (market.quote.bid + market.quote.ask) / Decimal("2")
    return {
        "source_symbol": market.source_symbol,
        "canonical_symbol": market.canonical_symbol,
        "source": SOURCE_NAME,
        "readiness": "READY",
        "closed_h1_bars": len(h1),
        "closed_h4_bars": len(h4),
        "h1_interval_gaps": h1_gaps,
        "h4_interval_gaps": h4_gaps,
        **weekend,
        "latest_h1_open_utc": _utc(latest_h1.timestamp_utc).isoformat(),
        "latest_h1_close_utc": source_bar_close_utc.isoformat(),
        "data_age_seconds": data_age_seconds,
        "volume_kind": "base_asset_volume",
        "best_bid": str(market.quote.bid),
        "best_ask": str(market.quote.ask),
        "midpoint": str(midpoint),
        "spread_price": str(spread_price),
        "quote_observed_at_utc": quote_time.isoformat(),
        "quote_age_seconds": quote_age_seconds,
        "feature_formula_profile": "AI-v1.0-price-formulas-readiness-adapter",
        "working_crypto_feature_schema_version": "AI-crypto-v1.0",
        "feature_snapshot_sha256": feature.sha256,
        "feature_snapshot": payload,
        "numeric_fee_policy_frozen": False,
        "numeric_slippage_policy_frozen": False,
        "all_in_round_trip_cost_policy_frozen": False,
        "activation_ready": False,
        "activation_blocker": "numeric_crypto_execution_cost_policy_not_frozen",
        "provider_call_made": False,
        "ledger_write_performed": False,
        "broker_execution_enabled": False,
    }


def evaluate_batch_readiness(
    inputs: dict[str, CryptoMarketReadinessInput],
    *,
    batch_frozen_at_utc: datetime,
    h1_required: int = 500,
    h4_required: int = 200,
) -> dict[str, Any]:
    missing = [symbol for symbol in MARKETS if symbol not in inputs]
    if missing:
        raise CryptoReadinessError(
            f"missing crypto readiness inputs: {', '.join(missing)}"
        )

    results = {
        symbol: evaluate_market_readiness(
            inputs[symbol],
            batch_frozen_at_utc=batch_frozen_at_utc,
            h1_required=h1_required,
            h4_required=h4_required,
        )
        for symbol in MARKETS
    }

    closes = {
        result["latest_h1_close_utc"] for result in results.values()
    }
    if len(closes) != 1:
        raise CryptoReadinessError(
            f"crypto batch H1 close mismatch: {sorted(closes)}"
        )

    return {
        "runtime_version": RUNTIME_VERSION,
        "decision_protocol_version": DECISION_PROTOCOL_VERSION,
        "source": SOURCE_NAME,
        "batch_frozen_at_utc": _utc(batch_frozen_at_utc).isoformat(),
        "markets": results,
        "common_source_bar_close_utc": next(iter(closes)),
        "k1_market_readiness": "PASS",
        "activation_readiness": "BLOCKED_NUMERIC_COST_POLICY_NOT_FROZEN",
        "provider_call_made": False,
        "ledger_write_performed": False,
        "scheduler_changed": False,
        "public_signal_exposure_enabled": False,
        "broker_execution_enabled": False,
    }
