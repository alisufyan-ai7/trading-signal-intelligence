#!/usr/bin/env python3
"""OFFLINE reviewer only: sign one time-limited owner approval.

Must run on an operator-controlled OFFLINE machine, never Railway/web/CI.
The reviewer owns an encrypted Ed25519 private key OUTSIDE the repo.
The resulting signed JSON contains identifiers; transfer privately to the
separate migrator operator. No private key or password is ever printed.
"""
from __future__ import annotations

import argparse
import base64
import getpass
import hashlib
import json
import os
from pathlib import Path
import stat
import sys

from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, load_pem_private_key,
)
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    OwnerProvisioningDenied, _canonical, _no_duplicate_keys,
    verify_owner_approval,
)


def main(argv: list[str] | None = None) -> int:
    parser=argparse.ArgumentParser(description="Sign a one-time VowSig owner approval offline")
    parser.add_argument("--unsigned-approval-file",required=True)
    parser.add_argument("--encrypted-private-key-file",required=True)
    parser.add_argument("--output-file",required=True)
    args=parser.parse_args(argv)
    try:
        if (
            os.environ.get("CI") or os.environ.get("GITHUB_ACTIONS")
            or os.environ.get("RAILWAY_ENVIRONMENT")
            or not sys.stdin.isatty() or not sys.stdout.isatty()
        ):
            raise OwnerProvisioningDenied("Must sign on an offline interactive reviewer workstation")
        private_file=Path(args.encrypted_private_key_file)
        if (private_file.is_symlink() or not private_file.is_file()
                or private_file.stat().st_mode & (stat.S_IRWXG | stat.S_IRWXO)
                or private_file.stat().st_size > 10_000):
            raise OwnerProvisioningDenied("Reviewer private key file permissions invalid")
        manifest_file=Path(args.unsigned_approval_file)
        if manifest_file.is_symlink() or manifest_file.stat().st_size > 8_192:
            raise OwnerProvisioningDenied("Invalid reviewer manifest file")
        manifest=json.loads(manifest_file.read_text(encoding="utf-8"),
                            object_pairs_hook=_no_duplicate_keys)
        if not isinstance(manifest,dict):
            raise OwnerProvisioningDenied("Invalid reviewer authorization fields")
        key_bytes=private_file.read_bytes()
        if not key_bytes.startswith(b"-----BEGIN ENCRYPTED PRIVATE KEY-----"):
            raise OwnerProvisioningDenied("Encrypted Ed25519 private key required")
        passphrase=getpass.getpass("Encrypted reviewer key password (hidden): ")
        if not passphrase:
            raise OwnerProvisioningDenied("Reviewer private key must be password protected")
        key=load_pem_private_key(key_bytes,password=passphrase.encode("utf-8"))
        if not isinstance(key, Ed25519PrivateKey):
            raise OwnerProvisioningDenied("Reviewer must use Ed25519")
        signature=key.sign(_canonical(manifest))
        signed=_canonical({
            "authorization":manifest,
            "signature_ed25519_b64u":base64.urlsafe_b64encode(signature).decode().rstrip("="),
        })
        public=key.public_key().public_bytes(
            Encoding.PEM,PublicFormat.SubjectPublicKeyInfo,
        )
        pin=hashlib.sha256(public).hexdigest()
        verify_owner_approval(signed,trusted_reviewer_public_key_pem=public,
                              trusted_key_sha256=pin)
        outfile=Path(args.output_file)
        if outfile.is_symlink() or outfile.exists():
            raise OwnerProvisioningDenied("Refusing to overwrite signed approval")
        fd=os.open(str(outfile), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd,"wb") as output:
            output.write(signed+b"\n")
        print("OWNER_REVIEW_SIGNATURE=CREATED")
        print("REVIEWER_PUBLIC_KEY_SHA256="+pin)
        print("SECURE_TRANSFER_REQUIRED=YES")
        return 0
    except (OSError,ValueError,TypeError,RuntimeError,KeyError) as exc:
        print("OWNER_REVIEW_SIGNATURE=DENIED",file=sys.stderr)
        print("REASON_TYPE="+type(exc).__name__,file=sys.stderr)
        return 1


if __name__=="__main__":
    raise SystemExit(main())
