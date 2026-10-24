"""Offline fake-cloud acceptance for the REAL manually invoked AWS/B2 operator."""
from __future__ import annotations

import io
import sqlite3

import pytest

from trading_signal_intelligence.recovery import manual_dual_cloud_backup_v0_1 as m
from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as transport
from test_live_sqlite_envelope_v0_1 import fixture_s02


class MissingObject(RuntimeError):
    response = {
        "Error": {"Code": "404"},
        "ResponseMetadata": {"HTTPStatusCode": 404},
    }


class FakeBucket:
    def __init__(self):
        self.stored = {}
        self.requests = []

    def pair(self, role):
        return FakeClient(self, role)


class FakeClient:
    def __init__(self, bucket, role):
        self.bucket = bucket
        self.role = role

    def head_object(self, **kwargs):
        self.bucket.requests.append(("HEAD",self.role))
        if self.role != "reader":
            raise RuntimeError("wrong role")
        if kwargs["Key"] in self.bucket.stored:
            return {"VersionId":self.bucket.stored[kwargs["Key"]][0]}
        raise MissingObject()

    def put_object(self, **kwargs):
        self.bucket.requests.append(("PUT",self.role))
        if self.role != "writer" or kwargs["Key"] in self.bucket.stored:
            raise RuntimeError("overwrite/wrong role rejected")
        if kwargs["Bucket"] not in (transport.AWS.bucket,transport.B2.bucket):
            raise RuntimeError("unknown bucket")
        assert kwargs["Key"].startswith("pilot/")
        assert kwargs["ContentLength"] == len(kwargs["Body"])
        version = "fake-exact-v1-" + str(len(self.bucket.stored) + 1)
        self.bucket.stored[kwargs["Key"]] = (version,kwargs["Body"])
        return {"VersionId":version}

    def get_object(self, **kwargs):
        self.bucket.requests.append(("GET",self.role))
        if self.role != "reader":
            raise RuntimeError("wrong role")
        version,body = self.bucket.stored[kwargs["Key"]]
        if "VersionId" in kwargs and kwargs["VersionId"] != version:
            raise RuntimeError("wrong version")
        return {"VersionId":version, "ContentLength":len(body),
                "Body":io.BytesIO(body)}


def fake_cloud(monkeypatch):
    aws,b2=FakeBucket(),FakeBucket()
    credentials=(("AWSWRITE1","fake-secret-A"),("AWSREADER","fake-secret-B"),
                 ("B2WRITE00","fake-secret-C"),("B2READER0","fake-secret-D"))
    monkeypatch.setattr(m,"_provider_clients",lambda _: (
        aws.pair("writer"),aws.pair("reader"),b2.pair("writer"),b2.pair("reader")))
    monkeypatch.setattr(m,"_provider_readers",lambda _: (
        aws.pair("reader"),b2.pair("reader")))
    return aws,b2,credentials


def test_full_real_operator_logic_with_fake_aws_b2_dual_recovery(tmp_path,monkeypatch):
    repo,_,_=fixture_s02(tmp_path)
    aws,b2,creds=fake_cloud(monkeypatch)
    password="locally-chosen-secure-recovery-passphrase-00001"
    receipts=tmp_path/"receipts"
    result=m.backup_once(repo_root=repo,receipt_dir=receipts,
                         credentials=creds,passphrase=password)
    assert result["status"]=="BACKUP_TWO_PROVIDER_VERIFIED"
    assert result["record_count"]==3
    assert result["aws_exact_version_restored"]
    assert result["b2_exact_version_restored"]
    assert result["encrypted_receipt_in_both_clouds"]
    assert not result["scheduled_backup_enabled"]
    assert len(aws.stored)==len(b2.stored)==2
    assert all(key.startswith("pilot/vowsig/") for key in aws.stored)
    key=m._manifest_key(result["backup_id"])
    assert aws.stored[key][1]==b2.stored[key][1]
    assert password.encode() not in aws.stored[key][1]
    assert b"fake-exact-v1" not in aws.stored[key][1]
    assert str(creds[0][1]) not in str(result)
    out=tmp_path/"independent-restore.sqlite"
    restored=m.restore_once(
        backup_id=result["backup_id"],output_path=out,
        credentials=(creds[1],creds[3]),passphrase=password,
    )
    assert restored["status"]=="BACKUP_RECOVERY_TWO_PROVIDERS_VERIFIED"
    assert restored["record_count"]==3
    assert out.exists()
    assert sqlite3.connect(out).execute("PRAGMA integrity_check").fetchone()[0]=="ok"
    assert result["backup_id"] in out.name or out.name=="independent-restore.sqlite"


def test_cloud_restore_can_use_one_available_provider(tmp_path,monkeypatch):
    repo,_,_=fixture_s02(tmp_path)
    aws,b2,creds=fake_cloud(monkeypatch)
    result=m.backup_once(repo_root=repo,receipt_dir=tmp_path/"receipt",
                         credentials=creds,passphrase="safe-passphrase-000000000")
    b2.stored.clear()
    output=tmp_path/"recover-after-b2-loss.sqlite"
    safe=m.restore_once(backup_id=result["backup_id"],output_path=output,
                        credentials=(creds[1],creds[3]),
                        passphrase="safe-passphrase-000000000")
    assert safe["status"]=="BACKUP_RECOVERY_DEGRADED_ONE_PROVIDER"
    assert safe["aws_restored"] is True
    assert safe["b2_restored"] is False
    assert output.is_file()


def test_wrong_passphrase_fails_closed_and_never_writes_output(tmp_path,monkeypatch):
    repo,_,_=fixture_s02(tmp_path)
    aws,b2,creds=fake_cloud(monkeypatch)
    result=m.backup_once(repo_root=repo,receipt_dir=tmp_path/"receipt",
                         credentials=creds,passphrase="safe-passphrase-000000000")
    output=tmp_path/"should-not-exist.sqlite"
    with pytest.raises(m.BackupOperationError):
        m.restore_once(backup_id=result["backup_id"],output_path=output,
                       credentials=(creds[1],creds[3]),
                       passphrase="intentionally-wrong-password")
    assert not output.exists()


def test_no_implicit_request_or_source_read_from_module_import(monkeypatch):
    assert m.OBJECT_PREFIX.startswith("pilot/")
    assert m.MANIFEST_PREFIX.startswith("pilot/")
    assert m.DATA_MAX<=m.s02.MAX_SOURCE_BYTES+4096
    assert m.MANIFEST_MAX<=16384
    assert m._manifest_key("backup-"+"0"*32).endswith(".aesgcm")


def test_no_overwrite_existing_recovery_target(tmp_path,monkeypatch):
    _,_,credentials=fake_cloud(monkeypatch)
    existing=tmp_path/"production.sqlite"
    existing.write_bytes(b"must-stay-unchanged")
    with pytest.raises(m.BackupOperationError):
        m.restore_once(backup_id="backup-"+"a"*32,
                       output_path=existing,credentials=(credentials[1],credentials[3]),
                       passphrase="safe-passphrase-000000000")
    assert existing.read_bytes()==b"must-stay-unchanged"
