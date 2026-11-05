"""Owner-only nine-source signed research history read adapter.

Never signs source records, promotes database status, generates source rights,
writes SQL, exposes private evidence filenames/keys or enables subscriptions.
The independently appointed reviewers and protected private files must exist
in a controlled Railway candidate before any full-history result is possible.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any,Callable

from trading_signal_intelligence.product.accounts.source_inventory import SOURCES
from trading_signal_intelligence.product.accounts.verified_history import (
    HistoryAttestationError,verify_signed_history_attestation,
)
from trading_signal_intelligence.product.accounts.platform_history import (
    PlatformHistoryHold,verify_all_nine_market_history,
)

_ENV=(
    "VOWSIG_PLATFORM_SIGNED_UNIVERSE_PATH",
    "VOWSIG_PLATFORM_UNIVERSE_REVIEWER_PUBLIC_PEM_PATH",
    "VOWSIG_PLATFORM_UNIVERSE_REVIEWER_PUBLIC_SHA256",
    "VOWSIG_PLATFORM_COHORT_REVIEWER_PUBLIC_PEM_PATH",
    "VOWSIG_PLATFORM_COHORT_REVIEWER_PUBLIC_SHA256",
    "VOWSIG_PLATFORM_COHORT_SIGNED_DIR",
    "VOWSIG_PLATFORM_ORIGINAL_TWELVE_MANIFEST_SHA256",
)
_MAX_COHORT_BYTES=64_000


def _unavailable(status: str)->dict[str,Any]:
    return {
        "status":status,
        "verified_full_history":False,
        "verified_full_cohort_history":False,
        "platform_history_population_reconciled":False,
        "performance":None,
        "market_cohorts":[],
        "original_source_rights_verified":False,
        "crypto_external_k5_verified":False,
        "production_performance_publishing_automatically_authorized":False,
        "owner_exact_sha_approval_required":True,
    }


def _private_regular_file(path: str, *, max_bytes: int)->bytes:
    candidate=Path(path)
    if (not candidate.is_absolute() or candidate.is_symlink()
        or not candidate.is_file() or not 0<candidate.stat().st_size<=max_bytes):
        raise PlatformHistoryHold("Private review document unavailable")
    # The private evidence and public key must never be read via symlink.
    if candidate.resolve(strict=True)!=candidate:
        raise PlatformHistoryHold("Private review document link unavailable")
    return candidate.read_bytes()


def _sha_pin(data: bytes, expected: str)->None:
    import re
    if (not isinstance(expected,str)
        or not re.fullmatch(r"[0-9a-f]{64}",expected)
        or hashlib.sha256(data).hexdigest()!=expected):
        raise PlatformHistoryHold("Independent reviewer public key not pinned")


def load_owner_verified_platform_history(
    connect: Callable[[],Any], *,
    settings: dict[str,str]|None=None,
)->dict[str,Any]:
    """Read only. Fail closed for missing or invalid nine-source proof."""
    env=settings if settings is not None else os.environ
    configured=[bool(env.get(n,"")) for n in _ENV]
    if not any(configured):
        return _unavailable("awaiting_independent_full_platform_source_review")
    if not all(configured):
        return _unavailable("independent_platform_source_configuration_incomplete")
    try:
        universe_bytes=_private_regular_file(env[_ENV[0]],max_bytes=64_000)
        universe_key=_private_regular_file(env[_ENV[1]],max_bytes=4096)
        cohort_key=_private_regular_file(env[_ENV[3]],max_bytes=4096)
        _sha_pin(universe_key,env[_ENV[2]])
        _sha_pin(cohort_key,env[_ENV[4]])
        if env[_ENV[2]]==env[_ENV[4]]:
            raise PlatformHistoryHold("Independent reviewer roles share one trust key")
        directory=Path(env[_ENV[5]])
        if (not directory.is_absolute() or directory.is_symlink()
            or not directory.is_dir() or directory.resolve(strict=True)!=directory):
            raise PlatformHistoryHold("Unapproved signed-cohort directory")
        requested=[s for s in SOURCES if s.program!="s02-forward"]
        if len(requested)!=9:
            raise PlatformHistoryHold("Original AI population changed")
        cohort_claims={}
        signed_documents={}
        for spec in requested:
            # Market identifiers come exclusively from the fixed source registry.
            signed=_private_regular_file(str(directory/(spec.symbol+".signed.json")),
                                         max_bytes=_MAX_COHORT_BYTES)
            claim=verify_signed_history_attestation(
                signed,reviewer_public_key_pem=cohort_key,
            )
            if claim["source_program_id"]!=spec.program or claim["model_version"]!=spec.model_version:
                raise PlatformHistoryHold("Signed cohort model/program mismatch")
            cohort_claims[spec.symbol]=claim
            signed_documents[spec.symbol]=signed
        private={}
        with connect() as conn:
            conn.execute("SET TRANSACTION READ ONLY")
            for spec in requested:
                att=cohort_claims[spec.symbol]
                snapshots=conn.execute(
                    """SELECT source_program_id,model_version,source_snapshot_sha256,
                              source_head_hash,ingest_status,completeness_verified,id
                       FROM vowsig_research_source_snapshots
                       WHERE source_program_id=%s AND model_version=%s
                         AND source_snapshot_sha256=%s LIMIT 2""",
                    (att["source_program_id"],att["model_version"],
                     att["source_snapshot_sha256"]),
                ).fetchall()
                if len(snapshots)!=1:
                    raise PlatformHistoryHold("Missing unique private source projection")
                fact_rows=conn.execute(
                    """SELECT entity_id,source_record_sha256,state,exit_at_utc,
                              combined_net_r,cost_model_version,after_costs_verified,
                              cohort FROM vowsig_research_outcome_facts
                       WHERE source_snapshot_id=%s ORDER BY entity_id
                       LIMIT 250001""",
                    (snapshots[0]["id"],),
                ).fetchall()
                private[spec.symbol]={
                    "signed_attestation":signed_documents[spec.symbol],
                    "source_snapshot":dict(snapshots[0]),
                    "facts":[dict(row) for row in fact_rows],
                }
        full=verify_all_nine_market_history(
            signed_universe=universe_bytes,
            universe_reviewer_pem=universe_key,
            universe_reviewer_key_sha256=env[_ENV[2]],
            cohort_reviewer_pem=cohort_key,
            cohort_reviewer_key_sha256=env[_ENV[4]],
            owner_recorded_original_manifest_sha256=env[_ENV[6]],
            scoped_private_cohorts=private,
        )
        if (full.get("verified_full_history") is not True
            or full.get("ai_market_count")!=9
            or full.get("s02_benchmark_is_not_ai_history") is not True):
            raise PlatformHistoryHold("Untrusted platform-wide history claim")
        return {
            **full,
            "verified_full_cohort_history":True,
            "platform_history_population_reconciled":True,
            "performance":None,
            "original_source_rights_verified":True,
            "crypto_external_k5_verified":True,
            "owner_exact_sha_approval_required":True,
        }
    except (PlatformHistoryHold,HistoryAttestationError,KeyError,TypeError,
            ValueError,OSError,OverflowError):
        return _unavailable("independent_platform_source_evidence_rejected")
