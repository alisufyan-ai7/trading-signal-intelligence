"""Integrated S02 backup release candidate: no actual cloud or source reads."""
from __future__ import annotations

import ast
import inspect

import pytest

from trading_signal_intelligence.recovery import integrated_s02_backup_operator_v0_1 as op
from trading_signal_intelligence.recovery import live_sqlite_envelope_v0_1 as core
from trading_signal_intelligence.recovery import live_dual_provider_transport_v0_1 as p2
from trading_signal_intelligence.recovery import backup_release_evidence_gate_v0_1 as p3
from trading_signal_intelligence.recovery import offline_immutable_receipt_escrow_v0_1 as p7


def review(override=None):
    fields = {
        "source_processor_region_rights_verified": True,
        "provider_account_zero_charge_enforced": True,
        "bucket_versioning_privacy_retention_verified": True,
        "four_off_vps_scoped_identities_verified": True,
        "independent_data_and_manifest_keys_recoverable": True,
        "independent_receipt_store_verified": True,
        "independent_offhost_restore_verified": True,
        "windows_scratch_acl_and_disk_encryption_verified": True,
        "partial_failure_alert_and_rollback_verified": True,
        "owner_exact_pilot_approved": True,
        "approval_reference_sha256": "a" * 64,
    }
    if override:
        fields.update(override)
    return op.OperatorReleaseReview(**fields)


def negative_assessment():
    return p3.ReleaseEvidenceAssessment(
        offline_document_verified=True,
        release_status="OFFLINE_SIGNED_EVIDENCE_ONLY_EXTERNAL_HOLDS",
        independently_verified_provider_accounts=False,
        independently_verified_zero_spend=False,
        independently_verified_storage_rights=False,
        live_provider_requests_authorized=False,
    )


def config(tmp_path, *, release=None):
    class NoTouch:
        def __getattribute__(self, field):
            raise AssertionError("client must never be accessed")
    def no_call(*args, **kwargs):
        raise AssertionError("escrow must never be accessed")
    # No synthetic fixture necessary: hard release gate must stop before
    # source, escrow, credentials or provider calls, even with false inputs.
    return dict(
        repo_root=tmp_path / "THIS_DOES_NOT_EXIST",
        scratch_parent=tmp_path / "ABSENT",
        run_id="production-prohibited-0001",
        release_review=release or review(),
        signed_evidence=negative_assessment(),
        source_authorization=core.SourceAuthorization(
            core.SOURCE_REL, "S02", "a"*64, "b"*64,
            (p2.AWS.region, p2.B2.region),
        ),
        transfer_authorization=p2.ReleaseAuthorization(
            p2.APPROVAL, "a"*64, "b"*64, "c"*64, "d"*64,
            (p2.AWS.bucket,p2.B2.bucket), (p2.AWS.region,p2.B2.region)
        ),
        data_key=b"k"*32,
        manifest_key=b"m"*32,
        escrow_write_once=no_call,
        escrow_read_exact=no_call,
        writer_scope_ref_sha256="a"*64,
        reader_scope_ref_sha256="b"*64,
        recovery_custody_ref_sha256="c"*64,
        aws_writer=NoTouch(), aws_reader=NoTouch(),
        b2_writer=NoTouch(), b2_reader=NoTouch(),
    )


def test_status_without_evidence_is_not_a_live_backup():
    result = op.release_status()
    assert result["status"] == "BACKUP_NOT_LIVE_RELEASE_HOLD"
    assert result["backup_running"] is False
    assert result["real_provider_requests_authorized"] is False
    assert result["real_data_capture_authorized"] is False
    assert "CLOUD_REQUESTS_COMPILED_OFF" in result["review_blockers"]


def test_even_forged_all_true_attestations_cannot_authorize_cloud(tmp_path):
    status = op.release_status(review())
    assert status["backup_running"] is False
    assert "CLOUD_REQUESTS_COMPILED_OFF" in status["review_blockers"]
    with pytest.raises(op.BackupReleaseHold, match="compiled OFF"):
        op.run_exact_approved_s02_once(**config(tmp_path))
    assert not (tmp_path / "THIS_DOES_NOT_EXIST").exists()


@pytest.mark.parametrize("name", [
    "source_processor_region_rights_verified",
    "provider_account_zero_charge_enforced",
    "bucket_versioning_privacy_retention_verified",
    "four_off_vps_scoped_identities_verified",
    "independent_data_and_manifest_keys_recoverable",
    "independent_receipt_store_verified",
    "independent_offhost_restore_verified",
    "windows_scratch_acl_and_disk_encryption_verified",
    "partial_failure_alert_and_rollback_verified",
    "owner_exact_pilot_approved",
])
def test_each_external_release_condition_has_its_own_hold(name):
    result = op.release_status(review({name: False}))
    assert len(result["review_blockers"]) == 2
    assert "CLOUD_REQUESTS_COMPILED_OFF" in result["review_blockers"]
    assert result["backup_running"] is False


def test_object_keys_match_already_scoped_pilot_credentials(tmp_path):
    # Scope must match owner-described pilot/* IAM, not historical prefix.
    assert op.REQUIRED_STORAGE_PREFIX == "pilot/vowsig/approved-s02/v1/"
    assert p2.KEY_RX.fullmatch(
        op.REQUIRED_STORAGE_PREFIX + "release-test-0001/" + "0"*64 + ".aesgcm"
    )
    assert not p2.KEY_RX.fullmatch(
        "vowsig/approved-s02/v1/release-test-0001/" + "0"*64 + ".aesgcm"
    )
    assert p7.ESCROW_PREFIX == "pilot/vowsig/private-recovery-receipts/v1"
    assert p7._identity("release-test-0001", "0"*64).startswith("pilot/")


def test_no_hidden_cloud_activation_via_environment_or_command_line():
    source = inspect.getsource(op)
    assert op.ACTUAL_PROVIDER_REQUESTS_ENABLED is False
    assert "os.environ" not in source
    assert "subprocess" not in source
    assert 'if __name__ == "__main__"' not in source
    imports = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            imports.update(x.name.split(".")[0] for x in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    assert not imports.intersection({
        "boto3", "botocore", "socket", "requests", "urllib", "subprocess"
    })
