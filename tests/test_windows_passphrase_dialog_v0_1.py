"""Windows GUI passphrase input: reject invalid/mismatched before cloud activity."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import windows_passphrase_dialog_v0_1 as ui
from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as backup
from scripts import vowsig_dual_cloud_backup as cli


def test_gui_requires_minimum_16_nonsecret_characters():
    for value in ("", "short", "x" * 15, "a\x00" + "x"*23,
                  "x"*20 + "\n", "x" * 1025):
        with pytest.raises(ui.PrivatePassphraseRejected):
            ui.validate("restore", value)
    assert ui.validate("restore", "x" * 16) == "x" * 16
    assert ui.validate("restore", "x" * 32) == "x" * 32


def test_double_entry_must_match_exactly_before_cloud_or_source():
    one = "Random-Demo-Recovery-Password-55"
    assert ui.validate("backup", one, one) == one
    for wrong in (None, "", one[:-1], one + " "):
        with pytest.raises(ui.PrivatePassphraseRejected, match="confirmation"):
            ui.validate("backup", one, wrong)


def test_operator_requires_only_gui_for_private_recovery_phrase(monkeypatch):
    expected = "GUI-Only-No-Console-Passphrase-998877"
    received = []
    def gui(mode):
        received.append(mode)
        return expected
    monkeypatch.setattr(cli.password_dialog, "prompt", gui)
    assert cli._passphrase("backup") == expected
    assert cli._passphrase("restore") == expected
    assert received == ["backup", "restore"]
    source = inspect.getsource(cli._passphrase)
    tree = ast.parse(source)
    # Inspect executable Python nodes, not words in comments/docstrings.
    assert not any(
        isinstance(node, ast.Import)
        and any(alias.name.split(".")[0] == "getpass" for alias in node.names)
        or isinstance(node, ast.ImportFrom) and node.module == "getpass"
        or isinstance(node, ast.Attribute) and node.attr == "getpass"
        or isinstance(node, ast.Name) and node.id == "getpass"
        for node in ast.walk(tree)
    )
    # Check executable access, not incidental words inside docstrings.
    tree = ast.parse(source)
    assert not any(
        isinstance(node, ast.Attribute)
        and node.attr in {"environ", "getenv", "stdin"}
        for node in ast.walk(tree)
    )
    assert "password_dialog.prompt" in source


def test_gui_cancel_failure_redacted_from_operator(monkeypatch):
    def cancelled(mode):
        raise ui.PrivatePassphraseRejected("private secret must never be shown")
    monkeypatch.setattr(cli.password_dialog, "prompt", cancelled)
    with pytest.raises(backup.BackupOperationError) as exc:
        cli._passphrase("backup")
    assert "private secret" not in str(exc.value)


def test_real_gui_refuses_non_windows_before_tk_or_cloud(monkeypatch):
    monkeypatch.setattr(ui.sys, "platform", "linux")
    with pytest.raises(ui.PrivatePassphraseRejected, match="Windows RDP"):
        ui.prompt("backup")
    with pytest.raises(ui.PrivatePassphraseRejected, match="unsupported"):
        ui.prompt("unknown")


def test_lazy_tk_import_and_no_secret_persistence():
    source = inspect.getsource(ui)
    tree = ast.parse(source)
    modules = set()
    for node in tree.body:
        if isinstance(node, ast.Import):
            modules.update(item.name.split(".")[0] for item in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module.split(".")[0])
    assert "tkinter" not in modules
    assert modules.isdisjoint({"boto3", "socket", "subprocess", "urllib"})
    # A mention of an obsolete API in the module's documentation is not
    # an import or runtime reference to that API.
    assert not any(
        isinstance(node, ast.Import)
        and any(alias.name.split(".")[0] == "getpass" for alias in node.names)
        or isinstance(node, ast.ImportFrom) and node.module == "getpass"
        or isinstance(node, ast.Attribute) and node.attr == "getpass"
        or isinstance(node, ast.Name) and node.id == "getpass"
        for node in ast.walk(tree)
    )
    assert "os.environ" not in source
    assert "CredWriteW" not in source
    assert "show=\"*\"" in source
    assert "StringVar" in source
    assert "len(password_var.get())" in source
    assert "root.mainloop()" in source
