"""Fail-closed, signed source-ledger attestations for owner Performance Lab.

The app NEVER signs an attestation or promotes quarantined source facts.
A separate independently reviewed, owner-approved audit must produce the
Ed25519-signed manifest from *original* immutable ledgers, pin the trusted
reviewer public key, and explicitly authorize the cohort's source rights.
No manifest is shipped by default, therefore no performance can be certified.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from typing import Any

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.serialization import load_pem_public_key
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from trading_signal_intelligence.product.accounts.performance import (
    MetricContractError, complete_performance, utc_time,
)

_HEX64 = re.compile(r"^[0-9a-f]{64}$")
_SIGNATURE = re.compile(r"^[A-Za-z0-9_-]{86}$")
_FIELDS = frozenset({
    "schema_version", "source_program_id", "model_version", "cohort",
    "source_head_hash", "source_snapshot_sha256",
    "expected_population_count", "expected_closed_count",
    "outcome_population_sha256", "source_evidence_sha256",
    "source_rights_approved", "independent_source_reconciliation",
    "reviewer_id", "verified_at_utc",
    "window_start_utc", "window_end_utc", "as_of_utc",
    "cost_model_version",
})
_ROW_FIELDS = (
    "entity_id", "source_record_sha256", "state", "exit_at_utc",
    "combined_net_r", "cost_model_version", "after_costs_verified",
    "cohort",
)
_MAX_ROWS = 250_000


class HistoryAttestationError(ValueError):
    """Signed evidence mismatch: never allow fallback to partial performance."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, allow_nan=False,
        sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _decode_unique(raw: bytes) -> dict[str, Any]:
    if not isinstance(raw, bytes) or len(raw) > 64_000:
        raise HistoryAttestationError("Missing or oversized signed source attestation")
    def unique(pairs):
        result = {}
        for k, v in pairs:
            if k in result:
                raise ValueError("Duplicate JSON key")
            result[k] = v
        return result
    try:
        obj = json.loads(
            raw.decode("utf-8"), object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")),
        )
    except (ValueError, UnicodeDecodeError) as exc:
        raise HistoryAttestationError("Invalid signed source JSON") from exc
    if not isinstance(obj, dict) or set(obj) != {"attestation", "signature_ed25519_b64u"}:
        raise HistoryAttestationError("Unexpected signed source envelope")
    return obj


def verify_signed_history_attestation(
    signed_bytes: bytes, *, reviewer_public_key_pem: bytes,
) -> dict[str, Any]:
    """Authenticate an independently supplied reviewer document before SQL lookup.

    Verification proves integrity under a TRUSTED key; it is not itself proof
    that the reviewer inspected the original ledger or owns data rights.
    """
    envelope = _decode_unique(signed_bytes)
    body = envelope["attestation"]
    signature = envelope["signature_ed25519_b64u"]
    if not isinstance(body, dict) or set(body) != _FIELDS:
        raise HistoryAttestationError("Incomplete original-ledger attestation")
    if not isinstance(signature, str) or not _SIGNATURE.fullmatch(signature):
        raise HistoryAttestationError("Invalid signed source signature encoding")
    try:
        key = load_pem_public_key(reviewer_public_key_pem)
        if not isinstance(key, Ed25519PublicKey):
            raise HistoryAttestationError("Reviewer key must be Ed25519")
        signature_bytes = base64.urlsafe_b64decode(signature + "==")
        if len(signature_bytes) != 64:
            raise HistoryAttestationError("Invalid Ed25519 signature length")
        key.verify(signature_bytes, _canonical(body))
    except (ValueError, TypeError, InvalidSignature, binascii.Error) as exc:
        raise HistoryAttestationError("Independent reviewer signature invalid") from exc

    if body["schema_version"] != 1 or type(body["schema_version"]) is not int:
        raise HistoryAttestationError("Unknown independent source schema")
    if (body["independent_source_reconciliation"] is not True
            or body["source_rights_approved"] is not True):
        raise HistoryAttestationError("Original source audit and rights not approved")
    for name in ("source_snapshot_sha256", "outcome_population_sha256",
                 "source_evidence_sha256"):
        if not isinstance(body[name], str) or not _HEX64.fullmatch(body[name]):
            raise HistoryAttestationError("Missing independent source hash")
    if (not isinstance(body["source_head_hash"], str)
            or not 1 <= len(body["source_head_hash"]) <= 128):
        raise HistoryAttestationError("Missing source ledger head")
    for name in ("source_program_id", "model_version", "cohort",
                 "cost_model_version", "reviewer_id"):
        if not isinstance(body[name], str) or not 1 <= len(body[name]) <= 128:
            raise HistoryAttestationError("Missing reviewer/source identity")
    n, closed = body["expected_population_count"], body["expected_closed_count"]
    if (type(n) is not int or type(closed) is not int
            or n < 1 or n > _MAX_ROWS or closed < 0 or closed > n):
        raise HistoryAttestationError("Invalid independently reviewed population size")
    try:
        start = utc_time(body["window_start_utc"])
        end = utc_time(body["window_end_utc"])
        asof = utc_time(body["as_of_utc"])
        reviewed = utc_time(body["verified_at_utc"])
    except (MetricContractError, TypeError) as exc:
        raise HistoryAttestationError("Invalid signed UTC window") from exc
    if not start < end <= asof or reviewed < end or reviewed > datetime.now(timezone.utc):
        raise HistoryAttestationError("Invalid reviewer/source time ordering")
    return body


def _normalized_row(record: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise HistoryAttestationError("Non-object source outcome")
    if any(f not in record for f in _ROW_FIELDS):
        raise HistoryAttestationError("Incomplete source projection")
    state = record["state"]
    net = record["combined_net_r"]
    exit_at = record["exit_at_utc"]
    if state == "closed":
        if type(net) not in (float, int) or not math.isfinite(net):
            raise HistoryAttestationError("Incomplete cost-normalized outcome")
        if isinstance(exit_at, datetime):
            if exit_at.tzinfo is None:
                raise HistoryAttestationError("Unzoned closed outcome")
            exit_at = exit_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
        else:
            try:
                exit_at = utc_time(exit_at).isoformat().replace("+00:00", "Z")
            except MetricContractError as exc:
                raise HistoryAttestationError("Invalid source exit time") from exc
    elif state in ("open", "no_trade", "rejected", "error"):
        if net is not None or exit_at is not None:
            raise HistoryAttestationError("Non-closed outcome contains realized result")
        exit_at = None
    else:
        raise HistoryAttestationError("Unknown outcome state")
    return {
        "entity_id": record["entity_id"],
        "source_record_sha256": record["source_record_sha256"],
        "state": state, "exit_at_utc": exit_at,
        "combined_net_r": float(net) if state == "closed" else None,
        "cost_model_version": record["cost_model_version"],
        "after_costs_verified": record["after_costs_verified"],
        "cohort": record["cohort"],
    }


def outcome_population_sha256(facts: list[dict[str, Any]]) -> str:
    """Exact full-population source audit digest, sorted by immutable identity."""
    if not isinstance(facts, list) or not 1 <= len(facts) <= _MAX_ROWS:
        raise HistoryAttestationError("Missing/oversized outcome population")
    normalized = [_normalized_row(row) for row in facts]
    identities = [row["entity_id"] for row in normalized]
    if not all(isinstance(x, str) and x for x in identities) or len(set(identities)) != len(identities):
        raise HistoryAttestationError("Missing or duplicate source outcome identity")
    return hashlib.sha256(
        _canonical(sorted(normalized, key=lambda row: row["entity_id"]))
    ).hexdigest()


def reconcile_attested_history(
    attestation: dict[str, Any], *,
    snapshot: dict[str, Any], facts: list[dict[str, Any]],
) -> dict[str, Any]:
    """Require trusted audit, DB approval AND exact row-level population proof."""
    if not isinstance(attestation, dict) or not isinstance(snapshot, dict):
        raise HistoryAttestationError("Independent source metadata absent")
    expected = {
        "source_program_id": "source_program_id",
        "model_version": "model_version",
        "source_head_hash": "source_head_hash",
        "source_snapshot_sha256": "source_snapshot_sha256",
    }
    if any(snapshot.get(k) != attestation.get(v) for k, v in expected.items()):
        raise HistoryAttestationError("Database source anchor mismatches independent audit")
    if snapshot.get("ingest_status") != "verified" or snapshot.get("completeness_verified") is not True:
        raise HistoryAttestationError("Source projection not independently promoted")
    if len(facts) != attestation["expected_population_count"]:
        raise HistoryAttestationError("Full outcome population count mismatch")
    if (sum(row.get("state") == "closed" for row in facts)
            != attestation["expected_closed_count"]):
        raise HistoryAttestationError("Full completed population count mismatch")
    if outcome_population_sha256(facts) != attestation["outcome_population_sha256"]:
        raise HistoryAttestationError("Independent full-population digest mismatch")
    for row in facts:
        if row.get("cohort") != attestation["cohort"]:
            raise HistoryAttestationError("Mixed source cohort")
    report_facts = [{
        "program_id": attestation["source_program_id"],
        "model_version": attestation["model_version"],
        "cohort": attestation["cohort"],
        "entity_id": row["entity_id"],
        "source_record_sha256": row["source_record_sha256"],
        "state": row["state"],
        "combined_net_r": row["combined_net_r"],
        "exit_at_utc": _normalized_row(row)["exit_at_utc"],
        "after_costs_verified": row["after_costs_verified"],
        "cost_model_version": row["cost_model_version"],
    } for row in facts]
    try:
        performance = complete_performance(
            report_facts,
            program_id=attestation["source_program_id"],
            model_version=attestation["model_version"],
            cohort=attestation["cohort"],
            window_start_utc=attestation["window_start_utc"],
            window_end_utc=attestation["window_end_utc"],
            as_of_utc=attestation["as_of_utc"],
            source_snapshot_sha256=attestation["source_snapshot_sha256"],
            cost_model_version=attestation["cost_model_version"],
        )
    except MetricContractError as exc:
        raise HistoryAttestationError("Verified history metric contract failed") from exc
    return {
        "status": "independently_attested_source_history",
        "verified_full_history": False,
        "verified_full_cohort_history": True,
        "platform_history_population_reconciled": False,
        "source_ledger_independently_reconciled": True,
        "performance": performance,
        "reviewer_id": attestation["reviewer_id"],
        "source_evidence_sha256": attestation["source_evidence_sha256"],
        "reviewed_at_utc": attestation["verified_at_utc"],
        "rights_approved": True,
        "research_only": True,
        "broker_execution_pnl_available": False,
    }
