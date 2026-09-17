from __future__ import annotations

import argparse
import json
from collections import Counter

from trading_signal_intelligence.connectors.mt5 import MT5Connector


TARGET_ALIASES: dict[str, tuple[str, ...]] = {
    "EUR/USD": ("EURUSD",),
    "GBP/USD": ("GBPUSD",),
    "USD/JPY": ("USDJPY",),
    "XAU/USD": ("XAUUSD", "GOLD"),
    "XAG/USD": ("XAGUSD", "SILVER"),
    "NASDAQ 100": ("USTEC", "NAS100", "NASDAQ"),
    "S&P 500": ("US500", "SP500", "SPX500", "S&P 500"),
    "DOW 30": ("US30", "DJ30", "DOW"),
    "WTI": ("USOIL", "WTI", "XTIUSD"),
    "BTC/USD": ("BTCUSD",),
    "BTC/USDT": ("BTCUSDT",),
    "ETH/USD": ("ETHUSD",),
    "SOL/USD": ("SOLUSD",),
}


def category_from_path(path: str | None) -> str:
    if not path:
        return "(no path)"
    parts = [part for part in path.split("\\") if part]
    if len(parts) >= 2:
        return parts[1]
    return parts[0] if parts else "(no path)"


def compact_symbol(item: object) -> dict[str, object]:
    return {
        "name": getattr(item, "name", None),
        "description": getattr(item, "description", None),
        "path": getattr(item, "path", None),
        "digits": getattr(item, "digits", None),
        "currency_base": getattr(item, "currency_base", None),
        "currency_profit": getattr(item, "currency_profit", None),
        "trade_mode": getattr(item, "trade_mode", None),
        "visible": getattr(item, "visible", None),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit the MT5 symbol universe")
    parser.add_argument("--terminal-path", default=None, help="Optional path to terminal64.exe")
    args = parser.parse_args()

    connector = MT5Connector(source_name="exness_mt5_demo")
    connector.connect(args.terminal_path)
    try:
        symbols = connector.symbols()
        counts = Counter(category_from_path(getattr(item, "path", None)) for item in symbols)

        print(f"total symbols: {len(symbols)}")
        print("category counts:")
        for category, count in sorted(counts.items(), key=lambda pair: (-pair[1], pair[0])):
            print(json.dumps({"category": category, "count": count}))

        print("target matches:")
        for canonical, aliases in TARGET_ALIASES.items():
            matches: list[dict[str, object]] = []
            for item in symbols:
                name = str(getattr(item, "name", "") or "")
                description = str(getattr(item, "description", "") or "")
                haystack = f"{name} {description}".upper()
                if any(alias.upper() in haystack for alias in aliases):
                    matches.append(compact_symbol(item))
            print(json.dumps({"canonical": canonical, "matches": matches}, default=str))
    finally:
        connector.disconnect()


if __name__ == "__main__":
    main()
