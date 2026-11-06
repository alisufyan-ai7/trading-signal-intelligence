"""Read-only private frozen-ledger lifecycle population checks.

Only discrete event identity/order is established. This deliberately DOES NOT
interpret financial outcome payloads as independently after-cost verified.
Run on private consistent copied sources, never against mutable production DB.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from pathlib import Path
import sqlite3
from typing import Any


class FrozenLifecycleError(ValueError):
    pass


def frozen_lifecycle_counts(copy_path: str | Path, *, profile: str) -> dict[str,Any]:
    if profile not in ("ai_v1","s02_forward"):
        raise FrozenLifecycleError("Unapproved source lifecycle profile")
    path=Path(copy_path)
    if path.is_symlink() or not path.is_file():
        raise FrozenLifecycleError("Frozen ledger must be existing regular file")
    table="forward_records" if profile=="s02_forward" else "ai_records"
    signals: dict[str,int]={}
    exits: dict[str,int]={}
    partials: dict[str,int]={}
    types: Counter[str]=Counter()
    sequence=0
    try:
        with closing(sqlite3.connect(path.resolve(strict=True).as_uri()+"?mode=ro",
                                      uri=True,timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            for current,kind,entity in db.execute(
                f"SELECT sequence,record_type,entity_id FROM {table} ORDER BY sequence"
            ):
                sequence+=1
                if current!=sequence or not isinstance(entity,str) or not entity:
                    raise FrozenLifecycleError("Untrusted lifecycle source row")
                types[kind]+=1
                if kind=="SIGNAL":
                    if entity in signals:
                        raise FrozenLifecycleError("Duplicate original SIGNAL entity")
                    signals[entity]=sequence
                elif kind=="EXIT":
                    if entity in exits:
                        raise FrozenLifecycleError("Duplicate original EXIT entity")
                    exits[entity]=sequence
                elif kind=="PARTIAL_EXIT":
                    if entity in partials:
                        raise FrozenLifecycleError("Duplicate original PARTIAL_EXIT entity")
                    partials[entity]=sequence
    except sqlite3.Error as exc:
        raise FrozenLifecycleError("Frozen read-only lifecycle unavailable") from exc

    missing_signal_exits=sum(e not in signals for e in exits)
    premature_exits=sum(e in signals and exits[e]<=signals[e] for e in exits)
    unmatched_partials=sum(e not in signals for e in partials)
    early_partials=sum(e in signals and partials[e]<=signals[e] for e in partials)
    partials_after_close=sum(
        e in exits and partials[e]>=exits[e] for e in partials
    )
    closed=sum(e in exits for e in signals)
    open_count=len(signals)-closed
    lifecycle_consistent=(
        missing_signal_exits==0 and premature_exits==0
        and unmatched_partials==0 and early_partials==0
        and partials_after_close==0
    )
    return {
        "status":"SOURCE_EVENT_LIFECYCLE_SELF_CONSISTENT_NOT_FINANCIALLY_VERIFIED"
        if lifecycle_consistent else "SOURCE_EVENT_LIFECYCLE_HOLD_REVIEW_REQUIRED",
        "profile":profile,
        "source_event_rows":sequence,
        "signal_entities":len(signals),
        "exited_signal_entities":closed,
        "open_signal_entities":open_count,
        "partially_exited_signal_entities":len(partials),
        "orphan_exit_entities":missing_signal_exits,
        "exit_before_signal_entities":premature_exits,
        "orphan_partial_exit_entities":unmatched_partials,
        "partial_before_signal_entities":early_partials,
        "partial_after_exit_entities":partials_after_close,
        "event_counts":dict(sorted(types.items())),
        "original_entity_identifiers_exported":False,
        "independent_source_pins_approved":False,
        "cost_model_arithmetic_verified":False,
        "trading_profits_verified":False,
    }
