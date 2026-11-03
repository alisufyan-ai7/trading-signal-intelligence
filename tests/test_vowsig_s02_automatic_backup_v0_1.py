"""Offline regression for unattended S02 task; NO real keys or provider API calls."""
from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from scripts import vowsig_s02_automatic_backup_v0_1 as scheduler
from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as cloud
from trading_signal_intelligence.recovery import windows_credential_manager_v0_1 as vault


@contextmanager
def fake_lock(path):
    yield


def setup(tmp_path, monkeypatch):
    base = tmp_path / scheduler.STATE_DIR_NAME
    state = base / "state"
    state.mkdir(parents=True)
    repo = tmp_path / "trading-signal-intelligence"
    (repo / ".git").mkdir(parents=True)
    (repo / "data").mkdir()
    (repo / "data" / "forward.sqlite").write_bytes(b"synthetic")
    monkeypatch.setattr(scheduler, "_one_instance", fake_lock)
    monkeypatch.setattr(vault, "scheduled_credential_status", lambda: {
        "ready":True,"network_requests":0
    })
    monkeypatch.setattr(vault, "load_credentials", lambda mode: (
        ("aws-writer", "private-fake-key-a"),
        ("aws-reader", "private-fake-key-b"),
        ("b2-writer", "private-fake-key-c"),
        ("b2-reader", "private-fake-key-d"),
    ))
    monkeypatch.setattr(vault, "load_scheduled_recovery_passphrase",
                        lambda: "PRIVATE-TEST-ONLY-MOCK-PASSPHRASE")
    return repo,state


def test_new_scoped_vault_passphrase_entry_and_no_echo():
    assert vault.SCHEDULED_PASSPHRASE_TARGET == "VowSig.S02.Recovery.Passphrase.v1"
    assert vault.SCHEDULED_PASSPHRASE_USERNAME == "VowSigS02"
    secret = vault.ScopedSecret(vault.SCHEDULED_PASSPHRASE_USERNAME,
                                "PRIVATE Test recovery passphrase 2026!")
    def read(target):
        assert target == vault.SCHEDULED_PASSPHRASE_TARGET
        return secret
    assert vault.load_scheduled_recovery_passphrase(lookup=read) == secret.secret
    assert "PRIVATE" not in repr(secret)
    with pytest.raises(vault.WindowsVaultRejected):
        vault.load_scheduled_recovery_passphrase(
            lookup=lambda target: vault.ScopedSecret("wrong_user", secret.secret)
        )


def test_scheduled_readiness_only_local_no_provider_calls(tmp_path,monkeypatch):
    repo,state=setup(tmp_path,monkeypatch)
    result=scheduler.readiness(repo_root=repo,state_dir=state)
    assert result["ready"] is True
    assert result["network_requests"] == 0
    assert result["retention"] == "ALL_ENCRYPTED_CLOUD_VERSIONS_PRESERVED"


def test_scheduled_dual_backup_and_independent_cold_restore(tmp_path,monkeypatch):
    repo,state=setup(tmp_path,monkeypatch)
    calls=[]
    def fake_backup_once(**kwargs):
        calls.append(("backup",kwargs["repo_root"],kwargs["passphrase"]))
        assert kwargs["receipt_dir"].is_dir()
        return {"status":"BACKUP_TWO_PROVIDER_VERIFIED",
                "backup_id":"backup-"+"a"*32,"record_count":30}
    def fake_restore_once(**kwargs):
        calls.append(("restore",kwargs["backup_id"],kwargs["passphrase"]))
        kwargs["output_path"].write_bytes(b"mock-data")
        return {"status":"BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED",
                "aws_restored":True,"b2_restored":True}
    monkeypatch.setattr(cloud,"backup_once",fake_backup_once)
    monkeypatch.setattr(cloud,"restore_once",fake_restore_once)
    record=scheduler.run_once(repo_root=repo,state_dir=state)
    assert record["status"]==scheduler.SUCCESS
    assert record["record_count"]==30
    assert record["older_cloud_versions_deleted"] is False
    assert len(calls)==2
    assert calls[0][0]=="backup" and calls[1][0]=="restore"
    audit=[json.loads(line) for line in (state/scheduler.HISTORY).read_text().splitlines()]
    assert audit[-1]["backup_id"]==record["backup_id"]
    assert "PRIVATE" not in (state/scheduler.HISTORY).read_text()
    assert not (state/scheduler.REVIEW_FLAG).exists()


def test_partial_cloud_failure_latches_and_blocks_followup_run(tmp_path,monkeypatch):
    repo,state=setup(tmp_path,monkeypatch)
    calls=[]
    def ambiguous(**kwargs):
        calls.append(1)
        raise cloud.BackupOperationError("opaque provider failure")
    monkeypatch.setattr(cloud,"backup_once",ambiguous)
    with pytest.raises(scheduler.AutomatedBackupRejected,match="latch"):
        scheduler.run_once(repo_root=repo,state_dir=state)
    latch=json.loads((state/scheduler.REVIEW_FLAG).read_text())
    assert latch["retry_allowed"] is False
    assert latch["cloud_deletion_performed"] is False
    assert scheduler.readiness(repo_root=repo,state_dir=state)["ready"] is False
    with pytest.raises(scheduler.AutomatedBackupRejected,match="review required"):
        scheduler.run_once(repo_root=repo,state_dir=state)
    assert calls==[1]


def test_credential_missing_never_attempts_cloud_or_latch(tmp_path,monkeypatch):
    repo,state=setup(tmp_path,monkeypatch)
    monkeypatch.setattr(vault,"load_scheduled_recovery_passphrase",
                        lambda: (_ for _ in ()).throw(vault.WindowsVaultRejected("no vault")))
    monkeypatch.setattr(cloud,"backup_once",
                        lambda **kwargs: pytest.fail("cloud call forbidden"))
    with pytest.raises(scheduler.AutomatedBackupRejected,match="credential"):
        scheduler.run_once(repo_root=repo,state_dir=state)
    assert not (state/scheduler.REVIEW_FLAG).exists()


def test_reject_arbitrary_state_or_source_before_calls(tmp_path,monkeypatch):
    repo,state=setup(tmp_path,monkeypatch)
    with pytest.raises(scheduler.AutomatedBackupRejected):
        scheduler.readiness(repo_root=repo,state_dir=tmp_path)
    with pytest.raises(scheduler.AutomatedBackupRejected):
        scheduler.readiness(repo_root=tmp_path,state_dir=state)
