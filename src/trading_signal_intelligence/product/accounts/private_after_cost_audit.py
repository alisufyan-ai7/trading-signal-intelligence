"""Nonpromoting, private, original AI shadow-ledger after-cost arithmetic proof.

Requires previously exported SHA256 file/head pins; frozen SQLite only.
Does NOT claim market price truth, source rights, real executions, K5 provenance
or independent financial performance. No raw trades/identities leave this API.
"""
from __future__ import annotations

from contextlib import closing
import hashlib
import json
import math
from pathlib import Path
import re
import sqlite3
from typing import Any


class FrozenCostAuditHold(ValueError):
    pass


_AI = frozenset(("AI-v1.1","AI-v1.2.1","AI-v1.3"))
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _digest(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def _finite(value: Any) -> float:
    if isinstance(value,bool) or not isinstance(value,(float,int)):
        raise FrozenCostAuditHold("Missing numeric frozen outcome")
    number=float(value)
    if not math.isfinite(number):
        raise FrozenCostAuditHold("Nonfinite frozen cost or outcome")
    return number


def _close(a: float,b: float) -> bool:
    return math.isclose(a,b,rel_tol=1e-9,abs_tol=1e-9)


def _payload(raw: str) -> dict[str,Any]:
    def unique(pairs):
        result={}
        for key,value in pairs:
            if key in result:
                raise FrozenCostAuditHold("Duplicate frozen payload key")
            result[key]=value
        return result
    try:
        value=json.loads(raw,object_pairs_hook=unique,
                         parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
    except (ValueError,TypeError) as exc:
        raise FrozenCostAuditHold("Invalid original outcome payload") from exc
    if not isinstance(value,dict):
        raise FrozenCostAuditHold("Frozen outcome payload not object")
    return value


def _signal(p: dict[str,Any], *, model_version: str, market: str) -> None:
    if p.get("source_symbol")!=market or p.get("direction") not in ("BUY","SELL"):
        raise FrozenCostAuditHold("Signal source/direction mismatch")
    entry=_finite(p.get("entry"))
    risk=_finite(p.get("risk_price"))
    cost=_finite(p.get("total_cost_price"))
    if entry<=0 or risk<=0 or cost<0:
        raise FrozenCostAuditHold("Invalid frozen entry/risk/cost")
    tp1=_finite(p.get("tp1_position_fraction"))
    if not 0<tp1<1:
        raise FrozenCostAuditHold("Unapproved fractional-exit policy")
    if model_version=="AI-v1.3":
        if p.get("cost_policy_version")!="AI-v1.3-crypto-cost-v0.1":
            raise FrozenCostAuditHold("Crypto cost-policy version mismatch")
        expected=(
            _finite(p.get("round_trip_fee_price"))+
            _finite(p.get("spread_crossing_price"))+
            _finite(p.get("slippage_buffer_price"))
        )
        if (not _close(cost,expected) or
            not _close(_finite(p.get("estimated_cost_r")),cost/risk) or
            cost/risk>0.15+1e-9):
            raise FrozenCostAuditHold("Crypto cost breakdown/guard mismatch")
        # Frozen policy assumes 0.1% taker entry + 0.1% taker exit.
        midpoint=_finite(p.get("reference_midpoint"))
        if midpoint<=0 or not _close(_finite(p.get("round_trip_fee_price")),
                                    0.002*midpoint):
            raise FrozenCostAuditHold("Crypto taker fee assumption mismatch")
    else:
        spread=_finite(p.get("spread_price"))
        multiplier=_finite(p.get("cost_multiplier"))
        if spread<0 or multiplier<0 or not _close(cost,spread*multiplier):
            raise FrozenCostAuditHold("FX/index/metal cost hypothesis mismatch")


def _contribution(signal: dict[str,Any], exit_payload: dict[str,Any],
                  *, frac_field: str) -> float:
    risk=_finite(signal.get("risk_price"))
    fraction=_finite(exit_payload.get(frac_field))
    if not 0<fraction<=1:
        raise FrozenCostAuditHold("Invalid exit fraction")
    price=_finite(exit_payload.get("exit_price"))
    direction=signal["direction"]
    sign=1.0 if direction=="BUY" else -1.0
    gross=fraction*sign*(price-_finite(signal["entry"]))/risk
    cost=fraction*_finite(signal["total_cost_price"])/risk
    net=gross-cost
    if not all((
        _close(_finite(exit_payload.get("gross_contribution_r")),gross),
        _close(_finite(exit_payload.get("cost_contribution_r")),cost),
        _close(_finite(exit_payload.get("net_contribution_r")),net),
    )):
        raise FrozenCostAuditHold("Original exit R decomposition incorrect")
    return net


def audit_frozen_after_costs(
    path: str | Path, *, model_version: str, market: str,
    expected_frozen_file_sha256: str, expected_terminal_record_hash: str,
) -> dict[str,Any]:
    if model_version not in _AI or not isinstance(market,str) or not market:
        raise FrozenCostAuditHold("Unapproved source model/market")
    if (type(expected_frozen_file_sha256) is not str or
        not _SHA.fullmatch(expected_frozen_file_sha256) or
        type(expected_terminal_record_hash) is not str or
        not _SHA.fullmatch(expected_terminal_record_hash)):
        raise FrozenCostAuditHold("External source pins required")
    file=Path(path)
    if file.is_symlink() or not file.is_file():
        raise FrozenCostAuditHold("Frozen original ledger unavailable")
    if _digest(file)!=expected_frozen_file_sha256:
        raise FrozenCostAuditHold("Frozen file SHA256 mismatch")
    signals:dict[str,tuple[int,str,dict[str,Any]]]={}
    partials:dict[str,tuple[int,str,dict[str,Any]]]={}
    exits:dict[str,tuple[int,str,dict[str,Any]]]={}
    n=0
    head=None
    try:
        with closing(sqlite3.connect(
            file.resolve(strict=True).as_uri()+"?mode=ro&immutable=1",
            uri=True,timeout=1,
        )) as db:
            db.execute("PRAGMA query_only=ON")
            db.execute("BEGIN")
            for seq,kind,entity,row_hash,payload in db.execute(
                "SELECT sequence,record_type,entity_id,record_hash,payload_json "
                "FROM ai_records ORDER BY sequence"
            ):
                n+=1
                if seq!=n:
                    raise FrozenCostAuditHold("Frozen source event sequence gap")
                head=row_hash
                if kind not in ("SIGNAL","EXIT","PARTIAL_EXIT"):
                    continue
                target={"SIGNAL":signals,"PARTIAL_EXIT":partials,"EXIT":exits}[kind]
                if not isinstance(entity,str) or not entity or entity in target:
                    raise FrozenCostAuditHold("Duplicate or empty outcome identity")
                target[entity]=(seq,row_hash,_payload(payload))
    except sqlite3.Error as exc:
        raise FrozenCostAuditHold("Read-only private ledger unavailable") from exc
    if head!=expected_terminal_record_hash or n<1:
        raise FrozenCostAuditHold("Frozen original source head differs")
    if any(entity not in signals for entity in {*partials,*exits}):
        raise FrozenCostAuditHold("Orphan original signal exit")
    total_verified=0
    closed=0
    for entity,(sigseq,sighash,p) in signals.items():
        _signal(p,model_version=model_version,market=market)
        partial=partials.get(entity)
        exit=exits.get(entity)
        partial_net=0.0
        if partial:
            partseq,parthash,pp=partial
            if (partseq<=sigseq or pp.get("signal_record_hash")!=sighash
                or pp.get("source_symbol")!=market
                or pp.get("direction")!=p["direction"]
                or not _close(_finite(pp.get("fraction")),
                              _finite(p["tp1_position_fraction"]))):
                raise FrozenCostAuditHold("Partial exit identity/policy mismatch")
            partial_net=_contribution(p,pp,frac_field="fraction")
        if exit:
            exitseq,_,ep=exit
            if (exitseq<=sigseq or (partial and exitseq<=partial[0])
                or ep.get("signal_record_hash")!=sighash
                or ep.get("source_symbol")!=market
                or ep.get("direction")!=p["direction"]
                or ep.get("partial_exit_record_hash")!=
                    (partial[1] if partial else None)):
                raise FrozenCostAuditHold("Exit identity/partial lineage mismatch")
            expected_fraction=(
                1-_finite(p.get("tp1_position_fraction")) if partial else 1.0
            )
            if not _close(_finite(ep.get("remaining_fraction")),expected_fraction):
                raise FrozenCostAuditHold("Position fractions do not sum to one")
            exit_net=_contribution(p,ep,frac_field="remaining_fraction")
            if not _close(_finite(ep.get("total_combined_signal_net_r")),
                          partial_net+exit_net):
                raise FrozenCostAuditHold("Combined after-cost net R inconsistent")
            total_verified+=1
            closed+=1
    if _digest(file)!=expected_frozen_file_sha256:
        raise FrozenCostAuditHold("Frozen evidence changed during read")
    return {
        "status":"FROZEN_AFTER_COST_ARITHMETIC_SELF_CONSISTENT_NOT_ATTESTED",
        "model_version":model_version,"market":market,
        "original_event_records":n,"signal_count":len(signals),
        "closed_signal_count":closed,"open_signal_count":len(signals)-closed,
        "partial_exit_event_count":len(partials),
        "closed_after_cost_arithmetic_checked":total_verified,
        "source_snapshot_sha256_matches_external_owner_pin":True,
        "actual_broker_or_provider_costs_verified":False,
        "full_market_time_universe_verified":False,
        "source_rights_and_independent_reviewer_approved":False,
        "historical_profitability_certified":False,
        "raw_trade_identities_or_payloads_exported":False,
    }
