from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    RatesReadState,
    RatesSynchronizationResult,
    synchronize_rates_snapshot,
)
from trading_signal_intelligence.models import Candle


@dataclass(frozen=True, slots=True)
class SynchronizedMarketBars:
    synchronization: RatesSynchronizationResult
    h1_all: list[Candle]
    h4_all: list[Candle]


def read_synchronized_market_bars(
    *,
    connector,
    source_symbol: str,
    canonical_symbol: str,
    scan_started_utc: datetime,
    h1_count: int,
    h4_count: int,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    max_wait_seconds: float = 30.0,
    poll_interval_seconds: float = 1.0,
) -> SynchronizedMarketBars:
    latest_h1: list[Candle] = []
    latest_h4: list[Candle] = []

    def read_state() -> RatesReadState:
        nonlocal latest_h1, latest_h4

        quote = connector.latest_quote(source_symbol, canonical_symbol)
        latest_h1 = connector.bars_from_pos(
            source_symbol,
            canonical_symbol,
            "H1",
            0,
            h1_count,
            current_bar_is_closed=False,
        )
        latest_h4 = connector.bars_from_pos(
            source_symbol,
            canonical_symbol,
            "H4",
            0,
            h4_count,
            current_bar_is_closed=False,
        )

        return RatesReadState(
            observed_at_utc=scan_started_utc,
            latest_tick_utc=quote.timestamp_utc,
            newest_h1_open_utc=(
                latest_h1[-1].timestamp_utc if latest_h1 else None
            ),
            newest_h4_open_utc=(
                latest_h4[-1].timestamp_utc if latest_h4 else None
            ),
            h1_rows=len(latest_h1),
            h4_rows=len(latest_h4),
        )

    result = synchronize_rates_snapshot(
        scan_started_utc=scan_started_utc,
        read_state=read_state,
        monotonic=monotonic,
        sleep=sleep,
        max_wait_seconds=max_wait_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
    return SynchronizedMarketBars(
        synchronization=result,
        h1_all=latest_h1,
        h4_all=latest_h4,
    )
