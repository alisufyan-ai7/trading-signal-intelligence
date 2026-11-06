#!/usr/bin/env python3
"""Offline, two-person owner-factor operator. NEVER run in the web container.

No writes by default. For production, only an approved one-off migrator
environment with a directly authenticated PostgreSQL connection may apply.
Does not create roles, databases, owners or secrets automatically.
"""
from __future__ import annotations

import argparse
import base64
import binascii
import getpass
import hashlib
import json
import os
from pathlib import Path
import sys
from urllib.parse import parse_qs, urlsplit

from trading_signal_intelligence.product.accounts.owner_mfa import load_master_key
from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    OwnerProvisioningDenied, apply_owner_operation, preflight_owner_operation,
    verify_owner_approval,
)

ACK = "I_APPROVE_ONE_OFF_OWNER_SESSION_REVOCATION"
SOLO_ACK = "I_ACCEPT_FIRST_OWNER_SELF_AUTHORIZATION_NO_INDEPENDENT_REVIEW"


def _reviewed_dsn() -> str:
    dsn = os.environ.get("VOWSIG_OWNER_MIGRATOR_DATABASE_URL", "")
    p = urlsplit(dsn)
    params = parse_qs(p.query, strict_parsing=True)
    if (
        p.scheme != "postgresql"
        or p.hostname != "postgres.railway.internal"
        or p.username != "vowsig_migrator"
        or not p.password
        or params.get("sslmode") != ["verify-full"]
        or len(params.get("sslrootcert", [])) != 1
        or params.get("sslrootcert", [""])[0] !=
           "/app/config/tls/railway-postgres-root-ca-20261104.pem"
        or p.fragment
    ):
        raise OwnerProvisioningDenied("Verified private migrator connection required")
    return dsn


def _read_approval(path: str) -> bytes:
    file = Path(path)
    if file.is_symlink() or not file.is_file() or file.stat().st_size > 8192:
        raise OwnerProvisioningDenied("Missing or oversized signed authorization file")
    return file.read_bytes()


def _secret_base32(value: str) -> bytes:
    value = value.strip().upper()
    if len(value) != 32 or not all(x in "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567" for x in value):
        raise OwnerProvisioningDenied("Expected exact 160-bit base32 authenticator secret")
    try:
        raw = base64.b32decode(value, casefold=False)
    except (ValueError, binascii.Error) as exc:
        raise OwnerProvisioningDenied("Invalid authenticator secret encoding") from exc
    if len(raw) != 20:
        raise OwnerProvisioningDenied("Invalid offline secret length")
    return raw


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="VowSig offline, signed owner operator")
    parser.add_argument("--approval-file", required=True)
    parser.add_argument("--reviewer-public-key-file", required=True)
    parser.add_argument("--mode", choices=("preview", "apply"), default="preview")
    parser.add_argument("--operator-id", default="")
    parser.add_argument("--acknowledge", default="")
    parser.add_argument("--solo-founder-first-owner", action="store_true")
    parser.add_argument("--acknowledge-solo", default="")
    args = parser.parse_args(argv)

    try:
        doc = _read_approval(args.approval_file)
        public_key = Path(args.reviewer_public_key_file).read_bytes()
        expected_key = os.environ.get("VOWSIG_OWNER_REVIEWER_PUBLIC_KEY_SHA256", "")
        approval = verify_owner_approval(
            doc,
            trusted_reviewer_public_key_pem=public_key,
            trusted_key_sha256=expected_key,
        )
        dsn = _reviewed_dsn()
        if args.solo_founder_first_owner:
            if (approval["operation"] != "first_owner_solo"
                or args.mode != "apply"
                or args.acknowledge_solo != SOLO_ACK
                or args.operator_id != approval["reviewer_id"]):
                raise OwnerProvisioningDenied("Exact solo founder authorization required")
        elif (approval["operation"] == "first_owner_solo"
              or args.acknowledge_solo
              or (args.mode == "apply" and args.operator_id == approval["reviewer_id"])):
            raise OwnerProvisioningDenied("Founder exception requires explicit solo mode")
        if args.mode == "apply" and (
            args.acknowledge != ACK or not sys.stdin.isatty()
            or not sys.stdout.isatty() or not args.operator_id
        ):
            raise OwnerProvisioningDenied("Interactive owner approval is required")
        import psycopg
        from psycopg.rows import dict_row

        with psycopg.connect(
            dsn, row_factory=dict_row, connect_timeout=5, autocommit=True,
        ) as conn:
            with conn.transaction():
                conn.execute("SET LOCAL search_path TO vowsig, pg_catalog")
                current = conn.execute(
                    "SELECT current_user AS role, current_schema() AS schema"
                ).fetchone()
                if current != {"role": "vowsig_migrator", "schema": "vowsig"}:
                    raise OwnerProvisioningDenied("Not running as dedicated schema migrator")
                preview = preflight_owner_operation(conn, approval)
                if args.mode == "preview":
                    print(json.dumps(preview, sort_keys=True))
                    return 0

            # Collect secrets outside SQL, not through argv/history or output.
            master = load_master_key(os.environ.get("VOWSIG_OWNER_TOTP_MASTER_KEY_B64", ""))
            secret = _secret_base32(getpass.getpass(
                "Authenticator's enrolled 32-character Base32 secret (hidden): "
            ))
            code = getpass.getpass("Owner's current six-digit authenticator code (hidden): ")
            with conn.transaction():
                conn.execute("SET LOCAL search_path TO vowsig, pg_catalog")
                receipt = apply_owner_operation(
                    conn, doc,
                    trusted_reviewer_public_key_pem=public_key,
                    trusted_key_sha256=expected_key,
                    enrolled_secret=secret,
                    master_key=master,
                    owner_code=code,
                    operator_id=args.operator_id,
                )
            print(json.dumps(receipt, sort_keys=True))
            return 0
    except (OSError, ValueError, RuntimeError, LookupError) as exc:
        # Do not serialize SQL DSN, passwords, authenticators, SQL errors,
        # reviewer key or raw OIDC subject into CI/logs/chat.
        print("OWNER_OFFLINE_OPERATION=DENIED", file=sys.stderr)
        print("REASON_TYPE="+type(exc).__name__, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
