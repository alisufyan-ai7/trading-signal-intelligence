from __future__ import annotations

from datetime import datetime
from typing import Any

from trading_signal_intelligence.ai_v1.expansion_v1_2_1 import (
    ExpansionMarketSpecV121,
)
from trading_signal_intelligence.ai_v1.readiness_v1_2 import (
    probe_market_readiness_v1_2,
)
from trading_signal_intelligence.ai_v1.rates_sync_v1_1 import (
    SYNC_MAX_WAIT_SECONDS,
    SYNC_POLL_INTERVAL_SECONDS,
)


def probe_market_readiness_v1_2_1(
    *,
    connector,
    market: ExpansionMarketSpecV121,
    scan_started_utc: datetime,
    h1_count: int = 500,
    h4_count: int = 200,
    max_wait_seconds: float = SYNC_MAX_WAIT_SECONDS,
    poll_interval_seconds: float = SYNC_POLL_INTERVAL_SECONDS,
) -> dict[str, Any]:
    # Intentional exact reuse of the already-tested read-only market
    # compatibility semantics. AI-v1.2.1 changes no market-data behavior.
    return probe_market_readiness_v1_2(
        connector=connector,
        market=market,
        scan_started_utc=scan_started_utc,
        h1_count=h1_count,
        h4_count=h4_count,
        max_wait_seconds=max_wait_seconds,
        poll_interval_seconds=poll_interval_seconds,
    )
