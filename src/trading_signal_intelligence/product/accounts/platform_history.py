"""Two-signer, all-nine-source, read-only owner platform-history acceptance.

One signed cohort is NOT a platform. Require individually signed and exact
full source populations for each market and a separately signed nine-market
universe with independently approved K5 coverage, source rights, cost, time.
This authenticates designated reviewer claims, not physical market truth.
No trading execution, source promotion, signing or account DB mutations.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from datetime import datetime,timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

from trading_signal_intelligence.product.accounts.source_inventory import SOURCES
from trading_signal_intelligence.product.accounts.verified_history import (
    HistoryAttestationError, verify_signed_history_attestation,
    reconcile_attested_history,
)

_SHA=re.compile(r"^[0-9a-f]{64}$")
_SIG=re.compile(r"^[A-Za-z0-9_-]{86}$")
_SOURCE_FIELDS=frozenset((
    "source_program_id","model_version","market","cohort",
    "source_snapshot_sha256","source_head_hash","source_evidence_sha256",
    "signed_cohort_attestation_sha256","expected_population_count",
    "expected_closed_count",
))
_UNIVERSE_FIELDS=frozenset((
    "schema_version","repository","research_scope",
    "original_twelve_source_manifest_sha256","market_sources",
    "reviewer_id","reviewed_at_utc","complete_market_cohort_windows",
    "external_crypto_k5_h1_h4_opportunity_coverage_approved",
    "source_rights_independently_approved",
    "full_after_cost_method_independently_approved",
    "s02_benchmark_kept_separate",
))


class PlatformHistoryHold(ValueError):
    """No source-promotion fallback on absent or contradictory signoffs."""


def _canon(obj: Any)->bytes:
    return json.dumps(obj,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode()


def _unique(pairs):
    out={}
    for key,val in pairs:
        if key in out:
            raise PlatformHistoryHold("Duplicate independent universe key")
        out[key]=val
    return out


def _pinned_key(pem: bytes, expected_sha: str)->Ed25519PublicKey:
    if (not isinstance(pem,bytes) or not isinstance(expected_sha,str) or
        not _SHA.fullmatch(expected_sha) or
        hashlib.sha256(pem).hexdigest()!=expected_sha):
        raise PlatformHistoryHold("Independent auditor key not pinned")
    try:
        key=load_pem_public_key(pem)
    except (ValueError,TypeError) as exc:
        raise PlatformHistoryHold("Invalid reviewer public key") from exc
    if not isinstance(key,Ed25519PublicKey):
        raise PlatformHistoryHold("Reviewer public key not Ed25519")
    return key


def verify_all_nine_market_history(
    *, signed_universe: bytes, universe_reviewer_pem: bytes,
    universe_reviewer_key_sha256: str, cohort_reviewer_pem: bytes,
    cohort_reviewer_key_sha256: str, owner_recorded_original_manifest_sha256: str,
    scoped_private_cohorts: dict[str,dict[str,Any]],
)->dict[str,Any]:
    """Verify signed nine-market scope and each independently reconciled cohort.

    scoped_private_cohorts map value contains signed_attestation BYTES,
    source_snapshot (strict database-read-only fact), and facts list, never
    public partial snapshots. The caller must independently authorize actual
    source rights and reviewer authority before trusting these proofs.
    """
    if (not isinstance(owner_recorded_original_manifest_sha256,str)
        or not _SHA.fullmatch(owner_recorded_original_manifest_sha256)):
        raise PlatformHistoryHold("Owner original-twelve source pin absent")
    if cohort_reviewer_key_sha256==universe_reviewer_key_sha256:
        raise PlatformHistoryHold("Independent universe and cohort reviewer keys must differ")
    universe_key=_pinned_key(universe_reviewer_pem,universe_reviewer_key_sha256)
    _pinned_key(cohort_reviewer_pem,cohort_reviewer_key_sha256)
    if not isinstance(signed_universe,bytes) or not 1<=len(signed_universe)<=64_000:
        raise PlatformHistoryHold("Signed full universe document unavailable")
    try:
        envelope=json.loads(
            signed_universe.decode("utf-8"),object_pairs_hook=_unique,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError()),
        )
        if (not isinstance(envelope,dict) or
            set(envelope)!={"universe","signature_ed25519_b64u"}):
            raise PlatformHistoryHold("Invalid platform universe envelope")
        body=envelope["universe"]
        signature=envelope["signature_ed25519_b64u"]
        if (not isinstance(body,dict) or set(body)!=_UNIVERSE_FIELDS
            or not isinstance(signature,str) or not _SIG.fullmatch(signature)):
            raise PlatformHistoryHold("Incomplete independent platform universe")
        raw=base64.urlsafe_b64decode(signature+"==")
        if len(raw)!=64:
            raise PlatformHistoryHold("Wrong universe signature length")
        universe_key.verify(raw,_canon(body))
    except PlatformHistoryHold:
        raise
    except (ValueError,TypeError,UnicodeDecodeError,binascii.Error,InvalidSignature) as exc:
        raise PlatformHistoryHold("Invalid trusted universe signature") from exc

    required={
        "schema_version":1,
        "repository":"alisufyan-ai7/trading-signal-intelligence",
        "research_scope":"ALL_NINE_AI_MARKET_COHORTS",
        "original_twelve_source_manifest_sha256":owner_recorded_original_manifest_sha256,
        "complete_market_cohort_windows":True,
        "external_crypto_k5_h1_h4_opportunity_coverage_approved":True,
        "source_rights_independently_approved":True,
        "full_after_cost_method_independently_approved":True,
        "s02_benchmark_kept_separate":True,
    }
    for key,value in required.items():
        if type(body.get(key)) is not type(value) or body.get(key)!=value:
            raise PlatformHistoryHold("Original sources/K5/rights/after-cost universe not approved")
    reviewer=body["reviewer_id"]
    if not isinstance(reviewer,str) or not 3<=len(reviewer)<=120:
        raise PlatformHistoryHold("Independent universe reviewer identity absent")
    try:
        when=datetime.fromisoformat(body["reviewed_at_utc"].replace("Z","+00:00"))
        if (when.tzinfo is None or when.utcoffset().total_seconds()!=0 or
            when>datetime.now(timezone.utc)):
            raise PlatformHistoryHold("Untrusted universe reviewer time")
    except (ValueError,TypeError,AttributeError) as exc:
        raise PlatformHistoryHold("Invalid platform-review UTC") from exc
    expected={(r.program,r.model_version,r.symbol) for r in SOURCES if r.program!="s02-forward"}
    rows=body["market_sources"]
    if not isinstance(rows,list) or len(rows)!=9:
        raise PlatformHistoryHold("Expected nine independent AI sources")
    if not isinstance(scoped_private_cohorts,dict):
        raise PlatformHistoryHold("Missing private cohort facts map")
    observed={}
    for r in rows:
        if not isinstance(r,dict) or set(r)!=_SOURCE_FIELDS:
            raise PlatformHistoryHold("Incomplete independent source row")
        identity=(r["source_program_id"],r["model_version"],r["market"])
        if identity in observed or identity not in expected:
            raise PlatformHistoryHold("Duplicate or forbidden market/program/model")
        for k in ("source_snapshot_sha256","source_evidence_sha256",
                  "signed_cohort_attestation_sha256"):
            if not isinstance(r[k],str) or not _SHA.fullmatch(r[k]):
                raise PlatformHistoryHold("Unsigned or unpinned original AI source")
        if (not isinstance(r["source_head_hash"],str) or
            not 1<=len(r["source_head_hash"])<=128 or
            not isinstance(r["cohort"],str) or
            not 1<=len(r["cohort"])<=128 or
            type(r["expected_population_count"]) is not int or
            type(r["expected_closed_count"]) is not int or
            r["expected_population_count"]<1 or
            not 0<=r["expected_closed_count"]<=r["expected_population_count"]):
            raise PlatformHistoryHold("Source population/review metadata invalid")
        observed[identity]=r
    if set(observed)!=expected or set(scoped_private_cohorts)!={i[2] for i in expected}:
        raise PlatformHistoryHold("Incomplete exact nine-market population")
    summaries=[]
    for program,version,market in sorted(expected):
        row=observed[(program,version,market)]
        private=scoped_private_cohorts[market]
        if (not isinstance(private,dict) or
            set(private)!={"signed_attestation","source_snapshot","facts"} or
            not isinstance(private["signed_attestation"],bytes)):
            raise PlatformHistoryHold("Missing private verified cohort input")
        if hashlib.sha256(private["signed_attestation"]).hexdigest()!=row["signed_cohort_attestation_sha256"]:
            raise PlatformHistoryHold("Individual signed source-review digest mismatch")
        try:
            cohort=verify_signed_history_attestation(
                private["signed_attestation"],
                reviewer_public_key_pem=cohort_reviewer_pem,
            )
            if cohort["reviewer_id"]==reviewer:
                raise PlatformHistoryHold("Independent universe and source reviewer same identity")
            matching={
                "source_program_id":program,"model_version":version,
                "cohort":row["cohort"],
                "source_snapshot_sha256":row["source_snapshot_sha256"],
                "source_head_hash":row["source_head_hash"],
                "source_evidence_sha256":row["source_evidence_sha256"],
                "expected_population_count":row["expected_population_count"],
                "expected_closed_count":row["expected_closed_count"],
            }
            if any(cohort.get(k)!=v for k,v in matching.items()):
                raise PlatformHistoryHold("Source cohort outside signed universe")
            reconciled=reconcile_attested_history(
                cohort,snapshot=private["source_snapshot"],facts=private["facts"],
            )
            if (reconciled.get("verified_full_cohort_history") is not True
                or reconciled.get("rights_approved") is not True):
                raise PlatformHistoryHold("Original source population not approved")
            metrics=reconciled["performance"]
            summaries.append({
                "market":market,"program":program,"model_version":version,
                "cohort":row["cohort"],
                "original_outcomes":metrics["total_outcomes"],
                "after_cost_closed_outcomes":metrics["completed_count"],
                "verified_cohort":True,
            })
        except (HistoryAttestationError,KeyError,TypeError,ValueError) as exc:
            raise PlatformHistoryHold("An original full-market cohort failed verification") from exc

    return {
        "status":"INDEPENDENTLY_SIGNED_NINE_AI_COHORT_UNIVERSE_RECONCILED",
        "verified_full_history":True,
        "verified_original_nine_ai_market_cohort_scope":True,
        "market_cohorts":summaries,
        "source_programs":3,
        "ai_market_count":9,
        "s02_benchmark_is_not_ai_history":True,
        "original_source_manifest_sha256":owner_recorded_original_manifest_sha256,
        "crypto_k5_externally_approved_by_signed_reviewer":True,
        "original_data_rights_signed_by_independent_reviewer":True,
        "reviewer_assertions_require_separate_real_custody":True,
        "broker_execution_pnl_available":False,
        "production_performance_publishing_automatically_authorized":False,
        "owner_release_approval_required":True,
        "raw_trade_entities_exported":False,
    }
