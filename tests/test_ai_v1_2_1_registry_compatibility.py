from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

import trading_signal_intelligence.ai_v1.runtime_verifier_registry_compat_v1_2_1 as compat_runtime
from trading_signal_intelligence.ai_v1.observability_v1_2_1 import (
    verify_expansion_artifacts_v1_2_1,
)
from trading_signal_intelligence.ai_v1.registry_compat_v1_2_1 import (
    RegistryCompatibilityV121Error,
    load_registry_compatibility_manifest,
    validate_registry_transition,
    verify_expansion_artifacts_registry_compat_v1_2_1,
    verify_registry_compatibility_v1_2_1,
)

ROOT = Path(__file__).resolve().parents[1]
ANCHOR = (
    ROOT
    / "research"
    / "forward"
    / "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
)
FROZEN_REGISTRY_COMMIT = "4056a0a762135bfd37725474d41dc49d0a116eaa"
FROZEN_REGISTRY_SHA256 = (
    "b92b80d18f422ba012b991ca8ba5a538f9212ee2823813d29754f24a804491ca"
)
APPROVED_REGISTRY_SHA256 = (
    "f2f3d993fdd171ac43edd5234e18cfbea3eb7cf8da5dc2e6e6d4529613cd1681"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _anchor() -> dict:
    return json.loads(ANCHOR.read_text(encoding="utf-8"))


def _old_registry() -> dict:
    raw = subprocess.check_output(
        [
            "git",
            "show",
            f"{FROZEN_REGISTRY_COMMIT}:config/instruments.json",
        ],
        cwd=ROOT,
    )
    return json.loads(raw.decode("utf-8"))


def _current_registry() -> dict:
    return json.loads(
        (ROOT / "config" / "instruments.json").read_text(encoding="utf-8")
    )


def _allowed_additions() -> list[dict]:
    return load_registry_compatibility_manifest(ROOT)["allowed_additions"]


def test_original_v1_2_1_frozen_runtime_files_remain_byte_exact() -> None:
    anchor = _anchor()
    hashes = anchor["artifact_hashes"]

    assert _sha256(
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "observability_v1_2_1.py"
    ) == hashes["observability_source_v1_2_1"]
    assert _sha256(
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "runtime_verifier_v1_2_1.py"
    ) == hashes["runtime_verifier_source_v1_2_1"]
    assert _sha256(
        ROOT / "scripts" / "run_ai_v1_2_1_live.py"
    ) == hashes["live_runner_script_v1_2_1"]
    assert _sha256(
        ROOT / "scripts" / "run_ai_v1_2_1_shadow_task.cmd"
    ) == hashes["task_runner_script_v1_2_1"]


def test_manifest_pins_exact_old_to_new_registry_transition() -> None:
    manifest = load_registry_compatibility_manifest(ROOT)

    assert manifest["frozen_registry_git_commit"] == FROZEN_REGISTRY_COMMIT
    assert manifest["frozen_registry_sha256"] == FROZEN_REGISTRY_SHA256
    assert (
        manifest["approved_expanded_registry_sha256"]
        == APPROVED_REGISTRY_SHA256
    )
    assert manifest["allowed_additions"] == [
        {
            "canonical": "ETH/USDT",
            "asset_class": "crypto",
            "sources": {
                "binance_spot": {
                    "symbol": "ETHUSDT",
                    "status": "primary",
                }
            },
        },
        {
            "canonical": "SOL/USDT",
            "asset_class": "crypto",
            "sources": {
                "binance_spot": {
                    "symbol": "SOLUSDT",
                    "status": "primary",
                }
            },
        },
    ]


def test_original_artifact_verifier_sees_only_registry_mismatch() -> None:
    result = verify_expansion_artifacts_v1_2_1(ROOT, _anchor())

    assert result["valid"] is False
    assert set(result["mismatches"]) == {"instrument_registry"}
    assert result["mismatches"]["instrument_registry"] == {
        "expected": FROZEN_REGISTRY_SHA256,
        "actual": APPROVED_REGISTRY_SHA256,
    }


def test_registry_compatibility_accepts_only_current_approved_transition() -> None:
    result = verify_registry_compatibility_v1_2_1(
        ROOT,
        expected_anchor_hash=FROZEN_REGISTRY_SHA256,
        actual_registry_hash=APPROVED_REGISTRY_SHA256,
    )

    assert result["valid"] is True
    assert result["protected_preexisting_entries"] == 13
    assert result["approved_additions"] == ["ETH/USDT", "SOL/USDT"]


def test_compat_artifact_verifier_preserves_every_other_frozen_hash() -> None:
    result = verify_expansion_artifacts_registry_compat_v1_2_1(
        ROOT,
        _anchor(),
    )

    assert result["valid"] is True
    assert result["mismatches"] == {}
    assert result["compatibility_applied"] is True
    assert set(result["original_mismatches"]) == {"instrument_registry"}
    assert result["compatibility"]["valid"] is True


@pytest.mark.parametrize(
    "expected_hash,actual_hash",
    [
        ("0" * 64, APPROVED_REGISTRY_SHA256),
        (FROZEN_REGISTRY_SHA256, "0" * 64),
    ],
)
def test_registry_compatibility_rejects_unapproved_hashes(
    expected_hash: str,
    actual_hash: str,
) -> None:
    with pytest.raises(RegistryCompatibilityV121Error):
        verify_registry_compatibility_v1_2_1(
            ROOT,
            expected_anchor_hash=expected_hash,
            actual_registry_hash=actual_hash,
        )


def test_registry_transition_rejects_mutation_of_preexisting_entry() -> None:
    current = _current_registry()
    mutated = copy.deepcopy(current)
    eurusd = next(
        item for item in mutated["instruments"] if item["canonical"] == "EUR/USD"
    )
    eurusd["sources"]["exness_mt5_demo"]["digits"] = 4

    with pytest.raises(
        RegistryCompatibilityV121Error,
        match="pre-existing registry entry changed",
    ):
        validate_registry_transition(
            frozen_registry=_old_registry(),
            current_registry=mutated,
            allowed_additions=_allowed_additions(),
        )


def test_registry_transition_rejects_deletion_of_preexisting_entry() -> None:
    current = _current_registry()
    mutated = copy.deepcopy(current)
    mutated["instruments"] = [
        item
        for item in mutated["instruments"]
        if item["canonical"] != "XAG/USD"
    ]

    with pytest.raises(
        RegistryCompatibilityV121Error,
        match="pre-existing registry entry deleted",
    ):
        validate_registry_transition(
            frozen_registry=_old_registry(),
            current_registry=mutated,
            allowed_additions=_allowed_additions(),
        )


def test_registry_transition_rejects_extra_addition() -> None:
    current = _current_registry()
    mutated = copy.deepcopy(current)
    mutated["instruments"].append(
        {
            "canonical": "DOGE/USDT",
            "asset_class": "crypto",
            "sources": {
                "binance_spot": {
                    "symbol": "DOGEUSDT",
                    "status": "primary",
                }
            },
        }
    )

    with pytest.raises(
        RegistryCompatibilityV121Error,
        match="registry additions differ",
    ):
        validate_registry_transition(
            frozen_registry=_old_registry(),
            current_registry=mutated,
            allowed_additions=_allowed_additions(),
        )


def test_registry_transition_rejects_wrong_allowed_addition() -> None:
    current = _current_registry()
    mutated = copy.deepcopy(current)
    eth = next(
        item for item in mutated["instruments"] if item["canonical"] == "ETH/USDT"
    )
    eth["sources"]["binance_spot"]["status"] = "comparison_only"

    with pytest.raises(
        RegistryCompatibilityV121Error,
        match="approved registry addition differs",
    ):
        validate_registry_transition(
            frozen_registry=_old_registry(),
            current_registry=mutated,
            allowed_additions=_allowed_additions(),
        )


def test_registry_transition_rejects_top_level_metadata_change() -> None:
    current = _current_registry()
    mutated = copy.deepcopy(current)
    mutated["notes"] = [*mutated["notes"], "unauthorized note"]

    with pytest.raises(
        RegistryCompatibilityV121Error,
        match="top-level metadata changed",
    ):
        validate_registry_transition(
            frozen_registry=_old_registry(),
            current_registry=mutated,
            allowed_additions=_allowed_additions(),
        )


def _synthetic_report(*, scheduler_healthy: bool | None) -> dict:
    return {
        "runtime_version": "AI-v1.2.1",
        "decision_protocol_version": "AI-v1.0",
        "activation": {
            "anchor_file": (
                "research/forward/"
                "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
            ),
            "activated_at_utc": "2026-10-07T09:35:43.183221+00:00",
            "predecessor_runtime_version": "AI-v1.2",
            "predecessor_evidence_carry_forward": False,
            "calendar_carry_forward": False,
            "parallel_to_runtime_version": "AI-v1.1",
        },
        "health": {
            "ledgers_valid": True,
            "expansion_artifacts_valid": False,
            "activation_anchor_upstream_valid": True,
            "scheduler_healthy": scheduler_healthy,
            "public_exposure_disabled": True,
            "broker_execution_disabled": True,
        },
        "markets": {
            symbol: {
                "records": 10,
                "current_head_hash": "a" * 64,
                "counts_by_type": {
                    "ACTIVATION": 1,
                    "INFERENCE": 3,
                },
                "open_signals": 0,
            }
            for symbol in ("EURUSD", "XAGUSD", "USOIL")
        },
    }


def test_compat_runtime_verifier_does_not_bypass_scheduler_health(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    anchor_path = (
        tmp_path
        / "research"
        / "forward"
        / "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
    )
    anchor_path.parent.mkdir(parents=True)
    anchor_path.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        compat_runtime,
        "verify_active_runtime_v1_1",
        lambda *args, **kwargs: {
            "runtime_verification": "PASS",
            "broker_execution_disabled": True,
        },
    )
    monkeypatch.setattr(
        compat_runtime,
        "build_report_v1_2_1",
        lambda *args, **kwargs: _synthetic_report(scheduler_healthy=False),
    )
    monkeypatch.setattr(
        compat_runtime,
        "verify_expansion_artifacts_registry_compat_v1_2_1",
        lambda *args, **kwargs: {
            "valid": True,
            "compatibility_applied": True,
        },
    )

    with pytest.raises(
        compat_runtime.RegistryCompatibleRuntimeVerificationV121Error,
        match="scheduler unhealthy",
    ):
        compat_runtime.verify_active_runtime_registry_compat_v1_2_1(
            tmp_path,
            include_scheduler=True,
            verify_upstream=True,
        )


def test_compat_runtime_verifier_accepts_valid_registry_correction(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    anchor_path = (
        tmp_path
        / "research"
        / "forward"
        / "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
    )
    anchor_path.parent.mkdir(parents=True)
    anchor_path.write_text("{}\n", encoding="utf-8")

    monkeypatch.setattr(
        compat_runtime,
        "verify_active_runtime_v1_1",
        lambda *args, **kwargs: {
            "runtime_verification": "PASS",
            "broker_execution_disabled": True,
        },
    )
    monkeypatch.setattr(
        compat_runtime,
        "build_report_v1_2_1",
        lambda *args, **kwargs: _synthetic_report(scheduler_healthy=True),
    )
    monkeypatch.setattr(
        compat_runtime,
        "verify_expansion_artifacts_registry_compat_v1_2_1",
        lambda *args, **kwargs: {
            "valid": True,
            "compatibility_applied": True,
            "compatibility": {
                "valid": True,
                "correction_version": "AI-v1.2.1-registry-compat-v0.1",
            },
        },
    )

    result = compat_runtime.verify_active_runtime_registry_compat_v1_2_1(
        tmp_path,
        include_scheduler=True,
        verify_upstream=True,
    )

    assert result["runtime_verification"] == "PASS"
    assert result["expansion_artifacts_valid"] is True
    assert result["registry_compatibility"]["compatibility_applied"] is True
    assert result["scheduler_healthy"] is True


def test_registry_compatible_live_runner_changes_only_verifier_hook() -> None:
    original = (ROOT / "scripts" / "run_ai_v1_2_1_live.py").read_text(
        encoding="utf-8"
    )
    corrected = (
        ROOT / "scripts" / "run_ai_v1_2_1_live_registry_compat.py"
    ).read_text(encoding="utf-8")

    corrected = corrected.removeprefix(
        "# ruff: noqa: I001, TRY004, UP017, BLE001\n"
    )
    normalized = corrected.replace(
        "runtime_verifier_registry_compat_v1_2_1",
        "runtime_verifier_v1_2_1",
    ).replace(
        "verify_active_runtime_registry_compat_v1_2_1",
        "verify_active_runtime_v1_2_1",
    ).replace(
        "registry-compatible expansion shadow scan",
        "expansion shadow scan",
    )

    assert normalized == original


def test_k3_and_crypto_runtime_use_compatibility_verifier() -> None:
    activation = (ROOT / "scripts" / "activate_ai_v1_3_crypto.py").read_text(
        encoding="utf-8"
    )
    crypto_verifier = (
        ROOT
        / "src"
        / "trading_signal_intelligence"
        / "ai_v1"
        / "crypto_runtime_verifier_v1_3.py"
    ).read_text(encoding="utf-8")

    for text in (activation, crypto_verifier):
        assert "runtime_verifier_registry_compat_v1_2_1" in text
        assert "verify_active_runtime_registry_compat_v1_2_1" in text


def test_registry_compatible_task_runner_is_prepared_but_not_installed() -> None:
    runner = (
        ROOT / "scripts" / "run_ai_v1_2_1_shadow_task_registry_compat.cmd"
    ).read_text(encoding="utf-8")

    assert "run_ai_v1_2_1_live_registry_compat.py" in runner
    assert "verify_ai_v1_2_1_registry_compat_runtime.py" in runner
    assert "Register-ScheduledTask" not in runner
