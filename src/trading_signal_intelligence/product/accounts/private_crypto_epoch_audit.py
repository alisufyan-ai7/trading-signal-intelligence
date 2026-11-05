"""Private read-only AI-v1.3 frozen epoch and inference-terminal reconciliation.

This checks the ledger-internal hourly-cycle population on an already
SHA-pinned, hash-chain-validated private SQLite snapshot. External Binance
H1/H4 availability, actual scheduled-run receipts, natural K5 provenance,
source rights, and financial outcome costs are NOT verified by this module.
No source rows, ids, timestamps or raw error messages are returned.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
from typing import Any

SYMBOLS = ("BTCUSDT","ETHUSDT","SOLUSDT")
CYCLE_TYPES = frozenset((
    "INFERENCE","NO_TRADE","REJECTED_INFERENCE","SIGNAL",
    "ERROR","MISSED_INFERENCE",
))
TERMINALS = frozenset(("NO_TRADE","REJECTED_INFERENCE","SIGNAL"))
_STAGES = frozenset(("provider_inference","crypto_execution_cost_context"))


class FrozenCryptoEpochAuditError(ValueError):
    """Unsupported or unreadable frozen source; never expose payload details."""


def _utc(value: str) -> datetime:
    if not isinstance(value,str):
        raise FrozenCryptoEpochAuditError("Invalid epoch timestamp encoding")
    try:
        time=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise FrozenCryptoEpochAuditError("Invalid epoch datetime") from exc
    if time.tzinfo is None or time.utcoffset()!=timedelta(0):
        raise FrozenCryptoEpochAuditError("Crypto epoch requires UTC")
    return time.astimezone(timezone.utc)


def _cycle_id(value: str, symbol: str, activation: datetime) -> datetime:
    prefix=f"AI-v1.3:{symbol}:"
    if not isinstance(value,str) or not value.startswith(prefix):
        raise FrozenCryptoEpochAuditError("Unexpected crypto cycle identity")
    date_part=value[len(prefix):]
    stamp=_utc(date_part)
    if (not date_part.endswith("Z") or stamp.minute or stamp.second
        or stamp.microsecond or stamp<=activation
        or stamp.isoformat().replace("+00:00","Z")!=date_part):
        raise FrozenCryptoEpochAuditError("Crypto cycle close is not postactivation hourly UTC")
    return stamp


def _unique(pairs):
    obj={}
    for k,v in pairs:
        if k in obj:
            raise FrozenCryptoEpochAuditError("Duplicate payload JSON key")
        obj[k]=v
    return obj


def _payload(raw: str) -> dict[str,Any]:
    if not isinstance(raw,str):
        raise FrozenCryptoEpochAuditError("Crypto event payload missing")
    try:
        value=json.loads(
            raw,object_pairs_hook=_unique,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError("nonfinite")),
        )
    except (ValueError,TypeError) as exc:
        raise FrozenCryptoEpochAuditError("Malformed crypto event payload") from exc
    if not isinstance(value,dict):
        raise FrozenCryptoEpochAuditError("Crypto event payload is not an object")
    return value


def audit_frozen_crypto_epoch(
    path: str | Path, *, symbol: str, activated_at_utc: str,
) -> dict[str,Any]:
    if symbol not in SYMBOLS:
        raise FrozenCryptoEpochAuditError("Unapproved crypto market")
    file=Path(path)
    if file.is_symlink() or not file.is_file():
        raise FrozenCryptoEpochAuditError("Frozen crypto copy unavailable")
    activation=_utc(activated_at_utc)
    cycles: dict[str,list[tuple[int,str,str,dict[str,Any]]]]={}
    counts:Counter[str]=Counter()
    error_stages:Counter[str]=Counter()
    misses:Counter[str]=Counter()
    n=0
    activation_count=0
    try:
        with closing(sqlite3.connect(
            file.resolve(strict=True).as_uri()+"?mode=ro&immutable=1",
            uri=True,timeout=1,
        )) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            for sequence,kind,entity,effective,recorded,payload_raw,row_hash in db.execute(
                "SELECT sequence,record_type,entity_id,effective_at_utc,"
                "recorded_at_utc,payload_json,record_hash "
                "FROM ai_records ORDER BY sequence"
            ):
                n+=1
                if sequence!=n:
                    raise FrozenCryptoEpochAuditError("Source sequence discontinuity")
                counts[kind]+=1
                if kind=="ACTIVATION":
                    activation_count+=1
                    if sequence!=1:
                        raise FrozenCryptoEpochAuditError("Crypto activation not first")
                    continue
                if kind in ("EXIT","PARTIAL_EXIT"):
                    continue
                if kind not in CYCLE_TYPES:
                    raise FrozenCryptoEpochAuditError("Unapproved original crypto event")
                cycle=_cycle_id(entity,symbol,activation)
                if _utc(effective)!=cycle or _utc(recorded)<cycle:
                    raise FrozenCryptoEpochAuditError("Crypto event time/identity mismatch")
                payload=_payload(payload_raw)
                if (payload.get("runtime_version")!="AI-v1.3" or
                    payload.get("source_symbol")!=symbol):
                    raise FrozenCryptoEpochAuditError("Crypto source identity invalid")
                # NO_TRADE and REJECTED_INFERENCE terminal payloads do not
                # repeat exposure flags in the original crypto engine. A
                # missing flag is allowed ONLY on these two terminal types.
                if kind in ("NO_TRADE","REJECTED_INFERENCE"):
                    if (payload.get("broker_execution_enabled",False) is not False or
                        payload.get("public_signal_exposure_enabled",False) is not False):
                        raise FrozenCryptoEpochAuditError("Crypto terminal exposure enabled")
                elif (payload.get("broker_execution_enabled") is not False or
                      payload.get("public_signal_exposure_enabled") is not False):
                    raise FrozenCryptoEpochAuditError("Crypto execution/exposure enabled")
                if "source_bar_close_utc" in payload:
                    if _utc(str(payload["source_bar_close_utc"]))!=cycle:
                        raise FrozenCryptoEpochAuditError("Payload cycle close mismatch")
                if kind=="INFERENCE":
                    snapshot=payload.get("feature_snapshot")
                    if (not isinstance(snapshot,dict) or
                        _utc(str(snapshot.get("source_bar_close_utc")))!=cycle):
                        raise FrozenCryptoEpochAuditError("Inference feature close mismatch")
                if kind=="ERROR":
                    stage=payload.get("stage")
                    error_stages[stage if stage in _STAGES else "other"]+=1
                if kind=="MISSED_INFERENCE":
                    reason=payload.get("reason")
                    misses[reason if reason in (
                        "scheduler_gap_or_stale_at_discovery",
                        "next_h1_open_unavailable","stale_before_provider_call"
                    ) else "other"]+=1
                cycles.setdefault(entity,[]).append((n,kind,row_hash,payload))
    except sqlite3.Error as exc:
        raise FrozenCryptoEpochAuditError("Read-only frozen crypto source unavailable") from exc
    if activation_count!=1 or not cycles:
        raise FrozenCryptoEpochAuditError("Crypto activation/cycles absent")
    matched=0
    held=0
    failed_links=0
    for events in cycles.values():
        inferred=[r for r in events if r[1]=="INFERENCE"]
        terminal=[r for r in events if r[1] in TERMINALS]
        failures=[r for r in events if r[1] in ("ERROR","MISSED_INFERENCE")]
        if len(inferred)==1 and len(terminal)==1 and len(failures)==0:
            a,b=inferred[0],terminal[0]
            if (a[0]>=b[0] or
                b[3].get("originating_inference_record_hash")!=a[2] or
                (b[1]=="SIGNAL" and a[3].get("guard_publishable") is not True) or
                (b[1]=="REJECTED_INFERENCE" and a[3].get("guard_publishable") is not False)):
                held+=1
                failed_links+=1
            else:
                matched+=1
        elif len(inferred)==0 and len(terminal)==0 and len(failures)==1:
            pass
        else:
            held+=1
            failed_links+=1
    cycle_closes=sorted(_cycle_id(e,symbol,activation) for e in cycles)
    missing_hours=int((cycle_closes[-1]-cycle_closes[0])/timedelta(hours=1))+1-len(cycle_closes)
    if missing_hours<0:
        raise FrozenCryptoEpochAuditError("Duplicate internal hourly epoch")
    # K5 external opportunity and scheduler proof must be evaluated separately.
    return {
        "status":("FROZEN_CRYPTO_INTERNAL_EPOCH_CONSISTENT_NOT_K5_CERTIFIED"
                  if not held and not missing_hours
                  else "FROZEN_CRYPTO_EPOCH_HOLD_SOURCE_COVERAGE_REVIEW"),
        "market":symbol,
        "source_event_rows":n,
        "postactivation_cycle_entities":len(cycles),
        "inference_cycles":counts["INFERENCE"],
        "matched_inference_outcomes":matched,
        "unmatched_or_duplicate_cycle_entities":held,
        "unmatched_inference_terminal_links":failed_links,
        "unobserved_internal_h1_closes":missing_hours,
        "error_stage_counts":dict(sorted(error_stages.items())),
        "missed_reason_counts":dict(sorted(misses.items())),
        "event_type_counts":dict(sorted(counts.items())),
        "raw_source_rows_or_cycle_identities_exported":False,
        "activation_source_anchor_verified_separately":True,
        "external_h1_h4_provider_coverage_verified":False,
        "scheduler_receipts_verified":False,
        "complete_k5_natural_epoch_provenance_verified":False,
        "after_cost_returns_verified":False,
    }
