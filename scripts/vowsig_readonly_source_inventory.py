#!/usr/bin/env python3
"""Read-only VowSig source inventory operator; never alters live ledgers.

Shows counts and observed hash heads only. This is NOT a frozen source audit
or independent immutable pin, even when all expected paths are present.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from trading_signal_intelligence.product.accounts.source_inventory import (
    inventory_expected_sources,
)

ACK="READ_ONLY_NO_VPS_LEDGER_CHANGES"


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Read-only 12-ledger VowSig source inventory")
    parser.add_argument("--repo-root",required=True)
    parser.add_argument("--confirm",required=True)
    args=parser.parse_args(argv)
    try:
        root=Path(args.repo_root).resolve(strict=True)
        if args.confirm!=ACK or root.name!="trading-signal-intelligence":
            raise ValueError("Exact repo root and explicit read-only confirmation required")
        result=inventory_expected_sources(root)
        print(json.dumps(result,sort_keys=True,allow_nan=False))
        return 0
    except (ValueError,OSError,RuntimeError) as exc:
        print("SOURCE_INVENTORY=DENIED",file=sys.stderr)
        print("REASON_TYPE="+type(exc).__name__,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
