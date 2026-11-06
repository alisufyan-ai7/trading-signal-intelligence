"""Inline, no-download, one-time WINDOWS VPS original source snapshot operator.

Run only in approved locked-down PRIVATE destination. Backup writes copies,
not the twelve live sources. No network, broker, Git, scheduler or cloud use.
CI imports this file with synthetic roots; VPS executes its source via stdin.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import stat
import sys
import time
from contextlib import closing
from datetime import datetime,timezone

FILES=(
    ("AI-v1.1","XAUUSD","ai_v1_1_xauusd.sqlite","ai_records",1324,"cd43509bfc8698b3b4675f8d3c3b8eb42f87d8aedcb60ede34ad673064434475"),
    ("AI-v1.1","USTEC","ai_v1_1_ustec.sqlite","ai_records",1331,"0e472d9d8aa75259632fcec1eb8df94e53aafe8e905fca473edb7584eed960b3"),
    ("AI-v1.1","US30","ai_v1_1_us30.sqlite","ai_records",1328,"847ff0c30acc3d5e21adea30326618c60ce2509b6a2f2773c65c145b8b563ca6"),
    ("AI-v1.2.1","EURUSD","ai_v1_2_1_eurusd.sqlite","ai_records",1092,"858c67d626fcf7c4b6edc2deff96a2472a121d5cef32be13a8db06adbfc18f99"),
    ("AI-v1.2.1","XAGUSD","ai_v1_2_1_xagusd.sqlite","ai_records",1051,"1be82bacf5c9c533a8a997dae33a9ea74c7667c408aa4fb723820ae196b4e7b2"),
    ("AI-v1.2.1","USOIL","ai_v1_2_1_usoil.sqlite","ai_records",1055,"1ac30968d4f902b3cad1e26393e94588bf32cb7d91552939a08a078f5c019e3f"),
    ("AI-v1.3","BTCUSDT","ai_v1_3_btcusdt.sqlite","ai_records",1091,"039c8bfd0bd19934d3029ee54467096b4538389d13904bd439b885a1a26e3fa9"),
    ("AI-v1.3","ETHUSDT","ai_v1_3_ethusdt.sqlite","ai_records",1099,"0a7d8610f33b2105f1d6f2c4900e6e527fe927ba1230e3bbe4e2490f21c7d896"),
    ("AI-v1.3","SOLUSDT","ai_v1_3_solusdt.sqlite","ai_records",1095,"41fea4a6113d72cbad78b91f409b96466fc1c7653fddcf0c1ad0b7c8e94d696e"),
    ("S02-v0.1","XAUUSD","forward.sqlite","forward_records",35,"178f0ca8b3cb674600e997c161e297a3dd4e90262583529eb58e6deaf94ab1a2"),
    ("S02-v0.1","USTEC","forward_ustec.sqlite","forward_records",45,"cc7e459fc01edf298366255b9951c5be9b43dc9a3df9cde6e7fd5567f6efdf25"),
    ("S02-v0.1","US30","forward_us30.sqlite","forward_records",40,"c8b92832e16795f0e0ccd6a6bddf667b71216ed05b4f4c904472977527adea7e"),
)
AI_TYPES=frozenset(("ACTIVATION","INFERENCE","NO_TRADE","REJECTED_INFERENCE",
                    "SIGNAL","EXIT","PARTIAL_EXIT","MISSED_INFERENCE","ERROR"))
S02_TYPES=frozenset(("ACTIVATION","SIGNAL","EXIT","MISSED_SIGNAL","SKIPPED_SIGNAL"))
ANCHOR="research/forward/AI-v1.3-crypto-expansion-activation-2026-10-09T195556Z.json"


def sha256(path):
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()


def unique_json(pairs):
    result={}
    for k,v in pairs:
        if k in result:
            raise ValueError("Duplicate JSON property")
        result[k]=v
    return result


def capture(root,private,rows=FILES):
    root=Path(root).resolve(strict=True)
    private=Path(private).resolve(strict=True)
    if (root.name!="trading-signal-intelligence" or root==private or
        root in private.parents or private in root.parents or
        not private.is_dir() or len(rows)!=12):
        raise ValueError("Unapproved source/destination")
    if (os.name!="nt" and stat.S_IMODE(private.stat().st_mode)&0o077):
        raise ValueError("Private root permissions insufficient")
    paths=[]
    for version,market,name,table,prefix_n,prefix_h in rows:
        original=root/"data"/name
        if (original.is_symlink() or not original.is_file()
            or root not in original.resolve(strict=True).parents):
            raise ValueError("Original ledger path unavailable")
        paths.append(original)
    anchor_path=root/ANCHOR
    if (anchor_path.is_symlink() or not anchor_path.is_file() or
        root not in anchor_path.resolve(strict=True).parents):
        raise ValueError("Crypto anchor unavailable")
    anchor=json.loads(anchor_path.read_text(encoding="utf-8"),
                      object_pairs_hook=unique_json)
    if (anchor.get("public_signal_exposure_enabled") is not False or
        anchor.get("broker_execution_enabled") is not False or
        set(anchor.get("markets",{}))!={"BTCUSDT","ETHUSDT","SOLUSDT"}):
        raise ValueError("Unsafe crypto activation contract")
    sys.path.insert(0,str(root/"src"))
    from trading_signal_intelligence.ai_v1.ledger import _record_hash, canonical_json
    run_id="freeze-"+datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+os.urandom(6).hex()
    run=private/run_id
    run.mkdir(mode=0o700)
    ledger_info=[]
    for source,spec in zip(paths,rows):
        version,market,name,table,prefix_n,prefix_h=spec
        copy=run/name
        began=datetime.now(timezone.utc).isoformat()
        started=time.monotonic()
        def watchdog(status,remaining,total):
            if time.monotonic()-started>180:
                raise TimeoutError("SQLite online backup timeout")
        with closing(sqlite3.connect(source.as_uri()+"?mode=ro",uri=True,timeout=1)) as live:
            live.execute("PRAGMA query_only=ON")
            with closing(sqlite3.connect(str(copy),timeout=1)) as target:
                live.backup(target,pages=128,sleep=0.1,progress=watchdog)
        with closing(sqlite3.connect(copy.as_uri()+"?mode=ro",uri=True,timeout=1)) as db:
            db.execute("PRAGMA query_only=ON")
            if db.execute("PRAGMA quick_check").fetchone()!=("ok",):
                raise ValueError("Frozen SQLite integrity check failed")
            db.execute("BEGIN")
            prior=db.execute(
                f"SELECT record_hash FROM {table} WHERE sequence=?",(prefix_n,)
            ).fetchone()
            if prior!=(prefix_h,):
                raise ValueError("Prior independently observed prefix mismatch")
            rows_db=db.execute(
                f"SELECT sequence,record_id,record_type,entity_id,"
                f"recorded_at_utc,effective_at_utc,payload_json,"
                f"previous_hash,record_hash FROM {table} ORDER BY sequence"
            )
            previous=None
            digest=hashlib.sha256()
            counts={}
            count=0
            activation=None
            permitted=S02_TYPES if table=="forward_records" else AI_TYPES
            for row in rows_db:
                sequence,record_id,kind,entity,recorded,effective,payload_text,prev,h=row
                count+=1
                if sequence!=count or prev!=previous or kind not in permitted:
                    raise ValueError("Frozen source sequence, event or chain mismatch")
                payload=json.loads(payload_text,object_pairs_hook=unique_json,
                                   parse_constant=lambda x:(_ for _ in ()).throw(ValueError("Nonfinite")))
                canonical=canonical_json(payload)
                if canonical!=payload_text:
                    raise ValueError("Noncanonical ledger event")
                expected=_record_hash(
                    record_id=record_id,record_type=kind,entity_id=entity,
                    recorded_at_utc=recorded,effective_at_utc=effective,
                    payload_json=payload_text,previous_hash=prev)
                if not isinstance(h,str) or not re.fullmatch("[0-9a-f]{64}",h) or expected!=h:
                    raise ValueError("Original source hash-chain mismatch")
                if version=="AI-v1.3" and kind=="ACTIVATION":
                    if activation is not None:
                        raise ValueError("Multiple crypto activations")
                    activation=(h,payload)
                digest.update(f"{count}:{h}\n".encode("ascii"))
                counts[kind]=counts.get(kind,0)+1
                previous=h
            if count<prefix_n or previous is None:
                raise ValueError("Source truncated or empty")
            if version=="AI-v1.3":
                expected_anchor=anchor["markets"][market]
                if (activation is None or activation[0]!=expected_anchor["record_hash"]
                    or activation[1]!=expected_anchor["payload"]):
                    raise ValueError("Crypto activation source mismatch")
        copy_hash=sha256(copy)
        if sha256(copy)!=copy_hash:
            raise ValueError("Frozen source changed while inspected")
        os.chmod(copy,stat.S_IREAD)
        ledger_info.append({
            "model_version":version,"market":market,"private_file":name,
            "source_path":"data/"+name,"captured_start_utc":began,
            "captured_end_utc":datetime.now(timezone.utc).isoformat(),
            "rows":count,"terminal_sequence":count,
            "terminal_record_hash":previous,
            "frozen_file_sha256":copy_hash,
            "prior_observed_prefix_match":True,
            "self_consistent_full_chain":True,
            "event_counts":counts,
            "sequence_chain_sha256":digest.hexdigest(),
            "crypto_activation_match_not_k5":version=="AI-v1.3",
        })
    manifest={
        "schema_version":1,
        "status":"PRIVATE_FROZEN_COPIES_SELF_VERIFIED_EXTERNAL_REVIEW_REQUIRED",
        "snapshot_mode":"SEQUENTIAL_SQLITE_BACKUP_API",
        "synchronized_all_markets_at_one_instant":False,
        "count":12,"ledgers":ledger_info,
        "contains_raw_payloads_in_private_copies":True,
        "contains_raw_payloads_in_manifest":False,
        "external_file_hashes_independently_approved":False,
        "crypto_k5_epoch_provenance_verified":False,
        "source_rights_after_costs_and_full_history_verified":False,
    }
    manifest_file=run/"manifest.preliminary.json"
    manifest_file.write_text(json.dumps(manifest,sort_keys=True,separators=(",",":")),encoding="utf-8")
    os.chmod(manifest_file,stat.S_IREAD)
    return {"status":manifest["status"],"run_dir":str(run),
            "manifest_sha256":sha256(manifest_file),"ledgers":ledger_info,
            "independent_historical_profit_verified":False}


if __name__=="__main__":
    try:
        if len(sys.argv)!=3:
            raise ValueError("Exact source and destination arguments required")
        result=capture(sys.argv[1],sys.argv[2])
        print(json.dumps(result,sort_keys=True,separators=(",",":")))
        print("PRIVATE_SOURCE_FREEZE=COMPLETED_NOT_INDEPENDENTLY_CERTIFIED")
    except Exception as exc:
        print("PRIVATE_SOURCE_FREEZE=INCOMPLETE_PRIVATE_COPIES_NOT_APPROVED")
        print("REASON_TYPE="+type(exc).__name__)
        sys.exit(1)
