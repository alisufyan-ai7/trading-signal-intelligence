-- P2 immutable-source *projection* schema. No direct SQLite access, no API writer.
-- Pending explicit lawful/sanitized, source-hash-reconciled ingest/replay gate.
CREATE TABLE IF NOT EXISTS vowsig_research_source_snapshots (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source_program_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    source_snapshot_sha256 CHAR(64) NOT NULL
      CHECK (source_snapshot_sha256 ~ '^[0-9a-f]{64}$'),
    source_head_hash TEXT,
    observed_at_utc TIMESTAMPTZ NOT NULL,
    completeness_verified BOOLEAN NOT NULL DEFAULT FALSE,
    ingest_status TEXT NOT NULL DEFAULT 'quarantined'
      CHECK (ingest_status IN ('quarantined','verified','rejected')),
    UNIQUE(source_program_id, model_version, source_snapshot_sha256)
);
CREATE TABLE IF NOT EXISTS vowsig_research_outcome_facts (
    source_snapshot_id BIGINT NOT NULL
      REFERENCES vowsig_research_source_snapshots(id) ON DELETE RESTRICT,
    source_program_id TEXT NOT NULL,
    model_version TEXT NOT NULL,
    cohort TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    state TEXT NOT NULL
      CHECK (state IN ('closed','open','no_trade','rejected','error')),
    source_record_sha256 CHAR(64) NOT NULL
      CHECK (source_record_sha256 ~ '^[0-9a-f]{64}$'),
    exit_at_utc TIMESTAMPTZ,
    combined_net_r DOUBLE PRECISION,
    cost_model_version TEXT,
    after_costs_verified BOOLEAN NOT NULL DEFAULT FALSE,
    PRIMARY KEY (source_snapshot_id,source_program_id,model_version,entity_id),
    CONSTRAINT vowsig_closed_costs CHECK (
      (state = 'closed'
        AND exit_at_utc IS NOT NULL AND combined_net_r IS NOT NULL
        AND combined_net_r NOT IN ('NaN'::float8, 'Infinity'::float8,
                                   '-Infinity'::float8)
        AND after_costs_verified
        AND cost_model_version IS NOT NULL)
      OR
      (state <> 'closed' AND exit_at_utc IS NULL AND combined_net_r IS NULL
        AND NOT after_costs_verified)
    )
);
CREATE INDEX IF NOT EXISTS vowsig_outcomes_window
 ON vowsig_research_outcome_facts (source_program_id,model_version,cohort,exit_at_utc);
-- Future authorized ingest must be idempotent, signed/pinned, versioned,
-- transactional and byte-for-byte reconciled to immutable source; reject
-- partial/missing events. No signals are auto-published by these tables.
