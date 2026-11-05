"""Disposable signed release evidence; never use test signatures for production."""
from __future__ import annotations
import base64
from datetime import datetime,timedelta,timezone
import hashlib
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding,PublicFormat,
)

from trading_signal_intelligence.product.accounts import release_acceptance as gate

CANDIDATE="a"*40
MAIN="b"*40
NOW=datetime(2026,11,5,6,tzinfo=timezone.utc)
STAMP=(NOW-timedelta(minutes=15)).isoformat()


def fixture():
    signer=Ed25519PrivateKey.generate()
    pem=signer.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)
    sha=hashlib.sha256(pem).hexdigest()
    docs={name:{
        "status":"PASS","type":kind,
        "receipt_sha256":hashlib.sha256(name.encode()).hexdigest(),
        "observed_at_utc":STAMP,
        "human_reviewer_id":"independent-source-auditor" if kind.startswith("independent_") else "staging-reviewer",
        "private_receipt_custody_confirmed":True,
        "exact_candidate_commit_sha":CANDIDATE,
    } for name,kind in gate.REQUIRED_GATES.items()}
    obj={
        "schema_version":1,"repository":gate.REPOSITORY,
        "pull_request_number":93,"candidate_commit_sha":CANDIDATE,
        "main_before_release_sha":MAIN,"release_scope":gate.RELEASE_SCOPE,
        "mode":"SHADOW_ONLY","research_only":True,
        "broker_execution_disabled":True,
        "six_noncore_public_signal_details_disabled":True,
        "historical_performance_requires_independent_source_attestation":True,
        "new_railway_postgres_backup_unverified":True,
        "owner_accepted_recovery_risk":True,
        "first_postlaunch_action":gate._BACKUP_FIRST,
        "reviewed_at_utc":NOW.isoformat(),
        "gates":docs,"release_reviewer_id":"different-release-reviewer",
    }
    def sign(data):
        signature=signer.sign(gate._canonical(data))
        encoded=base64.urlsafe_b64encode(signature).decode().rstrip("=")
        return gate._canonical({"payload":data,"signature_ed25519_b64u":encoded})
    def check(doc,pem_=pem,sha_=sha,head=CANDIDATE,main=MAIN):
        return gate.verify_signed_release_receipts(
            doc,owner_trusted_public_key_pem=pem_,
            owner_trusted_public_key_sha256=sha_,
            expected_commit_sha=head,expected_main_sha=main,now=NOW)
    return obj,sign,check,pem,sha


def test_all_signed_fixtures_bind_exact_shas_but_never_automatically_deploy():
    obj,sign,check,_,_=fixture()
    result=check(sign(obj))
    assert result["mandatory_gates_checked"]==len(gate.REQUIRED_GATES)
    assert result["production_release_automatically_authorized"] is False
    assert result["owner_exact_sha_merge_deploy_approval_still_required"] is True
    assert result["new_railway_postgres_recovery_verified"] is False
    assert result["raw_receipts_or_credentials_exported"] is False


@pytest.mark.parametrize("gate_name",[
    "auth0_verified_email_signup","resend_actual_delivery",
    "railway_authenticated_app_role_verify_full",
    "owner_signed_offline_mfa_enrollment",
    "nine_ai_ledgers_cost_complete_independent_review",
    "crypto_k5_external_opportunity_coverage",
    "full_research_cohort_universe_signed",
    "staging_rollback_rehearsal",
])
def test_missing_human_external_evidence_holds(gate_name):
    obj,sign,check,_,_=fixture()
    obj["gates"][gate_name]["status"]="HOLD"
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj))


def test_missing_rollback_and_wrong_exact_sha_and_unsigned_hold():
    obj,sign,check,_,_=fixture()
    obj["gates"].pop("staging_rollback_rehearsal")
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj))
    obj,sign,check,_,_=fixture()
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj),head="c"*40)
    original=sign(obj)
    bad=original.replace(b"SHADOW_ONLY",b"LIVE_BROKER")
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(bad)


@pytest.mark.parametrize("field,value",[
    ("broker_execution_disabled",False),
    ("six_noncore_public_signal_details_disabled",False),
    ("new_railway_postgres_backup_unverified",False),
    ("owner_accepted_recovery_risk",False),
    ("first_postlaunch_action","NONE"),
    ("release_scope","EARLY_FEATURE_DISABLED_LAUNCH"),
])
def test_release_scope_and_backup_exception_are_binding(field,value):
    obj,sign,check,_,_=fixture()
    obj[field]=value
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj))


def test_self_review_and_untrusted_key_and_stale_receipts_hold():
    obj,sign,check,pem,sha=fixture()
    obj["release_reviewer_id"]="independent-source-auditor"
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj))
    obj,sign,check,pem,sha=fixture()
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj),sha_="f"*64)
    obj["gates"]["auth0_verified_email_signup"]["observed_at_utc"]=(NOW-timedelta(days=31)).isoformat()
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj))


def test_no_raw_secrets_are_accepted_in_evidence_envelope():
    obj,sign,check,_,_=fixture()
    obj["gates"]["resend_actual_delivery"]["api_key"]="unsafe"
    with pytest.raises(gate.ReleaseEvidenceHold):
        check(sign(obj))
