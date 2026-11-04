"""Strict READ-ONLY, fixed 12-ledger source inventory for the VowSig owner.

Only paths explicitly declared in this repository's governed shadow runtime
and launch-universe contracts. No glob of customer files and no ledger
constructor, PRAGMA mutation, cloud, network, or raw payload export.
A live head/count is NOT an independent frozen source proof.
"""
from __future__ import annotations

from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import re
import sqlite3
from typing import Any


@dataclass(frozen=True)
class ExpectedSource:
    program: str
    model_version: str
    symbol: str
    relative_path: str
    table: str


SOURCES=(
    ExpectedSource("core-ai-shadow","AI-v1.1","XAUUSD","data/ai_v1_1_xauusd.sqlite","ai_records"),
    ExpectedSource("core-ai-shadow","AI-v1.1","USTEC","data/ai_v1_1_ustec.sqlite","ai_records"),
    ExpectedSource("core-ai-shadow","AI-v1.1","US30","data/ai_v1_1_us30.sqlite","ai_records"),
    ExpectedSource("market-expansion-1","AI-v1.2.1","EURUSD","data/ai_v1_2_1_eurusd.sqlite","ai_records"),
    ExpectedSource("market-expansion-1","AI-v1.2.1","XAGUSD","data/ai_v1_2_1_xagusd.sqlite","ai_records"),
    ExpectedSource("market-expansion-1","AI-v1.2.1","USOIL","data/ai_v1_2_1_usoil.sqlite","ai_records"),
    ExpectedSource("crypto-expansion-1","AI-v1.3","BTCUSDT","data/ai_v1_3_btcusdt.sqlite","ai_records"),
    ExpectedSource("crypto-expansion-1","AI-v1.3","ETHUSDT","data/ai_v1_3_ethusdt.sqlite","ai_records"),
    ExpectedSource("crypto-expansion-1","AI-v1.3","SOLUSDT","data/ai_v1_3_solusdt.sqlite","ai_records"),
    ExpectedSource("s02-forward","S02-v0.1","XAUUSD","data/forward.sqlite","forward_records"),
    ExpectedSource("s02-forward","S02-v0.1","USTEC","data/forward_ustec.sqlite","forward_records"),
    ExpectedSource("s02-forward","S02-v0.1","US30","data/forward_us30.sqlite","forward_records"),
)

_HASH=re.compile(r"^[0-9a-f]{64}$")
_SAFE_TYPES=("ACTIVATION","INFERENCE","NO_TRADE","REJECTED_INFERENCE",
             "SIGNAL","EXIT","PARTIAL_EXIT","MISSED_INFERENCE","ERROR")


def inventory_expected_sources(root: str | Path) -> dict[str, Any]:
    root_path=Path(root).resolve(strict=True)
    result=[]
    for spec in SOURCES:
        item={
            "program":spec.program,
            "model_version":spec.model_version,
            "symbol":spec.symbol,
            "relative_path":spec.relative_path,
            "status":"MISSING",
            "record_count":None,
            "sequence_max":None,
            "last_record_hash":None,
            "event_counts":None,
            "other_event_type_rows":None,
            "frozen_source_independently_verified":False,
        }
        file=root_path / spec.relative_path
        if file.is_symlink() or not file.is_file():
            item["status"]="SYMLINK_REFUSED" if file.is_symlink() else "MISSING"
            result.append(item)
            continue
        try:
            resolved=file.resolve(strict=True)
            if not resolved.is_relative_to(root_path):
                item["status"]="ESCAPES_REPO_REFUSED"
                result.append(item)
                continue
            with closing(sqlite3.connect(resolved.as_uri()+"?mode=ro",
                                         uri=True,timeout=0.5)) as conn:
                conn.row_factory=sqlite3.Row
                conn.execute("PRAGMA query_only=ON")
                conn.execute("BEGIN")
                counts=conn.execute(
                    "SELECT count(*) AS n,max(sequence) AS max_seq FROM "+spec.table
                ).fetchone()
                head=conn.execute(
                    "SELECT record_hash FROM "+spec.table+
                    " ORDER BY sequence DESC LIMIT 1"
                ).fetchone()
                types=conn.execute(
                    "SELECT record_type,count(*) AS n FROM "+spec.table+
                    " GROUP BY record_type"
                ).fetchall()
            number=int(counts["n"])
            last=head["record_hash"] if head is not None else None
            # Do not return malformed or non-SHA ledger heads as trustworthy.
            if (number and
                (type(last) is not str or not _HASH.fullmatch(last))):
                raise ValueError("Untrusted original source head")
            metrics={kind:0 for kind in _SAFE_TYPES}
            other_event_type_rows=0
            for row in types:
                if row["record_type"] in metrics:
                    metrics[row["record_type"]]=int(row["n"])
                else:
                    # Do not expose unexpected original event names or payloads.
                    other_event_type_rows+=int(row["n"])
            item.update({
                "status":"OBSERVED_UNFROZEN" if number else "EMPTY_LEDGER",
                "record_count":number,
                "sequence_max":int(counts["max_seq"]) if number else None,
                "last_record_hash":last,
                "event_counts":metrics,
                "other_event_type_rows":other_event_type_rows,
            })
        except (sqlite3.Error, OSError,ValueError,OverflowError):
            item["status"]="READ_ONLY_SOURCE_UNAVAILABLE"
        result.append(item)
    found=sum(x["status"]=="OBSERVED_UNFROZEN" for x in result)
    empty=sum(x["status"]=="EMPTY_LEDGER" for x in result)
    unavailable=len(SOURCES)-found-empty
    unknown=sum((x["other_event_type_rows"] or 0) for x in result)
    return {
        "schema_version":1,
        "status":"PRELIMINARY_LIVE_SOURCE_INVENTORY_UNVERIFIED",
        "source":"repository_defined_original_ledger_paths",
        "expected_ledger_files":len(SOURCES),
        "observed_nonempty_ledger_files":found,
        "empty_ledger_files":empty,
        "missing_or_unreadable_ledger_files":unavailable,
        "other_event_type_rows":unknown,
        "all_original_sources_independently_verified":False,
        "crypto_k5_provenance_verified":False,
        "historical_net_r_verified":False,
        "contains_raw_source_records":False,
        "warning":(
            "A live SQLite count/head is NOT an immutable external pin. "
            "Freeze authorized copies and compare independent reviewed hashes "
            "before any source history or profitability certification."
        ),
        "ledgers":result,
    }
