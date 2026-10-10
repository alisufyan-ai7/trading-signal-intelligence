"""Offline prospective registry-compatibility correction tests: no network or production mutations."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from trading_signal_intelligence.product import expansion_registry_compat_v0_1 as compat


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def fixture_registry(monkeypatch, tmp_path):
    """Create synthetic standalone prior/current Git bytes and a local CRLF checkout."""
    old = {
        "schema_version": 1,
        "notes": ["historical cleared source rights"],
        "instruments": [
            {"canonical": "EUR/USD", "asset_class": "forex",
             "sources": {"exness_mt5_demo": {"symbol": "EURUSD", "status": "include"}}},
            {"canonical": "XAG/USD", "asset_class": "metal",
             "sources": {"exness_mt5_demo": {"symbol": "XAGUSD", "status": "include"}}},
        ],
    }
    new = copy.deepcopy(old)
    new["instruments"][1:1] = copy.deepcopy(compat.ADDITIONS)

    lf_old = (json.dumps(old, indent=2) + "\n").encode("utf-8")
    lf_new = (json.dumps(new, indent=2) + "\n").encode("utf-8")
    def crlf(raw):
        return raw.replace(b"\n", b"\r\n")
    monkeypatch.setattr(compat, "HISTORIC_LF_SHA256", digest(lf_old))
    monkeypatch.setattr(compat, "HISTORIC_CRLF_SHA256", digest(crlf(lf_old)))
    monkeypatch.setattr(compat, "CURRENT_LF_SHA256", digest(lf_new))
    monkeypatch.setattr(compat, "CURRENT_CRLF_SHA256", digest(crlf(lf_new)))
    git_bytes = {
        compat.HISTORICAL_COMMIT: lf_old,
        compat.ADDITION_COMMIT: lf_new,
        "HEAD": lf_new,
    }
    monkeypatch.setattr(compat, "_git_file", lambda _root, ref: git_bytes[ref])
    local = tmp_path / "config" / "instruments.json"
    local.parent.mkdir()
    local.write_bytes(crlf(lf_new))
    return git_bytes, local, old, new


def report():
    return {
        "runtime_version": "AI-v1.2.1",
        "decision_protocol_version": "AI-v1.0",
        "protocol_version": "AI-v1.0",
        "health": {
            "healthy": False,
            "expansion_artifacts_valid": False,
            "ledgers_valid": True,
            "activation_anchor_upstream_valid": True,
            "scheduler_healthy": True,
            "public_exposure_disabled": True,
            "broker_execution_disabled": True,
        },
        "activation": {
            "artifact_verification": {
                "valid": False,
                "checked": 34,
                "mismatches": {
                    "instrument_registry": {
                        "expected": compat.HISTORIC_CRLF_SHA256,
                        "actual": compat.CURRENT_CRLF_SHA256,
                    },
                },
            },
        },
        "markets": {
            name: {"ledger_verification": {"valid": True}, "activation_anchor_match": True}
            for name in ("EURUSD", "XAGUSD", "USOIL")
        },
        "totals": {"valid_inferences": 10},
        "gates": {},
    }


def test_exact_additive_current_crlf_attested_and_historic_failure_preserved(monkeypatch, tmp_path):
    fixture_registry(monkeypatch, tmp_path)
    evidence = report()
    before = copy.deepcopy(evidence)
    proof = compat.prove_expansion_compatibility(tmp_path, evidence)
    assert proof["historic_activation_artifacts_valid"] is False
    assert proof["added_symbols"] == ["ETHUSDT", "SOLUSDT"]
    assert proof["unchanged_frozen_artifacts_verified"] == 33
    public = compat.build_compatibility_qualified_program(tmp_path, evidence)
    assert public["program_id"] == "market-expansion-1"
    assert public["health"]["healthy"] is True  # prospective product health only
    assert public["health"]["historic_activation_artifacts_valid"] is False
    assert public["health"]["operational_compatibility_valid"] is True
    assert public["registry_compatibility"] == proof
    assert evidence == before             # immutable historic report untouched
    assert evidence["health"]["healthy"] is False


@pytest.mark.parametrize("health_key", [
    "ledgers_valid", "activation_anchor_upstream_valid", "scheduler_healthy",
    "public_exposure_disabled", "broker_execution_disabled",
])
def test_other_failed_health_flag_blocks_exception(monkeypatch, tmp_path, health_key):
    fixture_registry(monkeypatch, tmp_path)
    bad = report()
    bad["health"][health_key] = False
    with pytest.raises(compat.CompatibilityRejected):
        compat.prove_expansion_compatibility(tmp_path, bad)


@pytest.mark.parametrize("invalidity", [
    "extra_mismatch", "no_mismatch", "wrong_expected", "wrong_actual",
    "wrong_artifact_count", "unexpected_runtime", "healthy_already",
    "ledger_corrupt", "anchor_mismatch", "extra_market", "frozen_verifier_valid",
])
def test_frozen_artifact_evidence_cannot_be_downgraded(monkeypatch, tmp_path, invalidity):
    fixture_registry(monkeypatch, tmp_path)
    bad = report()
    verification = bad["activation"]["artifact_verification"]
    match = verification["mismatches"]["instrument_registry"]
    if invalidity == "extra_mismatch":
        verification["mismatches"]["runtime_verifier_source"] = {
            "expected": "older", "actual": "newer",
        }
    elif invalidity == "no_mismatch":
        verification["mismatches"] = {}
    elif invalidity == "wrong_expected":
        match["expected"] = "wrong"
    elif invalidity == "wrong_actual":
        match["actual"] = "wrong"
    elif invalidity == "wrong_artifact_count":
        verification["checked"] = 35
    elif invalidity == "unexpected_runtime":
        bad["runtime_version"] = "AI-v1.3"
    elif invalidity == "healthy_already":
        bad["health"]["healthy"] = True
    elif invalidity == "ledger_corrupt":
        bad["markets"]["XAGUSD"]["ledger_verification"]["valid"] = False
    elif invalidity == "anchor_mismatch":
        bad["markets"]["USOIL"]["activation_anchor_match"] = False
    elif invalidity == "extra_market":
        bad["markets"]["SOLUSDT"] = {
            "ledger_verification": {"valid": True}, "activation_anchor_match": True
        }
    elif invalidity == "frozen_verifier_valid":
        verification["valid"] = True
    with pytest.raises(compat.CompatibilityRejected):
        compat.prove_expansion_compatibility(tmp_path, bad)


def test_future_local_edit_is_not_whitelisted(monkeypatch, tmp_path):
    _, local, _, _ = fixture_registry(monkeypatch, tmp_path)
    local.write_bytes(local.read_bytes() + b" ")
    with pytest.raises(compat.CompatibilityRejected, match="live registry"):
        compat.prove_expansion_compatibility(tmp_path, report())


def test_unapproved_git_history_is_not_whitelisted(monkeypatch, tmp_path):
    git_bytes, _, _, _ = fixture_registry(monkeypatch, tmp_path)
    git_bytes["HEAD"] = git_bytes[compat.HISTORICAL_COMMIT]
    with pytest.raises(compat.CompatibilityRejected, match="Git history"):
        compat.prove_expansion_compatibility(tmp_path, report())


def test_historic_registry_edit_even_with_recomputed_hashes_fails(monkeypatch, tmp_path):
    git_bytes, _, old, new = fixture_registry(monkeypatch, tmp_path)
    new["instruments"][0]["canonical"] = "CHANGED"
    replacement = (json.dumps(new, indent=2) + "\n").encode()
    git_bytes["HEAD"] = replacement
    git_bytes[compat.ADDITION_COMMIT] = replacement
    monkeypatch.setattr(compat, "CURRENT_LF_SHA256", digest(replacement))
    monkeypatch.setattr(
        compat, "CURRENT_CRLF_SHA256", digest(replacement.replace(b"\n", b"\r\n"))
    )
    (tmp_path / "config/instruments.json").write_bytes(
        replacement.replace(b"\n", b"\r\n")
    )
    # Even if hostile input supplies internally self-consistent new hashes,
    # semantic historical instrument preservation must still be proven.
    modified_report = report()
    modified_report["activation"]["artifact_verification"]["mismatches"][
        "instrument_registry"
    ]["actual"] = compat.CURRENT_CRLF_SHA256
    with pytest.raises(compat.CompatibilityRejected, match="non-additive"):
        compat.prove_expansion_compatibility(tmp_path, modified_report)


def test_unrecognized_future_addition_is_not_approved(monkeypatch, tmp_path):
    git_bytes, local, _, current = fixture_registry(monkeypatch, tmp_path)
    current["instruments"].append({"canonical": "UNAPPROVED"})
    future = (json.dumps(current, indent=2) + "\n").encode()
    git_bytes["HEAD"] = future
    git_bytes[compat.ADDITION_COMMIT] = future
    monkeypatch.setattr(compat, "CURRENT_LF_SHA256", digest(future))
    monkeypatch.setattr(compat, "CURRENT_CRLF_SHA256", digest(
        future.replace(b"\n", b"\r\n")
    ))
    local.write_bytes(future.replace(b"\n", b"\r\n"))
    evidence = report()
    evidence["activation"]["artifact_verification"]["mismatches"][
        "instrument_registry"
    ]["actual"] = compat.CURRENT_CRLF_SHA256
    with pytest.raises(compat.CompatibilityRejected, match="non-additive"):
        compat.prove_expansion_compatibility(tmp_path, evidence)


def test_missing_pinned_git_object_rejected(monkeypatch, tmp_path):
    fixture_registry(monkeypatch, tmp_path)
    def unavailable(*_):
        raise compat.CompatibilityRejected("pinned Git registry object not available")
    monkeypatch.setattr(compat, "_git_file", unavailable)
    with pytest.raises(compat.CompatibilityRejected, match="Git"):
        compat.prove_expansion_compatibility(tmp_path, report())


def test_compatibility_never_qualifies_an_already_healthy_report(monkeypatch, tmp_path):
    fixture_registry(monkeypatch, tmp_path)
    normal = report()
    normal["health"]["healthy"] = True
    with pytest.raises(compat.CompatibilityRejected):
        compat.build_compatibility_qualified_program(tmp_path, normal)
