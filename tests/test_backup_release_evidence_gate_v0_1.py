"""Only synthetic release claims; no VPS source, AWS/B2 SDK or real keys."""
from __future__ import annotations

import ast
import hashlib
import inspect
from datetime import datetime, timedelta, timezone

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from trading_signal_intelligence.recovery import backup_release_evidence_gate_v0_1 as gate


FIXED = datetime(2026, 10, 23, 11, 0, tzinfo=timezone.utc)


def signed_fixture(now=FIXED):
    document = {
        "schema": gate.SCHEMA,
        "repository": gate.REPOSITORY,
        "source_relative_path": gate.SOURCE,
        "source_type": "S02",
        "candidate_head": "a" * 40,
        "main_head": "b" * 40,
        "provider_targets": [list(x) for x in gate.PROVIDERS],
        "max_signed_requests": gate.MAX_SIGNED_REQUESTS,
        "max_source_bytes": gate.MAX_SOURCE_BYTES,
        "issued_utc": (now - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "expires_utc": (now + timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "nonce": "c" * 64,
    }
    for key in gate.EVIDENCE_KEYS:
        document[key] = "d" * 64
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    sig = private.sign(gate._canonical(document))
    return document, public, sig, hashlib.sha256(public).hexdigest()


def test_signed_offline_attestation_can_pass_but_never_grants_live_permissions():
    doc, pub, sig, pin = signed_fixture()
    result = gate.verify_signed_offline_review(
        doc, signing_public_key=pub, signature=sig,
        pinned_public_key_sha256=pin, now=FIXED,
    )
    assert result.offline_document_verified is True
    assert result.release_status == "OFFLINE_SIGNED_EVIDENCE_ONLY_EXTERNAL_HOLDS"
    assert result.live_provider_requests_authorized is False
    assert result.independently_verified_zero_spend is False
    assert result.independently_verified_storage_rights is False
    assert result.independently_verified_provider_accounts is False


@pytest.mark.parametrize("mutate", [
    lambda x: x.update({"source_relative_path": "data/research.sqlite"}),
    lambda x: x.update({"source_type": "RESEARCH"}),
    lambda x: x.update({"repository": "someone-else/repo"}),
    lambda x: x.update({"provider_targets": [list(gate.PROVIDERS[0])]}),
    lambda x: x.update({"max_signed_requests": 6}),
    lambda x: x.update({"max_signed_requests": True}),
    lambda x: x.update({"max_source_bytes": 1024 * 1024 * 1024}),
    lambda x: x.update({"nonce": "bad"}),
    lambda x: x.update({"extra_credential": "SECRET"}),
    lambda x: x.pop("source_rights_review_sha256"),
    lambda x: x.update({"offhost_disaster_restore_drill_sha256": "fake"}),
    lambda x: x.update({"candidate_head": "b" * 40}),
])
def test_invalid_or_misscoped_evidence_fails_closed(mutate):
    doc, pub, sig, pin = signed_fixture()
    mutate(doc)
    with pytest.raises(gate.ReleaseEvidenceRejected):
        gate.verify_signed_offline_review(
            doc, signing_public_key=pub, signature=sig,
            pinned_public_key_sha256=pin, now=FIXED,
        )


def test_signature_tamper_and_unpinned_key_fail():
    doc, pub, sig, pin = signed_fixture()
    doc["nonce"] = "e" * 64
    with pytest.raises(gate.ReleaseEvidenceRejected, match="signature"):
        gate.verify_signed_offline_review(
            doc, signing_public_key=pub, signature=sig,
            pinned_public_key_sha256=pin, now=FIXED,
        )
    doc, pub, sig, pin = signed_fixture()
    with pytest.raises(gate.ReleaseEvidenceRejected, match="signing identity"):
        gate.verify_signed_offline_review(
            doc, signing_public_key=pub, signature=sig,
            pinned_public_key_sha256="0" * 64, now=FIXED,
        )


@pytest.mark.parametrize("offsets", [
    (timedelta(days=-9), timedelta(days=-8)),   # expired
    (timedelta(minutes=2), timedelta(hours=1)), # not yet issued
    (timedelta(days=-1), timedelta(days=8)),    # excessive window
    (timedelta(days=1), timedelta(hours=-1)),   # impossible
])
def test_signed_time_window_does_not_authorize_invalid_review(offsets):
    doc, pub, _, pin = signed_fixture()
    a, b = offsets
    doc["issued_utc"] = (FIXED + a).strftime("%Y-%m-%dT%H:%M:%SZ")
    doc["expires_utc"] = (FIXED + b).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(gate.ReleaseEvidenceRejected):
        gate.validate_document(doc, now=FIXED)


def test_unconditional_live_prohibition():
    with pytest.raises(gate.ReleaseEvidenceRejected, match="disabled"):
        gate.block_unattested_live_backup()


def test_release_gate_source_has_no_network_data_or_credential_entrypoint():
    src = inspect.getsource(gate)
    parsed = ast.parse(src)
    imported = set()
    for stmt in parsed.body:
        if isinstance(stmt, ast.Import):
            imported.update(x.name.split(".")[0] for x in stmt.names)
        if isinstance(stmt, ast.ImportFrom) and stmt.module:
            imported.add(stmt.module.split(".")[0])
    assert imported.isdisjoint({
        "boto3", "botocore", "requests", "socket", "urllib", "sqlite3",
        "subprocess", "os", "pathlib",
    })
    assert 'if __name__ == "__main__"' not in src
    assert "live_provider_requests_authorized=False" in src
