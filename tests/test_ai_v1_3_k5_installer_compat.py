"""Offline structural guards for the additive post-K4 K5 installer.

No PowerShell task registration, Binance requests, or provider calls are made.
Windows-native runtime and scheduler checks remain owner VPS prerequisites.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "scripts" / "install_ai_v1_3_crypto_shadow_task.ps1"
SUCCESSOR = ROOT / "scripts" / "install_ai_v1_3_crypto_shadow_task_post_k4.ps1"
EXPECTED_LEGACY = "6db18223f3d8576ae4cd6b2cba1d8c0e2d32cdc8142445e7f652aece9f52c5ce"


def test_k3_frozen_installer_remains_exact():
    assert hashlib.sha256(LEGACY.read_bytes()).hexdigest() == EXPECTED_LEGACY


def test_post_k4_successor_uses_full_verifier_and_read_only_default():
    source = SUCCESSOR.read_text(encoding="utf-8")
    assert '& $python $verifier\n' in source
    assert '& $python $verifier --activation-only' not in source
    assert '& $python $verifier --include-scheduler' not in source
    assert 'if (-not $ConfirmK5Installation)' in source
    assert source.index('if (-not $ConfirmK5Installation)') < source.index('Register-ScheduledTask ')
    assert 'K5_PREVIEW_ONLY=PASS' in source
    assert 'K5_TASK_REGISTRATION=NOT_ATTEMPTED' in source
    assert 'Register-ScheduledTask -TaskName $TaskName -InputObject $task -ErrorAction Stop' in source
    assert 'Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force' not in source


def test_post_k4_evidence_and_frozen_crypto_gate_guards():
    source = SUCCESSOR.read_text(encoding="utf-8")
    for fragment in (
        'Get-FileHash -LiteralPath $legacyInstaller -Algorithm SHA256',
        'FIRST_CYCLE_ATTEMPTED.json',
        'RUN-AI-V1.3-CRYPTO-FIRST-CYCLE',
        'ONE_SHOT_NO_RETRY',
        'activated_anchor_sha256',
        '5d30b294ea3bce57fbfb7ae324c2290e03b142a03f6bafd98090de35514b35e2',
        '24dc7e6ed71270a573de1cdc9d1473534d84bd1a3dc70ed57ff95619d50f2233',
        'fdc2b6f8b81e5bff1a43a0c8f5541038ecade9089860d02cce4ec4d3e7a36eba',
        '$verified.crypto.health.activation_anchor_upstream_valid',
        '$verified.crypto.health.broker_execution_disabled',
        '$verified.crypto.health.public_signal_exposure_disabled',
        'K5_FROZEN_K3_ARTIFACTS=UNCHANGED',
    ):
        assert fragment in source

def test_post_k4_evidence_paths_initialized_before_use():
    source = SUCCESSOR.read_text(encoding="utf-8")
    definitions = {
        "$legacyInstaller": 'Join-Path $repoRoot "scripts\\install_ai_v1_3_crypto_shadow_task.ps1"',
        "$k4Marker": 'Join-Path $env:ProgramData "VowSig\\K4FirstCycle\\FIRST_CYCLE_ATTEMPTED.json"',
        "$expectedLegacySha256": '"6db18223f3d8576ae4cd6b2cba1d8c0e2d32cdc8142445e7f652aece9f52c5ce"',
        "$expectedK4AnchorSha256": '"561b1a532d196dcdbf852f39561798e40e8e297a5022a9f3155d2038bb5b150e"',
    }
    for variable, expected_expression in definitions.items():
        assignment = f"{variable} = {expected_expression}"
        assert source.count(assignment) == 1, variable
        # Variable reads must not precede assignment.
        assert source.index(assignment) < source.index(
            "if (-not (Test-Path -LiteralPath $legacyInstaller"
        )
