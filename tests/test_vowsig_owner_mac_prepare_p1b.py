"""Isolated synthetic-only Mac founder ceremony tests; never use real keys or providers."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import importlib.util
import json
import os
import stat

import pytest
from cryptography.exceptions import InvalidTag

from trading_signal_intelligence.product.accounts.owner_offline_provisioning import (
    verify_owner_approval,
)

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts" / "vowsig_owner_founder_mac_prepare.py"


def _load():
    spec = importlib.util.spec_from_file_location("mac_founder_test_module", MODULE)
    obj = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(obj)
    return obj


def test_encrypted_vault_authenticates_and_refuses_wrong_password():
    m = _load()
    data = {"owner_master_b64u": m._b64(bytes(range(32))),
            "totp_base32": "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"}
    enc = m._lock(data, "an-offline-private-long-passphrase")
    assert "owner_master_b64u" not in enc.decode("utf-8")
    assert data == m._unlock(enc, "an-offline-private-long-passphrase")
    with pytest.raises((InvalidTag, ValueError)):
        m._unlock(enc, "some-other-long-passphrase")


def test_private_prepare_and_35_minute_first_owner_signature(tmp_path, monkeypatch, capsys):
    m = _load()
    monkeypatch.setattr(m, "ROOT", tmp_path / "owner" / "staging")
    monkeypatch.setattr(m, "_passphrase", lambda creation=False: "very-private-long-passphrase")
    monkeypatch.setattr(m, "_verify_phone", lambda value: None)
    m.prepare()
    out = capsys.readouterr().out
    assert "FOUNDER_MAC_PRIVATE_PREP=PASS" in out
    for n in (m.KEY, m.PUB, m.VAULT):
        assert stat.S_IMODE((m.ROOT / n).stat().st_mode) == 0o600

    source = iter((
        "01234567-89ab-4def-8abc-0123456789ab",
        "https://tenant.example.test/",
        "f" * 64,
        "founder.owner",
    ))
    monkeypatch.setattr("builtins.input", lambda _: next(source))
    m.sign()
    out = capsys.readouterr().out
    assert "FOUNDER_SIGNED_STAGING_APPROVAL=PASS" in out
    docs = list(m.ROOT.glob("approval-*.json"))
    assert len(docs) == 1
    assert stat.S_IMODE(docs[0].stat().st_mode) == 0o600
    doc = json.loads(docs[0].read_bytes())
    assert doc["authorization"]["operation"] == "first_owner_solo"
    assert doc["authorization"]["reviewer_id"] == "founder.owner"
    assert doc["authorization"]["owner_identity_reverified"] is True
    assert doc["authorization"]["owner_consent_confirmed"] is True
    pub = (m.ROOT / m.PUB).read_bytes()
    import hashlib
    assert verify_owner_approval(
        docs[0].read_bytes(), trusted_reviewer_public_key_pem=pub,
        trusted_key_sha256=hashlib.sha256(pub).hexdigest()
    )["account_id"] == "01234567-89ab-4def-8abc-0123456789ab"
    with pytest.raises(RuntimeError, match="ALREADY_EXISTS"):
        m.prepare()


def test_invalid_private_identity_never_creates_a_signed_file(tmp_path, monkeypatch):
    m = _load()
    monkeypatch.setattr(m, "ROOT", tmp_path / "owner" / "staging")
    monkeypatch.setattr(m, "_passphrase", lambda creation=False: "very-private-long-passphrase")
    monkeypatch.setattr(m, "_verify_phone", lambda _: None)
    m.prepare()
    source = iter(("not-uuid", "https://tenant.example.test", "f" * 64, "founder.owner"))
    monkeypatch.setattr("builtins.input", lambda _: next(source))
    with pytest.raises(RuntimeError, match="EXACT_ACCOUNT_UUIDV4_REQUIRED"):
        m.sign()
    assert not list(m.ROOT.glob("approval-*.json"))


def test_mac_operator_refuses_ci_railway_and_root(monkeypatch):
    m = _load()
    monkeypatch.setattr(m.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(m.os, "geteuid", lambda: 501)
    monkeypatch.setattr(m.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(m.sys.stdout, "isatty", lambda: True)
    monkeypatch.setenv("RAILWAY_ENVIRONMENT", "staging")
    with pytest.raises(RuntimeError, match="NOT_FOR_CI_OR_RAILWAY"):
        m._local_only()
    monkeypatch.delenv("RAILWAY_ENVIRONMENT")
    monkeypatch.setattr(m.os, "geteuid", lambda: 0)
    with pytest.raises(RuntimeError, match="PERSONAL_MAC_NONROOT_REQUIRED"):
        m._local_only()
