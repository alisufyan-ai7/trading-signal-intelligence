"""EXP038 isolated source fixture and fake-cloud pilot: never contacts remote APIs."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts import exp038_offline_synthetic_pilot as exp
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4


def test_offline_preflight_two_independent_restores_and_five_fake_calls():
    report = exp.run_offline_synthetic_preflight()
    assert report["status"] == "EXP038_OFFLINE_SYNTHETIC_PREFLIGHT_PASS"
    assert report["mode"] == "IN_MEMORY_FAKE_PROVIDERS_ONLY"
    assert report["remote_network_requests"] == 0
    assert report["actual_provider_calls"] == 0
    assert report["fake_provider_calls"] == 5
    assert report["aws_fake_calls"] == 2
    assert report["b2_fake_calls"] == 3
    assert report["independent_authenticated_restores"] == 2
    assert report["synthetic_records_per_restore"] == 2
    assert report["secrets_loaded"] is False
    assert report["cloud_pilot_authorized"] is False


def test_cli_explicit_offline_flag_json_output(capsys):
    assert exp.main(["--offline-only"]) == 0
    out = capsys.readouterr().out
    report = json.loads(out)
    assert report["status"] == "EXP038_OFFLINE_SYNTHETIC_PREFLIGHT_PASS"
    assert report["real_vps_database_reads"] == 0
    assert report["real_cloud_spend"] == 0
    assert "secret" not in out.lower().replace("secrets_loaded", "")
    assert "AccessKey" not in out


def test_cli_denies_no_flags(capsys):
    with pytest.raises(SystemExit) as ei:
        exp.main([])
    assert ei.value.code == 2
    assert "no remote execution mode" in capsys.readouterr().err


@pytest.mark.parametrize("args", [
    ["--execute"], ["--cloud"], ["--offline-only", "--execute"],
    ["--offline-only", "--aws-key", "sensitive"],
    ["--offline-only", "--b2-secret", "sensitive"],
])
def test_cli_rejects_cloud_or_credentials_flags(args, capsys):
    with pytest.raises(SystemExit) as ei:
        exp.main(args)
    assert ei.value.code == 2
    assert not capsys.readouterr().out


def test_fake_clients_do_not_have_network_or_provider_methods():
    store = exp._MemoryStore(b4.AWS)
    writer = exp._MemoryClient(store, role="writer")
    reader = exp._MemoryClient(store, role="reader")
    assert not hasattr(writer, "request")
    assert not hasattr(reader, "client")
    assert writer.meta.endpoint_url == b4.AWS.endpoint
    assert reader.meta.config.retries["total_max_attempts"] == 1


def test_fake_writer_cannot_head_or_get():
    store = exp._MemoryStore(b4.AWS)
    writer = exp._MemoryClient(store, role="writer")
    with pytest.raises(exp.OfflinePreflightRejected):
        writer.head_object(Bucket=b4.AWS.bucket, Key="pilot/synthetic/v1/fake/file")
    with pytest.raises(exp.OfflinePreflightRejected):
        writer.get_object(Bucket=b4.AWS.bucket, Key="pilot/synthetic/v1/fake/file")
    assert store.calls == []


def test_fake_reader_cannot_put():
    store = exp._MemoryStore(b4.B2)
    reader = exp._MemoryClient(store, role="reader")
    with pytest.raises(exp.OfflinePreflightRejected):
        reader.put_object(Bucket=b4.B2.bucket, Key="fake", Body=b"fake", ContentLength=4)
    assert not store.objects and not store.calls


def test_fake_writer_no_overwrite_and_no_delete():
    store = exp._MemoryStore(b4.AWS)
    writer = exp._MemoryClient(store, role="writer")
    request = dict(Bucket=b4.AWS.bucket, Key="pilot/synthetic/v1/fake/file",
                   Body=b"fake-bytes", ContentLength=10, IfNoneMatch="*")
    assert writer.put_object(**request)["VersionId"] == "synthetic-offline-v1"
    with pytest.raises(exp.OfflinePreflightRejected):
        writer.put_object(**request)
    assert store.calls == ["PUT"]
    assert not hasattr(writer, "delete_object")


def test_ephemeral_fixture_is_deleted_on_return(monkeypatch):
    original = exp.tempfile.TemporaryDirectory
    observed = []

    def captured(*args, **kwargs):
        tmp = original(*args, **kwargs)
        observed.append(tmp.name)
        return tmp

    monkeypatch.setattr(exp.tempfile, "TemporaryDirectory", captured)
    result = exp.run_offline_synthetic_preflight()
    assert result["independent_authenticated_restores"] == 2
    assert len(observed) == 1
    assert not Path(observed[0]).exists()


def test_offline_source_has_no_network_sdk_or_secret_loader():
    source = Path(exp.__file__).read_text(encoding="utf-8")
    assert "import boto3" not in source
    assert "import botocore" not in source
    assert "import requests" not in source
    assert "import urllib" not in source
    assert "import socket" not in source
    assert "os.getenv" not in source
    assert "os.environ" not in source
    assert "subprocess" not in source
    assert "--offline-only" in source
    assert "network_approved=True" in source  # Only two locally created fake clients.
