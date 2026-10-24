"""Integrated escrow is an SDK-compatible proposal, never a live trigger."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import dual_provider_encrypted_receipt_vault_v0_1 as vault
from trading_signal_intelligence.recovery import offline_immutable_receipt_escrow_v0_1 as p7


class NoTouchClient:
    def __getattribute__(self, name):
        raise AssertionError("external SDK client must never be inspected")


def test_escrow_compiled_off_before_any_sdk_property_or_object_inspection():
    a, b, c, d = (NoTouchClient() for _ in range(4))
    escrow = vault.PreparedDualProviderEncryptedReceiptVault(
        aws_writer=a, aws_reader=b, b2_writer=c, b2_reader=d
    )
    with pytest.raises(vault.CloudEscrowRejected, match="compiled OFF"):
        escrow.write_once("untrusted", b"private", "0" * 64)
    with pytest.raises(vault.CloudEscrowRejected):
        escrow.read_exact("untrusted")
    assert escrow._fence.attempts == 0
    assert escrow._invoked is False
    assert "REDACTED" in repr(escrow)


def test_b2_no_atomic_exclusive_create_remains_separate_hard_block(monkeypatch):
    # Even a hypothetical later bool toggle for general cloud I/O alone
    # cannot enable the B2 HEAD->PUT non-atomic escrow protocol.
    monkeypatch.setattr(vault, "REAL_ESCROW_REQUESTS_ENABLED", True)
    escrow = vault.PreparedDualProviderEncryptedReceiptVault(
        aws_writer=NoTouchClient(), aws_reader=NoTouchClient(),
        b2_writer=NoTouchClient(), b2_reader=NoTouchClient(),
    )
    with pytest.raises(vault.CloudEscrowRejected, match="B2 atomic no-overwrite"):
        escrow.write_once("untrusted", b"private", "0" * 64)
    assert escrow._fence.attempts == 0


def test_receipt_cloud_prefix_is_covered_by_pilot_iam_without_leaking_versions():
    assert p7.ESCROW_PREFIX == "pilot/vowsig/private-recovery-receipts/v1"
    key = p7._identity("release-test-0001", "a" * 64)
    assert key.startswith("pilot/")
    assert vault.MAX_ENCRYPTED_RECEIPT_BYTES == p7.MAX_SEALED_BYTES
    assert vault.MAX_WIRE_ATTEMPTS == 5
    assert vault.REAL_ESCROW_REQUESTS_ENABLED is False
    assert vault.B2_EXCLUSIVE_CREATE_PROTOCOL_AVAILABLE is False


def test_no_import_time_network_sdk_secrets_or_autonomous_scheduler():
    source = inspect.getsource(vault)
    imports = set()
    for node in ast.parse(source).body:
        if isinstance(node, ast.Import):
            imports.update(x.name.split(".")[0] for x in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert imports.isdisjoint({
        "boto3", "botocore", "socket", "requests", "subprocess",
        "sqlite3", "urllib3",
    })
    assert "os.environ" not in source
    assert 'if __name__ == "__main__"' not in source
