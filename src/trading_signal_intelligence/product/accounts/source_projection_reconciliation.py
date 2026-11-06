"""Read-only, exact SHA-pinned sanitized cohort -> original SQLite source link.

A successful link proves only that projected row anchors really occur in an
independently pinned *source chain*. It does not verify original rights,
after-cost arithmetic, full cohort/market universe, reviewer's independence,
AI-v1.3 K5 provenance, or permission to publish returns.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from trading_signal_intelligence.product.accounts.read_model import (
    check_sanitized_bundle, ReadModelValidationError,
)
from trading_signal_intelligence.product.accounts.source_ledger_audit import (
    audit_pinned_source, SourceLedgerAuditError,
)

_SOURCE_EVENTS = {
    "closed":"EXIT",
    "open":"SIGNAL",
    "no_trade":"NO_TRADE",
    "rejected":"REJECTED_INFERENCE",
    "error":"ERROR",
}


class SourceProjectionReconciliationError(ValueError):
    pass


def check_source_projection_link(
    *,
    sqlite_path: str | Path,
    source_profile: str,
    expected_source_head_sha256: str,
    expected_source_ledger_records: int,
    sanitized_bundle: bytes,
    expected_bundle_sha256: str,
    expected_outcome_population: int,
    expected_source_program_id: str,
    expected_model_version: str,
    expected_cohort: str,
) -> dict[str, Any]:
    """Require independently provided source pins and exact bundle membership.

    Source is opened read-only; no database migration, editor, replay, network
    request, secret, or raw record export is performed. The operator must have
    frozen the SQLite source via an approved immutable snapshot beforehand.
    """
    try:
        checked=check_sanitized_bundle(
            sanitized_bundle,
            pinned_artifact_sha256=expected_bundle_sha256,
            expected_source_records=expected_outcome_population,
            pinned_source_head_hash=expected_source_head_sha256,
        )
    except ReadModelValidationError as exc:
        raise SourceProjectionReconciliationError("Sanitized bundle pin/contract invalid") from exc
    if (checked.source_program_id!=expected_source_program_id
            or checked.model_version!=expected_model_version
            or checked.cohort!=expected_cohort):
        raise SourceProjectionReconciliationError("External program/model/cohort pin mismatch")
    if source_profile not in ("ai_v1","s02_forward"):
        raise SourceProjectionReconciliationError("Original source profile not approved")
    if checked.source_program_id=="crypto-expansion-1":
        raise SourceProjectionReconciliationError(
            "Crypto source requires its separate independent K5 audit"
        )
    # Only exact real ledger record hashes and the corresponding event IDs
    # are admitted; two outcomes cannot reuse the same event anchor.
    anchors: dict[str,tuple[str,str]]={}
    for r in checked.records:
        record_hash=r["source_record_sha256"]
        if record_hash in anchors:
            raise SourceProjectionReconciliationError("Duplicate anchored original source row")
        anchors[record_hash]=(r["entity_id"],_SOURCE_EVENTS[r["state"]])
    try:
        receipt=audit_pinned_source(
            sqlite_path, profile=source_profile,
            expected_head_sha256=expected_source_head_sha256,
            expected_records=expected_source_ledger_records,
            required_source_anchors=anchors,
        )
    except SourceLedgerAuditError as exc:
        raise SourceProjectionReconciliationError("Original source chain/anchor mismatch") from exc
    if receipt["matched_projection_anchors"] != checked.record_count:
        raise SourceProjectionReconciliationError("Original source coverage incomplete")
    return {
        "status":"PINNED_SOURCE_TO_PROJECTION_ANCHORS_MATCH",
        "source_program_id":checked.source_program_id,
        "model_version":checked.model_version,
        "cohort":checked.cohort,
        "source_profile":source_profile,
        "source_ledger_head_sha256":receipt["head_sha256"],
        "source_ledger_record_count":receipt["records"],
        "source_sequence_chain_sha256":receipt["sequence_chain_sha256"],
        "source_record_type_counts":receipt["record_type_counts"],
        "sanitized_bundle_sha256":checked.artifact_sha256,
        "sanitized_projected_outcomes":checked.record_count,
        "matched_projected_source_anchors":receipt["matched_projection_anchors"],
        "raw_source_payloads_exported":False,
        "complete_source_universe_reconciled":False,
        "independent_source_rights_approved":False,
        "independent_after_costs_proven":False,
        "all_market_history_verified":False,
        "broker_execution_enabled":False,
        "customer_signal_publication_permitted":False,
        "notice":(
            "This matches projected event anchors to an independently pinned "
            "source chain, NOT to independently reviewed complete trade "
            "population or after-cost results. No publication or role change."
        ),
    }
