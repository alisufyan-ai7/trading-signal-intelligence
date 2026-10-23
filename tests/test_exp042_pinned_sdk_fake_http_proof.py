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


def test_sanitized_probe_reports_booleans_never_request_values():
    from types import SimpleNamespace
    class FakeObject:
        object_key = "pilot/synthetic/v1/exp042/FAKEFILE"
        envelope = b"fake-encrypted-data"
    fake = FakeObject()
    request = SimpleNamespace(
        method="PUT",
        url=f"https://{exp.b4.AWS.endpoint.split('//')[1]}/{exp.b4.AWS.bucket}/{fake.object_key}",
        headers={
            "Authorization": "AWS4-HMAC-SHA256 Credential=FAKE-SECRET-KEY/20261023/us-east-1/s3/aws4_request",
            "Content-Type": "application/octet-stream",
            "Content-Length": str(len(fake.envelope)),
            "If-None-Match": "*",
        },
        body=fake.envelope,
    )
    probe = exp._SanitizedRequestProbe(fake)
    assert probe.make_handler(exp.b4.AWS, "writer")(request) is None
    assert probe.seen == 1
    assert probe.first_shape
    assert all(type(value) is bool for value in probe.first_shape.values())
    import json
    output = json.dumps(probe.first_shape)
    assert "FAKE-SECRET-KEY" not in output
    assert fake.object_key not in output
    assert "fake-encrypted-data" not in output
    assert probe.first_shape["body_exact_bytes"] is True
    assert probe.first_shape["host_is_pinned"] is True


def test_diagnostic_cli_holds_even_when_report_is_structured(monkeypatch, capsys):
    def fake_diagnostic(*, diagnostic=False):
        assert diagnostic is True
        return {
            "status": "EXP042_FAKE_HTTP_DIAGNOSTIC_HOLD",
            "sdk_before_send_observed": 1,
            "first_request_shape_checks": {"content_length_exact": False},
            "real_provider_requests": 0,
        }
    monkeypatch.setattr(exp, "run_pinned_fake_sdk_proof", fake_diagnostic)
    assert exp.main(["--diagnostic-only"]) == 2
    output = capsys.readouterr().out
    assert "EXP042_FAKE_HTTP_DIAGNOSTIC_HOLD" in output
    assert '"content_length_exact":false' in output.replace(" ", "")
    assert "FAKE-SECRET-KEY" not in output


def test_diagnostic_does_not_permit_unknown_arguments(monkeypatch):
    with pytest.raises(exp.SDKOfflineRejected, match="unapproved"):
        exp.main(["--diagnostic-only", "--secret", "DONT_ECHO"])
    with pytest.raises(exp.SDKOfflineRejected, match="unapproved"):
        exp.main(["--offline-only", "--diagnostic-only"])


def test_body_shape_exact_bytes_and_wrong_bytes_are_separately_identified():
    expected = b"synthetic-ciphertext"
    good = exp._safe_body_shape(expected, expected)
    bad = exp._safe_body_shape(expected + b"-mismatch", expected)
    assert good["body_is_bytes_type"] is True
    assert good["body_bytes_match"] is True
    assert bad["body_is_bytes_type"] is True
    assert bad["body_bytes_match"] is False
    assert good["body_has_stream_methods"] is False
    assert all(type(v) is bool for v in bad.values())


def test_body_shape_bounded_seekable_stream_matches_and_restores_cursor():
    import io
    expected = b"synthetic-encrypted"
    stream = io.BytesIO(expected)
    info = exp._safe_body_shape(stream, expected)
    assert info["body_is_bytes_type"] is False
    assert info["body_has_stream_methods"] is True
    assert info["body_stream_seekable"] is True
    assert info["body_stream_at_zero"] is True
    assert info["body_stream_full_payload_match"] is True
    assert info["body_stream_cursor_restored"] is True
    assert stream.tell() == 0
    assert stream.read() == expected


def test_body_shape_rejects_different_or_extra_stream_bytes_and_restores():
    import io
    expected = b"encrypted"
    for content in (b"changed!", expected + b"x", b""):
        stream = io.BytesIO(content)
        info = exp._safe_body_shape(stream, expected)
        assert info["body_stream_full_payload_match"] is False
        assert info["body_stream_cursor_restored"] is True
        assert stream.tell() == 0


def test_body_shape_does_not_read_nonseekable_or_nonzero_cursor():
    class NonSeekable:
        read_called = False
        def read(self, size):
            self.read_called = True
            raise AssertionError("nonseekable body must not be read")
        def seek(self, pos):
            raise AssertionError("nonseekable body must not be seeked")
        def tell(self):
            return 0
        def seekable(self):
            return False
    stream = NonSeekable()
    info = exp._safe_body_shape(stream, b"encrypted")
    assert info["body_has_stream_methods"] is True
    assert info["body_stream_seekable"] is False
    assert info["body_stream_full_payload_match"] is False
    assert stream.read_called is False

    import io
    off = io.BytesIO(b"encrypted")
    off.seek(3)
    info = exp._safe_body_shape(off, b"encrypted")
    assert info["body_stream_at_zero"] is False
    assert info["body_stream_full_payload_match"] is False
    assert off.tell() == 3


def test_body_shape_fixed_schema_never_includes_body_values_or_types():
    expected = b"UNSAFE-SECRET-FAKE-PAYLOAD"
    import io
    info = exp._safe_body_shape(io.BytesIO(expected), expected)
    import json
    text = json.dumps(info)
    assert all(type(value) is bool for value in info.values())
    assert "UNSAFE-SECRET-FAKE-PAYLOAD" not in text
    assert "BytesIO" not in text
    assert "bytes" in text  # fixed field names are permitted


def test_fake_only_body_freezer_accepts_exact_bytes_and_seekable_stream():
    from types import SimpleNamespace
    import io
    payload = b"\x00\x01\xfe\xffsynthetic-encrypted\x00"
    raw = SimpleNamespace(method="PUT", body=payload)
    exp._freeze_verified_fake_put_body(raw, payload)
    assert type(raw.body) is bytes and raw.body == payload
    stream = io.BytesIO(payload)
    prepared = SimpleNamespace(method="PUT", body=stream)
    exp._freeze_verified_fake_put_body(prepared, payload)
    assert type(prepared.body) is bytes and prepared.body == payload
    assert stream.tell() == 0
    assert stream.read() == payload


def test_fake_only_body_freezer_does_not_change_head_or_get_body():
    from types import SimpleNamespace
    import io
    envelope = b"\x03\x04\x05"
    for method in ("GET", "HEAD"):
        stream = io.BytesIO(b"other")
        prepared = SimpleNamespace(method=method, body=stream)
        exp._freeze_verified_fake_put_body(prepared, envelope)
        assert prepared.body is stream
        assert stream.tell() == 0


@pytest.mark.parametrize("content", [
    b"altered", b"", b"\x00\x01\x02\x04", b"\x00\x01\x02\x03\x00",
])
def test_fake_only_body_freezer_denies_wrong_truncated_or_extra_stream(content):
    from types import SimpleNamespace
    import io
    target = b"\x00\x01\x02\x03"
    original = io.BytesIO(content)
    prepared = SimpleNamespace(method="PUT", body=original)
    with pytest.raises(exp.SDKOfflineRejected, match="fake SDK payload stream"):
        exp._freeze_verified_fake_put_body(prepared, target)
    assert prepared.body is original
    assert original.tell() == 0


def test_fake_only_body_freezer_denies_nonzero_cursor_and_nonseekable():
    from types import SimpleNamespace
    import io
    target = b"\x00\x01\x02\x03"
    moved = io.BytesIO(target)
    moved.seek(1)
    prepared = SimpleNamespace(method="PUT", body=moved)
    with pytest.raises(exp.SDKOfflineRejected):
        exp._freeze_verified_fake_put_body(prepared, target)
    assert prepared.body is moved and moved.tell() == 1

    class NonSeekable:
        def read(self, count): raise AssertionError("cannot read nonseekable stream")
        def seek(self, pos): raise AssertionError("cannot seek nonseekable stream")
        def tell(self): return 0
        def seekable(self): return False
    ns = NonSeekable()
    prepared = SimpleNamespace(method="PUT", body=ns)
    with pytest.raises(exp.SDKOfflineRejected):
        exp._freeze_verified_fake_put_body(prepared, target)
    assert prepared.body is ns


def test_fake_only_body_freezer_denies_mismatched_bytes():
    from types import SimpleNamespace
    prepared = SimpleNamespace(method="PUT", body=b"incorrect")
    with pytest.raises(exp.SDKOfflineRejected, match="fake SDK payload did not match"):
        exp._freeze_verified_fake_put_body(prepared, b"authentic")
    assert prepared.body == b"incorrect"


def test_fake_only_body_freezer_denies_cannot_assign_immutable_request():
    from collections import namedtuple
    import io
    request = namedtuple("Request", "method body")("PUT", io.BytesIO(b"synthetic"))
    with pytest.raises(exp.SDKOfflineRejected, match="inspection failed"):
        exp._freeze_verified_fake_put_body(request, b"synthetic")


def test_fake_only_body_freezer_is_registered_before_original_b6():
    import inspect
    source = inspect.getsource(exp.run_pinned_fake_sdk_proof)
    assert source.index("normalize_fake_put") < source.index("fence.attach(aw, ar, bw, br)")
    assert "client.meta.events.register(" in source
    assert "_freeze_verified_fake_put_body(request, obj.envelope)" in source
    assert "http_session = transport" in source
    assert source.index("http_session = transport") < source.index("normalize_fake_put")


def test_sdk_after_call_probe_captures_only_fixed_safe_booleans():
    from types import SimpleNamespace
    probe = exp._SafeSDKPutParserProbe()
    assert probe.after_call_count == 0
    assert all(value is False for value in probe.flags.values())
    parsed = {
        "VersionId": exp.FAKE_VERSION,
        "ResponseMetadata": {"HTTPStatusCode": 200},
        "Authorization": "FAKE-DO-NOT-LOG-CREDENTIAL",
    }
    result = probe.observe(http_response=SimpleNamespace(status_code=200),
                           parsed=parsed)
    assert result is None
    assert probe.after_call_count == 1
    assert all(type(value) is bool for value in probe.flags.values())
    assert all(value is True for value in probe.flags.values())
    import json
    rendered = json.dumps(probe.flags)
    assert exp.FAKE_VERSION not in rendered
    assert "FAKE-DO-NOT-LOG-CREDENTIAL" not in rendered
    assert "Authorization" not in rendered


def test_sdk_after_call_probe_rejects_unexpected_parsed_shape_without_logging():
    from types import SimpleNamespace
    probe = exp._SafeSDKPutParserProbe()
    parsed = ["FAKE-DO-NOT-LOG"]
    probe.observe(http_response=SimpleNamespace(status_code=503), parsed=parsed)
    assert probe.flags["sdk_put_after_call_seen"] is True
    assert probe.flags["sdk_put_http_status_200"] is False
    assert probe.flags["sdk_put_parsed_is_dict"] is False
    assert probe.flags["sdk_put_parsed_version_exact"] is False
    assert probe.flags["sdk_put_parsed_metadata_status_200"] is False
    assert "FAKE-DO-NOT-LOG" not in json.dumps(probe.flags)


def test_sdk_after_call_probe_bad_or_absent_version_remains_false():
    from types import SimpleNamespace
    for parsed in (
        {"VersionId": "NOT-EXPECTED", "ResponseMetadata": {"HTTPStatusCode": 200}},
        {"ResponseMetadata": {"HTTPStatusCode": 200}},
        {"VersionId": exp.FAKE_VERSION, "ResponseMetadata": {"HTTPStatusCode": 400}},
    ):
        probe = exp._SafeSDKPutParserProbe()
        probe.observe(http_response=SimpleNamespace(status_code=200), parsed=parsed)
        assert probe.flags["sdk_put_after_call_seen"] is True
        assert probe.flags["sdk_put_parsed_is_dict"] is True
        assert probe.flags["sdk_put_parsed_version_exact"] is (parsed.get("VersionId") == exp.FAKE_VERSION)
        assert probe.flags["sdk_put_parsed_metadata_status_200"] is (parsed["ResponseMetadata"]["HTTPStatusCode"] == 200)


def test_fake_response_constructor_flag_marks_completed_awsresponse_only():
    from types import SimpleNamespace
    class DummyFence:
        attempted_sends = 1
    class DummyPayload:
        envelope = b"fake-ciphertext"
    class DummyResponse:
        def __init__(self, url, code, headers, body):
            assert code == 200
            assert body.read() == b""
    obj = exp._MockSDKResponses(DummyPayload(), DummyFence(), DummyResponse)
    request = SimpleNamespace(method="PUT", url="https://invalid.example")
    result = obj.make_handler(exp.b4.AWS, "writer")(request)
    assert isinstance(result, DummyResponse)
    assert obj.aws_put_fake_response_constructed is True
    assert obj.operations == ["AWS_S3_PUT"]


def test_mock_response_constructor_failure_does_not_mark_success():
    from types import SimpleNamespace
    class DummyFence:
        attempted_sends = 1
    class DummyPayload:
        envelope = b"fake-ciphertext"
    def raising_response(*args, **kwargs):
        raise ValueError("FAKE-DO-NOT-LOG-ERROR")
    obj = exp._MockSDKResponses(DummyPayload(), DummyFence(), raising_response)
    request = SimpleNamespace(method="PUT", url="https://invalid.example")
    with pytest.raises(ValueError):
        obj.make_handler(exp.b4.AWS, "writer")(request)
    assert obj.aws_put_fake_response_constructed is False


def test_parser_diagnostic_source_has_no_real_network_or_raw_parsed_storage():
    import inspect
    src = inspect.getsource(exp._SafeSDKPutParserProbe)
    assert 'self.flags["sdk_put_parsed_version_exact"]' in src
    assert "after_call_count" in src
    assert "request.url" not in src
    assert "http_response.headers" not in src
    assert "self.parsed =" not in src
    assert "self.exception =" not in src
    runner = inspect.getsource(exp.run_pinned_fake_sdk_proof)
    assert '"after-call.s3.PutObject", parser_probe.observe' in runner
    assert runner.index("http_session = transport") < runner.index("parser_probe =")
    assert "REAL_PROVIDER_REQUESTS_ENABLED = True" not in runner
