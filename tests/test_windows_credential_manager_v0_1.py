"""Windows Credential Manager fixed-target integration: NO real secrets needed."""
from __future__ import annotations

import inspect
import sys

import pytest

from trading_signal_intelligence.recovery import windows_credential_manager_v0_1 as vault
from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as backup


def _fake_values():
    ids = {
        "aws_writer": "FAKE_AWS_WRITER01",
        "aws_reader": "FAKE_AWS_READER01",
        "b2_writer": "FAKE_B2_WRITER01",
        "b2_reader": "FAKE_B2_READER01",
    }
    return {
        vault.TARGETS[role]: vault.ScopedSecret(access_id, "fake-secret-" + role)
        for role, access_id in ids.items()
    }


def test_target_names_are_exact_and_can_be_entered_via_windows_gui():
    assert vault.TARGETS == {
        "aws_writer": "VowSig.S02.AWS.Writer.v1",
        "aws_reader": "VowSig.S02.AWS.Reader.v1",
        "b2_writer": "VowSig.S02.B2.Writer.v1",
        "b2_reader": "VowSig.S02.B2.Reader.v1",
    }
    assert len(set(vault.TARGETS.values())) == 4


def test_four_scoped_backup_credentials_read_exactly_one_each_without_echo():
    stored = _fake_values()
    seen = []
    def reader(target):
        seen.append(target)
        return stored[target]
    got = vault.load_credentials("backup", lookup=reader)
    assert len(got) == 4
    assert seen == [vault.TARGETS[r] for r in vault.BACKUP_ROLES]
    assert [x[0] for x in got] == [stored[vault.TARGETS[r]].access_id for r in vault.BACKUP_ROLES]
    assert "fake-secret-" not in repr(stored[vault.TARGETS["aws_writer"]])
    assert "fake-secret-" not in str(vault.credential_status(lookup=reader))


def test_restore_reads_only_two_reader_roles():
    stored = _fake_values()
    seen = []
    def reader(target):
        seen.append(target)
        return stored[target]
    got = vault.load_credentials("restore", lookup=reader)
    assert len(got) == 2
    assert seen == [vault.TARGETS["aws_reader"], vault.TARGETS["b2_reader"]]


def test_gui_credential_status_contains_flags_not_actual_secrets_or_key_ids():
    stored = _fake_values()
    output = vault.credential_status(lookup=lambda target: stored[target])
    assert output["backup_roles_ready"] is True
    assert output["restore_roles_ready"] is True
    assert output["network_requests"] == 0
    for item in stored.values():
        assert item.secret not in str(output)
        assert item.access_id not in str(output)


@pytest.mark.parametrize("role", vault.BACKUP_ROLES)
def test_missing_entry_fails_closed_without_any_provider_calls(role):
    stored = _fake_values()
    stored.pop(vault.TARGETS[role])
    def reader(target):
        return stored[target]
    with pytest.raises(vault.WindowsVaultRejected, match="retrieval failed"):
        vault.load_credentials("backup", lookup=reader)
    status = vault.credential_status(lookup=reader)
    assert status["backup_roles_ready"] is False
    assert status["roles"][role] is False


def test_duplicate_writer_reader_identity_is_rejected():
    stored = _fake_values()
    stored[vault.TARGETS["b2_reader"]] = stored[vault.TARGETS["aws_reader"]]
    with pytest.raises(vault.WindowsVaultRejected, match="separate"):
        vault.load_credentials("backup", lookup=lambda target: stored[target])


@pytest.mark.parametrize("bad", ["BAD KEY", "bad\x00secret", "xx", "", "a"*257, "é"*10])
def test_nonprintable_or_short_secrets_are_not_accepted(bad):
    assert not vault._printable(bad)


def test_gui_blob_decode_supports_utf16le_and_plain_utf8_from_generic_api():
    secret = "FAKE_SECRET-12345"
    assert vault._decode_blob(secret.encode("utf-16-le")) == secret
    assert vault._decode_blob(secret.encode("utf-8")) == secret
    with pytest.raises(vault.WindowsVaultRejected):
        vault._decode_blob(b"\x00\x00")


def test_credential_status_on_non_windows_never_accesses_network(monkeypatch):
    monkeypatch.setattr(vault.sys, "platform", "linux")
    result = vault.credential_status()
    assert result["network_requests"] == 0
    assert result["backup_roles_ready"] is False
    with pytest.raises(vault.WindowsVaultRejected, match="Windows Credential Manager"):
        vault._read_generic(vault.TARGETS["aws_writer"])


def test_operator_credential_handler_never_has_manual_key_prompt_source():
    from scripts import vowsig_dual_cloud_backup as cli
    text = inspect.getsource(cli._credentials)
    assert "getpass" not in text
    assert "_prompt" not in text
    assert "vault.load_credentials" in text
    assert "AWS secret" not in text
    assert "CLOUD" not in str(vault.credential_status(lookup=lambda x: _fake_values()[x]))


def test_absent_windows_credential_store_does_not_fallback_to_env_or_cli(monkeypatch):
    from scripts import vowsig_dual_cloud_backup as cli
    def denied(*args, **kwargs):
        raise vault.WindowsVaultRejected("missing")
    monkeypatch.setattr(cli.vault, "load_credentials", denied)
    with pytest.raises(backup.BackupOperationError, match="Windows Credential Manager"):
        cli._credentials("backup")
    assert "os.environ" not in inspect.getsource(cli._credentials)


def test_no_import_side_effects_or_secret_persistence_calls():
    source = inspect.getsource(vault)
    assert "CredReadW" in source
    assert "CredWriteW" not in source
    assert "CredEnumerateW" not in source
    assert "os.environ" not in source
    assert 'if __name__ == "__main__"' not in source
    assert "boto3" not in source
    assert "subprocess" not in source
