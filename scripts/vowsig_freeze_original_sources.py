#!/usr/bin/env python3
"""ONE-TIME PRIVATE source capture; no source writers or scheduled changes."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from trading_signal_intelligence.product.accounts.private_source_freeze import (
    capture_private_frozen_sources, PrivateSourceFreezeError,
)


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo-root",required=True)
    parser.add_argument("--private-root",required=True)
    parser.add_argument("--confirm",required=True)
    args=parser.parse_args(argv)
    if args.confirm != "CREATE_12_PRIVATE_FROZEN_COPIES_NO_PUBLISH":
        print("SOURCE_FREEZE=DENIED",file=sys.stderr)
        return 1
    try:
        result=capture_private_frozen_sources(Path(args.repo_root),Path(args.private_root))
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
    except PrivateSourceFreezeError:
        print("SOURCE_FREEZE=INCOMPLETE_PRIVATE_COPIES_NOT_APPROVED",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
