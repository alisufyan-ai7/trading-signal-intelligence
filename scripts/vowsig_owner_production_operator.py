#!/usr/bin/env python3
"""One-use production-only founder enrollment. Run interactively in isolated operator.

Never run in the web app or CI. Only run in the isolated, named one-use production Railway operator service. No public listener,
persistent secret file, signing private key, external requests or HTTP route.
"""
from __future__ import annotations

import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import re
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from psycopg.rows import dict_row
import psycopg

from trading_signal_intelligence.product.accounts.owner_mfa import load_master_key
from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    apply_owner_operation, preflight_owner_operation, verify_owner_approval,
)

_PROJECT = "af8ed976-9971-4f5a-a304-3d8984df1565"
_ENV = "fb429ace-7b81-432f-a9d2-32e2044f4392"
_SERVICE = "vowsig-owner-production-operator"
_CA = Path("/app/config/tls/railway-production-pg-root-ca-20261105.pem")
_AAD = b"VowSig/production/first-owner-solo/v1"


def _refuse(code: str):
    raise RuntimeError(code)


def _b64url(s: str) -> bytes:
    if not isinstance(s, str) or not re.fullmatch(r"[A-Za-z0-9_-]+", s):
        _refuse("INVALID_TRANSFER_ENCODING")
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _unique(pairs):
    obj = {}
    for key, value in pairs:
        if key in obj:
            _refuse("DUPLICATE_TRANSFER_KEY")
        obj[key] = value
    return obj


def _decrypt(token: str, passphrase: str):
    if len(token) > 32768 or len(passphrase) < 20:
        _refuse("ENCRYPTED_TRANSFER_INVALID")
    envelope = json.loads(_b64url(token).decode("utf-8"), object_pairs_hook=_unique)
    if set(envelope) != {"schema_version", "kdf", "salt", "nonce", "ciphertext"}:
        _refuse("TRANSFER_FORMAT_INVALID")
    if envelope["schema_version"] != 1 or envelope["kdf"] != "scrypt-32768-8-1":
        _refuse("TRANSFER_KDF_INVALID")
    salt, nonce = _b64url(envelope["salt"]), _b64url(envelope["nonce"])
    if len(salt) != 16 or len(nonce) != 12:
        _refuse("TRANSFER_NONCE_INVALID")
    key = Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(
        passphrase.encode("utf-8")
    )
    clear = AESGCM(key).decrypt(nonce, _b64url(envelope["ciphertext"]), _AAD)
    package = json.loads(clear.decode("utf-8"), object_pairs_hook=_unique)
    if set(package) != {
        "schema", "approval_b64u", "reviewer_public_pem_b64u",
        "totp_base32",
    } or package["schema"] != "VowSigSoloFounderProductionBundleV1":
        _refuse("TRANSFER_PACKAGE_INVALID")
    public = _b64url(package["reviewer_public_pem_b64u"])
    if len(public) > 8192 or not public.startswith(b"-----BEGIN PUBLIC KEY-----"):
        _refuse("PUBLIC_KEY_INVALID")
    signed = _b64url(package["approval_b64u"])
    approval = verify_owner_approval(
        signed, trusted_reviewer_public_key_pem=public,
        trusted_key_sha256=hashlib.sha256(public).hexdigest(),
    )
    if approval["operation"] != "first_owner_solo":
        _refuse("SOLO_FIRST_OWNER_REQUIRED")
    # Only the live production app master via a Railway service-variable reference.
    # Neither the offline founder nor the transfer bundle provides or rotates it.
    master = load_master_key(os.environ.get("VOWSIG_OWNER_TOTP_MASTER_KEY_B64", ""))
    try:
        totp = base64.b32decode(package["totp_base32"], casefold=False)
    except (ValueError, TypeError):
        _refuse("FACTOR_FORMAT_INVALID")
    if len(totp) != 20:
        _refuse("FACTOR_LENGTH_INVALID")
    return signed, public, approval, master, totp


def _environment():
    if any(os.environ.get(k) for k in ("CI", "GITHUB_ACTIONS")):
        _refuse("CI_EXECUTION_REFUSED")
    checks = {
        "RAILWAY_PROJECT_ID": _PROJECT,
        "RAILWAY_ENVIRONMENT_ID": _ENV,
        "RAILWAY_ENVIRONMENT_NAME": "production",
        "RAILWAY_SERVICE_NAME": _SERVICE,
    }
    if not all(os.environ.get(k) == v for k, v in checks.items()):
        _refuse("ISOLATED_PRODUCTION_SERVICE_REQUIRED")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        _refuse("REAL_PRIVATE_INTERACTIVE_CONSOLE_REQUIRED")
    if not _CA.is_file() or _CA.is_symlink():
        _refuse("PRODUCTION_PINNED_CA_MISSING")
    db = os.environ.get("VOWSIG_OWNER_PRODUCTION_DATABASE", "")
    if not re.fullmatch(r"[a-z_][a-z0-9_]{0,62}", db):
        _refuse("EXACT_PRODUCTION_DATABASE_NAME_REQUIRED")
    # Password is collected only in the founder's interactive SSH console;
    # never persist the migrator login secret on this temporary service.
    password = getpass.getpass("Existing production vowsig_migrator password (hidden): ")
    if not re.fullmatch(r"[A-Za-z0-9_-]{44,128}", password):
        _refuse("PRODUCTION_MIGRATOR_PASSWORD_FORMAT_INVALID")
    return password


def run():
    password = _environment()
    print("OWNER_OPERATOR=PRODUCTION_ONLY")
    print("Paste the encrypted Mac handoff (input hidden).")
    token = getpass.getpass("Encrypted production handoff: ")
    passphrase = getpass.getpass("Separate transfer passphrase: ")
    signed, pub, body, master, factor = _decrypt(token, passphrase)
    pin = hashlib.sha256(pub).hexdigest()
    with psycopg.connect(
        host="vowsig-production-pg18.railway.internal",
        port=5432,
        dbname=os.environ["VOWSIG_OWNER_PRODUCTION_DATABASE"],
        user="vowsig_migrator",
        password=password,
        sslmode="verify-full",
        sslrootcert=str(_CA),
        connect_timeout=7,
        row_factory=dict_row,
        autocommit=True,
    ) as conn:
        with conn.transaction():
            conn.execute("SET LOCAL search_path TO vowsig, pg_catalog")
            role = conn.execute(
                "SELECT current_user AS role, current_schema() AS schema"
            ).fetchone()
            ssl = conn.execute(
                "SELECT ssl FROM pg_stat_ssl WHERE pid=pg_backend_pid()"
            ).fetchone()
            if role != {"role": "vowsig_migrator", "schema": "vowsig"} or not ssl or not ssl["ssl"]:
                _refuse("MIGRATOR_ROLE_OR_TLS_INVALID")
            preflight = preflight_owner_operation(conn, body)
            if preflight["status"] != "PREVIEW_OK":
                _refuse("PRODUCTION_PREFLIGHT_INVALID")
        print("PRODUCTION_FIRST_OWNER_PREFLIGHT=PASS")
        print("ACCOUNT_BOUND_TO_VERIFIED_OIDC=YES")
        print("NO_EXISTING_OWNER=YES")
        print("PROMOTION_PERFORMED=NO")
        confirm = input(
            "Type PROMOTE_PRODUCTION_FIRST_OWNER to approve exact one-use enrollment: "
        ).strip()
        if confirm != "PROMOTE_PRODUCTION_FIRST_OWNER":
            _refuse("FOUNDER_DID_NOT_APPROVE_APPLY")
        code = getpass.getpass("Fresh six-digit VowSig Production Google Authenticator code: ")
        with conn.transaction():
            conn.execute("SET LOCAL search_path TO vowsig, pg_catalog")
            receipt = apply_owner_operation(
                conn, signed,
                trusted_reviewer_public_key_pem=pub,
                trusted_key_sha256=pin,
                enrolled_secret=factor, master_key=master, owner_code=code,
                operator_id=body["reviewer_id"],
            )
    print("PRODUCTION_FIRST_OWNER_APPLY=PASS")
    print("OWNER_ROLE_ACTIVATED=YES")
    print("EXISTING_SESSIONS_REVOKED=" + str(receipt["revoked_sessions"]))
    print("NEW_AUTH0_LOGIN_AND_TOTP_REQUIRED=YES")
    print("SOLO_FOUNDER_EXCEPTION_AUDITED=YES")
    print("PRODUCTION_ROLE_AND_FACTOR_CHANGED=YES")
    print("APP_AND_PUBLISHER_CHANGED=NO")


if __name__ == "__main__":
    try:
        run()
    except Exception as exc:
        print("PRODUCTION_FIRST_OWNER_APPLY=HOLD", file=sys.stderr)
        print("REASON_TYPE=" + type(exc).__name__, file=sys.stderr)
        sys.exit(1)
