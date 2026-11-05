#!/usr/bin/env python3
"""Read-only offline verify of a PRIVATE twelve-ledger frozen evidence set."""
from __future__ import annotations
import argparse
import json
import sys
from trading_signal_intelligence.product.accounts.private_source_freeze import (
    PrivateSourceFreezeError,verify_private_frozen_set,
)


def main(argv=None):
    p=argparse.ArgumentParser()
    p.add_argument("--repo-root",required=True)
    p.add_argument("--private-run-dir",required=True)
    p.add_argument("--expected-manifest-sha256",required=True)
    p.add_argument("--confirm",required=True)
    a=p.parse_args(argv)
    if a.confirm!="READ_ONLY_PRIVATE_FROZEN_RECHECK":
        print("FROZEN_SOURCE_RECHECK=DENIED",file=sys.stderr)
        return 1
    try:
        result=verify_private_frozen_set(
            a.repo_root,a.private_run_dir,
            externally_recorded_manifest_sha256=a.expected_manifest_sha256,
        )
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
    except PrivateSourceFreezeError:
        print("FROZEN_SOURCE_RECHECK=HELD",file=sys.stderr)
        return 1
    return 0


if __name__=="__main__":
    raise SystemExit(main())
