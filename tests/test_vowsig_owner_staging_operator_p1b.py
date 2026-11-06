"""Synthetic-only coverage for private Mac <-> Railway staging owner handoff."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    _canonical,
)

ROOT = Path(__file__).resolve().parents[1]


def _load(path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    assert spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_mac_staging_operator_encrypted_handoff_real_signature_compatibility():
    mac = _load("scripts/vowsig_owner_founder_mac_prepare.py", "mac_creator")
    op = _load("scripts/vowsig_owner_staging_operator.py", "railway_reader")
    signer = Ed25519PrivateKey.generate()
    pub = signer.public_key().public_bytes(
        Encoding.PEM, PublicFormat.SubjectPublicKeyInfo
    )
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "schema_version": 1,
        "purpose": "VOWSIG_OFFLINE_OWNER_MFA_V1",
        "operation_id": str(uuid4()),
        "operation": "first_owner_solo",
        "account_id": str(uuid4()),
        "oidc_issuer": "https://auth.example.test/",
        "oidc_subject_sha256": "b" * 64,
        "reviewer_id": "founder.owner",
        "approved_at_utc": stamp(now - timedelta(seconds=10)),
        "expires_at_utc": stamp(now + timedelta(minutes=35)),
        "owner_identity_reverified": True,
        "owner_consent_confirmed": True,
    }
    signed = _canonical({
        "authorization": body,
        "signature_ed25519_b64u": mac._b64(signer.sign(_canonical(body))),
    })
    token = mac._b64(mac._lock({
        "schema": "VowSigSoloFounderStagingBundleV1",
        "approval_b64u": mac._b64(signed),
        "reviewer_public_pem_b64u": mac._b64(pub),
        "master_key_b64u": mac._b64(bytes(range(32))),
        "totp_base32": base64.b32encode(bytes(range(20))).decode(),
    }, "a-strong-transfer-passphrase-1234"))
    doc, out_pub, parsed, master, factor = op._decrypt(
        token, "a-strong-transfer-passphrase-1234"
    )
    assert doc == signed
    assert out_pub == pub
    assert parsed == body
    assert master == bytes(range(32))
    assert factor == bytes(range(20))
    assert hashlib.sha256(out_pub).hexdigest()


def test_encrypted_handoff_rejects_wrong_password_and_wrong_operation():
    mac = _load("scripts/vowsig_owner_founder_mac_prepare.py", "mac_bad")
    op = _load("scripts/vowsig_owner_staging_operator.py", "railway_bad")
    token = mac._b64(mac._lock(
        {"any": "test"}, "a-strong-transfer-passphrase-1234"
    ))
    with pytest.raises(Exception):
        op._decrypt(token, "wrong-transfer-passphrase-1234")
    with pytest.raises(Exception):
        op._decrypt(token, "a-strong-transfer-passphrase-1234")
    with pytest.raises(RuntimeError):
        op._decrypt("not-base64!!!", "a-strong-transfer-passphrase-1234")


def test_staging_operator_fails_closed_without_private_operator_context(monkeypatch):
    op = _load("scripts/vowsig_owner_staging_operator.py", "railway_context")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "unrelated-project")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "unrelated-environment")
    with pytest.raises(RuntimeError, match="ISOLATED_STAGING_SERVICE_REQUIRED"):
        op._environment()


def test_operator_artifact_cannot_run_as_web_or_publish_endpoint():
    docker=(ROOT/"Dockerfile.owner-operator").read_text()
    operator=(ROOT/"scripts/vowsig_owner_staging_operator.py").read_text()
    assert 'CMD ["sleep", "infinity"]' in docker
    assert 'COPY scripts/vowsig_owner_staging_operator.py' in docker
    assert 'uvicorn' not in docker.lower()
    assert 'EXPOSE ' not in docker
    assert "RAILWAY_PROJECT_ID" in operator
    assert 'sslmode="verify-full"' in operator
    assert 'preflight_owner_operation(conn, body)' in operator
    assert 'apply_owner_operation(' in operator
    assert "PROMOTE_STAGING_FIRST_OWNER" in operator
    assert "print(token)" not in operator
