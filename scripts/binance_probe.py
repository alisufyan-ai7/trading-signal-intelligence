from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from trading_signal_intelligence.connectors.binance import BinanceSpotConnector


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe Binance public Spot market data")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--canonical", default="BTC/USDT")
    parser.add_argument("--timeframe", default="H1")
    parser.add_argument("--bars", type=int, default=20)
    args = parser.parse_args()

    connector = BinanceSpotConnector()
    bars = connector.klines(
        args.symbol,
        args.canonical,
        args.timeframe,
        limit=args.bars,
    )
    print(f"received {len(bars)} {args.timeframe} bars for {args.symbol}")
    for candle in bars[-5:]:
        print(json.dumps(asdict(candle), default=str))


if __name__ == "__main__":
    main()
