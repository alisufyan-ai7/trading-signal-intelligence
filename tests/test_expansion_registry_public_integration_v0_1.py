"""Offline-only cross-surface guard checks for prospective V1.2.1 registry correction."""
from __future__ import annotations

import copy
import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from trading_signal_intelligence.product import expansion_registry_compat_v0_1 as compat

ROOT = Path(__file__).resolve().parents[1]
NOW = datetime(2026, 10, 10, 16, 5, 9, tzinfo=timezone.utc)


def _load(name: str, path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / path)
    assert spec and spec.loader
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def _base_programs():
    return [
        {"schema_version": 1, "program_id": "core-ai-shadow", "mode": "SHADOW_ONLY",
         "health": {"healthy": True, "broker_execution_disabled": True}},
        {"schema_version": 1, "program_id": "market-expansion-1", "mode": "SHADOW_ONLY",
         "health": {"healthy": True, "broker_execution_disabled": True}},
    ]


def _proof():
    return {
        "schema_version": 1,
        "status": "prospective_exact_registry_compatibility",
        "historic_activation_artifacts_valid": False,
        "historic_registry_sha256": compat.HISTORIC_CRLF_SHA256,
        "current_registry_sha256": compat.CURRENT_CRLF_SHA256,
        "additive_git_commit": compat.ADDITION_COMMIT,
        "added_symbols": ["ETHUSDT", "SOLUSDT"],
        "unchanged_frozen_artifacts_verified": 33,
    }


def _candidate():
    programs = _base_programs()
    programs[1]["registry_compatibility"] = _proof()
    programs[1]["health"].update({
        "historic_activation_artifacts_valid": False,
        "operational_compatibility_valid": True,
    })
    return {
        "generated_at_utc": NOW.isoformat(),
        "validation_programs": programs,
    }


def _patch_external_validators(monkeypatch):
    from trading_signal_intelligence.product import cloud_app
    monkeypatch.setattr(cloud_app, "_validate_snapshot", lambda payload: None)
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import push_public_snapshot
    monkeypatch.setattr(push_public_snapshot, "_validate_snapshot_for_push", lambda _: None)


def test_published_compatibility_is_separate_and_explicit(monkeypatch):
    _patch_external_validators(monkeypatch)
    guard = _load("registry_guard", "guarded_product_publish_v0_1.py")
    guard.validate_candidate(_candidate(), NOW)


@pytest.mark.parametrize("spoof", [
    "other_added_symbols", "unknown_commit", "forged_historical_pass",
    "wrong_latest_hash", "missing_public_health", "missing_certificate_field",
    "wrong_original_hash", "wrong_artifact_count",
])
def test_guard_rejects_unproven_public_registry_exception(monkeypatch, spoof):
    _patch_external_validators(monkeypatch)
    guard = _load("registry_guard_tamper", "guarded_product_publish_v0_1.py")
    payload = _candidate()
    proof = payload["validation_programs"][1]["registry_compatibility"]
    if spoof == "other_added_symbols":
        proof["added_symbols"].append("UNAUTHORIZED")
    elif spoof == "unknown_commit":
        proof["additive_git_commit"] = "0" * 40
    elif spoof == "forged_historical_pass":
        proof["historic_activation_artifacts_valid"] = True
    elif spoof == "wrong_latest_hash":
        proof["current_registry_sha256"] = "0" * 64
    elif spoof == "missing_public_health":
        payload["validation_programs"][1]["health"]["operational_compatibility_valid"] = False
    elif spoof == "missing_certificate_field":
        del proof["unchanged_frozen_artifacts_verified"]
    elif spoof == "wrong_original_hash":
        proof["historic_registry_sha256"] = "0" * 64
    elif spoof == "wrong_artifact_count":
        proof["unchanged_frozen_artifacts_verified"] = 32
    with pytest.raises(guard.PublicationHeld, match="registry"):
        guard.validate_candidate(payload, NOW)


def test_guarded_full_uses_proven_current_base_and_verified_crypto(monkeypatch):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    full = _load("attested_three_program", "export_guarded_full_v0_1.py")
    monkeypatch.setattr(full, "build_core_expansion_snapshot", lambda _: _candidate())
    monkeypatch.setattr(full, "crypto_activation_state", lambda _: {
        "any_state": True, "complete_shape": True,
    })
    monkeypatch.setattr(full, "_verify_crypto_validation_adapter_source", lambda _: None)
    crypto = {
        "program_id": "crypto-expansion-1",
        "public_signal_exposure": False,
        "health": {"healthy": True},
    }
    monkeypatch.setattr(
        full, "build_crypto_public_validation_program", lambda *_a, **_k: crypto
    )
    payload = full.build_guarded_full_snapshot(ROOT)
    assert [x["program_id"] for x in payload["validation_programs"]] == [
        "core-ai-shadow", "market-expansion-1", "crypto-expansion-1"
    ]
    assert payload["validation_programs"][1]["registry_compatibility"] == _proof()


@pytest.mark.parametrize("scenario", ["crypto_bad", "activation_missing", "signals_enabled"])
def test_three_program_export_fails_closed_without_good_crypto(monkeypatch, scenario):
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    full = _load("attested_three_program_bad", "export_guarded_full_v0_1.py")
    monkeypatch.setattr(full, "build_core_expansion_snapshot", lambda _: _candidate())
    monkeypatch.setattr(full, "crypto_activation_state", lambda _: {
        "any_state": scenario != "activation_missing",
        "complete_shape": scenario != "activation_missing",
    })
    monkeypatch.setattr(full, "_verify_crypto_validation_adapter_source", lambda _: None)
    monkeypatch.setattr(full, "build_crypto_public_validation_program", lambda *_a, **_k: {
        "program_id": "crypto-expansion-1",
        "public_signal_exposure": scenario == "signals_enabled",
        "health": {"healthy": scenario != "crypto_bad"},
    })
    with pytest.raises(RuntimeError):
        full.build_guarded_full_snapshot(ROOT)
