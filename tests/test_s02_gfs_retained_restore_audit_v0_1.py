"""Synthetic end-to-end read-only dual-cloud cold restore retention audit."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import s02_gfs_retained_restore_audit_v0_1 as a


ID_A="backup-"+("a"*32)
ID_B="backup-"+("b"*32)


def test_retained_ids_each_restore_two_providers(monkeypatch):
    seen=[]
    def fake_restore_once(**kw):
        seen.append((kw["backup_id"],kw["passphrase"],kw["output_path"]))
        kw["output_path"].write_bytes(b"synthetic")
        return {"status":"BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED",
                "backup_id":kw["backup_id"],"record_count":33,
                "aws_restored":True,"b2_restored":True}
    monkeypatch.setattr(a.backup,"restore_once",fake_restore_once)
    result=a.audit_retained_recovery_points(
        backup_ids=[ID_A,ID_B],
        read_credentials=(("aws-read","synthetic-secret"),
                          ("b2-read","synthetic-secret")),
        recovery_passphrase="PRIVATE-FAKE-TEST-PASSWORD-12345",
    )
    assert result["status"]=="ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED"
    assert result["verified_backup_count"]==2
    assert result["cloud_deletion_authorized"] is False
    assert result["provider_deletions_performed"] == 0
    assert [x[0] for x in seen] == [ID_A,ID_B]
    assert seen[0][2] != seen[1][2]


def test_single_provider_missing_fails_and_never_claims_healthy(monkeypatch):
    def degraded(**kw):
        return {"status":"BACKUP_RECOVERY_DEGRADED_ONE_PROVIDER",
                "backup_id":kw["backup_id"],"record_count":30,
                "aws_restored":True,"b2_restored":False}
    monkeypatch.setattr(a.backup,"restore_once",degraded)
    with pytest.raises(a.GfsRestoreAuditRejected, match="pruning blocked"):
        a.audit_retained_recovery_points(
            backup_ids=[ID_A],
            read_credentials=(("a","b"),("c","d")),
            recovery_passphrase="FAKE-TEST-PASSPHRASE-123456",
        )


def test_exception_with_provider_secret_not_exposed(monkeypatch):
    def cloud_error(**kw):
        raise ValueError("DO_NOT_LOG_MY_SECRET")
    monkeypatch.setattr(a.backup,"restore_once",cloud_error)
    with pytest.raises(a.GfsRestoreAuditRejected) as exc:
        a.audit_retained_recovery_points(
            backup_ids=[ID_A],read_credentials=(("a","b"),("c","d")),
            recovery_passphrase="FAKE-TEST-PASSPHRASE-123456",
        )
    assert "DO_NOT_LOG_MY_SECRET" not in str(exc.value)


@pytest.mark.parametrize("bad", [
    [],[ID_A,ID_A],["not a backup ID"],[ID_A]*81,
])
def test_unbounded_duplicate_or_invalid_ids_rejected(bad):
    with pytest.raises(a.GfsRestoreAuditRejected):
        a.audit_retained_recovery_points(
            backup_ids=bad,read_credentials=(("a","b"),("c","d")),
            recovery_passphrase="FAKE-TEST-PASSPHRASE-123456",
        )


def test_no_cloud_mutation_methods_in_restore_auditor():
    tree=ast.parse(inspect.getsource(a))
    assert not any(
        isinstance(node,ast.Attribute) and node.attr in (
            "delete_object", "delete_objects", "put_object",
            "put_bucket_lifecycle_configuration"
        ) for node in ast.walk(tree)
    )
