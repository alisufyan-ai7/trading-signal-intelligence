"""P2 offline sanitized outcome-bundle validator; never a production publisher.

Only validates bytes against an externally pinned artifact digest and expected
population count. Neither digest matching nor this code proves that data was
reconciled to original immutable Windows ledgers. That independent audit and
publishing permission are separate gates; output is NOT publicly surfaced.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any

from trading_signal_intelligence.product.accounts.performance import utc_time, MetricContractError

_HASH = re.compile(r"^[0-9a-f]{64}$")
ALLOWED_PROGRAMS = frozenset({
    "core-ai-shadow", "market-expansion-1", "crypto-expansion-1",
})
_RECORD_FIELDS = frozenset({
    "entity_id", "source_record_sha256", "state", "combined_net_r",
    "after_costs_verified", "cost_model_version", "exit_at_utc",
    "program_id", "model_version", "cohort",
})
_BUNDLE_FIELDS = frozenset({
    "schema_version", "source_program_id", "model_version", "cohort",
    "source_head_hash", "records",
})


class ReadModelValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CheckedBundle:
    artifact_sha256: str
    source_program_id: str
    model_version: str
    cohort: str
    source_head_hash: str
    record_count: int
    records: tuple[dict[str, Any], ...]
    source_ledger_independently_reconciled: bool = False
    customer_signal_publication_permitted: bool = False


def check_sanitized_bundle(
    raw: bytes, *, pinned_artifact_sha256: str,
    expected_source_records: int, pinned_source_head_hash: str,
) -> CheckedBundle:
    """Strictly reject partial, changed, mixed or unsanitized batch data."""
    if (
        not isinstance(raw, bytes) or len(raw) > 25_000_000
        or not _HASH.fullmatch(pinned_artifact_sha256)
        or not _HASH.fullmatch(pinned_source_head_hash)
        or type(expected_source_records) is not int
        or expected_source_records < 0
    ):
        raise ReadModelValidationError("Missing exact independently specified pins")
    actual = hashlib.sha256(raw).hexdigest()
    if actual != pinned_artifact_sha256:
        raise ReadModelValidationError("Sanitized artifact digest mismatch")
    try:
        def no_duplicate_keys(pairs):
            out = {}
            for key, value in pairs:
                if key in out:
                    raise ValueError("Duplicate manifest key")
                out[key] = value
            return out
        def no_nonfinite(value):
            raise ValueError("Non-finite JSON constant")
        manifest = json.loads(raw.decode("utf-8"),
                              object_pairs_hook=no_duplicate_keys,
                              parse_constant=no_nonfinite)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ReadModelValidationError("Invalid JSON UTF-8 sanitized manifest") from exc
    if not isinstance(manifest, dict) or set(manifest) != _BUNDLE_FIELDS:
        raise ReadModelValidationError("Unexpected or missing manifest keys")
    if manifest["schema_version"] != 1:
        raise ReadModelValidationError("Unknown manifest version")
    program = manifest["source_program_id"]
    model = manifest["model_version"]
    cohort = manifest["cohort"]
    head = manifest["source_head_hash"]
    if (
        not isinstance(program, str) or program not in ALLOWED_PROGRAMS
        or not isinstance(model, str) or not 1 <= len(model) <= 128
        or not isinstance(cohort, str) or not 1 <= len(cohort) <= 128
        or head != pinned_source_head_hash
    ):
        raise ReadModelValidationError("Wrong source lineage or head")
    records = manifest["records"]
    if not isinstance(records, list) or len(records) != expected_source_records:
        raise ReadModelValidationError("Incomplete source population")
    seen: set[str] = set()
    for r in records:
        if not isinstance(r, dict) or set(r) != _RECORD_FIELDS:
            raise ReadModelValidationError("Unsanitized or incomplete record")
        if (r["program_id"] != program or r["model_version"] != model
                or r["cohort"] != cohort or not isinstance(r["entity_id"], str)
                or not 1 <= len(r["entity_id"]) <= 128 or r["entity_id"] in seen
                or not isinstance(r["source_record_sha256"], str)
                or not _HASH.fullmatch(r["source_record_sha256"])):
            raise ReadModelValidationError("Invalid, duplicate or mixed source record")
        seen.add(r["entity_id"])
        if r["state"] not in ("closed", "open", "no_trade", "rejected", "error"):
            raise ReadModelValidationError("Unexpected lifecycle state")
        if r["state"] == "closed":
            n = r["combined_net_r"]
            if (
                type(n) not in (int, float) or not math.isfinite(n)
                or r["after_costs_verified"] is not True
                or not isinstance(r["cost_model_version"], str)
                or not 1 <= len(r["cost_model_version"]) <= 128
            ):
                raise ReadModelValidationError("Missing finite after-cost completed R")
            try:
                utc_time(r["exit_at_utc"])
            except MetricContractError as exc:
                raise ReadModelValidationError("Closed outcome needs UTC exit") from exc
        elif (
            r["combined_net_r"] is not None or r["exit_at_utc"] is not None
            or r["after_costs_verified"] is not False
            or r["cost_model_version"] is not None
        ):
            raise ReadModelValidationError("Uncompleted event cannot contain realized R")
    return CheckedBundle(
        artifact_sha256=actual, source_program_id=program,
        model_version=model, cohort=cohort, source_head_hash=head,
        record_count=len(records), records=tuple(records),
    )
