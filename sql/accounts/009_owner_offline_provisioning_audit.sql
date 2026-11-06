-- P1B-4 offline, reviewer-approved first-owner provisioning and recovery.
-- Apply only AFTER 001..008 as restricted vowsig_migrator in schema vowsig.
-- No public application enrollment or owner promotion is permitted.
CREATE TABLE IF NOT EXISTS vowsig_owner_provisioning_audit (
    operation_id UUID PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES vowsig_accounts(id) ON DELETE RESTRICT,
    operation TEXT NOT NULL CHECK (operation IN ('first_owner','rotate_factor')),
    reviewer_id TEXT NOT NULL CHECK (length(reviewer_id) BETWEEN 3 AND 100),
    operator_id TEXT NOT NULL CHECK (length(operator_id) BETWEEN 3 AND 100),
    CONSTRAINT vowsig_owner_independent_review CHECK (operator_id <> reviewer_id),
    approved_payload_sha256 CHAR(64) NOT NULL
      CHECK (approved_payload_sha256 ~ '^[0-9a-f]{64}$'),
    revoked_sessions INTEGER NOT NULL CHECK (revoked_sessions >= 0),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vowsig_owner_provisioning_unique_approval
      UNIQUE (approved_payload_sha256)
);
-- Audit rows are append-only for the runtime. Only the migration operator can
-- INSERT a record. There is no HTTP API for this table.
-- 007 granted SELECT to backup by default for new migrator-owned tables.
-- No public / app runtime DML granted.
