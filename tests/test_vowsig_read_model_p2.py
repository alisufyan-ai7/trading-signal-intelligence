"""P2 source-bundle fails closed on mismatch, extra keys and partial population."""
from __future__ import annotations

import copy
import hashlib
import json

import pytest

from trading_signal_intelligence.product.accounts.read_model import (
    ReadModelValidationError, check_sanitized_bundle,
)

SOURCE = "e"*64


def manifest():
    return {
        "schema_version": 1,
        "source_program_id": "core-ai-shadow", "model_version": "AI-v1.1",
        "cohort": "forward-shadow", "source_head_hash": SOURCE,
        "records": [{
            "program_id": "core-ai-shadow", "model_version": "AI-v1.1",
            "cohort": "forward-shadow", "entity_id": "abc",
            "source_record_sha256": "d"*64, "state": "closed",
            "combined_net_r": -1.0, "after_costs_verified": True,
            "cost_model_version": "cost-v1", "exit_at_utc": "2026-11-03T00:00:00Z",
        }],
    }


def load(doc=None, count=1, head=SOURCE, digest=None):
    b=json.dumps(manifest() if doc is None else doc, sort_keys=True).encode()
    return check_sanitized_bundle(
        b, pinned_artifact_sha256=digest or hashlib.sha256(b).hexdigest(),
        expected_source_records=count, pinned_source_head_hash=head,
    )


def test_exact_hash_and_source_count_verification_is_not_release_attestation():
    b=load()
    assert b.record_count==1 and b.source_program_id=="core-ai-shadow"
    assert b.source_ledger_independently_reconciled is False
    assert b.customer_signal_publication_permitted is False


@pytest.mark.parametrize("case", [
    "extra_field", "secret", "duplicate", "mixed_market",
    "missing", "version", "unsafe_program", "wrong_head",
])
def test_reject_untrusted_or_incomplete_source_artifacts(case):
    m=manifest()
    if case=="extra_field":m["bad"]="untrusted"
    if case=="secret":m["records"][0]["provider_key"]="NOT_ALLOWED"
    if case=="duplicate":m["records"].append(copy.deepcopy(m["records"][0]))
    if case=="mixed_market":m["records"][0]["program_id"]="crypto-expansion-1"
    if case=="missing":m["records"]=[]
    if case=="version":m["schema_version"]=99
    if case=="unsafe_program":m["source_program_id"]="unknown"
    if case=="wrong_head":m["source_head_hash"]="f"*64
    with pytest.raises(ReadModelValidationError):
        load(m)


def test_source_count_and_externally_pinned_artifact_hash_required():
    with pytest.raises(ReadModelValidationError):
        load(count=2)
    with pytest.raises(ReadModelValidationError):
        load(digest="b"*64)
    with pytest.raises(ReadModelValidationError):
        load(head="f"*64)


def test_commercial_crypto_population_cannot_turn_into_customer_signal_release():
    m=manifest()
    m["source_program_id"]="crypto-expansion-1"
    m["model_version"]="AI-v1.3"
    m["records"][0]["program_id"]="crypto-expansion-1"
    m["records"][0]["model_version"]="AI-v1.3"
    b=load(m)
    assert b.source_program_id=="crypto-expansion-1"
    assert b.customer_signal_publication_permitted is False


@pytest.mark.parametrize("state", ["NaN","Infinity","-Infinity"])
def test_nonfinite_json_literals_rejected_even_when_bytes_are_hash_pinned(state):
    valid=json.dumps(manifest(),sort_keys=True)
    forged=valid.replace("-1.0",state)
    raw=forged.encode()
    with pytest.raises(ReadModelValidationError):
        check_sanitized_bundle(
            raw,pinned_artifact_sha256=hashlib.sha256(raw).hexdigest(),
            expected_source_records=1,pinned_source_head_hash=SOURCE,
        )


def test_duplicate_json_keys_rejected_even_when_digest_matches():
    s=json.dumps(manifest(),sort_keys=True)
    duplicate=s.replace('"schema_version": 1,','"schema_version": 1, "schema_version": 99,')
    raw=duplicate.encode()
    with pytest.raises(ReadModelValidationError,match="Invalid JSON"):
        check_sanitized_bundle(
            raw,pinned_artifact_sha256=hashlib.sha256(raw).hexdigest(),
            expected_source_records=1,pinned_source_head_hash=SOURCE,
        )


@pytest.mark.parametrize("case", [
    {"combined_net_r":None},
    {"combined_net_r":True},
    {"combined_net_r":"1.0"},
    {"after_costs_verified":False},
    {"exit_at_utc":None},
    {"cost_model_version":None},
])
def test_closed_facts_require_exact_utc_after_cost_combined_r(case):
    m=manifest()
    m["records"][0].update(case)
    with pytest.raises(ReadModelValidationError):
        load(m)


def test_nonclosed_records_must_have_no_realized_net_r():
    m=manifest()
    m["records"][0]["state"]="open"
    with pytest.raises(ReadModelValidationError):
        load(m)
    m["records"][0].update({
        "combined_net_r":None,"exit_at_utc":None,
        "after_costs_verified":False,"cost_model_version":None,
    })
    out=load(m)
    assert out.record_count==1
    assert out.source_ledger_independently_reconciled is False
