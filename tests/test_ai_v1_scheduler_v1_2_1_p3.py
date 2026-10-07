from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BOUND_INSTALLER = ROOT / "scripts" / "install_ai_v1_2_1_shadow_task.ps1"
BOUND_RUNNER = ROOT / "scripts" / "run_ai_v1_2_1_shadow_task.cmd"
BOUND_LIVE_RUNNER = ROOT / "scripts" / "run_ai_v1_2_1_live.py"

P3_RUNNER = ROOT / "scripts" / "run_ai_v1_2_1_shadow_task_post_p2.cmd"
P3_INSTALLER = ROOT / "scripts" / "install_ai_v1_2_1_shadow_task_p3.ps1"

ANCHOR = (
    ROOT
    / "research"
    / "forward"
    / "AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_activation_bound_scheduler_artifacts_remain_unchanged() -> None:
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    hashes = anchor["artifact_hashes"]

    assert _sha256(BOUND_INSTALLER) == hashes[
        "task_installer_script_v1_2_1"
    ]
    assert _sha256(BOUND_RUNNER) == hashes[
        "task_runner_script_v1_2_1"
    ]
    assert _sha256(BOUND_LIVE_RUNNER) == hashes[
        "live_runner_script_v1_2_1"
    ]


def test_p3_runner_defers_scheduler_aware_verification_until_completion() -> None:
    text = P3_RUNNER.read_text(encoding="utf-8")

    assert "run_ai_v1_2_1_live.py" in text
    assert "verify_ai_v1_2_1_runtime.py" in text
    assert "--include-scheduler" not in text
    assert "verify_exit=SKIPPED" in text
    assert 'if not "!RUN_EXIT!"=="0"' in text


def test_p3_installer_uses_only_the_new_runner_for_task_action() -> None:
    text = P3_INSTALLER.read_text(encoding="utf-8")

    assert (
        'scripts\\run_ai_v1_2_1_shadow_task_post_p2.cmd'
        in text
    )
    assert (
        '$boundRunner = Join-Path $repoRoot '
        '"scripts\\run_ai_v1_2_1_shadow_task.cmd"'
        in text
    )
    assert (
        "aa4a1dbab8d85c90aaac3fd72a8b3dccfc62d99df080eeea9462c96024451454"
        in text
    )


def test_p3_installer_preserves_post_p2_evidence_gates() -> None:
    text = P3_INSTALLER.read_text(encoding="utf-8")

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


def test_p3_installer_keeps_plan_only_and_explicit_install_gate() -> None:
    text = P3_INSTALLER.read_text(encoding="utf-8")

    assert "[switch]$PlanOnly" in text
    assert "[switch]$ConfirmP2Passed" in text
    assert "if ($PlanOnly)" in text
    assert "MutationPerformed = $false" in text
    assert "MutationPerformed = $true" in text
    assert "Register-ScheduledTask" in text


def test_p3_scheduler_definition_remains_hourly_minute_03() -> None:
    text = P3_INSTALLER.read_text(encoding="utf-8")

    assert "AddMinutes(3)" in text
    assert "New-TimeSpan -Hours 1" in text
    assert "-MultipleInstances IgnoreNew" in text
    assert "ExecutionTimeLimit (New-TimeSpan -Minutes 10)" in text
    assert "PublicExposureEnabled = $false" in text
    assert "BrokerExecutionEnabled = $false" in text


def test_p3_installer_refuses_overwrite_and_requires_parallel_health() -> None:
    text = P3_INSTALLER.read_text(encoding="utf-8")

    assert "task already exists" in text
    assert "Parallel AI-v1.1 task must exist" in text
    assert "Parallel AI-v1.1 task last result must be 0" in text
    assert "-ActiveRepoRoot is permitted only with -PlanOnly" in text
