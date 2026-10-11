"""Synthetic-only contract tests for the Windows-safe crypto capture entry.

Do not run the entry --mode capture from tests. No actual databases, tasks,
network, subprocess or seal files are accessed by these tests.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "guarded_crypto_asof_capture_entry_v0_1.py"
SPEC = importlib.util.spec_from_file_location("guarded_capture_entry_under_test", PATH)
assert SPEC is not None and SPEC.loader is not None
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


@pytest.fixture
def guard(tmp_path: Path):
    return entry.CaptureGuard(tmp_path)


def test_exact_nine_active_source_identities(guard, tmp_path):
    assert len(entry.DB_NAMES) == len(guard.allowed) == 9
    assert len(set(entry.DB_NAMES)) == 9
    assert not {"forward", "research", "ai_v1_2_eurusd"}.intersection(
        entry.DB_NAMES
    )
    for name in entry.DB_NAMES:
        assert guard.db_key(
            "file:" + (tmp_path / "data" / (name + ".sqlite")).as_posix()
            + "?mode=ro"
        ) in guard.allowed


@pytest.mark.parametrize("database", (
    ":memory:",
    "data/ai_v1_3_btcusdt.sqlite",
    "file:other.sqlite?mode=ro",
    "file:other.sqlite?mode=rw",
    "file:other.sqlite?mode=rwc",
    "file:other.sqlite?mode=ro&cache=shared",
))
def test_sqlite_unapproved_targets_and_modes_rejected(guard, database):
    with pytest.raises(entry.CaptureGuardRejected):
        guard.db_key(database)


@pytest.mark.parametrize("argv,cwd,shell", (
    (["cmd.exe", "/c", "echo", "hello"], None, False),
    (["git", "reset", "--hard"], None, False),
    (["git", "fetch", "origin"], None, False),
    (["git", "show", "--help"], None, False),
    (["powershell.exe", "-EncodedCommand", "X"], None, False),
    (["git", "rev-parse", "HEAD"], None, True),
))
def test_child_mutation_and_shell_are_denied(guard, argv, cwd, shell):
    with pytest.raises(entry.CaptureGuardRejected):
        guard.check_process(argv, cwd, shell)


def test_approved_git_read_forms(guard):
    for command in (
        ["git", "rev-parse", "HEAD"],
        ["git", "rev-parse", "@{u}"],
        ["git", "show", "HEAD:docs/example.md"],
        ["git", "status", "--porcelain", "--untracked-files=no", "--",
         "research/example.json"],
        ["git", "ls-files", "--", "web"],
    ):
        guard.check_process(command, guard.live, False)


def test_read_only_task_inspection_form(guard):
    script = (
        "$ErrorActionPreference='Stop';"
        "$t=Get-ScheduledTask -TaskName 'VowSig AI-v1.3 Crypto Shadow Scan';"
        "$i=Get-ScheduledTaskInfo -TaskName 'VowSig AI-v1.3 Crypto Shadow Scan';"
        "$o=$t | ConvertTo-Json"
    )
    for argv in (
        ["powershell.exe", "-NoProfile", "-Command", script],
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
    ):
        guard.check_process(argv, None, False)
    with pytest.raises(entry.CaptureGuardRejected):
        guard.check_process([
            "powershell.exe", "-NoProfile", "-Command",
            script + ";Start-ScheduledTask -TaskName 'Other'"
        ], None, False)


def test_install_is_not_needed_for_contract_and_remains_dormant(guard):
    assert isinstance(subprocess.Popen, type)
    assert guard.opened == set()
    assert entry.CONFIRM == "CAPTURE-ONE-CRYPTO-ASOF-RESEARCH-SEAL"
    assert entry.OPT_IN == "VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED"
