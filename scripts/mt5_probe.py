from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from trading_signal_intelligence.connectors.mt5 import MT5Connector


def main() -> None:
    parser = argparse.ArgumentParser(description="Probe a locally running MetaTrader 5 terminal")
    parser.add_argument("--terminal-path", default=None, help="Optional path to terminal64.exe")
    parser.add_argument("--symbol", default="EURUSD", help="Broker source symbol to sample")
    parser.add_argument("--canonical", default="EUR/USD", help="Canonical symbol label")
    parser.add_argument("--timeframe", default="H1", help="M1/M5/M15/H1/H4/D1")
    parser.add_argument("--bars", type=int, default=20, help="Number of recent bars")
    parser.add_argument("--list-limit", type=int, default=30, help="Number of discovered symbols to print")
    args = parser.parse_args()

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        terminal = connector.terminal_info()
        account = connector.account_info()
        symbols = connector.symbols()

        print("MT5 terminal connected")
        if terminal is not None:
            print(f"terminal connected={getattr(terminal, 'connected', None)}")
        if account is not None:
            # Intentionally avoid printing login/account identifiers.
            print(
                "account metadata: "
                f"server={getattr(account, 'server', None)!r}, "
                f"currency={getattr(account, 'currency', None)!r}, "
                f"trade_allowed={getattr(account, 'trade_allowed', None)!r}"
            )

        print(f"discovered symbols: {len(symbols)}")
        for item in symbols[: args.list_limit]:
            print(
                json.dumps(
                    {
                        "name": getattr(item, "name", None),
                        "description": getattr(item, "description", None),
                        "path": getattr(item, "path", None),
                        "digits": getattr(item, "digits", None),
                        "currency_base": getattr(item, "currency_base", None),
                        "currency_profit": getattr(item, "currency_profit", None),
                    },
                    default=str,
                )
            )

        quote = connector.latest_quote(args.symbol, args.canonical)
        print("latest quote:")
        print(json.dumps(asdict(quote), default=str, indent=2))

        bars = connector.bars_from_pos(
            args.symbol,
            args.canonical,
            args.timeframe,
            start_pos=0,
            count=args.bars,
        )
        print(f"recent {args.timeframe} bars: {len(bars)}")
        for candle in bars[-5:]:
            print(json.dumps(asdict(candle), default=str))
    finally:
        connector.disconnect()


if __name__ == "__main__":
    main()
