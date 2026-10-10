"""Offline only: strict public schema, separate operational proof and full guarded export."""
from __future__ import annotations

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
         "title": "Core AI Shadow Validation",
         "health": {"healthy": True, "broker_execution_disabled": True}},
        {"schema_version": 1, "program_id": "market-expansion-1", "mode": "SHADOW_ONLY",
         "title": compat.PUBLIC_TITLE,
         "health": {"healthy": True, "broker_execution_disabled": True}},
    ]


def _candidate():
    return {
        "generated_at_utc": NOW.isoformat(),
        "validation_programs": _base_programs(),
    }


def _patch_external_validators(monkeypatch):
    from trading_signal_intelligence.product import cloud_app
    monkeypatch.setattr(cloud_app, "_validate_snapshot", lambda _: None)
    monkeypatch.syspath_prepend(str(ROOT / "scripts"))
    import push_public_snapshot
    monkeypatch.setattr(push_public_snapshot, "_validate_snapshot_for_push", lambda _: None)


def test_schema_v1_is_unmodified_and_product_health_has_no_extra_fields(monkeypatch):
    _patch_external_validators(monkeypatch)
    guard = _load("registry_guard", "guarded_product_publish_v0_1.py")
    payload = _candidate()
    guard.validate_candidate(payload, NOW)
    assert "registry_compatibility" not in payload["validation_programs"][1]
    schema = json.loads((ROOT / "config/public_validation_program_schema_v1.json").read_text())
    assert schema["additionalProperties"] is False
    assert schema["properties"]["health"]["additionalProperties"] is False


@pytest.mark.parametrize("invalidity", [
    "unregistered_certificate", "unknown_health_field", "healthy_false",
])
def test_public_program_rejects_unsafe_schema_or_health(monkeypatch, invalidity):
    _patch_external_validators(monkeypatch)
    guard = _load("registry_guard_bad", "guarded_product_publish_v0_1.py")
    payload = _candidate()
    row = payload["validation_programs"][1]
    if invalidity == "unregistered_certificate":
        row["registry_compatibility"] = {"unreviewed": True}
    elif invalidity == "unknown_health_field":
        row["health"]["operational_compatibility_valid"] = True
    elif invalidity == "healthy_false":
        row["health"]["healthy"] = False
    with pytest.raises(guard.PublicationHeld):
        guard.validate_candidate(payload, NOW)


def test_guard_rechecks_real_original_report_before_compatibility_publication(monkeypatch):
    _patch_external_validators(monkeypatch)
    guard = _load("registry_guard_recheck", "guarded_product_publish_v0_1.py")
    from trading_signal_intelligence.ai_v1 import observability_v1_2_1
    observed = []
    monkeypatch.setattr(observability_v1_2_1, "build_report_v1_2_1",
        lambda root, **kwargs: {"historical_artifacts_valid": False})
    monkeypatch.setattr(compat, "prove_expansion_compatibility",
        lambda root, original: observed.append((root, original)))
    guard._verify_current_expansion_claim(ROOT, _candidate())
    assert len(observed) == 1
    assert observed[0][1]["historical_artifacts_valid"] is False


def test_guard_holds_when_recheck_does_not_prove_historical_exception(monkeypatch):
    _patch_external_validators(monkeypatch)
    guard = _load("registry_guard_recheck_fail", "guarded_product_publish_v0_1.py")
    from trading_signal_intelligence.ai_v1 import observability_v1_2_1
    monkeypatch.setattr(observability_v1_2_1, "build_report_v1_2_1",
        lambda root, **kwargs: {"historical_artifacts_valid": False})
    def reject(*args):
        raise compat.CompatibilityRejected("unexpected new registry")
    monkeypatch.setattr(compat, "prove_expansion_compatibility", reject)
    with pytest.raises(guard.PublicationHeld, match="proof changed"):
        guard._verify_current_expansion_claim(ROOT, _candidate())


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
    assert payload["validation_programs"][1]["title"] == compat.PUBLIC_TITLE


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
