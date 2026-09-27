from __future__ import annotations

from trading_signal_intelligence.product.app import evidence, health, markets, signals


def main() -> None:
    h = health()
    m = markets()
    e = evidence()
    s = signals()

    assert h["live_signal_markets"] == 3
    assert len([row for row in m if row["product_status"] == "live_signal_market"]) == 3
    assert set(e["markets"]) == {"XAUUSD", "USTEC", "US30"}
    assert len(s["markets"]) == 3

    print("beta smoke: PASS")
    print(f"collectors_ready={h['ready_collector_count']}/{h['live_signal_markets']}")
    print(f"launch_ready={h['launch_ready']}")
    print(f"forward_signals={sum(len(row['signals']) for row in s['markets'])}")


if __name__ == "__main__":
    main()
