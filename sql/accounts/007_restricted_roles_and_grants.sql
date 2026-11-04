-- P1B-2 least privilege access policy. Apply ONLY AFTER:
-- * PostgreSQL roles vowsig_app, vowsig_migrator, vowsig_backup exist;
-- * schema vowsig is owned by vowsig_migrator;
-- * migrations 001-006 ran as vowsig_migrator with search_path vowsig,pg_catalog.
-- This file never creates production roles or touches public tables.
-- Runtime and backup permissions intentionally exclude every research write.
-- Must be executed as vowsig_migrator within the vowsig schema.
DO $$
BEGIN
  IF current_schema() <> 'vowsig'
     OR current_user <> 'vowsig_migrator'
     OR NOT EXISTS(
       SELECT 1 FROM pg_catalog.pg_namespace
       WHERE nspname = 'vowsig' AND nspowner = (
         SELECT oid FROM pg_catalog.pg_roles WHERE rolname = 'vowsig_migrator'
       )
     )
  THEN
    RAISE EXCEPTION 'vowsig grant policy requires migrator-owned isolated schema';
  END IF;
END $$;

REVOKE ALL ON SCHEMA vowsig FROM PUBLIC;
REVOKE ALL ON ALL TABLES IN SCHEMA vowsig FROM PUBLIC;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA vowsig FROM PUBLIC;

GRANT USAGE ON SCHEMA vowsig TO vowsig_app, vowsig_backup;
GRANT SELECT ON ALL TABLES IN SCHEMA vowsig TO vowsig_app, vowsig_backup;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA vowsig TO vowsig_backup;
-- App needs identity-backed INSERT sequences, not research-ingest sequences.
GRANT USAGE ON SEQUENCE
  vowsig.vowsig_account_audit_id_seq,
  vowsig.vowsig_account_identities_id_seq,
  vowsig.vowsig_account_consent_events_id_seq
TO vowsig_app;

-- Legitimate account/session/OIDC commands in accounts/store.py.
GRANT INSERT ON TABLE
  vowsig.vowsig_account_entitlements,
  vowsig.vowsig_account_identities,
  vowsig.vowsig_account_audit,
  vowsig.vowsig_account_consent_events
TO vowsig_app;
-- Only migration role may write accounts.role or promote an owner.
-- Runtime relies on the database DEFAULT role='member'.
GRANT INSERT (id, email, email_verified_at)
  ON TABLE vowsig.vowsig_accounts TO vowsig_app;

GRANT INSERT, UPDATE ON TABLE
  vowsig.vowsig_account_sessions,
  vowsig.vowsig_account_preferences,
  vowsig.vowsig_account_deletion_requests,
  vowsig.vowsig_auth_rate_windows
TO vowsig_app;
GRANT INSERT, DELETE ON TABLE
  vowsig.vowsig_watchlist_items,
  vowsig.vowsig_saved_research,
  vowsig.vowsig_oidc_authorizations
TO vowsig_app;

-- NO runtime INSERT/UPDATE/DELETE on:
-- vowsig_research_source_snapshots, vowsig_research_outcome_facts.
-- NO TRUNCATE, REFERENCES, TRIGGER, schema CREATE, or DB role management.
-- NO backup DML. Backup can pg_dump the separate schema read-only.
--
-- New migrations should explicitly audit permissions; do not silently grant
-- runtime DML to future tables by default.
ALTER DEFAULT PRIVILEGES FOR ROLE vowsig_migrator IN SCHEMA vowsig
  REVOKE ALL ON TABLES FROM PUBLIC;
ALTER DEFAULT PRIVILEGES FOR ROLE vowsig_migrator IN SCHEMA vowsig
  GRANT SELECT ON TABLES TO vowsig_backup;
