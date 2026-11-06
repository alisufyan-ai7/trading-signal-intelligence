"""No real trading data. Independent Ed25519 audit manifest and full-row proof.

Test-only signer keys are ephemeral; never used for source release.
"""
from __future__ import annotations

import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat,
)
from trading_signal_intelligence.product.accounts.verified_history import (
    HistoryAttestationError, _canonical, outcome_population_sha256,
    reconcile_attested_history, verify_signed_history_attestation,
)

STAMP = "2026-10-04T12:00:00Z"
SOURCE = "c" * 64
HEAD = "d" * 64
PROOF = "e" * 64


def sample_facts():
    return [
        {"entity_id": "loss", "source_record_sha256": "b"*64,
         "state": "closed", "combined_net_r": -1.0,
         "exit_at_utc": "2026-10-05T12:00:00Z",
         "cost_model_version": "after-cost-v1",
         "after_costs_verified": True, "cohort": "forward-shadow"},
        {"entity_id": "win", "source_record_sha256": "a"*64,
         "state": "closed", "combined_net_r": 2.0,
         "exit_at_utc": STAMP, "cost_model_version": "after-cost-v1",
         "after_costs_verified": True, "cohort": "forward-shadow"},
        {"entity_id": "no-trade", "source_record_sha256": "f"*64,
         "state": "no_trade", "combined_net_r": None,
         "exit_at_utc": None, "cost_model_version": None,
         "after_costs_verified": False, "cohort": "forward-shadow"},
    ]


def sample_attestation(facts):
    return {
        "schema_version": 1,
        "source_program_id": "core-ai-shadow",
        "model_version": "AI-v1.1",
        "cohort": "forward-shadow",
        "source_snapshot_sha256": SOURCE,
        "source_head_hash": HEAD,
        "expected_population_count": 3,
        "expected_closed_count": 2,
        "outcome_population_sha256": outcome_population_sha256(facts),
        "source_evidence_sha256": PROOF,
        "source_rights_approved": True,
        "independent_source_reconciliation": True,
        "reviewer_id": "independent-ledger-auditor-1",
        "verified_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "window_start_utc": "2026-10-01T00:00:00Z",
        "window_end_utc": "2026-10-31T23:59:59Z",
        "as_of_utc": "2026-11-01T00:00:00Z",
        "cost_model_version": "after-cost-v1",
    }


def signer():
    private = Ed25519PrivateKey.generate()
    public = private.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    return private, public


def signed(private, payload):
    sig = private.sign(_canonical(payload))
    return _canonical({
        "attestation": payload,
        "signature_ed25519_b64u": base64.urlsafe_b64encode(sig).decode().rstrip("="),
    })


def snapshot():
    return {
        "source_program_id": "core-ai-shadow",
        "model_version": "AI-v1.1",
        "source_snapshot_sha256": SOURCE,
        "source_head_hash": HEAD,
        "ingest_status": "verified",
        "completeness_verified": True,
    }


def test_valid_signed_independent_source_and_exact_full_population():
    facts = sample_facts()
    private, public = signer()
    attested = verify_signed_history_attestation(
        signed(private, sample_attestation(facts)), reviewer_public_key_pem=public,
    )
    report = reconcile_attested_history(attested, snapshot=snapshot(), facts=facts)
    assert report["verified_full_history"] is False
    assert report["verified_full_cohort_history"] is True
    assert report["platform_history_population_reconciled"] is False
    assert report["source_ledger_independently_reconciled"] is True
    metric = report["performance"]
    assert metric["completed_count"] == 2
    assert metric["total_outcomes"] == 3
    assert metric["no_trade_count"] == 1
    assert metric["sum_completed_net_r"] == pytest.approx(1.0)
    assert metric["win_rate"] == pytest.approx(0.5)
    assert metric["max_normalized_r_drawdown"] == pytest.approx(1.0)
    assert metric["real_execution_pnl_available"] is False
    assert report["research_only"] is True


@pytest.mark.parametrize("change", [
    ("source_rights_approved", False),
    ("independent_source_reconciliation", False),
    ("source_snapshot_sha256", "wrong"),
    ("expected_population_count", 0),
    ("expected_closed_count", 99),
    ("verified_at_utc", "2031-01-01T00:00:00Z"),
    ("cost_model_version", ""),
])
def test_reject_bad_attestation_even_when_signature_is_valid(change):
    facts = sample_facts()
    private, pub = signer()
    manifest = sample_attestation(facts)
    manifest[change[0]] = change[1]
    with pytest.raises(HistoryAttestationError):
        verify_signed_history_attestation(
            signed(private, manifest), reviewer_public_key_pem=pub,
        )


def test_valid_reviewer_signature_wrong_population_digest_fails_on_reconciliation():
    facts=sample_facts()
    private,pub=signer()
    manifest=sample_attestation(facts)
    manifest["outcome_population_sha256"]="0"*64
    body=verify_signed_history_attestation(
        signed(private,manifest),reviewer_public_key_pem=pub,
    )
    with pytest.raises(HistoryAttestationError, match="digest mismatch"):
        reconcile_attested_history(body,snapshot=snapshot(),facts=facts)


def test_unsigned_modified_or_wrong_reviewer_document_rejected():
    private, pub = signer()
    _, wrong_pub = signer()
    manifest = sample_attestation(sample_facts())
    raw = signed(private, manifest)
    with pytest.raises(HistoryAttestationError):
        verify_signed_history_attestation(raw, reviewer_public_key_pem=wrong_pub)
    envelope = json.loads(raw)
    envelope["attestation"]["expected_closed_count"] = 1
    with pytest.raises(HistoryAttestationError):
        verify_signed_history_attestation(_canonical(envelope), reviewer_public_key_pem=pub)
    with pytest.raises(HistoryAttestationError):
        verify_signed_history_attestation(b"{}", reviewer_public_key_pem=pub)
    with pytest.raises(HistoryAttestationError):
        verify_signed_history_attestation(
            raw.replace(b'"schema_version":1', b'"schema_version":1,"schema_version":1'),
            reviewer_public_key_pem=pub,
        )


@pytest.mark.parametrize("field,value", [
    ("source_head_hash", "wrong"),
    ("ingest_status", "quarantined"),
    ("completeness_verified", False),
    ("source_snapshot_sha256", "0"*64),
])
def test_database_flags_and_source_anchors_are_independently_required(field, value):
    facts = sample_facts()
    att = sample_attestation(facts)
    db = snapshot()
    db[field] = value
    with pytest.raises(HistoryAttestationError):
        reconcile_attested_history(att, snapshot=db, facts=facts)


def test_hash_count_outcome_and_cost_mismatch_fail_closed():
    base = sample_facts()
    att = sample_attestation(base)
    versions = [
        base[:2],
        [{**base[0], "combined_net_r": -1.1}, *base[1:]],
        [{**base[0], "source_record_sha256": "0"*64}, *base[1:]],
        [{**base[0], "state": "open", "exit_at_utc": None,
          "combined_net_r": None, "after_costs_verified": False,
          "cost_model_version": None}, *base[1:]],
        [{**base[0], "cohort": "another"}, *base[1:]],
        [base[0], base[0], base[2]],
    ]
    for version in versions:
        with pytest.raises(HistoryAttestationError):
            reconcile_attested_history(att, snapshot=snapshot(), facts=version)


def test_historical_net_r_cannot_be_claimed_without_reviewed_cost_model():
    facts = sample_facts()
    facts[0]["after_costs_verified"] = False
    manifest = sample_attestation(facts)
    with pytest.raises(HistoryAttestationError):
        reconcile_attested_history(manifest, snapshot=snapshot(), facts=facts)


def test_hash_is_order_independent_and_immutable_to_result_changes():
    a = sample_facts()
    assert outcome_population_sha256(a) == outcome_population_sha256(list(reversed(a)))
    b = deepcopy(a)
    b[0]["combined_net_r"] = -2.0
    assert outcome_population_sha256(a) != outcome_population_sha256(b)
