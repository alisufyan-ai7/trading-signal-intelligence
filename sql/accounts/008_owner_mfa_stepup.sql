-- P1B-3 owner TOTP step-up, one-time offline enrollment only.
-- Existing SQL 001..006 must run before this migration; SQL 007 grants
-- are applied AFTER this migration in the isolated role proof.
-- DO NOT expose public enrollment, owner promotion or plaintext secrets.
CREATE TABLE IF NOT EXISTS vowsig_owner_totp_credentials (
    account_id UUID PRIMARY KEY REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    secret_ciphertext BYTEA NOT NULL
        CHECK (octet_length(secret_ciphertext) = 48),
    key_version INTEGER NOT NULL DEFAULT 1 CHECK (key_version = 1),
    last_accepted_step BIGINT NOT NULL DEFAULT -1 CHECK (last_accepted_step >= -1),
    failed_attempts INTEGER NOT NULL DEFAULT 0
        CHECK (failed_attempts >= 0 AND failed_attempts < 5),
    locked_until TIMESTAMPTZ,
    provisioned_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Secret insertion/rotation/delete is restricted to migrator.
-- Runtime only reads ciphertext and advances challenge replay/lock state.
-- Must NEVER allow app runtime INSERT or UPDATE(secret_ciphertext).

-- The dedicated schema uses migrations in NUMERIC order 001..008.
-- If deployed with the restricted roles in schema vowsig, grant runtime only
-- SELECT and changes to challenge-state columns. Never secret rotation.
-- The legacy disposable integration test has no named roles / vowsig schema.
DO $$
BEGIN
  IF current_schema() = 'vowsig'
     AND to_regrole('vowsig_app') IS NOT NULL
     AND to_regrole('vowsig_backup') IS NOT NULL
  THEN
    GRANT SELECT ON vowsig.vowsig_owner_totp_credentials
      TO vowsig_app, vowsig_backup;
    GRANT UPDATE (last_accepted_step,failed_attempts,locked_until)
      ON vowsig.vowsig_owner_totp_credentials TO vowsig_app;
  END IF;
END $$;
