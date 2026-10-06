from __future__ import annotations

from datetime import datetime
from typing import Any

from trading_signal_intelligence.ai_v1.expansion_v1_2 import (
    ExpansionMarketSpec,
)
from trading_signal_intelligence.ai_v1.features import (
    FeatureSnapshotError,
    build_feature_snapshot,
)
from trading_signal_intelligence.ai_v1.mt5_rates_adapter_v1_1 import (
    read_synchronized_market_bars,
)
from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    SYNC_MAX_WAIT_SECONDS,
    SYNC_POLL_INTERVAL_SECONDS,
)


def probe_market_readiness_v1_2(
    *,
    connector,
    market: ExpansionMarketSpec,
    scan_started_utc: datetime,
    h1_count: int = 500,
    h4_count: int = 200,
    max_wait_seconds: float = SYNC_MAX_WAIT_SECONDS,
    poll_interval_seconds: float = SYNC_POLL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    synchronized = read_synchronized_market_bars(
        connector=connector,
        source_symbol=market.source_symbol,
        canonical_symbol=market.canonical_symbol,
        scan_started_utc=scan_started_utc,
        h1_count=h1_count,
        h4_count=h4_count,
        max_wait_seconds=max_wait_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )

    sync = synchronized.synchronization
    base = {
        "source_symbol": market.source_symbol,
        "canonical_symbol": market.canonical_symbol,
        "asset_class": market.asset_class,
        "digits": market.digits,
        "point_size": market.point_size,
        "synchronization_status": sync.status,
        "synchronization_ready": sync.ready,
        "synchronization_attempts": sync.attempts,
        "synchronization_waited_seconds": sync.waited_seconds,
        "saw_current_hour_tick": sync.saw_current_hour_tick,
        "h1_rows": len(synchronized.h1_all),
        "h4_rows": len(synchronized.h4_all),
        "provider_call_made": False,
        "ledger_write_performed": False,
        "broker_execution_enabled": False,
    }

    if not sync.ready:
        return {
            **base,
            "readiness": "INCONCLUSIVE_NO_CURRENT_MARKET_SNAPSHOT",
            "feature_snapshot_built": False,
        }

    try:
        snapshot = build_feature_snapshot(
            h1_candles=synchronized.h1_all,
            h4_candles=synchronized.h4_all,
            point_size=market.point_size,
            inference_started_utc=scan_started_utc,
            source_symbol=market.source_symbol,
            canonical_symbol=market.canonical_symbol,
        )
    except FeatureSnapshotError as exc:
        return {
            **base,
            "readiness": "FAIL_FEATURE_COMPATIBILITY",
            "feature_snapshot_built": False,
            "feature_error": str(exc),
        }

    payload = snapshot.payload
    if payload.get("feature_schema_version") != "AI-v1.0":
        return {
            **base,
            "readiness": "FAIL_FEATURE_SCHEMA_VERSION",
            "feature_snapshot_built": True,
        }
    if payload.get("source_symbol") != market.source_symbol:
        return {
            **base,
            "readiness": "FAIL_SOURCE_SYMBOL",
            "feature_snapshot_built": True,
        }
    if payload.get("canonical_symbol") != market.canonical_symbol:
        return {
            **base,
            "readiness": "FAIL_CANONICAL_SYMBOL",
            "feature_snapshot_built": True,
        }

    age = float(payload["data_age_seconds"])
    atr = float(payload["atr_14"])
    spread_price = float(payload["spread_price"])
    spread_atr_fraction = float(payload["spread_atr_fraction"])

    if age < 0 or age > 300:
        return {
            **base,
            "readiness": "FAIL_FRESHNESS",
            "feature_snapshot_built": True,
            "data_age_seconds": age,
        }
    if atr <= 0 or spread_price < 0 or spread_atr_fraction < 0:
        return {
            **base,
            "readiness": "FAIL_COST_INPUTS",
            "feature_snapshot_built": True,
        }

    return {
        **base,
        "readiness": "READY",
        "feature_snapshot_built": True,
        "feature_snapshot_sha256": snapshot.sha256,
        "feature_schema_version": payload["feature_schema_version"],
        "source_bar_open_utc": payload["source_bar_open_utc"],
        "source_bar_close_utc": payload["source_bar_close_utc"],
        "data_age_seconds": age,
        "atr_14": atr,
        "spread_price": spread_price,
        "spread_atr_fraction": spread_atr_fraction,
        "quality_flags": list(payload["quality_flags"]),
    }
