"""Pure offline unit tests. Never contact Railway, production PG, AWS or B2."""
import importlib.util
import io
import json
from pathlib import Path

import pytest

MODULE = Path(__file__).parents[1] / "ops" / "pg_recovery" / "backup.py"
spec = importlib.util.spec_from_file_location("vowsig_pg_backup", MODULE)
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


class FakeBody:
    def __init__(self, blob):
        self._file = io.BytesIO(blob)

    def iter_chunks(self, chunk_size):
        while data := self._file.read(chunk_size):
            yield data

    def read(self, n=-1):
        return self._file.read(n)

    def close(self):
        self._file.close()


class FakeCloud:
    def __init__(self, corrupt=False):
        self.objects = {}
        self.corrupt = corrupt

    def put_object(self, Bucket, Key, Body, **_kwargs):
        assert Key not in self.objects, "the test rejects overwriting existing cloud backups"
        self.objects[Key] = Body.read() if hasattr(Body, "read") else Body

    def get_object(self, Bucket, Key):
        blob = self.objects[Key]
        if self.corrupt and Key.endswith(".age"):
            blob += b"corrupted"
        return {"Body": FakeBody(blob)}

    def delete_object(self, *args, **kwargs):
        raise AssertionError("cloud deletion must never occur")


def test_backup_dual_copy_and_restore_not_inferred(monkeypatch):
    aws, b2 = FakeCloud(), FakeCloud()
    monkeypatch.setattr(backup, "_pg_env", lambda: {"PGUSER": "vowsig_backup"})
    monkeypatch.setattr(backup, "_verify_toolchain", lambda: None)
    monkeypatch.setattr(backup, "_required", lambda name: "age1" + "a" * 58)
    monkeypatch.setattr(backup, "_clients", lambda: (("aws", aws, "aws-bucket"), ("b2", b2, "b2-bucket")))
    monkeypatch.setattr(backup, "_encrypted_dump", lambda path, pg_env, recipient: path.write_bytes(b"encrypted" * 30))
    result = backup.run()
    assert result["providers"] == ["aws", "b2"]
    assert result["isolated_cold_restore"] == "NOT_YET_VERIFIED"
    assert result["cloud_deletions"] == 0
    assert aws.objects == b2.objects
    manifests = [json.loads(blob) for key, blob in aws.objects.items() if key.endswith(".json")]
    assert len(manifests) == 1
    assert manifests[0]["production_restore_permitted"] is False


def test_corrupt_second_provider_fails_closed(monkeypatch):
    aws, b2 = FakeCloud(), FakeCloud(corrupt=True)
    monkeypatch.setattr(backup, "_pg_env", lambda: {})
    monkeypatch.setattr(backup, "_verify_toolchain", lambda: None)
    monkeypatch.setattr(backup, "_required", lambda name: "age1" + "a" * 58)
    monkeypatch.setattr(backup, "_clients", lambda: (("aws", aws, "aws-bucket"), ("b2", b2, "b2-bucket")))
    monkeypatch.setattr(backup, "_encrypted_dump", lambda path, pg_env, recipient: path.write_bytes(b"ciphertext" * 30))
    with pytest.raises(backup.BackupFailure, match="remote_ciphertext_sha_mismatch"):
        backup.run()


def test_production_dsn_strict_guard(monkeypatch, tmp_path):
    ca = tmp_path / "ca.pem"
    ca.write_text("CA")
    monkeypatch.setattr(backup, "EXPECTED_CA", str(ca))
    dsn = f"postgresql://vowsig_backup:pw@postgres.railway.internal:5432/vowsig?sslmode=verify-full&sslrootcert={ca}"
    monkeypatch.setenv("VOWSIG_PG_BACKUP_DSN", dsn)
    assert backup._pg_env()["PGPASSWORD"] == "pw"
    monkeypatch.setenv("VOWSIG_PG_BACKUP_DSN", dsn.replace("verify-full", "disable"))
    with pytest.raises(backup.BackupFailure, match="source_dsn_guard"):
        backup._pg_env()
    monkeypatch.setenv("VOWSIG_PG_BACKUP_DSN", dsn.replace("vowsig_backup", "vowsig_app"))
    with pytest.raises(backup.BackupFailure, match="source_dsn_guard"):
        backup._pg_env()


def test_restore_target_requires_explicit_disposable_confirmation(monkeypatch):
    restorefile = Path(__file__).parents[1] / "ops" / "pg_recovery" / "verify_restore.py"
    s = importlib.util.spec_from_file_location("vowsig_pg_restore", restorefile)
    restore = importlib.util.module_from_spec(s)
    s.loader.exec_module(restore)
    monkeypatch.delenv("VOWSIG_LOCAL_RESTORE_CONFIRM", raising=False)
    with pytest.raises(restore.RestoreFailure, match="confirmation_missing"):
        restore._local_env("vowsig_restore_verify_aws_aabbccdd")
    monkeypatch.setenv("VOWSIG_LOCAL_RESTORE_CONFIRM", "YES_ISOLATED_THROWAWAY_PG18")
    monkeypatch.setenv("VOWSIG_LOCAL_RESTORE_PASSWORD", "local-ci-secret")
    with pytest.raises(restore.RestoreFailure, match="disposable_database_name_guard"):
        restore._local_env("vowsig")
