from __future__ import annotations

import os
from pathlib import Path

from trading_signal_intelligence.product.app import health as local_health


def main() -> None:
    local = local_health()
    assert local["launch_ready"] is True
    assert local["ready_collector_count"] == 3

    snapshot = Path("data/public_snapshot.json")
    if not snapshot.exists():
        raise SystemExit(
            "Run scripts/export_public_snapshot.py before this smoke check"
        )

    os.environ["TRADINGTOP_SNAPSHOT_PATH"] = str(snapshot.resolve())

    from trading_signal_intelligence.product.cloud_app import (
        health as cloud_health,
        markets as cloud_markets,
        signals as cloud_signals,
    )

    cloud = cloud_health()
    rows = cloud_markets()
    signal_payload = cloud_signals()

    assert cloud["launch_ready"] is True
    assert cloud["ready_collector_count"] == 3
    assert len(rows) >= 3
    assert len(signal_payload["markets"]) == 3

    print("launch layer smoke: PASS")
    print(
        f"local_collectors={local['ready_collector_count']}/"
        f"{local['live_signal_markets']}"
    )
    print(
        f"cloud_snapshot_collectors={cloud['ready_collector_count']}/"
        f"{cloud['live_signal_markets']}"
    )
    print(
        "snapshot_forward_signals="
        + str(
            sum(
                len(row.get("signals", []))
                for row in signal_payload["markets"]
            )
        )
    )


if __name__ == "__main__":
    main()
