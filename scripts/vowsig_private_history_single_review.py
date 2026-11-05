"""Consolidated read-only reviewer triage of the EXACT private November 5 set.

Reuses independently checked manifest SHA256 and all twelve source chains.
Audits nine AI outcome R arithmetic and three crypto cycle ledgers in one
bounded local operation. NEVER signs, promotes, transfers or publishes
source records, customer data, model performance or trading signals.
"""
from __future__ import annotations

from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from trading_signal_intelligence.product.accounts.source_inventory import SOURCES
from trading_signal_intelligence.product.accounts.private_source_freeze import (
    PrivateSourceFreezeError, verify_private_frozen_set, CRYPTO_ANCHOR_PATH,
)
from trading_signal_intelligence.product.accounts.private_after_cost_audit import (
    FrozenCostAuditHold, audit_frozen_after_costs,
)
from trading_signal_intelligence.product.accounts.private_crypto_epoch_audit import (
    FrozenCryptoEpochAuditError, audit_frozen_crypto_epoch,
)

NOV5_OWNER_MANIFEST_SHA256="bec335b870214b5e770af652869767f54bc960000dd6031278ea0ebf460cbc45"
_EXPECTED_EVENT_RECORDS=10595
_EXPECTED_AI_MARKETS=9


class PrivateHistoryReviewHold(ValueError):
    """A private source or protocol is unavailable; no raw details in receipt."""


def _unique(pairs):
    result={}
    for key,val in pairs:
        if key in result:
            raise PrivateHistoryReviewHold("Duplicate private evidence key")
        result[key]=val
    return result


def inspect_original_frozen_history(
    repo_root: str | Path, private_run_dir: str | Path, *,
    independently_recorded_manifest_sha256: str=NOV5_OWNER_MANIFEST_SHA256,
)->dict[str,Any]:
    if independently_recorded_manifest_sha256!=NOV5_OWNER_MANIFEST_SHA256:
        raise PrivateHistoryReviewHold("Not the approved frozen evidence-set digest")
    root=Path(repo_root)
    run=Path(private_run_dir)
    if (root.is_symlink() or run.is_symlink() or not run.is_dir()
        or not run.name.startswith("freeze-")
        or not run.parent.name.startswith("OriginalLedgerEvidence-")):
        raise PrivateHistoryReviewHold("Unrecognized private evidence path")
    root=root.resolve(strict=True)
    run=run.resolve(strict=True)
    if root.name!="trading-signal-intelligence" or root in run.parents:
        raise PrivateHistoryReviewHold("Unapproved original/private source boundary")
    try:
        base=verify_private_frozen_set(
            root,run,
            externally_recorded_manifest_sha256=independently_recorded_manifest_sha256,
        )
        manifest=json.loads(
            (run/"manifest.preliminary.json").read_text(encoding="utf-8"),
            object_pairs_hook=_unique,
        )
        if (base["copy_count"]!=12 or base["total_event_rows"]!=_EXPECTED_EVENT_RECORDS
            or manifest.get("count")!=12 or len(manifest.get("ledgers",[]))!=12):
            raise PrivateHistoryReviewHold("Frozen event population differs from owner pin")
        anchor=json.loads(
            (root/CRYPTO_ANCHOR_PATH).read_text(encoding="utf-8"),
            object_pairs_hook=_unique,
        )
        activated_at=anchor["activated_at_utc"]
        if not isinstance(activated_at,str):
            raise PrivateHistoryReviewHold("Crypto activation anchor time absent")
        by_file={}
        for entry in manifest["ledgers"]:
            name=entry.get("private_file")
            if not isinstance(name,str) or name in by_file:
                raise PrivateHistoryReviewHold("Private manifest filenames duplicated")
            by_file[name]=entry
        expected={Path(s.relative_path).name for s in SOURCES}
        if set(by_file)!=expected:
            raise PrivateHistoryReviewHold("Wrong twelve-source universe")
    except (PrivateSourceFreezeError,KeyError,OSError,TypeError,ValueError) as exc:
        raise PrivateHistoryReviewHold("Original frozen source manifest not admitted") from exc

    groups=[]
    cost_held=0
    missing_hour_review=0
    crypto_held=0
    ai_files=0
    checked_closed=0
    s02_files=0
    for spec in SOURCES:
        name=Path(spec.relative_path).name
        entry=by_file[name]
        private=run/name
        if spec.program=="s02-forward":
            s02_files+=1
            # This is a distinct rules benchmark, NEVER AI net-R population.
            groups.append({
                "program":spec.program,"market":spec.symbol,
                "source_event_rows":entry["rows"],"research_after_cost_applicable":False,
                "status":"SEPARATE_SOURCE_BENCHMARK_NOT_AI_PERFORMANCE",
            })
            continue
        ai_files+=1
        report={
            "program":spec.program,"model_version":spec.model_version,
            "market":spec.symbol,"source_event_rows":entry["rows"],
            "after_cost_arithmetic":"HOLD_REVIEW_REQUIRED",
            "crypto_epoch":"NOT_APPLICABLE",
            "full_original_cohort_verified":False,
        }
        try:
            arithmetic=audit_frozen_after_costs(
                private,model_version=spec.model_version,market=spec.symbol,
                expected_frozen_file_sha256=entry["frozen_file_sha256"],
                expected_terminal_record_hash=entry["terminal_record_hash"],
            )
            if (arithmetic["original_event_records"]!=entry["rows"] or
                arithmetic["signal_count"]<1 or
                arithmetic["closed_after_cost_arithmetic_checked"]<1):
                raise FrozenCostAuditHold("Incomplete original cohort")
            report["after_cost_arithmetic"]="SOURCE_NET_R_ARITHMETIC_SELF_CHECK_PASS"
            report["signals"]=arithmetic["signal_count"]
            report["closed_signals"]=arithmetic["closed_signal_count"]
            report["partial_exit_events"]=arithmetic["partial_exit_event_count"]
            checked_closed+=arithmetic["closed_after_cost_arithmetic_checked"]
        except (FrozenCostAuditHold,OSError,ValueError,KeyError,TypeError):
            cost_held+=1
        if spec.program=="crypto-expansion-1":
            try:
                epoch=audit_frozen_crypto_epoch(
                    private,symbol=spec.symbol,activated_at_utc=activated_at,
                )
                report["crypto_epoch"]=epoch["status"]
                report["ledger_internal_missing_hour_count"]=epoch["unobserved_internal_h1_closes"]
                report["ledger_internal_cycle_review_holds"]=epoch[
                    "unmatched_or_duplicate_cycle_entities"
                ]
                missing_hour_review+=epoch["unobserved_internal_h1_closes"]
                if (epoch["status"]!="FROZEN_CRYPTO_INTERNAL_EPOCH_CONSISTENT_NOT_K5_CERTIFIED"
                    or epoch["unmatched_or_duplicate_cycle_entities"]):
                    crypto_held+=1
            except (FrozenCryptoEpochAuditError,OSError,ValueError,KeyError,TypeError):
                crypto_held+=1
                report["crypto_epoch"]="HOLD_READ_ONLY_EPOCH_REVIEW"
        groups.append(report)
    if ai_files!=_EXPECTED_AI_MARKETS or s02_files!=3:
        raise PrivateHistoryReviewHold("AI/S02 source scope changed")
    no_holds=cost_held==0 and crypto_held==0 and missing_hour_review==0
    return {
        "status":("PRIVATE_FROZEN_AI_ARITHMETIC_AND_INTERNAL_EPOCH_PASS_NOT_ATTESTED"
                  if no_holds else "PRIVATE_FROZEN_HISTORY_REVIEW_HOLDS_NOT_ATTESTED"),
        "source_manifest_sha256":independently_recorded_manifest_sha256,
        "source_files_sha256_and_chains_rechecked":12,
        "total_original_event_rows":_EXPECTED_EVENT_RECORDS,
        "ai_market_sources_checked":ai_files,
        "s02_benchmark_sources_excluded_from_ai_performance":s02_files,
        "ai_cost_arithmetic_market_holds":cost_held,
        "crypto_internal_epoch_market_holds":crypto_held,
        "crypto_missing_internal_hour_count":missing_hour_review,
        "ai_closed_outcomes_arithmetic_checked":checked_closed,
        "external_crypto_market_data_opportunity_verified":False,
        "source_rights_and_human_independent_review_verified":False,
        "all_market_time_windows_independently_attested":False,
        "live_provider_costs_verified":False,
        "historical_performance_certified":False,
        "platform_history_publication_authorized":False,
        "original_sqlite_copies_transferred":False,
        "raw_trade_payloads_or_entity_ids_exported":False,
        "program_market_diagnostics":groups,
    }


def main()->int:
    import argparse
    p=argparse.ArgumentParser(description="VowSig one-step private frozen-history triage")
    p.add_argument("--repo-root",required=True)
    p.add_argument("--private-run-dir",required=True)
    p.add_argument("--expected-manifest-sha256",default=NOV5_OWNER_MANIFEST_SHA256)
    p.add_argument("--confirm",required=True)
    args=p.parse_args()
    if args.confirm!="READ_ONLY_PRIVATE_HISTORY_NO_PROMOTION":
        print("VOWSIG_PRIVATE_HISTORY=DENIED")
        return 1
    try:
        result=inspect_original_frozen_history(
            args.repo_root,args.private_run_dir,
            independently_recorded_manifest_sha256=args.expected_manifest_sha256,
        )
    except (PrivateHistoryReviewHold,OSError):
        print("VOWSIG_PRIVATE_HISTORY=INTEGRITY_HOLD")
        print("HISTORICAL_PERFORMANCE_CERTIFIED=NO")
        return 1
    print(json.dumps(result,sort_keys=True,separators=(",",":")))
    print("VOWSIG_PRIVATE_HISTORY=TRIAGE_COMPLETED_NOT_INDEPENDENT_ATTESTATION")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
