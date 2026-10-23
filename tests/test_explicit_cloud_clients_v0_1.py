"""Fixed target four-client factory is OFF until separately approved release."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import explicit_cloud_clients_v0_1 as factory


def test_real_client_preparation_stops_without_any_sdk_or_credentials():
    class Untouchable:
        def __getattribute__(self, name):
            raise AssertionError("cannot inspect provider credential")
    with pytest.raises(factory.ExplicitClientRejected, match="compiled OFF"):
        factory.construct_four_explicit_clients(
            aws_writer=Untouchable(), aws_reader=Untouchable(),
            b2_writer=Untouchable(), b2_reader=Untouchable()
        )
    assert factory.REAL_CLIENT_CREATION_ENABLED is False


def test_sensitive_identity_never_in_repr_or_validation_error():
    a = factory.EphemeralS3Credential("FAKE_ACCESS_ID", "FAKE_SUPER_SECRET")
    assert "FAKE_ACCESS" not in repr(a)
    assert "FAKE_SUPER_SECRET" not in repr(a)
    bad = factory.EphemeralS3Credential("FAKE_ACCESS_ID", "BAD SECRET WITH SPACES")
    with pytest.raises(factory.ExplicitClientRejected) as exc:
        bad.validate()
    assert "BAD SECRET" not in str(exc.value)


def test_dependency_pins_and_no_eager_sdk_import():
    assert factory.PINNED == {
        "boto3":"1.43.114", "botocore":"1.43.114",
        "jmespath":"1.0.1", "s3transfer":"0.19.3",
        "python-dateutil":"2.9.0.post0", "urllib3":"2.8.0",
        "six":"1.17.0"
    }
    source = inspect.getsource(factory)
    module = ast.parse(source)
    for node in module.body:
        if isinstance(node, ast.Import):
            assert all(x.name not in {"boto3", "botocore"} for x in node.names)
        if isinstance(node, ast.ImportFrom):
            assert node.module not in {"boto3", "botocore"}
    assert "os.environ" not in source
    assert 'if __name__ == "__main__"' not in source
