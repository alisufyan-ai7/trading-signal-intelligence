#!/usr/bin/env python3
"""Read-only original AI/S02 SQLite source -> sanitized cohort audit CLI.

No ledger constructors, database migrations, customer data ingestion, network,
broker or cloud publication. Only aggregate receipt to STDOUT on success.
Run on a pre-frozen read-only copy with independently reviewed external pins.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from trading_signal_intelligence.product.accounts.source_projection_reconciliation import (
    SourceProjectionReconciliationError, check_source_projection_link,
)

ACK="READ_ONLY_FROZEN_SOURCE_RECONCILIATION"


def _frozen_digest(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        raise SourceProjectionReconciliationError("Source must be a frozen existing regular file")
    digest=hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b""):
            digest.update(chunk)
    return digest.hexdigest()


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="VowSig original-source read-only cross-check")
    parser.add_argument("--source-file",required=True)
    parser.add_argument("--profile",required=True,choices=("ai_v1","s02_forward"))
    parser.add_argument("--expected-frozen-file-sha256",required=True)
    parser.add_argument("--source-head-sha256",required=True)
    parser.add_argument("--source-record-count",required=True,type=int)
    parser.add_argument("--bundle-file",required=True)
    parser.add_argument("--bundle-sha256",required=True)
    parser.add_argument("--outcome-count",required=True,type=int)
    parser.add_argument("--source-program",required=True)
    parser.add_argument("--model-version",required=True)
    parser.add_argument("--cohort",required=True)
    parser.add_argument("--confirm",required=True)
    args=parser.parse_args(argv)
    try:
        if args.confirm!=ACK:
            raise SourceProjectionReconciliationError("Explicit offline read-only approval needed")
        source=Path(args.source_file)
        bundle=Path(args.bundle_file)
        if bundle.is_symlink() or not bundle.is_file() or bundle.stat().st_size>25_000_000:
            raise SourceProjectionReconciliationError("Sanitized bundle must be a local finite file")
        expected=args.expected_frozen_file_sha256
        if len(expected)!=64 or any(x not in "0123456789abcdef" for x in expected):
            raise SourceProjectionReconciliationError("Source file SHA256 pin required")
        before=_frozen_digest(source)
        if before!=expected:
            raise SourceProjectionReconciliationError("Frozen source file digest mismatch")
        receipt=check_source_projection_link(
            sqlite_path=source,
            source_profile=args.profile,
            expected_source_head_sha256=args.source_head_sha256,
            expected_source_ledger_records=args.source_record_count,
            sanitized_bundle=bundle.read_bytes(),
            expected_bundle_sha256=args.bundle_sha256,
            expected_outcome_population=args.outcome_count,
            expected_source_program_id=args.source_program,
            expected_model_version=args.model_version,
            expected_cohort=args.cohort,
        )
        after=_frozen_digest(source)
        if after!=expected or before!=after:
            raise SourceProjectionReconciliationError("Source changed during audit")
        print(json.dumps({
            **receipt,
            "source_file_sha256_verified":True,
            "source_changed_during_audit":False,
            "contains_private_ledger_rows":False,
        },sort_keys=True,separators=(",",":"),allow_nan=False))
        return 0
    except (ValueError,OSError,RuntimeError) as exc:
        # Do not print absolute file paths, sensitive source payloads or
        # raw Python SQL/database exception strings.
        print("VOWSIG_SOURCE_PROJECTION_AUDIT=FAIL_CLOSED",file=sys.stderr)
        print("REASON_TYPE="+type(exc).__name__,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
