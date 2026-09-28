from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from trading_signal_intelligence.ai_v1.features import build_feature_snapshot
from trading_signal_intelligence.connectors.mt5 import MT5Connector


ALLOWED = {"XAUUSD", "USTEC", "US30"}


def registry_entry(path: str, source_symbol: str) -> tuple[str, float]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    for instrument in payload["instruments"]:
        cfg = instrument.get("sources", {}).get("exness_mt5_demo")
        if cfg and cfg.get("symbol") == source_symbol:
            digits = int(cfg["digits"])
            return str(instrument["canonical"]), 10.0 ** (-digits)
    raise ValueError(f"No Exness registry entry for {source_symbol}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a read-only live AI-v1 feature snapshot from MT5"
    )
    parser.add_argument("--symbol", default="XAUUSD", choices=sorted(ALLOWED))
    parser.add_argument("--registry", default="config/instruments.json")
    parser.add_argument("--terminal-path", default=None)
    parser.add_argument("--h1-bars", type=int, default=500)
    parser.add_argument("--h4-bars", type=int, default=200)
    args = parser.parse_args()

    canonical, point_size = registry_entry(args.registry, args.symbol)
    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        h1 = connector.bars_from_pos(
            args.symbol,
            canonical,
            "H1",
            0,
            args.h1_bars,
            current_bar_is_closed=False,
        )
        h4 = connector.bars_from_pos(
            args.symbol,
            canonical,
            "H4",
            0,
            args.h4_bars,
            current_bar_is_closed=False,
        )
    finally:
        connector.disconnect()

    now = datetime.now(timezone.utc)
    snapshot = build_feature_snapshot(
        h1_candles=h1,
        h4_candles=h4,
        point_size=point_size,
        inference_started_utc=now,
        source_symbol=args.symbol,
        canonical_symbol=canonical,
    )

    print(
        json.dumps(
            {
                "mode": "read_only_feature_snapshot",
                "provider_call_made": False,
                "broker_execution_enabled": False,
                "feature_snapshot_sha256": snapshot.sha256,
                "freshness_guard_eligible": (
                    snapshot.payload["data_age_seconds"] <= 300
                ),
                "snapshot": snapshot.payload,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
