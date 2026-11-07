"""Offline-only first-owner production handoff tests; no production calls."""
import base64
from datetime import datetime, timedelta, timezone
import hashlib
import importlib.util
from pathlib import Path
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from trading_signal_intelligence.product.accounts.owner_offline_provisioning import _canonical

ROOT = Path(__file__).resolve().parents[1]


def _load(path, name):
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fixture():
    mac = _load("scripts/vowsig_owner_founder_mac_production.py", "mac_prod_test")
    op = _load("scripts/vowsig_owner_production_operator.py", "op_prod_test")
    key = Ed25519PrivateKey.generate()
    pub = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    stamp = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "schema_version": 1, "purpose": "VOWSIG_OFFLINE_OWNER_MFA_V1",
        "operation_id": str(uuid4()), "operation": "first_owner_solo",
        "account_id": str(uuid4()), "oidc_issuer": "https://example.test/",
        "oidc_subject_sha256": "c" * 64, "reviewer_id": "founder.owner",
        "approved_at_utc": stamp(now - timedelta(seconds=10)),
        "expires_at_utc": stamp(now + timedelta(minutes=30)),
        "owner_identity_reverified": True, "owner_consent_confirmed": True,
    }
    approval = _canonical({
        "authorization": body,
        "signature_ed25519_b64u": mac._b64(key.sign(_canonical(body))),
    })
    package = {
        "schema": "VowSigSoloFounderProductionBundleV1",
        "approval_b64u": mac._b64(approval),
        "reviewer_public_pem_b64u": mac._b64(pub),
        "totp_base32": base64.b32encode(bytes(range(20))).decode(),
    }
    return mac, op, approval, pub, body, package


def test_existing_live_master_is_not_in_founder_bundle(monkeypatch):
    mac, op, signed, pub, body, package = _fixture()
    live_master = bytes(range(32))
    monkeypatch.setenv("VOWSIG_OWNER_TOTP_MASTER_KEY_B64", mac._b64(live_master))
    sealed = mac._b64(mac._lock(package, "random-long-one-use-transfer-passphrase"))
    doc, parsed_pub, parsed_body, master, secret = op._decrypt(
        sealed, "random-long-one-use-transfer-passphrase"
    )
    assert (doc, parsed_pub, parsed_body) == (signed, pub, body)
    assert master == live_master
    assert secret == bytes(range(20))
    assert set(package) == {"schema", "approval_b64u", "reviewer_public_pem_b64u", "totp_base32"}
    assert "master_key_b64u" not in str(package)
    assert hashlib.sha256(pub).hexdigest()


def test_missing_live_master_refuses(monkeypatch):
    mac, op, _, _, _, package = _fixture()
    monkeypatch.delenv("VOWSIG_OWNER_TOTP_MASTER_KEY_B64", raising=False)
    sealed = mac._b64(mac._lock(package, "random-long-one-use-transfer-passphrase"))
    with pytest.raises(Exception):
        op._decrypt(sealed, "random-long-one-use-transfer-passphrase")


def test_wrong_passphrase_and_staging_package_refused(monkeypatch):
    mac, op, _, _, _, package = _fixture()
    monkeypatch.setenv("VOWSIG_OWNER_TOTP_MASTER_KEY_B64", mac._b64(bytes(range(32))))
    sealed = mac._b64(mac._lock(package, "random-long-one-use-transfer-passphrase"))
    with pytest.raises(Exception):
        op._decrypt(sealed, "wrong-long-one-use-transfer-passphrase")
    package["schema"] = "VowSigSoloFounderStagingBundleV1"
    with pytest.raises(Exception):
        op._decrypt(mac._b64(mac._lock(package, "random-long-one-use-transfer-passphrase")),
                    "random-long-one-use-transfer-passphrase")


def test_production_operator_context_refuses_web_and_ci(monkeypatch):
    op = _load("scripts/vowsig_owner_production_operator.py", "operator_guard")
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    monkeypatch.setenv("RAILWAY_PROJECT_ID", "af8ed976-9971-4f5a-a304-3d8984df1565")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_ID", "fb429ace-7b81-432f-a9d2-32e2044f4392")
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    monkeypatch.setenv("RAILWAY_SERVICE_NAME", "tradingtop-early-access")
    with pytest.raises(RuntimeError, match="ISOLATED_PRODUCTION_SERVICE_REQUIRED"):
        op._environment()
    monkeypatch.setenv("RAILWAY_SERVICE_NAME", "vowsig-owner-production-operator")
    monkeypatch.setenv("CI", "true")
    with pytest.raises(RuntimeError, match="CI_EXECUTION_REFUSED"):
        op._environment()


def test_dedicated_operator_no_public_app_and_private_role(monkeypatch):
    docker = (ROOT / "Dockerfile.owner-production-operator").read_text()
    op = (ROOT / "scripts/vowsig_owner_production_operator.py").read_text()
    mac = (ROOT / "scripts/vowsig_owner_founder_mac_production.py").read_text()
    assert 'CMD ["sleep", "infinity"]' in docker
    assert 'uvicorn' not in docker.lower()
    assert "EXPOSE " not in docker
    assert "railway-postgres-root-ca-20261104.pem" in op
    assert 'user="vowsig_migrator"' in op
    assert 'sslmode="verify-full"' in op
    assert 'host="postgres.railway.internal"' in op
    assert "vowsig-production-pg18.railway.internal" not in op
    assert "preflight_owner_operation(conn, body)" in op
    assert "apply_owner_operation(" in op
    assert "PROMOTE_PRODUCTION_FIRST_OWNER" in op
    assert "PROMOTE_STAGING_FIRST_OWNER" not in op
    assert 'MASTER_KEY_B64' not in mac
    assert "password = getpass.getpass" in op
