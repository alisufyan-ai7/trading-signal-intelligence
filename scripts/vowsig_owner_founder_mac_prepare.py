#!/usr/bin/env python3
"""Private, offline Mac ceremony for VowSig STAGING first-owner bootstrap.

Run on the founder's Mac only. It never connects to GitHub, Auth0, Railway,
the staging database, or VowSig; it never mutates a hosted account.
Reviewer signing key + MFA materials stay encrypted and outside the repo.
"""
from __future__ import annotations

import argparse
import base64
from datetime import datetime, timedelta, timezone
import getpass
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import secrets
import stat
import sys
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption, Encoding, PublicFormat, PrivateFormat,
    NoEncryption, load_pem_private_key,
)

ROOT = Path.home() / ".vowsig-owner-private" / "staging"
KEY = "reviewer-encrypted-ed25519.pem"
PUB = "reviewer-public.pem"
VAULT = "mfa-vault.enc.json"
AAD = b"VowSig/staging/first-owner-solo/v1"
REVIEW_ID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.@-]{2,100}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _local_only():
    if platform.system() != "Darwin" or os.geteuid() == 0:
        raise RuntimeError("PERSONAL_MAC_NONROOT_REQUIRED")
    if any(os.environ.get(k) for k in (
        "CI", "GITHUB_ACTIONS", "RAILWAY_ENVIRONMENT", "RAILWAY_PROJECT_ID"
    )):
        raise RuntimeError("NOT_FOR_CI_OR_RAILWAY")
    if not (sys.stdin.isatty() and sys.stdout.isatty()):
        raise RuntimeError("PRIVATE_INTERACTIVE_TERMINAL_REQUIRED")


def _directory():
    parent = ROOT.parent
    for p in (parent, ROOT):
        if p.is_symlink():
            raise RuntimeError("PRIVATE_DIRECTORY_SYMLINK_REFUSED")
        if not p.exists():
            p.mkdir(mode=0o700)
        if not p.is_dir() or p.stat().st_uid != os.geteuid():
            raise RuntimeError("PRIVATE_DIRECTORY_OWNERSHIP_INVALID")
        if stat.S_IMODE(p.stat().st_mode) & 0o077:
            raise RuntimeError("PRIVATE_DIRECTORY_PERMISSIONS_TOO_BROAD")
    return ROOT


def _read_private(path: Path) -> bytes:
    if (path.is_symlink() or not path.is_file()
            or path.stat().st_uid != os.geteuid()
            or stat.S_IMODE(path.stat().st_mode) & 0o077
            or path.stat().st_size > 50_000):
        raise RuntimeError("PRIVATE_FILE_INVALID")
    return path.read_bytes()


def _write_private(path: Path, content: bytes):
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    flags |= getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags, 0o600)
    with os.fdopen(fd, "wb") as f:
        f.write(content)
        f.flush()
        os.fsync(f.fileno())


def _b64(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def _derive(passphrase: str, salt: bytes) -> bytes:
    return Scrypt(salt=salt, length=32, n=2**15, r=8, p=1).derive(
        passphrase.encode("utf-8")
    )


def _lock(material: dict[str, str], passphrase: str) -> bytes:
    salt, nonce = secrets.token_bytes(16), secrets.token_bytes(12)
    raw = json.dumps(material, sort_keys=True, separators=(",", ":")).encode()
    vault = {
        "schema_version": 1, "kdf": "scrypt-32768-8-1",
        "salt": _b64(salt), "nonce": _b64(nonce),
        "ciphertext": _b64(AESGCM(_derive(passphrase, salt)).encrypt(
            nonce, raw, AAD
        )),
    }
    return (json.dumps(vault, sort_keys=True, indent=2) + "\n").encode()


def _unlock(data: bytes, passphrase: str) -> dict[str, str]:
    obj = json.loads(data.decode())
    if obj.get("schema_version") != 1 or obj.get("kdf") != "scrypt-32768-8-1":
        raise RuntimeError("VAULT_VERSION_INVALID")
    plain = AESGCM(_derive(passphrase, _unb64(obj["salt"]))).decrypt(
        _unb64(obj["nonce"]), _unb64(obj["ciphertext"]), AAD
    )
    result = json.loads(plain)
    if set(result) != {"owner_master_b64u", "totp_base32"}:
        raise RuntimeError("PRIVATE_VAULT_INVALID")
    if len(_unb64(result["owner_master_b64u"])) != 32:
        raise RuntimeError("OWNER_MASTER_KEY_INVALID")
    if len(base64.b32decode(result["totp_base32"])) != 20:
        raise RuntimeError("OWNER_FACTOR_SECRET_INVALID")
    return result


def _passphrase(*, creation=False) -> str:
    p = getpass.getpass("Private key vault passphrase (hidden): ")
    if creation:
        if len(p) < 16:
            raise RuntimeError("PASSPHRASE_MINIMUM_16_CHARACTERS")
        if p != getpass.getpass("Repeat passphrase (hidden): "):
            raise RuntimeError("PASSPHRASE_CONFIRMATION_FAILED")
    return p


def _verify_phone(secret: bytes):
    from trading_signal_intelligence.product.accounts.owner_mfa import match_step
    code = getpass.getpass("Google Authenticator VowSig Staging code (hidden): ")
    if match_step(code, secret, now=datetime.now(timezone.utc), last_step=-1) is None:
        raise RuntimeError("GOOGLE_AUTHENTICATOR_CODE_MISMATCH")


def prepare():
    folder = _directory()
    if any((folder / n).exists() for n in (KEY, PUB, VAULT)):
        raise RuntimeError("PRIVATE_VAULT_ALREADY_EXISTS_DO_NOT_REGENERATE")
    password = _passphrase(creation=True)
    master = secrets.token_bytes(32)
    totp = secrets.token_bytes(20)
    token = base64.b32encode(totp).decode("ascii").rstrip("=")
    signer = Ed25519PrivateKey.generate()
    private = signer.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8,
        BestAvailableEncryption(password.encode("utf-8"))
    )
    public = signer.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    print("\nAdd a new MANUAL-ENTRY account in Google Authenticator:")
    print("Account name: VowSig Staging")
    print("Type: Time based (6-digit, 30-second)")
    print("Secret (PRIVATE; do not paste into chat, GitHub or shell history):")
    print(token)
    print("\nConfirm the displayed six-digit code before any credentials are saved.")
    _verify_phone(totp)
    _write_private(folder / KEY, private)
    _write_private(folder / PUB, public)
    _write_private(folder / VAULT, _lock({
        "owner_master_b64u": _b64(master),
        "totp_base32": token,
    }, password))
    print("\nFOUNDER_MAC_PRIVATE_PREP=PASS")
    print("PRIVATE_DIRECTORY=" + str(folder))
    print("PUBLIC_REVIEWER_KEY_SHA256=" + hashlib.sha256(public).hexdigest())
    print("MASTER_AND_FACTOR_PERSISTED_ENCRYPTED=YES")
    print("SIGNED_APPROVAL_CREATED=NO")
    print("STAGING_OWNER_PROMOTED=NO")


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode()


def sign():
    from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
        verify_owner_approval,
    )
    folder = _directory()
    public = _read_private(folder / PUB)
    encrypted = _read_private(folder / KEY)
    vault = _read_private(folder / VAULT)
    p = _passphrase()
    signer = load_pem_private_key(encrypted, password=p.encode())
    if not isinstance(signer, Ed25519PrivateKey):
        raise RuntimeError("WRONG_SIGNER_ALGORITHM")
    materials = _unlock(vault, p)
    if signer.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    ) != public:
        raise RuntimeError("REVIEWER_KEYPAIR_MISMATCH")
    print("Use ONLY the exact private staging verified-account identity receipt.")
    account = input("Verified staging account UUIDv4: ").strip()
    issuer = input("Exact configured staging OIDC issuer (https): ").strip()
    subject = input("SHA256 of immutable OIDC subject (64 hex chars): ").strip()
    founder = input("Your truthful operator/reviewer ID (e.g. founder.owner): ").strip()
    try:
        if str(UUID(account)) != account or UUID(account).version != 4:
            raise ValueError("UUIDv4 required")
    except (ValueError, TypeError):
        raise RuntimeError("EXACT_ACCOUNT_UUIDV4_REQUIRED")
    if not issuer.startswith("https://") or len(issuer) > 512:
        raise RuntimeError("EXACT_OIDC_ISSUER_REQUIRED")
    if not HEX64.fullmatch(subject):
        raise RuntimeError("SUBJECT_SHA256_REQUIRED")
    if not REVIEW_ID.fullmatch(founder):
        raise RuntimeError("TRUTHFUL_FOUNDER_ID_REQUIRED")
    _verify_phone(base64.b32decode(materials["totp_base32"]))
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = lambda dt: dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    approval = {
        "schema_version": 1,
        "purpose": "VOWSIG_OFFLINE_OWNER_MFA_V1",
        "operation_id": str(uuid4()),
        "operation": "first_owner_solo",
        "account_id": account,
        "oidc_issuer": issuer,
        "oidc_subject_sha256": subject,
        "reviewer_id": founder,
        "approved_at_utc": stamp(now),
        "expires_at_utc": stamp(now + timedelta(minutes=35)),
        "owner_identity_reverified": True,
        "owner_consent_confirmed": True,
    }
    signature = _b64(signer.sign(_canonical(approval)))
    envelope = _canonical({
        "authorization": approval, "signature_ed25519_b64u": signature
    }) + b"\n"
    verify_owner_approval(
        envelope,
        trusted_reviewer_public_key_pem=public,
        trusted_key_sha256=hashlib.sha256(public).hexdigest(),
        now=now,
    )
    filename = "approval-" + now.strftime("%Y%m%dT%H%M%SZ") + "-" + uuid4().hex[:8] + ".json"
    path = folder / filename
    _write_private(path, envelope)
    print("\nFOUNDER_SIGNED_STAGING_APPROVAL=PASS")
    print("SIGNED_APPROVAL_FILE=" + str(path))
    print("REVIEWER_PUBLIC_KEY_FILE=" + str(folder / PUB))
    print("REVIEWER_PUBLIC_KEY_SHA256=" + hashlib.sha256(public).hexdigest())
    print("APPROVAL_EXPIRES_UTC=" + approval["expires_at_utc"])
    print("OWNER_ROLE_CHANGED=NO")


def status():
    folder = _directory()
    files = [folder / n for n in (KEY, PUB, VAULT)]
    if not all(p.exists() for p in files):
        print("FOUNDER_MAC_PRIVATE_PREP=NOT_YET_COMPLETE")
        return
    for p in files:
        _read_private(p)
    print("FOUNDER_MAC_PRIVATE_PREP=COMPLETE")
    print("PUBLIC_REVIEWER_KEY_SHA256=" + hashlib.sha256(
        _read_private(folder / PUB)).hexdigest())
    print("SIGNED_APPROVAL_COUNT=" + str(len(list(folder.glob("approval-*.json")))))
    print("OWNER_ROLE_CHANGED=NO")


def main():
    parser = argparse.ArgumentParser(
        description="VowSig staging-only, founder's offline Mac owner MFA prep"
    )
    parser.add_argument("action", choices=("prepare", "status", "sign"))
    args = parser.parse_args()
    try:
        _local_only()
        if args.action == "prepare":
            prepare()
        elif args.action == "sign":
            sign()
        else:
            status()
        return 0
    except Exception as exc:
        # Never reveal passphrases, private identities, keys or TOTP secret.
        print("FOUNDER_MAC_SETUP=HOLD", file=sys.stderr)
        print("REASON_CODE=" + (
            str(exc) if type(exc) is RuntimeError else type(exc).__name__
        ), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
