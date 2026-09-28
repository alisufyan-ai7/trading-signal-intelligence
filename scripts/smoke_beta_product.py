from __future__ import annotations

from trading_signal_intelligence.product.app import (
    ai_insights,
    evidence,
    health,
    markets,
    signals,
)


def main() -> None:
    h = health()
    m = markets()
    e = evidence()
    s = signals(limit_per_market=20)
    ai = ai_insights()

    assert h["live_signal_markets"] == 3
    assert len([row for row in m if row["product_status"] == "live_signal_market"]) == 3
    assert set(e["markets"]) == {"XAUUSD", "USTEC", "US30"}
    assert len(s["markets"]) == 3
    assert ai["protocol_version"] == "AI-v1.0"
    assert ai["mode"] == "SHADOW_ONLY"
    assert ai["raw_market_data_included"] is False
    assert ai["raw_feature_snapshots_included"] is False
    assert ai["provider_request_metadata_included"] is False
    assert ai["hidden_reasoning_included"] is False

    print("beta smoke: PASS")
    print(f"collectors_ready={h['ready_collector_count']}/{h['live_signal_markets']}")
    print(f"launch_ready={h['launch_ready']}")
    print(f"forward_signals={sum(len(row['signals']) for row in s['markets'])}")
    print(f"ai_v1_health={ai['health']['healthy']}")
    print(f"ai_v1_valid_inferences={ai['totals']['valid_inferences']}")
    print(f"ai_v1_shadow_signals={ai['totals']['signals']}")


if __name__ == "__main__":
    main()
