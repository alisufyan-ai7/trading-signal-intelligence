"""EXP040 Windows-VPS operator: all tests OFFLINE and S3 clients in memory only."""
from __future__ import annotations

import hashlib
import inspect
import io
import json
from pathlib import Path

import pytest

from scripts import exp040_vps_one_shot_synthetic_cloud_operator as op
from scripts import exp038_offline_synthetic_pilot as fake
from trading_signal_intelligence.recovery import b3_synthetic_encrypted_offsite_v0_1 as b3
from trading_signal_intelligence.recovery import b4_synthetic_s3_pilot_v0_1 as b4


def test_cloud_compiled_disabled():
    assert op.REAL_PROVIDER_REQUESTS_ENABLED is False


def test_cli_offline_only_passes_and_json_contains_no_secrets(capsys):
    assert op.main(["--offline-only"]) == 0
    stdout = capsys.readouterr().out
    result = json.loads(stdout)
    assert result == {
        "status": "EXP040_OFFLINE_VPS_OPERATOR_PASS",
        "mode": "DISPOSABLE_FAKE_S3_ONLY",
        "fake_s3_method_calls": 5,
        "independent_synthetic_restores": 2,
        "actual_provider_requests": 0,
        "credential_prompts": 0,
        "cloud_mode_enabled": False,
        "real_data_reads": 0,
        "production_modified": False,
    }
    assert "aws_secret_access_key" not in stdout
    assert "secret access key" not in stdout


def test_direct_offline_method_has_no_provider_requests():
    result = op.offline_preflight()
    assert result["actual_provider_requests"] == 0
    assert result["fake_s3_method_calls"] == 5
    assert result["independent_synthetic_restores"] == 2


def test_cloud_mode_rejects_before_secret_prompt_or_client_creation(monkeypatch):
    attempted = []
    def forbid(*args, **kwargs):
        attempted.append(True)
        raise AssertionError("must never reach credential/network path")
    monkeypatch.setattr(op, "_require_interactive_windows_console", forbid)
    monkeypatch.setattr(op, "_construct_explicit_boto3_client", forbid)
    monkeypatch.setattr(op, "_masked_credentials", forbid)
    with pytest.raises(op.OperatorRejected, match="cloud pilot DISABLED"):
        op.main(["--cloud-pilot"])
    with pytest.raises(op.OperatorRejected, match="cloud pilot DISABLED"):
        op.cloud_pilot(phrase=op.CLOUD_APPROVAL_PHRASE, prompt_fn=forbid)
    assert attempted == []


def test_direct_client_factory_rejects_before_sdk_import(monkeypatch):
    cred = op.Credential("SYNTHETICACCESSID0123", "SYNTHETICSECRET0123")
    def forbidden(*args, **kwargs):
        raise AssertionError("client construction should not reach B4")
    monkeypatch.setattr(b4, "_check_client", forbidden)
    with pytest.raises(op.OperatorRejected, match="not authorized"):
        op._construct_explicit_boto3_client(b4.AWS, cred)


@pytest.mark.parametrize("argv", [
    [], ["--execute"], ["--live"], ["--offline-only", "--cloud-pilot"],
    ["--cloud-pilot", "--approval", "SHOULD_NOT_ECHO"],
    ["--offline-only", "--secret-access-key", "SHOULD_NOT_ECHO"],
    ["--aws-access-key-id", "SHOULD_NOT_ECHO"],
])
def test_cli_rejects_unknown_conflicting_or_credential_args_without_echo(argv, capsys):
    with pytest.raises(op.OperatorRejected, match="invalid or conflicting operator arguments"):
        op.main(argv)
    captured = capsys.readouterr()
    assert "SHOULD_NOT_ECHO" not in captured.out + captured.err
    assert captured.out == ""


def test_masked_credential_entry_reads_without_logging(capsys):
    prompts = []
    answers = iter(["SYNTHETICACCESSID0123", "SYNTHETICSECRET0123"])
    def reader(label):
        prompts.append(label)
        return next(answers)
    credential = op._masked_credentials("Fake AWS writer", reader)
    assert credential.access_key_id == "SYNTHETICACCESSID0123"
    assert credential.secret_access_key == "SYNTHETICSECRET0123"
    assert len(prompts) == 2
    assert all("masked" in prompt for prompt in prompts)
    assert capsys.readouterr().out == ""
    assert "SYNTHETICSECRET0123" not in repr(credential)
    assert repr(credential) == "<redacted credential>"


@pytest.mark.parametrize("invalid", [
    ("", "secretsecret"), ("short", "secretsecret"),
    ("VALIDKEY12345", ""), ("VALIDKEY12345", "bad\nsecret"),
    (" VALIDKEY12345", "secretsecret"), ("VALIDKEY12345", "secretsecret "),
    ("VALIDKEY12345", "a" * 257),
])
def test_invalid_credential_fails_closed_without_values(invalid):
    with pytest.raises(op.OperatorRejected) as err:
        op.Credential(*invalid)
    assert "secretsecret" not in str(err.value)


def test_cancelled_prompt_never_constructs_credential():
    def cancel(label):
        raise KeyboardInterrupt
    with pytest.raises(op.OperatorRejected, match="entry cancelled"):
        op._masked_credentials("Fake B2 reader", cancel)


def test_complete_b1_b3_b4_b5_restore_with_four_injected_fake_clients(tmp_path):
    root = tmp_path / "vowsig-b1b2-fixture-exp040"
    root.mkdir()
    copied, obj, key = op._synthetic_inputs(root)
    aws, b2 = fake._MemoryStore(b4.AWS), fake._MemoryStore(b4.B2)
    result, aws_calls, b2_calls = op._run_pilot_with_clients(
        root, copied, obj, key,
        fake._MemoryClient(aws, role="writer"),
        fake._MemoryClient(aws, role="reader"),
        fake._MemoryClient(b2, role="writer"),
        fake._MemoryClient(b2, role="reader"),
    )
    assert result["status"] == "SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES"
    assert aws_calls == ["PUT", "GET"] and b2_calls == ["HEAD", "PUT", "GET"]
    assert len(aws.objects) == len(b2.objects) == 1
    src_hash = hashlib.sha256(copied.read_bytes()).hexdigest()
    for tag in ("awsrestore", "b2restore"):
        restored = root / "restored" / tag / "forward.sqlite"
        assert restored.is_file()
        assert hashlib.sha256(restored.read_bytes()).hexdigest() == src_hash
    assert obj.envelope_sha256 != src_hash
    assert len(obj.envelope) <= b4.MAX_ENVELOPE_BYTES


def test_offline_disposable_directory_deleted(monkeypatch):
    original = op.tempfile.TemporaryDirectory
    paths = []
    def wrapped(*args, **kwargs):
        obj = original(*args, **kwargs)
        paths.append(Path(obj.name))
        return obj
    monkeypatch.setattr(op.tempfile, "TemporaryDirectory", wrapped)
    result = op.offline_preflight()
    assert result["status"] == "EXP040_OFFLINE_VPS_OPERATOR_PASS"
    assert len(paths) == 1 and not paths[0].exists()


def test_source_imports_boto3_only_inside_unauthorized_factory():
    source = inspect.getsource(op)
    assert "REAL_PROVIDER_REQUESTS_ENABLED = False" in source
    assert "if not REAL_PROVIDER_REQUESTS_ENABLED:" in source
    assert "import boto3" in source  # lazy import within hard-gated function only
    assert "import subprocess" not in source
    assert "os.environ" not in source
    assert "os.getenv" not in source
    assert "getpass.getpass" in source
    assert "--offline-only" in source
    assert "--cloud-pilot" in source
    assert "kwargs" not in op.Credential.__repr__(op.Credential("SYNTHETICACCESSID0123", "SYNTHETICSECRET0123"))
    assert ".env" in source  # explicit prohibition, not an actual loader


def test_source_never_contains_real_backup_path_or_scheduled_task():
    source = inspect.getsource(op)
    assert "data/research.sqlite" not in source
    assert "schedule_task(" not in source
    assert "requests.get(" not in source
    assert "delete_object(" not in source
    assert "list_objects(" not in source


def test_offline_never_uses_real_client_constructor(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("offline must not construct a real SDK client")
    monkeypatch.setattr(op, "_construct_explicit_boto3_client", forbidden)
    assert op.offline_preflight()["status"] == "EXP040_OFFLINE_VPS_OPERATOR_PASS"
