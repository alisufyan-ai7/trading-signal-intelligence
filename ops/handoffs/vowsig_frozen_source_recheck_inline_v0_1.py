"""No-download, READ-ONLY recheck of owner-exported 12 private frozen ledgers.

The pinned hashes here came from the owner's 2026-11-05T03:12Z stdout,
durably recorded in PR #93 comment 6648710534. This is NOT independent
reviewer custody, K5 epoch verification, source rights, or after-cost proof.
No Git, network, source write, destination write, SQL mutation or raw export.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
import hashlib
import json
from pathlib import Path
import re
import sqlite3
import sys

MANIFEST_SHA256="bec335b870214b5e770af652869767f54bc960000dd6031278ea0ebf460cbc45"
# version, symbol, table, source row count, frozen-file SHA256, terminal row hash
PINNED={
 "ai_v1_1_xauusd.sqlite":("AI-v1.1","XAUUSD","ai_records",1325,"704b7935e68315f5e0296efe5dbd1eb6b4c13117ebb47818500b5ef581d87cf1","5162be2a041c82c1a2e3bab81acfe39f3f3fa902ec62d3a215a543b0dd62333a"),
 "ai_v1_1_ustec.sqlite":("AI-v1.1","USTEC","ai_records",1332,"eec027e06fc7c944ec0c40bcd91d42f76602fb7950cc5cd88018c0bb437601f3","4b9ac140a9ad2f496b5b9e91c2c2fbc6573f400e90c113dbfa77dd714ce998be"),
 "ai_v1_1_us30.sqlite":("AI-v1.1","US30","ai_records",1329,"14917ed7da6e2880a28f38b00e80bf61a657f48cb9341dc0fe0394b98ed2a4da","42f277a59f76fef2d5adc4a333881b9c1d05d59442db184f3297cae178ecd4b1"),
 "ai_v1_2_1_eurusd.sqlite":("AI-v1.2.1","EURUSD","ai_records",1093,"be744098e7e50f6accb2dc273bb91af3fd296a401305a05d4b8752f7f57a27e1","9bd46cf326e2753d0d9dc59182945fb93bae4278cf39d1a0419d14341970570d"),
 "ai_v1_2_1_xagusd.sqlite":("AI-v1.2.1","XAGUSD","ai_records",1052,"a0314586db35d0b9bf74c4058ef0b8210cc72fe6db3b2a25949ba7d6e0d7bbc9","5e12c038267341e5d114da58e7384baf89b774c06a1b47f32c28786cb37615b3"),
 "ai_v1_2_1_usoil.sqlite":("AI-v1.2.1","USOIL","ai_records",1056,"ed289188a959302d12a319205e256c36032e0af68fc99a58e56a6a00194e3b0d","dec77330493480f4d1708e1ecd576b80c4042237fb1a61fb83ece3b4ee6edba1"),
 "ai_v1_3_btcusdt.sqlite":("AI-v1.3","BTCUSDT","ai_records",1092,"bc6f6d8d5f5ecbca6bd47add3c764cab6d946810056b6a3d3f53a31317508e02","f93383970f373465c771ee2a00d4783b61a8baf1463ab35d3d0d5848739b8225"),
 "ai_v1_3_ethusdt.sqlite":("AI-v1.3","ETHUSDT","ai_records",1100,"e3cf46b107feac4f1becf254b2ebe7d2cfbb5c65cece575a597ea20b4a97786e","e26db53002c25b6bae0f81981b52c5290919e2f6a2b85e104ade796cdaeafc37"),
 "ai_v1_3_solusdt.sqlite":("AI-v1.3","SOLUSDT","ai_records",1096,"0d73fb6088130b4a0959eb95533ad1dbc9109dcd86200ff12079a5d77c1c1776","09bd314381ed021c8f5ebab2a438b5e3df938fd6373125936761e9a0302fd99c"),
 "forward.sqlite":("S02-v0.1","XAUUSD","forward_records",35,"07b55cd6b18594775e970d9951ca132ca0dea8cc0b89fb1c384ed6aaa81c53f5","178f0ca8b3cb674600e997c161e297a3dd4e90262583529eb58e6deaf94ab1a2"),
 "forward_ustec.sqlite":("S02-v0.1","USTEC","forward_records",45,"f04e4ad5160dc7055fe676dd4b64a2a36d8f41dea7aea7359f1e62cd03e478c1","cc7e459fc01edf298366255b9951c5be9b43dc9a3df9cde6e7fd5567f6efdf25"),
 "forward_us30.sqlite":("S02-v0.1","US30","forward_records",40,"0a99859b65f4e4153745ba0745f61a99968e38679443be0690fc6aca52240c4e","c8b92832e16795f0e0ccd6a6bddf667b71216ed05b4f4c904472977527adea7e"),
}
CRYPTO_ACTIVATION_HASHES={
 "BTCUSDT":"8d91fb9a079c43fa79e770ed261f0dad5d8752a0cee3c87adceb97a0d67020b0",
 "ETHUSDT":"fc037684100616b241aaec40aedecaa64f3cbb1d89d9ff523ec721ed135d6931",
 "SOLUSDT":"dc62cd34f44fff7128af7a94ae6813195020e4de49404f84ab79f1f9e2968907",
}
AI_TYPES=frozenset(("ACTIVATION","INFERENCE","NO_TRADE","REJECTED_INFERENCE",
                    "SIGNAL","EXIT","PARTIAL_EXIT","MISSED_INFERENCE","ERROR"))
S02_TYPES=frozenset(("ACTIVATION","SIGNAL","EXIT","MISSED_SIGNAL","SKIPPED_SIGNAL"))
RECEIPT_STATUS="FROZEN_SOURCE_RECHECK_AGAINST_OWNER_RECORDED_PIN_NOT_THIRD_PARTY_ATTESTED"


class FrozenRecheckHold(ValueError):
    pass


def _digest(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def _unique(pairs):
    value={}
    for key,item in pairs:
        if key in value:
            raise FrozenRecheckHold("Duplicate JSON field")
        value[key]=item
    return value


def _canonical(data)->str:
    return json.dumps(data,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False,default=str)


def _read_one(path:Path, table:str, version:str, market:str, rows_required:int,
              head_required:str, expected_activations:dict[str,str])->dict:
    kind_counts:Counter[str]=Counter()
    signals={}
    exits={}
    partials={}
    count=0
    previous=None
    chain_digest=hashlib.sha256()
    activation=[]
    with closing(sqlite3.connect(path.as_uri()+"?mode=ro&immutable=1",
                                 uri=True,timeout=1)) as con:
        con.execute("PRAGMA query_only=ON")
        if con.execute("PRAGMA quick_check").fetchone()!=("ok",):
            raise FrozenRecheckHold("Copy integrity check failed")
        con.execute("BEGIN")
        cur=con.execute(
            "SELECT sequence,record_id,record_type,entity_id,"
            "recorded_at_utc,effective_at_utc,payload_json,"
            "previous_hash,record_hash FROM "+table+" ORDER BY sequence")
        allowed=S02_TYPES if table=="forward_records" else AI_TYPES
        for seq,record_id,kind,entity,recorded,effective,payload_text,prev,head in cur:
            count+=1
            if (seq!=count or prev!=previous or kind not in allowed or
                not isinstance(entity,str) or not entity or
                not isinstance(payload_text,str)):
                raise FrozenRecheckHold("Sequence, kind, entity or previous hash mismatch")
            decoded=json.loads(payload_text,object_pairs_hook=_unique,
                               parse_constant=lambda _:(_ for _ in ()).throw(
                                   FrozenRecheckHold("Nonfinite source value")))
            if _canonical(decoded)!=payload_text:
                raise FrozenRecheckHold("Noncanonical payload")
            material={
                "record_id":record_id,"record_type":kind,"entity_id":entity,
                "recorded_at_utc":recorded,"effective_at_utc":effective,
                "payload_json":payload_text,"previous_hash":prev,
            }
            computed=hashlib.sha256(_canonical(material).encode("utf-8")).hexdigest()
            if head!=computed:
                raise FrozenRecheckHold("Full canonical record hash mismatch")
            if kind=="SIGNAL":
                if entity in signals:
                    raise FrozenRecheckHold("Duplicate signal")
                signals[entity]=seq
            elif kind=="EXIT":
                if entity in exits:
                    raise FrozenRecheckHold("Duplicate exit")
                exits[entity]=seq
            elif kind=="PARTIAL_EXIT":
                if entity in partials:
                    raise FrozenRecheckHold("Duplicate partial")
                partials[entity]=seq
            elif kind=="ACTIVATION":
                activation.append((seq,head))
            chain_digest.update((str(seq)+":"+head+"\n").encode("ascii"))
            kind_counts[kind]+=1
            previous=head
        if count!=rows_required or previous!=head_required:
            raise FrozenRecheckHold("Copy count/terminal row hash mismatch")
        if version=="AI-v1.3" and (len(activation)!=1 or
            activation[0]!=(1,expected_activations[market])):
            raise FrozenRecheckHold("Crypto activation anchor mismatch")
    unmatched_exit=sum(e not in signals for e in exits)
    early_exit=sum(e in signals and exits[e]<=signals[e] for e in exits)
    unmatched_partial=sum(e not in signals for e in partials)
    early_partial=sum(e in signals and partials[e]<=signals[e] for e in partials)
    late_partial=sum(e in exits and partials[e]>=exits[e] for e in partials)
    hold=any((unmatched_exit,early_exit,unmatched_partial,early_partial,late_partial))
    return {
        "rows":count,
        "head":previous,
        "sequence_chain_sha256":chain_digest.hexdigest(),
        "event_counts":dict(sorted(kind_counts.items())),
        "signals":len(signals),
        "closed_signals":sum(e in exits for e in signals),
        "open_signals":sum(e not in exits for e in signals),
        "partial_signals":len(partials),
        "orphan_exit":unmatched_exit,
        "early_exit":early_exit,
        "orphan_partial":unmatched_partial,
        "early_partial":early_partial,
        "partial_after_exit":late_partial,
        "lifecycle_status":"HOLD_REVIEW" if hold else "SOURCE_ENTITY_ORDER_CONSISTENT",
    }


def recheck(private_dir:str|Path, *, pins=PINNED, manifest_sha=MANIFEST_SHA256,
            crypto_hashes=CRYPTO_ACTIVATION_HASHES)->dict:
    run=Path(private_dir)
    if run.is_symlink() or not run.is_dir() or not run.name.startswith("freeze-"):
        raise FrozenRecheckHold("Unrecognized private freeze run")
    run=run.resolve(strict=True)
    if not run.parent.name.startswith("OriginalLedgerEvidence-"):
        raise FrozenRecheckHold("Unrecognized private evidence parent")
    if len(pins)!=12 or set(crypto_hashes)!={"BTCUSDT","ETHUSDT","SOLUSDT"}:
        raise FrozenRecheckHold("Original source scope mismatch")
    manifest=run/"manifest.preliminary.json"
    if manifest.is_symlink() or not manifest.is_file() or _digest(manifest)!=manifest_sha:
        raise FrozenRecheckHold("Manifest does not match external owner record")
    payload=json.loads(manifest.read_text(encoding="utf-8"),object_pairs_hook=_unique)
    if (payload.get("schema_version")!=1 or payload.get("count")!=12 or
        payload.get("status")!="PRIVATE_FROZEN_COPIES_SELF_VERIFIED_EXTERNAL_REVIEW_REQUIRED" or
        payload.get("synchronized_all_markets_at_one_instant") is not False):
        raise FrozenRecheckHold("Unapproved manifest")
    ledgers=payload.get("ledgers")
    if not isinstance(ledgers,list) or len(ledgers)!=12:
        raise FrozenRecheckHold("Missing frozen entries")
    indexed={}
    for row in ledgers:
        if not isinstance(row,dict) or row.get("private_file") in indexed:
            raise FrozenRecheckHold("Duplicate or malformed manifest ledger")
        indexed[row["private_file"]]=row
    if set(indexed)!=set(pins):
        raise FrozenRecheckHold("Unexpected private file inventory")
    outcomes=[]
    for name, (version,market,table,num,sha,head) in pins.items():
        entry=indexed[name]
        if (entry.get("model_version")!=version or entry.get("market")!=market or
            entry.get("rows")!=num or entry.get("terminal_sequence")!=num or
            entry.get("frozen_file_sha256")!=sha or
            entry.get("terminal_record_hash")!=head or
            entry.get("source_path")!="data/"+name):
            raise FrozenRecheckHold("Recorded manifest source facts differ")
        file=run/name
        if file.is_symlink() or not file.is_file() or file.resolve(strict=True).parent!=run:
            raise FrozenRecheckHold("Unsafe private file")
        if _digest(file)!=sha:
            raise FrozenRecheckHold("Frozen bytes differ from owner-exported file pin")
        result=_read_one(file,table,version,market,num,head,crypto_hashes)
        if (result["sequence_chain_sha256"]!=entry.get("sequence_chain_sha256") or
            result["event_counts"]!=entry.get("event_counts") or
            entry.get("self_consistent_full_chain") is not True or
            entry.get("prior_observed_prefix_match") is not True):
            raise FrozenRecheckHold("Manifest disagrees with canonical recheck")
        if _digest(file)!=sha:
            raise FrozenRecheckHold("Frozen bytes changed during recheck")
        outcomes.append({
            "model_version":version,"market":market,
            "rows":num,"record_counts":result["event_counts"],
            "signals":result["signals"],
            "closed_signals":result["closed_signals"],
            "open_signals":result["open_signals"],
            "partial_signals":result["partial_signals"],
            "lifecycle_status":result["lifecycle_status"],
            "orphan_exit":result["orphan_exit"],
            "early_exit":result["early_exit"],
            "orphan_partial":result["orphan_partial"],
            "early_partial":result["early_partial"],
            "partial_after_exit":result["partial_after_exit"],
            "frozen_file_sha256_verified":True,
            "canonical_full_chain_verified":True,
        })
    # Confirm manifest bytes did not change while the private set was audited.
    if _digest(manifest)!=manifest_sha:
        raise FrozenRecheckHold("Manifest changed during audit")
    held=sum(x["lifecycle_status"]!="SOURCE_ENTITY_ORDER_CONSISTENT" for x in outcomes)
    return {
        "status":RECEIPT_STATUS,
        "manifest_pin_matches_owner_export":True,
        "file_sha256_against_owner_record":12,
        "full_canonical_hash_chains_checked":12,
        "source_entity_lifecycle_holds":held,
        "sum_source_event_rows":sum(x["rows"] for x in outcomes),
        "crypto_activation_hashes_pinned_against_repository":True,
        "crypto_k5_epoch_provenance_verified":False,
        "independent_third_party_source_custody_approved":False,
        "source_rights_verified":False,
        "after_cost_net_r_verified":False,
        "broker_execution_enabled":False,
        "raw_source_rows_exported":False,
        "ledgers":outcomes,
    }


def main(args:list[str])->int:
    try:
        if len(args)!=1:
            raise FrozenRecheckHold("Exact private freeze run path required")
        result=recheck(args[0])
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
        print("FROZEN_RECHECK=COMPLETE_OWNER_PIN_MATCH_NOT_INDEPENDENT_ATTESTATION")
        return 0
    except (FrozenRecheckHold,sqlite3.Error,ValueError,OSError,
            TypeError,KeyError,OverflowError):
        print("FROZEN_RECHECK=HOLD_SOURCE_EVIDENCE_UNVERIFIED")
        return 1


if __name__=="__main__":
    raise SystemExit(main(sys.argv[1:]))
