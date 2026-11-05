"""Single-release, externally signed evidence checklist. NEVER a deploy command.

A valid signature authenticates a trusted human reviewer of receipts; it does
NOT make screenshots, mock tests, or self-declarations intrinsically true.
No provider credentials, database changes, secret loading or network calls.
"""
from __future__ import annotations

import base64
import binascii
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from cryptography.hazmat.primitives.serialization import load_pem_public_key

REPOSITORY="alisufyan-ai7/trading-signal-intelligence"
RELEASE_SCOPE="ONE_FULLY_ENABLED_RESEARCH_BETA_RELEASE"
_BACKUP_FIRST="RAILWAY_PG_ENCRYPTED_S3_B2_BACKUP_AND_COLD_RESTORE"
_HASH=re.compile(r"^[0-9a-f]{40}$")
_SHA256=re.compile(r"^[0-9a-f]{64}$")
_B64=re.compile(r"^[A-Za-z0-9_-]{86}$")
REQUIRED_GATES={
    "exact_head_ci":"github_actions",
    "auth0_public_oidc_jwks":"read_only_live_provider",
    "auth0_verified_email_signup":"real_staging_auth_flow",
    "auth0_unverified_duplicate_replay_denial":"real_staging_auth_flow",
    "auth0_return_login_logout":"real_staging_auth_flow",
    "resend_actual_delivery":"real_staging_email",
    "railway_authenticated_app_role_verify_full":"real_private_railway_sql",
    "railway_migration_role_isolation":"real_private_railway_sql",
    "owner_signed_offline_mfa_enrollment":"owner_human_two_person",
    "owner_mfa_stepup_rotation_recovery":"owner_human_two_person",
    "nine_ai_ledgers_cost_complete_independent_review":"independent_private_source_review",
    "crypto_k5_external_opportunity_coverage":"independent_private_source_review",
    "full_research_cohort_universe_signed":"independent_private_source_review",
    "owner_admin_performance_and_market_reliability":"real_staging_product",
    "customer_signal_center_entitlements_and_privacy":"real_staging_product",
    "public_publisher_latest_reliability":"real_hosted_observation",
    "staging_security_browser_permissions":"real_staging_security",
    "staging_rollback_rehearsal":"real_staging_rollback",
}
_KEYS=frozenset((
    "schema_version","repository","pull_request_number","candidate_commit_sha",
    "main_before_release_sha","release_scope","mode","research_only",
    "broker_execution_disabled","six_noncore_public_signal_details_disabled",
    "historical_performance_requires_independent_source_attestation",
    "new_railway_postgres_backup_unverified",
    "owner_accepted_recovery_risk","first_postlaunch_action",
    "reviewed_at_utc","gates","release_reviewer_id",
))
_EVIDENCE_KEYS=frozenset((
    "status","type","receipt_sha256","observed_at_utc","human_reviewer_id",
    "private_receipt_custody_confirmed","exact_candidate_commit_sha",
))
_MAX_BYTES=128_000


class ReleaseEvidenceHold(ValueError):
    """One or more release boundaries lack authentic, exact scope evidence."""


def _canonical(value: Any)->bytes:
    return json.dumps(value,sort_keys=True,separators=(",",":"),
                      ensure_ascii=False,allow_nan=False).encode("utf-8")


def _unique(pairs: list[tuple[str,Any]])->dict[str,Any]:
    result={}
    for k,v in pairs:
        if k in result:
            raise ReleaseEvidenceHold("Duplicate release evidence field")
        result[k]=v
    return result


def _read_utc(value: Any, *, now: datetime)->datetime:
    if not isinstance(value,str) or len(value)>48:
        raise ReleaseEvidenceHold("Invalid evidence UTC timestamp")
    try:
        stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ReleaseEvidenceHold("Unparseable evidence timestamp") from exc
    if stamp.tzinfo is None or stamp.utcoffset()!=timedelta(0):
        raise ReleaseEvidenceHold("Evidence timestamp must use UTC")
    stamp=stamp.astimezone(timezone.utc)
    if stamp>now+timedelta(minutes=2) or stamp<now-timedelta(days=30):
        raise ReleaseEvidenceHold("Release evidence outside allowed review window")
    return stamp


def verify_signed_release_receipts(
    document: bytes, *,
    owner_trusted_public_key_pem: bytes,
    owner_trusted_public_key_sha256: str,
    expected_commit_sha: str,
    expected_main_sha: str,
    now: datetime|None=None,
)->dict[str,Any]:
    """Verify exact reviewed pre-launch receipts, with NO automatic deployment.

    The signed release reviewer must examine separately held original receipts.
    Caller obtains the public signing key and pin via independent custody; do
    not trust a key supplied within the document being checked.
    """
    moment=now or datetime.now(timezone.utc)
    if moment.tzinfo is None:
        raise ReleaseEvidenceHold("Trusted UTC review clock required")
    moment=moment.astimezone(timezone.utc)
    if (not isinstance(expected_commit_sha,str) or not _HASH.fullmatch(expected_commit_sha)
        or not isinstance(expected_main_sha,str) or not _HASH.fullmatch(expected_main_sha)
        or expected_commit_sha==expected_main_sha):
        raise ReleaseEvidenceHold("Exact candidate/base commit pin invalid")
    if (not isinstance(owner_trusted_public_key_sha256,str) or
        not _SHA256.fullmatch(owner_trusted_public_key_sha256) or
        hashlib.sha256(owner_trusted_public_key_pem).hexdigest()!=owner_trusted_public_key_sha256):
        raise ReleaseEvidenceHold("Unapproved release reviewer trust key")
    if not isinstance(document,bytes) or not 1<=len(document)<=_MAX_BYTES:
        raise ReleaseEvidenceHold("Missing/oversized signed release evidence")
    try:
        envelope=json.loads(
            document.decode("utf-8"),object_pairs_hook=_unique,
            parse_constant=lambda _:(_ for _ in ()).throw(ValueError()),
        )
        if not isinstance(envelope,dict) or set(envelope)!={"payload","signature_ed25519_b64u"}:
            raise ReleaseEvidenceHold("Unexpected release signature envelope")
        body=envelope["payload"]
        signature=envelope["signature_ed25519_b64u"]
        if not isinstance(body,dict) or set(body)!=_KEYS:
            raise ReleaseEvidenceHold("Incomplete/extended release review")
        if not isinstance(signature,str) or not _B64.fullmatch(signature):
            raise ReleaseEvidenceHold("Invalid release signature encoding")
        key=load_pem_public_key(owner_trusted_public_key_pem)
        if not isinstance(key,Ed25519PublicKey):
            raise ReleaseEvidenceHold("Release reviewer key must be Ed25519")
        data=base64.urlsafe_b64decode(signature+"==")
        if len(data)!=64:
            raise ReleaseEvidenceHold("Invalid release signature length")
        key.verify(data,_canonical(body))
    except ReleaseEvidenceHold:
        raise
    except (ValueError,UnicodeDecodeError,TypeError,InvalidSignature,binascii.Error) as exc:
        raise ReleaseEvidenceHold("Independent release reviewer signature invalid") from exc

    exact={
        "schema_version":1,"repository":REPOSITORY,"pull_request_number":93,
        "candidate_commit_sha":expected_commit_sha,
        "main_before_release_sha":expected_main_sha,
        "release_scope":RELEASE_SCOPE,"mode":"SHADOW_ONLY","research_only":True,
        "broker_execution_disabled":True,
        "six_noncore_public_signal_details_disabled":True,
        "historical_performance_requires_independent_source_attestation":True,
        "new_railway_postgres_backup_unverified":True,
        "owner_accepted_recovery_risk":True,
        "first_postlaunch_action":_BACKUP_FIRST,
    }
    for k,expected in exact.items():
        if type(body.get(k)) is not type(expected) or body.get(k)!=expected:
            raise ReleaseEvidenceHold("Release scope/policy or exact SHA mismatch")
    reviewer=body["release_reviewer_id"]
    if not isinstance(reviewer,str) or not 3<=len(reviewer)<=120:
        raise ReleaseEvidenceHold("Independent release reviewer identity missing")
    reviewed=_read_utc(body["reviewed_at_utc"],now=moment)
    gates=body["gates"]
    if not isinstance(gates,dict) or set(gates)!=set(REQUIRED_GATES):
        raise ReleaseEvidenceHold("Missing or extra mandatory release gate")
    reviewers=set()
    for label,kind in REQUIRED_GATES.items():
        row=gates[label]
        if not isinstance(row,dict) or set(row)!=_EVIDENCE_KEYS:
            raise ReleaseEvidenceHold("Incomplete gate receipt")
        if (row["status"]!="PASS" or row["type"]!=kind or
            row["private_receipt_custody_confirmed"] is not True or
            row["exact_candidate_commit_sha"]!=expected_commit_sha or
            not isinstance(row["receipt_sha256"],str) or
            not _SHA256.fullmatch(row["receipt_sha256"])):
            raise ReleaseEvidenceHold("Gate lacks exact-commit verified evidence")
        human=row["human_reviewer_id"]
        if not isinstance(human,str) or not 3<=len(human)<=120:
            raise ReleaseEvidenceHold("Gate has no human reviewer")
        observed=_read_utc(row["observed_at_utc"],now=moment)
        if observed>reviewed:
            raise ReleaseEvidenceHold("Release review predates gate evidence")
        if kind.startswith("independent_"):
            reviewers.add(human)
    if reviewer in reviewers:
        raise ReleaseEvidenceHold("Release reviewer cannot self-attest original source rights")
    return {
        "status":"SIGNED_RELEASE_EVIDENCE_GATE_COMPLETE_OWNER_APPROVAL_REQUIRED",
        "validated_candidate_commit_sha":expected_commit_sha,
        "validated_main_before_release_sha":expected_main_sha,
        "mandatory_gates_checked":len(REQUIRED_GATES),
        "real_provider_evidence_claims_cryptographically_bound":True,
        "independent_source_review_claims_cryptographically_bound":True,
        "actual_external_test_truth_not_independently_proven_by_signature":True,
        "new_railway_postgres_recovery_verified":False,
        "first_postlaunch_action":_BACKUP_FIRST,
        "broker_execution_enabled":False,
        "noncore_public_signal_details_enabled":False,
        "production_release_automatically_authorized":False,
        "owner_exact_sha_merge_deploy_approval_still_required":True,
        "raw_receipts_or_credentials_exported":False,
    }


def main()->int:
    import argparse
    p=argparse.ArgumentParser(description="No-write VowSig one-release evidence gate")
    p.add_argument("--signed-receipts",required=True)
    p.add_argument("--trusted-public-key",required=True)
    p.add_argument("--trusted-public-key-sha256",required=True)
    p.add_argument("--expected-candidate-sha",required=True)
    p.add_argument("--expected-main-sha",required=True)
    args=p.parse_args()
    try:
        result=verify_signed_release_receipts(
            Path(args.signed_receipts).read_bytes(),
            owner_trusted_public_key_pem=Path(args.trusted_public_key).read_bytes(),
            owner_trusted_public_key_sha256=args.trusted_public_key_sha256,
            expected_commit_sha=args.expected_candidate_sha,
            expected_main_sha=args.expected_main_sha,
        )
    except (ReleaseEvidenceHold,OSError):
        print("VOWSIG_ONE_RELEASE_EVIDENCE=HOLD")
        print("PRODUCTION_DEPLOY_AUTHORIZED=NO")
        return 1
    print("VOWSIG_ONE_RELEASE_EVIDENCE=REVIEWED_SIGNED_RECEIPTS_PASS")
    print("MANDATORY_GATES="+str(result["mandatory_gates_checked"]))
    print("OWNER_EXACT_SHA_MERGE_DEPLOY_APPROVAL_REQUIRED=YES")
    print("PRODUCTION_DEPLOY_AUTHORIZED=NO")
    print("DATABASE_RECOVERY_UNVERIFIED")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
