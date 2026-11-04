"""Synthetic PostgreSQL 18 first-owner / recovered-factor proof, CI ONLY.

Run only after scripts/vowsig_accounts_ci_pg18_role_boundaries.py.
NEVER connects to a production or external database. All authorization
signers, TOTP secrets and account identities are disposable test values.
"""
from __future__ import annotations

import base64
from datetime import datetime, timedelta, timezone
import hashlib
import os
from uuid import uuid4

import psycopg
from psycopg.rows import dict_row

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    OwnerProvisioningDenied, _canonical, verify_owner_approval,
    preflight_owner_operation, apply_owner_operation,
)
from trading_signal_intelligence.product.accounts.owner_mfa import (
    decrypt_for_owner, totp_at,
)
from vowsig_accounts_ci_pg18_role_boundaries import _guard


ACCOUNT="00000000-0000-4000-8000-000000000001"


def _signed(private, body):
    sig=private.sign(_canonical(body))
    return _canonical({
        "authorization":body,
        "signature_ed25519_b64u":base64.urlsafe_b64encode(sig).decode().rstrip("="),
    })


def _approval(now, *, operation, operation_id):
    return {
        "schema_version":1,
        "purpose":"VOWSIG_OFFLINE_OWNER_MFA_V1",
        "operation_id":operation_id,
        "operation":operation,
        "account_id":ACCOUNT,
        "oidc_issuer":"https://idp.example.test",
        "oidc_subject_sha256":hashlib.sha256(b"ci-identity").hexdigest(),
        "reviewer_id":"independent-reviewer.ci",
        "approved_at_utc":(now-timedelta(minutes=1)).isoformat().replace("+00:00","Z"),
        "expires_at_utc":(now+timedelta(minutes=25)).isoformat().replace("+00:00","Z"),
        "owner_identity_reverified":True,
        "owner_consent_confirmed":True,
    }


def _deny(fn, label):
    try:
        fn()
    except OwnerProvisioningDenied:
        return
    raise RuntimeError(f"Expected offline owner rejection: {label}")


def main():
    dsn=_guard()
    if os.environ.get("GITHUB_ACTIONS")!="true":
        raise RuntimeError("CI required")
    target=dsn.replace("/vowsig_test?","/vowsig_roles_test?")
    now=datetime.now(timezone.utc)
    signer=Ed25519PrivateKey.generate()
    public=signer.public_key().public_bytes(Encoding.PEM,PublicFormat.SubjectPublicKeyInfo)
    public_sha=hashlib.sha256(public).hexdigest()
    original_secret=b"12345678901234567890"
    fresh_secret=b"09876543210987654321"
    master=bytes(range(32))
    initial_hash="d"*64
    second_hash="e"*64

    with psycopg.connect(target, autocommit=True,row_factory=dict_row) as db:
        db.execute(
            """INSERT INTO vowsig.vowsig_account_sessions
               (token_sha256,account_id,expires_at)
               VALUES (%s,%s::uuid,%s)""",
            (initial_hash,ACCOUNT,now+timedelta(hours=1)),
        )

    with psycopg.connect(target, autocommit=True,row_factory=dict_row) as migrator:
        migrator.execute("SET SESSION AUTHORIZATION vowsig_migrator")
        migrator.execute("SET search_path TO vowsig,pg_catalog")
        first=_approval(now,operation="first_owner",operation_id=str(uuid4()))
        signed=_signed(signer,first)
        doc=verify_owner_approval(
            signed,trusted_reviewer_public_key_pem=public,
            trusted_key_sha256=public_sha,now=now,
        )
        assert preflight_owner_operation(migrator,doc)["status"]=="PREVIEW_OK"
        assert migrator.execute(
            "SELECT role FROM vowsig_accounts WHERE id=%s::uuid",(ACCOUNT,),
        ).fetchone()["role"]=="member"
        with migrator.transaction():
            receipt=apply_owner_operation(
                migrator,signed,
                trusted_reviewer_public_key_pem=public,
                trusted_key_sha256=public_sha,
                enrolled_secret=original_secret,
                master_key=master,
                owner_code=totp_at(original_secret,int(now.timestamp())//30),
                operator_id="operator.ci",now=now,
            )
        assert receipt["status"]=="APPLIED_REQUIRES_FRESH_LOGIN"
        assert receipt["revoked_sessions"]==1
        assert migrator.execute(
            "SELECT role FROM vowsig_accounts WHERE id=%s::uuid",(ACCOUNT,),
        ).fetchone()["role"]=="owner"
        assert migrator.execute(
            "SELECT revoked_at FROM vowsig_account_sessions WHERE token_sha256=%s",
            (initial_hash,),
        ).fetchone()["revoked_at"] is not None
        _deny(lambda: preflight_owner_operation(migrator,doc),"replayed first-owner approval")
        _deny(lambda: apply_owner_operation(
            migrator,signed,
            trusted_reviewer_public_key_pem=public,trusted_key_sha256=public_sha,
            enrolled_secret=original_secret,master_key=master,
            owner_code=totp_at(original_secret,int(now.timestamp())//30),
            operator_id="operator.ci",now=now,
        ),"nontransactional or replay")

        with psycopg.connect(target,autocommit=True,row_factory=dict_row) as db:
            db.execute(
                """INSERT INTO vowsig.vowsig_account_sessions
                   (token_sha256,account_id,expires_at)
                   VALUES (%s,%s::uuid,%s)""",
                (second_hash,ACCOUNT,now+timedelta(hours=1)),
            )

        rotated=_approval(now,operation="rotate_factor",operation_id=str(uuid4()))
        rotation_signed=_signed(signer,rotated)
        assert preflight_owner_operation(migrator,rotated)["status"]=="PREVIEW_OK"
        _deny(lambda: apply_owner_operation(
            migrator,rotation_signed,
            trusted_reviewer_public_key_pem=public,trusted_key_sha256=public_sha,
            enrolled_secret=fresh_secret,master_key=master,
            owner_code=totp_at(fresh_secret,int(now.timestamp())//30),
            operator_id=rotated["reviewer_id"],now=now,
        ),"reviewer cannot act as operator")

        with migrator.transaction():
            recovered=apply_owner_operation(
                migrator,rotation_signed,
                trusted_reviewer_public_key_pem=public,trusted_key_sha256=public_sha,
                enrolled_secret=fresh_secret,master_key=master,
                owner_code=totp_at(fresh_secret,int(now.timestamp())//30),
                operator_id="operator.ci",now=now,
            )
        assert recovered["revoked_sessions"]==1
        assert migrator.execute(
            "SELECT revoked_at FROM vowsig_account_sessions WHERE token_sha256=%s",
            (second_hash,),
        ).fetchone()["revoked_at"] is not None
        row=migrator.execute(
            "SELECT secret_ciphertext,last_accepted_step,failed_attempts,locked_until "
            "FROM vowsig_owner_totp_credentials WHERE account_id=%s::uuid",
            (ACCOUNT,),
        ).fetchone()
        assert decrypt_for_owner(bytes(row["secret_ciphertext"]),ACCOUNT,master)==fresh_secret
        assert row["last_accepted_step"]==-1
        assert row["failed_attempts"]==0
        assert row["locked_until"] is None
        audit=migrator.execute(
            "SELECT operation,reviewer_id,operator_id,revoked_sessions "
            "FROM vowsig_owner_provisioning_audit ORDER BY created_at",
        ).fetchall()
        assert len(audit)==2
        assert {r["operation"] for r in audit}=={"first_owner","rotate_factor"}
        assert all(r["reviewer_id"]!=r["operator_id"] for r in audit)
        assert migrator.execute(
            "SELECT count(*) AS n FROM vowsig_accounts WHERE role='owner'"
        ).fetchone()["n"]==1

    print(
        "PG18_OWNER_OFFLINE_BOOTSTRAP_RECOVERY=PASS; "
        "signed_reviewer=YES; exact_subject=YES; first_owner_only=YES; "
        "cross_operator=YES; replay_rejected=YES; session_revocation=YES; "
        "encrypted_factor_rotation=YES; no_real_secrets=YES"
    )


if __name__=="__main__":
    main()
