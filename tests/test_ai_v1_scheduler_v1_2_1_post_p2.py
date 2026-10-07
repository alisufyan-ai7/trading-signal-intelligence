from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
POST_P2_INSTALLER = (
    ROOT / "scripts" / "install_ai_v1_2_1_shadow_task_post_p2.ps1"
)
BOUND_INSTALLER = ROOT / "scripts" / "install_ai_v1_2_1_shadow_task.ps1"
BOUND_TASK_RUNNER = ROOT / "scripts" / "run_ai_v1_2_1_shadow_task.cmd"
BOUND_LIVE_RUNNER = ROOT / "scripts" / "run_ai_v1_2_1_live.py"
ANCHOR = (
    ROOT
    / "research"
    / "forward"
    / "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_post_p2_installer_is_additive_and_preserves_bound_artifacts() -> None:
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    hashes = anchor["artifact_hashes"]

    assert _sha256(BOUND_INSTALLER) == hashes[
        "task_installer_script_v1_2_1"
    ]
    assert _sha256(BOUND_TASK_RUNNER) == hashes[
        "task_runner_script_v1_2_1"
    ]
    assert _sha256(BOUND_LIVE_RUNNER) == hashes[
        "live_runner_script_v1_2_1"
    ]


def test_post_p2_installer_uses_full_runtime_not_activation_only() -> None:
    text = POST_P2_INSTALLER.read_text(encoding="utf-8")

    assert "verify_ai_v1_2_1_runtime.py" in text
    assert "--activation-only" not in text
    assert "report_ai_v1_2_1_progress.py" in text
    assert "--skip-scheduler" in text


def test_post_p2_installer_binds_exact_p2_evidence() -> None:
    text = POST_P2_INSTALLER.read_text(encoding="utf-8")

    assert (
        "02fea7c7e9edc7b294be331acf6689b72738559e11f85125a6971610c6251f81"
        in text
    )
    assert (
        "47941806a6241bb72acffaa89705bf842db20f8e2b90ecd5c3c61ea86e103eae"
        in text
    )
    assert (
        "842d428aef53f2bd5c27b36271c54946ec214a0a9b5ab5cf2c1d873ec4502b8b"
        in text
    )
    assert "valid_inferences -ne 3" in text
    assert "errors -ne 0" in text
    assert "missed_inferences -ne 0" in text
    assert "signals -ne 2" in text
    assert "no_trade -ne 1" in text


def test_post_p2_plan_only_precedes_any_registration() -> None:
    text = POST_P2_INSTALLER.read_text(encoding="utf-8")

    plan_pos = text.index("if ($PlanOnly)")
    register_pos = text.index("Register-ScheduledTask")

    assert plan_pos < register_pos
    assert "MutationPerformed = $false" in text
    assert "MutationPerformed = $true" in text


def test_post_p2_installer_preserves_frozen_scheduler_definition() -> None:
    text = POST_P2_INSTALLER.read_text(encoding="utf-8")

    assert "run_ai_v1_2_1_shadow_task.cmd" in text
    assert "AddMinutes(3)" in text
    assert "New-TimeSpan -Hours 1" in text
    assert "-MultipleInstances IgnoreNew" in text
    assert "ExecutionTimeLimit (New-TimeSpan -Minutes 10)" in text
    assert "PublicExposureEnabled = $false" in text
    assert "BrokerExecutionEnabled = $false" in text


def test_post_p2_installer_refuses_overwrite_and_requires_parallel_health() -> None:
    text = POST_P2_INSTALLER.read_text(encoding="utf-8")

    assert "task already exists" in text
    assert "Parallel AI-v1.1 task must exist" in text
    assert "Parallel AI-v1.1 task last result must be 0" in text
    assert "-ConfirmP2Passed" in text
