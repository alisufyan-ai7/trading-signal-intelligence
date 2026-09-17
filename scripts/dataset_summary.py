from __future__ import annotations

import argparse
import json

from trading_signal_intelligence.storage import CandleStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize locally persisted research candles")
    parser.add_argument("--database", default="data/research.sqlite", help="SQLite path")
    args = parser.parse_args()

    store = CandleStore(args.database)
    print(json.dumps(store.summary(), indent=2))


if __name__ == "__main__":
    main()
