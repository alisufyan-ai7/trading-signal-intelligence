"""P2 offline deterministic, idempotent PostgreSQL quarantine replay.

No cloud HTTP endpoint. No Windows ledger access. Replays *sanitized, externally
hash-pinned* complete bundles to an isolated QUARANTINED projection. A hash and
a row-count assertion cannot certify source ledger authenticity/rights; neither
an ingest_status promotion nor public/admin performance publishing exists here.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from trading_signal_intelligence.product.accounts.performance import utc_time
from trading_signal_intelligence.product.accounts.read_model import (
    ReadModelValidationError, check_sanitized_bundle,
)

class ProjectionReplayError(ValueError):
    pass


def _same_fact(database_row: dict[str, Any], incoming: dict[str, Any]) -> bool:
    actual_exit = database_row["exit_at_utc"]
    actual_exit = actual_exit.astimezone(timezone.utc) if actual_exit else None
    expected_exit = utc_time(incoming["exit_at_utc"]) if incoming["state"] == "closed" else None
    return (
        database_row["entity_id"] == incoming["entity_id"]
        and database_row["source_record_sha256"] == incoming["source_record_sha256"]
        and database_row["state"] == incoming["state"]
        and database_row["combined_net_r"] == incoming["combined_net_r"]
        and database_row["after_costs_verified"] is incoming["after_costs_verified"]
        and database_row["cost_model_version"] == incoming["cost_model_version"]
        and actual_exit == expected_exit
    )


def replay_quarantined_bundle(
    conn, raw: bytes, *, pinned_artifact_sha256: str,
    pinned_source_head_hash: str, expected_source_records: int,
    observed_at_utc: str,
) -> dict[str, Any]:
    """Replays only verified-shape bytes; pins supplied separately by operator.

    Callable only by an authorized offline process with an isolated migration/
    ingestion role. No assertion of independent reconciliation is made.
    """
    manifest = check_sanitized_bundle(
        raw, pinned_artifact_sha256=pinned_artifact_sha256,
        pinned_source_head_hash=pinned_source_head_hash,
        expected_source_records=expected_source_records,
    )
    try:
        observed = utc_time(observed_at_utc)
    except ValueError as exc:
        raise ProjectionReplayError("UTC source observation required") from exc
    with conn.transaction():
        row = conn.execute(
            """INSERT INTO vowsig_research_source_snapshots
               (source_program_id,model_version,source_snapshot_sha256,
                source_head_hash,observed_at_utc,ingest_status,completeness_verified)
               VALUES (%s,%s,%s,%s,%s,'quarantined',FALSE)
               ON CONFLICT DO NOTHING RETURNING id""",
            (manifest.source_program_id,manifest.model_version,
             manifest.artifact_sha256,manifest.source_head_hash,observed),
        ).fetchone()
        inserted = row is not None
        if not inserted:
            row = conn.execute(
                """SELECT id,source_head_hash,ingest_status,completeness_verified
                   FROM vowsig_research_source_snapshots
                   WHERE source_program_id=%s AND model_version=%s
                     AND source_snapshot_sha256=%s FOR UPDATE""",
                (manifest.source_program_id,manifest.model_version,manifest.artifact_sha256),
            ).fetchone()
            if row is None or row["source_head_hash"] != manifest.source_head_hash:
                raise ProjectionReplayError("Existing source projection pin mismatch")
            # Do not silently overwrite previously reviewed or rejected cohorts.
            if row["ingest_status"] != "quarantined" or row["completeness_verified"]:
                raise ProjectionReplayError("Only quarantined snapshots can be replayed")
        snapshot_id = row["id"]
        if inserted:
            for record in manifest.records:
                conn.execute(
                    """INSERT INTO vowsig_research_outcome_facts
                       (source_snapshot_id,source_program_id,model_version,
                        cohort,entity_id,state,source_record_sha256,
                        exit_at_utc,combined_net_r,cost_model_version,after_costs_verified)
                       VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
                    (snapshot_id,manifest.source_program_id,manifest.model_version,
                     manifest.cohort,record["entity_id"],record["state"],
                     record["source_record_sha256"],record["exit_at_utc"],
                     record["combined_net_r"],record["cost_model_version"],
                     record["after_costs_verified"]),
                )
        actual = conn.execute(
            """SELECT entity_id,state,source_record_sha256,exit_at_utc,combined_net_r,
                      cost_model_version,after_costs_verified,cohort
               FROM vowsig_research_outcome_facts
               WHERE source_snapshot_id=%s AND source_program_id=%s
                 AND model_version=%s ORDER BY entity_id""",
            (snapshot_id,manifest.source_program_id,manifest.model_version),
        ).fetchall()
        expected = sorted(manifest.records, key=lambda x:x["entity_id"])
        if (
            len(actual)!=manifest.record_count
            or any(r["cohort"] != manifest.cohort or not _same_fact(r, s)
                   for r,s in zip(actual,expected))
        ):
            raise ProjectionReplayError("Projection replay does not exactly reconcile")
    return {
        "source_snapshot_id":snapshot_id,
        "source_program_id":manifest.source_program_id,
        "source_snapshot_sha256":manifest.artifact_sha256,
        "record_count":manifest.record_count,
        "idempotent_replay":not inserted,
        "status":"quarantined",
        "source_ledger_independently_reconciled":False,
        "customer_signal_publication_permitted":False,
    }
