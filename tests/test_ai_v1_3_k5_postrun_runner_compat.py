"""Offline K5 scheduler compatibility checks; never execute a .cmd or provider scan.

The task action swap, installer execution, Binance and OpenAI calls are owner-gated.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FROZEN_RUNNER = ROOT / "scripts" / "run_ai_v1_3_crypto_shadow_task.cmd"
SUCCESSOR = ROOT / "scripts" / "run_ai_v1_3_crypto_shadow_task_post_k5_compat.cmd"
REFERENCE = ROOT / "scripts" / "run_ai_v1_2_1_shadow_task_registry_compat.cmd"
ANCHOR = (
    ROOT
    / "research"
    / "forward"
    / "AI-v1.3-crypto-expansion-activation-2026-10-09T195556Z.json"
)
FROZEN_RUNNER_SHA256 = "395f3d7c460488f1098352fc50a4146d6e2a9d277dbef3d34302212b85981304"


def _active_lines(path: Path) -> str:
    return "\n".join(
        line for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().lower().startswith("rem ")
    )


def test_original_k3_runner_stays_byte_for_byte_frozen() -> None:
    anchor = json.loads(ANCHOR.read_text(encoding="utf-8"))
    assert anchor["artifact_hashes"]["task_runner"] == FROZEN_RUNNER_SHA256
    assert hashlib.sha256(FROZEN_RUNNER.read_bytes()).hexdigest() == FROZEN_RUNNER_SHA256


def test_k5_successor_uses_same_windows_scheduler_runner_conventions() -> None:
    script = _active_lines(SUCCESSOR)
    reference = _active_lines(REFERENCE)

    for shared in (
        "@echo off",
        "setlocal EnableDelayedExpansion",
        'cd /d "%~dp0.."',
        'set "PY=%CD%\\.venv\\Scripts\\python.exe"',
        'set "LOGDIR=%CD%\\data\\forward-task-logs"',
        'if not exist "%PY%"',
        'if not exist "%LOGDIR%" mkdir "%LOGDIR%"',
        'set "RUN_EXIT=!ERRORLEVEL!"',
        "verify_exit=SKIPPED",
        'set "VERIFY_EXIT=!ERRORLEVEL!"',
        "exit /b 0",
    ):
        assert shared in reference
        assert shared in script

    assert 'set "LOG=%LOGDIR%\\ai_v1_3_crypto_shadow.log"' in script


def test_k5_successor_invokes_exactly_one_crypto_scan_then_read_only_verifier() -> None:
    script = _active_lines(SUCCESSOR)

    live = '"%PY%" "scripts\\run_ai_v1_3_crypto_live.py" >> "%LOG%" 2>&1'
    verify = '"%PY%" "scripts\\verify_ai_v1_3_crypto_runtime.py" >> "%LOG%" 2>&1'

    assert script.count(live) == 1
    assert script.count(verify) == 1
    assert script.index(live) < script.index('set "RUN_EXIT=!ERRORLEVEL!"')
    assert script.index("verify_exit=SKIPPED") < script.index(verify)
    assert script.index(verify) < script.index('set "VERIFY_EXIT=!ERRORLEVEL!"')

    # The verifier still performs ledger/anchor/risk checks, but the task must
    # never require its own last-successful-result before it can return 0.
    assert "--include-scheduler" not in script
    assert "--activation-only" not in script
    assert "PYTHONPATH" not in script
    assert "Register-ScheduledTask" not in script
    assert "Start-ScheduledTask" not in script
    assert "Disable-ScheduledTask" not in script
    assert "Enable-ScheduledTask" not in script

    assert 'if not "!RUN_EXIT!"=="0" (' in script
    assert "exit /b !RUN_EXIT!" in script
    assert 'if not "!VERIFY_EXIT!"=="0" exit /b !VERIFY_EXIT!' in script


def test_successor_is_additive_not_a_modified_frozen_runner() -> None:
    assert SUCCESSOR != FROZEN_RUNNER
    assert SUCCESSOR.is_file()
    assert FROZEN_RUNNER.is_file()
    script = _active_lines(SUCCESSOR)
    assert script.count("scripts\\run_ai_v1_3_crypto_live.py") == 1
    assert script.count("scripts\\verify_ai_v1_3_crypto_runtime.py") == 1
