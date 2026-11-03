"""Integrated single-S02 backup candidate -- NEVER an implicit live uploader.

One library boundary for the already-reviewed P1 source/AEAD, P2 five signed
AWS/B2 operations, P6 exact private VersionId sink, and P7 exclusive escrow.
The external rights/$0/accounts/recovery approval has NOT been established.
Consequently this candidate is physically OFF until a *separate reviewed code
revision* establishes an independently validated release gate.

No import-time files, credentials, network, tasks, SDK clients or source read.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from . import live_sqlite_envelope_v0_1 as core
from . import live_dual_provider_transport_v0_1 as transport
from . import offline_private_receipt_handoff_v0_1 as handoff
from . import offline_immutable_receipt_escrow_v0_1 as escrow
from . import backup_release_evidence_gate_v0_1 as evidence

# Never change in response to an environment variable, CLI option, plaintext
# authorization phrase, owner-approved hash, or automated configuration file.
# A separately security-reviewed exact-SHA patch is required for a live pilot.
ACTUAL_PROVIDER_REQUESTS_ENABLED = False
ONE_SHOT_ONLY = True
REQUIRED_STORAGE_PREFIX = "pilot/vowsig/approved-s02/v1/"


class BackupReleaseHold(RuntimeError):
    """Never echo a cloud key, data row, callback exception or VersionId."""


@dataclass(frozen=True)
class OperatorReleaseReview:
    """Explicit external facts; syntax is not substantive verification."""
    source_processor_region_rights_verified: bool
    provider_account_zero_charge_enforced: bool
    bucket_versioning_privacy_retention_verified: bool
    four_off_vps_scoped_identities_verified: bool
    independent_data_and_manifest_keys_recoverable: bool
    independent_receipt_store_verified: bool
    independent_offhost_restore_verified: bool
    windows_scratch_acl_and_disk_encryption_verified: bool
    partial_failure_alert_and_rollback_verified: bool
    owner_exact_pilot_approved: bool
    approval_reference_sha256: str

    def blockers(self) -> tuple[str, ...]:
        required = (
            ("STORAGE_RIGHTS_HOLD", self.source_processor_region_rights_verified),
            ("HARD_ZERO_COST_HOLD", self.provider_account_zero_charge_enforced),
            ("BUCKET_SECURITY_HOLD", self.bucket_versioning_privacy_retention_verified),
            ("CLOUD_IDENTITIES_HOLD", self.four_off_vps_scoped_identities_verified),
            ("RECOVERY_KEY_CUSTODY_HOLD", self.independent_data_and_manifest_keys_recoverable),
            ("INDEPENDENT_ESCROW_HOLD", self.independent_receipt_store_verified),
            ("REAL_OFFHOST_RESTORE_HOLD", self.independent_offhost_restore_verified),
            ("WINDOWS_SCRATCH_SECURITY_HOLD", self.windows_scratch_acl_and_disk_encryption_verified),
            ("INCIDENT_RESPONSE_HOLD", self.partial_failure_alert_and_rollback_verified),
            ("EXACT_PILOT_APPROVAL_HOLD", self.owner_exact_pilot_approved),
        )
        missing = [code for code, ok in required if ok is not True]
        if (type(self.approval_reference_sha256) is not str
                or not core.HEX64.fullmatch(self.approval_reference_sha256)):
            missing.append("RELEASE_REFERENCE_HOLD")
        return tuple(missing)


def release_status(review: OperatorReleaseReview | None = None) -> dict:
    """Read-only, zero-credential status. Does not infer account readiness."""
    if review is not None and type(review) is not OperatorReleaseReview:
        raise BackupReleaseHold("release review type rejected")
    blockers = (
        review.blockers() if review is not None else
        ("EXTERNAL_EVIDENCE_NOT_PROVIDED",)
    )
    if not ACTUAL_PROVIDER_REQUESTS_ENABLED:
        blockers += ("CLOUD_REQUESTS_COMPILED_OFF",)
    return {
        "status": "BACKUP_NOT_LIVE_RELEASE_HOLD",
        "backup_running": False,
        "real_provider_requests_authorized": False,
        "real_data_capture_authorized": False,
        "scope": core.SOURCE_REL,
        "aws_region": transport.AWS.region,
        "b2_region": transport.B2.region,
        "review_blockers": list(blockers),
        "next_milestone": "INDEPENDENT_RELEASE_EVIDENCE_AND_EXACT_OWNER_SIGNOFF",
    }


def _validate_before_source_or_provider(
    *, review: OperatorReleaseReview,
    signed_evidence: evidence.ReleaseEvidenceAssessment,
    source_authorization: core.SourceAuthorization,
    transfer_authorization: transport.ReleaseAuthorization,
    data_key: bytes, manifest_key: bytes,
    escrow_writer: Callable, escrow_reader: Callable,
    four_clients: tuple[Any, Any, Any, Any],
) -> None:
    # Absolute gate BEFORE touching database, credentials or network.
    if not ACTUAL_PROVIDER_REQUESTS_ENABLED:
        raise BackupReleaseHold("cloud requests are compiled OFF")
    if type(review) is not OperatorReleaseReview or review.blockers():
        raise BackupReleaseHold("external release gates remain unverified")
    if (type(signed_evidence) is not evidence.ReleaseEvidenceAssessment
            or signed_evidence.live_provider_requests_authorized is not True
            or signed_evidence.independently_verified_provider_accounts is not True
            or signed_evidence.independently_verified_zero_spend is not True
            or signed_evidence.independently_verified_storage_rights is not True):
        raise BackupReleaseHold("independent signed release evaluation missing")
    if (type(source_authorization) is not core.SourceAuthorization
            or type(transfer_authorization) is not transport.ReleaseAuthorization
            or type(data_key) is not bytes or len(data_key) != 32
            or type(manifest_key) is not bytes or len(manifest_key) != 32
            or data_key == manifest_key
            or not callable(escrow_writer) or not callable(escrow_reader)
            or escrow_writer is escrow_reader
            or type(four_clients) is not tuple or len(four_clients) != 4):
        raise BackupReleaseHold("secure one-shot operator inputs missing")
    source_authorization.validate()
    if (source_authorization.permitted_provider_regions
            != (transport.AWS.region, transport.B2.region)):
        raise BackupReleaseHold("unapproved provider region pair")


def run_exact_approved_s02_once(
    *, repo_root: Path, scratch_parent: Path, run_id: str,
    release_review: OperatorReleaseReview,
    signed_evidence: evidence.ReleaseEvidenceAssessment,
    source_authorization: core.SourceAuthorization,
    transfer_authorization: transport.ReleaseAuthorization,
    data_key: bytes, manifest_key: bytes,
    escrow_write_once: Callable[[str, bytes, str], dict],
    escrow_read_exact: Callable[[str], bytes],
    writer_scope_ref_sha256: str, reader_scope_ref_sha256: str,
    recovery_custody_ref_sha256: str,
    aws_writer: Any, aws_reader: Any, b2_writer: Any, b2_reader: Any,
) -> dict:
    """Prospective manual one-shot orchestration. NOT callable for live I/O.

    Any later enabled release must first independently verify all conditions,
    enforce chosen provider-side no-overwrite and signed transport/ACL behavior,
    ensure real encrypted receipt durability, and update release evidence gate
    through an exact reviewed SHA. No automatic retries, resumption or deletes.
    """
    clients = (aws_writer, aws_reader, b2_writer, b2_reader)
    _validate_before_source_or_provider(
        review=release_review, signed_evidence=signed_evidence,
        source_authorization=source_authorization,
        transfer_authorization=transfer_authorization,
        data_key=data_key, manifest_key=manifest_key,
        escrow_writer=escrow_write_once, escrow_reader=escrow_read_exact,
        four_clients=clients,
    )
    # Everything below is unreachable in this specific reviewed revision.
    # Preserve no-overwrite scratch and always require a separate manifest
    # store; never equate local-readback with independently durable receipt.
    try:
        snapshot = core.capture_approved_s02(
            repo_root=Path(repo_root), scratch_parent=Path(scratch_parent),
            run_id=run_id, authorization=source_authorization,
        )
        sealed = core.seal_verified_copy(
            copied=snapshot, run_id=run_id, key=data_key,
            authorization=source_authorization,
        )
        if not sealed.object_key.startswith(REQUIRED_STORAGE_PREFIX):
            raise BackupReleaseHold("cloud principal prefix is incompatible")
        sink = handoff.OfflinePrivateReceiptSink(
            data_key=data_key, manifest_key=manifest_key,
            key_custody_ref_sha256=recovery_custody_ref_sha256,
            commit_and_readback=escrow.OfflineImmutableReceiptEscrow(
                write_once=escrow_write_once, read_exact=escrow_read_exact,
                writer_scope_ref_sha256=writer_scope_ref_sha256,
                reader_scope_ref_sha256=reader_scope_ref_sha256,
                owner_recovery_custody_ref_sha256=recovery_custody_ref_sha256,
            ),
        )
        result = transport.replicate_approved_s02(
            obj=sealed, key=data_key, authorization=transfer_authorization,
            aws_writer=aws_writer, aws_reader=aws_reader,
            b2_writer=b2_writer, b2_reader=b2_reader,
            recovery_scratch=Path(scratch_parent),
            require_private_receipt=True, private_receipt_sink=sink,
        )
        if (result.get("status") != "LIVE_S02_TWO_PROVIDER_VERIFIED_LOCAL_RECEIPT_ONLY"
                or result.get("attempted_signed_requests") != 5
                or result.get("offhost_persistence_verified") is not False):
            raise BackupReleaseHold("private encrypted backup receipt not independently durable")
        # This software path cannot self-certify independent remote
        # persistence. A future release must use separate external evidence.
        return {
            "status": "DUAL_PROVIDER_RESTORED_LOCAL_RECEIPT_ONLY",
            "offhost_persistence_verified": False,
            "real_disaster_recovery_verified": False,
            "production_backup_scheduler_enabled": False,
            "provider_requests_attempted": 5,
        }
    except Exception:
        # Do not lie about whether writes may already have succeeded on
        # partial cloud failure; never automatically retry or delete.
        raise BackupReleaseHold(
            "one-shot backup stopped; remote partial state UNKNOWN; manual reconciliation required"
        ) from None
