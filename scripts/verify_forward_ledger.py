from __future__ import annotations

import argparse
import json

from trading_signal_intelligence.forward import ForwardLedger


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify the append-only forward ledger hash chain")
    parser.add_argument("--database", default="data/forward.sqlite")
    args = parser.parse_args()

    ledger = ForwardLedger(args.database)
    payload = {
        "database": args.database,
        "verification": ledger.verify(),
        "counts_by_type": ledger.counts_by_type(),
        "unresolved_signal_entities": ledger.unresolved_signal_entities(),
        "ledger_head_hash": ledger.head_hash(),
    }
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    main()
