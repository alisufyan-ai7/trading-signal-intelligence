"""EXP042: never attempt live HTTP, credential use, or package installation."""
from __future__ import annotations

import importlib
import json
import socket

import pytest

from scripts import exp042_pinned_sdk_fake_http_proof as exp
from scripts import exp040_vps_one_shot_synthetic_cloud_operator as old


def test_real_cloud_is_hard_disabled_and_fake_sdk_pin_recorded():
    assert exp.PROVIDER_CALLS_ALLOWED is False
    assert old.REAL_PROVIDER_REQUESTS_ENABLED is False
    assert exp.PIN_BOTO3 == "1.43.114"
    assert exp.PIN_BOTOCORE == "1.43.114"
    assert "FAKE_NEVER_VALID" in exp.FAKE_ACCESS
    assert "FAKE_NEVER_VALID" in exp.FAKE_SECRET


def test_fail_closed_if_sdk_not_installed(monkeypatch):
    def version(name):
        raise exp.importlib.metadata.PackageNotFoundError(name)
    monkeypatch.setattr(exp.importlib.metadata, "version", version)
    assert exp.sdk_pin_status() == "PINNED_SDK_NOT_INSTALLED"
    with pytest.raises(exp.SDKOfflineRejected, match="PINNED_SDK_NOT_INSTALLED"):
        exp.run_pinned_fake_sdk_proof()


def test_fail_closed_on_sdk_version_mismatch(monkeypatch):
    def version(name):
        return "0.0.0" if name == "boto3" else "1.43.114"
    monkeypatch.setattr(exp.importlib.metadata, "version", version)
    assert exp.sdk_pin_status() == "PINNED_SDK_VERSION_MISMATCH"
    with pytest.raises(exp.SDKOfflineRejected, match="PINNED_SDK_VERSION_MISMATCH"):
        exp.run_pinned_fake_sdk_proof()


def test_sdk_status_does_not_import_boto3_or_network(monkeypatch):
    seen = []
    def version(name):
        seen.append(name)
        return "1.43.114"
    monkeypatch.setattr(exp.importlib.metadata, "version", version)
    assert exp.sdk_pin_status() == "PINNED_SDK_AVAILABLE"
    assert seen == ["boto3", "botocore"]


def test_deny_all_http_session_does_not_forward():
    transport = exp._DenyHTTPTransport()
    with pytest.raises(exp.SDKOfflineRejected, match="unauthorized SDK HTTP"):
        transport.send(object())
    assert transport.unsolicited_send_calls == 1
    assert transport.close() is None


def test_no_actual_network_socket_even_if_transport_attempted():
    old_connect = socket.socket.connect
    old_connect_ex = socket.socket.connect_ex
    old_create = socket.create_connection
    with exp._block_external_socket_connections():
        with socket.socket() as sock:
            with pytest.raises(exp.SDKOfflineRejected, match="external network blocked"):
                sock.connect(("127.0.0.1", 9))
            with pytest.raises(exp.SDKOfflineRejected):
                sock.connect_ex(("127.0.0.1", 9))
        with pytest.raises(exp.SDKOfflineRejected):
            socket.create_connection(("127.0.0.1", 9))
    assert socket.socket.connect is old_connect
    assert socket.socket.connect_ex is old_connect_ex
    assert socket.create_connection is old_create


def test_cli_requires_only_offline_and_never_echoes_secret(capsys):
    with pytest.raises(exp.SDKOfflineRejected, match="unapproved"):
        exp.main(["--cloud-pilot", "--secret", "SENSITIVE_DO_NOT_ECHO"])
    with pytest.raises(exp.SDKOfflineRejected, match="unapproved"):
        exp.main([])
    output = capsys.readouterr()
    assert "SENSITIVE_DO_NOT_ECHO" not in output.out + output.err


def test_mock_response_requires_preceding_b6_fence():
    class NeverSend:
        attempted_sends = 0
    class DummyObject:
        envelope = b"fake"
    fake_response = exp._MockSDKResponses(DummyObject(), NeverSend(), object)
    handler = fake_response.make_handler(
        exp.b4.AWS, "writer")
    class FakeRequest:
        method = "PUT"
        url = "https://invalid.example"
    with pytest.raises(exp.SDKOfflineRejected, match="did not precede"):
        handler(FakeRequest())


def test_pinned_sdk_actual_serialization_and_signing_if_available():
    # Missing/wrong SDK MUST NOT be silently counted as compatibility proof.
    # The operator CLI is a separate required PASS/HOLD gate.
    status = exp.sdk_pin_status()
    if status != "PINNED_SDK_AVAILABLE":
        pytest.skip("EXP042 SDK COMPATIBILITY HOLD: " + status)
    output = exp.run_pinned_fake_sdk_proof()
    assert output["status"] == "EXP042_PINNED_SDK_FAKE_TRANSPORT_PASS"
    assert output["http_transport_send_invocations"] == 0
    assert output["sdk_serialized_and_signed_pre_send_events"] == 5
    assert output["synthetic_independent_restores"] == 2
    assert output["real_provider_requests"] == 0
    assert output["real_credentials"] is False


def test_source_contains_no_provider_keys_or_live_sdk_activation():
    from pathlib import Path
    source = Path(exp.__file__).read_text(encoding="utf-8")
    assert "REAL_PROVIDER_REQUESTS_ENABLED = True" not in source
    assert "PROVIDER_CALLS_ALLOWED = False" in source
    assert "getpass.getpass" not in source
    assert "os.environ" not in source
    assert "subprocess" not in source
    assert "pip install" not in source
    assert "https://s3.us-east-1.amazonaws.com" not in source
    assert "https://s3.us-east-005.backblazeb2.com" not in source
    assert "--offline-only" in source
