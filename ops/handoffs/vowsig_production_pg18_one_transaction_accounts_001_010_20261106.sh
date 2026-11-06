#!/usr/bin/env bash
# PRIVATE ONE-TIME PRODUCTION SQL SCHEMA BOOTSTRAP. ONLY Railway > positioning-engine-cron > production > Postgres > Console.
# First run only on a DB with ZERO VowSig roles/tables/schema. One atomic PG transaction.
# Exact reviewed original sql/accounts/001..009 plus SQL 010; no source refactor.
# No change to live app, /data publisher, VPS, trading or customer feature flags.
bash <<'VOWSIG_PROD_SCHEMA_OPERATOR'
set -Eeuo pipefail
set +x
umask 077
[[ "${RAILWAY_PROJECT_NAME:-}" == 'positioning-engine-cron' ]] || { echo REFUSED_PROJECT; exit 1; }
[[ "${RAILWAY_ENVIRONMENT_NAME:-}" == 'production' ]] || { echo REFUSED_ENVIRONMENT; exit 1; }
[[ "${RAILWAY_SERVICE_NAME:-}" == 'Postgres' ]] || { echo REFUSED_SERVICE; exit 1; }
[[ -n "${POSTGRES_DB:-}" && -n "${POSTGRES_USER:-}" && -n "${POSTGRES_PASSWORD:-}" ]] || { echo REFUSED_DATABASE_ENV; exit 1; }
[[ -r /dev/tty ]] || { echo INTERACTIVE_PRIVATE_CONSOLE_REQUIRED; exit 1; }
command -v psql >/dev/null && command -v openssl >/dev/null || { echo REQUIRED_TOOLS_MISSING; exit 1; }
export PGPASSWORD="$POSTGRES_PASSWORD"
identity="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database()||'|'||current_user||'|'||current_setting('ssl')")"
[[ "$identity" == "$POSTGRES_DB|$POSTGRES_USER|on" ]] || { echo REFUSED_PROD_DB_IDENTITY_SSL; exit 1; }
version="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW server_version_num")"
[[ "$version" =~ ^18[0-9]{4}$ ]] || { echo REFUSED_PG_VERSION; exit 1; }
cert="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW ssl_cert_file")"
datadir="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW data_directory")"
[[ "$cert" == /* ]] || cert="$datadir/$cert"
[[ -r "$cert" ]] || { echo REFUSED_CERT_READ; exit 1; }
leaf="$(openssl x509 -in "$cert" -noout -fingerprint -sha256 | sed -E 's/.*=//;s/://g' | tr '[:upper:]' '[:lower:]')"
[[ "$leaf" == '42574eca8c9afa481beefb2c3ea6b508bcd3e6c27e1b287d20274d72458e9526' ]] || { echo TLS_LEAF_PIN_CHANGED_HOLD; exit 1; }
openssl x509 -in "$cert" -noout -ext subjectAltName | grep -Fq 'DNS:postgres.railway.internal' || { echo TLS_HOSTNAME_HOLD; exit 1; }
state="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT (SELECT count(*) FROM pg_roles WHERE rolname IN ('vowsig_app','vowsig_migrator','vowsig_backup'))||'|'||(SELECT count(*) FROM pg_namespace WHERE nspname='vowsig')||'|'||(SELECT count(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'vowsig_%')")"
[[ "$state" == '0|0|0' ]] || { echo ALREADY_CONFIGURED_OR_PARTIAL_STATE_HOLD_NO_RERUN; exit 1; }
echo 'This initializes 3 RESTRICTED new database roles and the dedicated VowSig schema (16 tables), once.'
echo 'Use three UNIQUE 44+ character URL-safe random passwords SAVED IN YOUR PRIVATE PASSWORD MANAGER.'
printf 'App role password (hidden): ' >/dev/tty
IFS= read -r -s VOWSIG_APP_ROLE_PASSWORD </dev/tty
printf '\nMigrator role password (hidden): ' >/dev/tty
IFS= read -r -s VOWSIG_MIGRATOR_ROLE_PASSWORD </dev/tty
printf '\nBackup role password (hidden): ' >/dev/tty
IFS= read -r -s VOWSIG_BACKUP_ROLE_PASSWORD </dev/tty
printf '\n' >/dev/tty
for x in "$VOWSIG_APP_ROLE_PASSWORD" "$VOWSIG_MIGRATOR_ROLE_PASSWORD" "$VOWSIG_BACKUP_ROLE_PASSWORD"; do
  [[ "$x" =~ ^[A-Za-z0-9_-]{44,128}$ ]] || { echo INVALID_ROLE_PASSWORD_FORMAT; exit 1; }
done
[[ "$VOWSIG_APP_ROLE_PASSWORD" != "$VOWSIG_MIGRATOR_ROLE_PASSWORD" && "$VOWSIG_APP_ROLE_PASSWORD" != "$VOWSIG_BACKUP_ROLE_PASSWORD" && "$VOWSIG_MIGRATOR_ROLE_PASSWORD" != "$VOWSIG_BACKUP_ROLE_PASSWORD" ]] || { echo PASSWORDS_MUST_BE_DISTINCT; exit 1; }
export VOWSIG_APP_ROLE_PASSWORD VOWSIG_MIGRATOR_ROLE_PASSWORD VOWSIG_BACKUP_ROLE_PASSWORD
trap 'unset VOWSIG_APP_ROLE_PASSWORD VOWSIG_MIGRATOR_ROLE_PASSWORD VOWSIG_BACKUP_ROLE_PASSWORD PGPASSWORD' EXIT
printf 'Type INIT_PROD_VOWSIG_001_010 to apply once (anything else cancels): ' >/dev/tty
IFS= read -r confirmation </dev/tty
[[ "$confirmation" == 'INIT_PROD_VOWSIG_001_010' ]] || { echo CANCELLED_NO_CHANGE; exit 1; }
psql -XwqAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'VOWSIG_PRODUCTION_SQL'
BEGIN;
DO $guard$
BEGIN
 IF (SELECT count(*) FROM pg_roles WHERE rolname IN ('vowsig_app','vowsig_migrator','vowsig_backup'))<>0
    OR EXISTS(SELECT 1 FROM pg_namespace WHERE nspname='vowsig')
    OR EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'vowsig_%')
 THEN RAISE EXCEPTION 'VowSig production schema no longer pristine'; END IF;
END $guard$;
\getenv app_password VOWSIG_APP_ROLE_PASSWORD
\getenv migrator_password VOWSIG_MIGRATOR_ROLE_PASSWORD
\getenv backup_password VOWSIG_BACKUP_ROLE_PASSWORD
SELECT format('CREATE ROLE vowsig_app LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'app_password') \gexec
SELECT format('CREATE ROLE vowsig_migrator LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'migrator_password') \gexec
SELECT format('CREATE ROLE vowsig_backup LOGIN PASSWORD %L NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS', :'backup_password') \gexec
CREATE SCHEMA vowsig AUTHORIZATION vowsig_migrator;
SELECT format('ALTER ROLE %I IN DATABASE %I SET search_path TO vowsig, pg_catalog','vowsig_app',current_database()) \gexec
SELECT format('ALTER ROLE %I IN DATABASE %I SET search_path TO vowsig, pg_catalog','vowsig_migrator',current_database()) \gexec
SELECT format('ALTER ROLE %I IN DATABASE %I SET search_path TO vowsig, pg_catalog','vowsig_backup',current_database()) \gexec
SET ROLE vowsig_migrator;
SET LOCAL search_path TO vowsig, pg_catalog;
-- SOURCE: sql/accounts/001_accounts_sessions_entitlements_watchlist.sql
-- P1A REVIEW-ONLY accounts schema, no database has been provisioned.
-- Stable account identity, session, watchlist and entitlement domains.
-- Free research is a tier value, NOT an account type or table name.
-- No automatic schema migration and no session issuer in this PR.

CREATE TABLE IF NOT EXISTS vowsig_accounts (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'owner')),
    email_verified_at TIMESTAMPTZ,
    disabled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT vowsig_account_email_nonempty CHECK (length(btrim(email)) > 3)
);
CREATE UNIQUE INDEX IF NOT EXISTS vowsig_accounts_email_ci
    ON vowsig_accounts (lower(btrim(email)));

-- This table can later hold paid access_tier values without renaming the user,
-- session, or watchlist tables. Paid tiers still require explicit eligibility,
-- billing and signal-publication gates; an access_tier alone grants none.
CREATE TABLE IF NOT EXISTS vowsig_account_entitlements (
    account_id UUID PRIMARY KEY REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    access_tier TEXT NOT NULL DEFAULT 'research_free'
        CHECK (access_tier ~ '^[a-z][a-z0-9_]{1,63}$'),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'suspended', 'revoked')),
    granted_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Issuer must store only sha256(base64url-without-padding(32 random bytes)).
-- Real issuer, account email verification, revocation, role/MFA grant and
-- session expiry policies require separate approved P1B implementation.
CREATE TABLE IF NOT EXISTS vowsig_account_sessions (
    token_sha256 CHAR(64) PRIMARY KEY
        CHECK (token_sha256 ~ '^[0-9a-f]{64}$'),
    account_id UUID NOT NULL REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    mfa_verified_at TIMESTAMPTZ,
    CONSTRAINT vowsig_session_expiry CHECK (
        expires_at > created_at AND expires_at <= created_at + INTERVAL '7 days'
    )
);
CREATE INDEX IF NOT EXISTS vowsig_account_sessions_account
    ON vowsig_account_sessions(account_id);

CREATE TABLE IF NOT EXISTS vowsig_watchlist_items (
    account_id UUID NOT NULL REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL CHECK (symbol IN (
        'XAUUSD', 'USTEC', 'US30', 'EURUSD', 'XAGUSD', 'USOIL',
        'BTCUSDT', 'ETHUSDT', 'SOLUSDT'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (account_id, symbol)
);

CREATE TABLE IF NOT EXISTS vowsig_account_audit (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id UUID REFERENCES vowsig_accounts(id) ON DELETE SET NULL,
    action TEXT NOT NULL CHECK (action IN ('watchlist_saved', 'watchlist_removed')),
    market_symbol TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Separate infrastructure PR needed for: least-privilege DB credentials, TLS
-- certificate/CA, backups/restore, connection pool, GDPR-like deletion/export,
-- retention, migration audit and rollback. No paid plans are active.

-- SOURCE: sql/accounts/002_verified_identity_binding.sql
-- P1B-0. Review-only, requires an approved managed PostgreSQL schema rollout.
-- Identity link is provider issuer + immutable provider subject, NOT email.
-- A new provider account must never silently attach by matching an email.
-- SQL migration 001 must be applied before this migration.

CREATE TABLE IF NOT EXISTS vowsig_account_identities (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    issuer TEXT NOT NULL,
    subject TEXT NOT NULL,
    linked_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_verified_at TIMESTAMPTZ,
    CONSTRAINT vowsig_oidc_issuer_https CHECK (left(issuer, 8) = 'https://'),
    CONSTRAINT vowsig_oidc_subject_nonempty CHECK (length(btrim(subject)) > 0),
    CONSTRAINT vowsig_oidc_issuer_subject_unique UNIQUE (issuer, subject),
    -- Do not create two identities for the same account at one provider.
    CONSTRAINT vowsig_oidc_one_subject_per_issuer UNIQUE (account_id, issuer)
);
CREATE INDEX IF NOT EXISTS vowsig_account_identities_account
    ON vowsig_account_identities (account_id);

-- No seed identities and NO public write API in P1B-0.
-- Future registration code must prove the OIDC callback, then create account,
-- initial 'research_free' entitlement and binding atomically, and revalidate
-- the email address before session issuance. Linking existing accounts needs
-- explicit authenticated re-verification, NEVER email equality.

-- SOURCE: sql/accounts/003_preferences_and_saved_research.sql
-- P1/P4 account preferences and saved research metadata, never broker credentials.
-- No email alert sending/notifications are enabled by these data structures.
CREATE TABLE IF NOT EXISTS vowsig_account_preferences (
    account_id UUID PRIMARY KEY REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    timezone TEXT NOT NULL DEFAULT 'UTC'
        CHECK (length(timezone) BETWEEN 1 AND 64),
    educational_level TEXT NOT NULL DEFAULT 'beginner'
        CHECK (educational_level IN ('beginner','intermediate','advanced')),
    research_updates_opt_in BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS vowsig_saved_research (
    account_id UUID NOT NULL REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    signal_id TEXT NOT NULL CHECK (length(signal_id) BETWEEN 1 AND 128),
    source_symbol TEXT NOT NULL CHECK (
        source_symbol IN ('XAUUSD','USTEC','US30')
    ),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(account_id, signal_id)
);
-- NO message queue, outbound customer alert, subscription or email sender.

-- SOURCE: sql/accounts/004_research_read_model_contract.sql
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

-- SOURCE: sql/accounts/005_consent_audit_deletion_requests.sql
-- P4 privacy-minimal research preference audit and account deletion request queue.
-- Neither creates marketing email, trade alert delivery, nor destructive deletion.
CREATE TABLE IF NOT EXISTS vowsig_account_consent_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    account_id UUID NOT NULL REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    purpose TEXT NOT NULL CHECK (purpose = 'research_product_updates'),
    opted_in BOOLEAN NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS vowsig_account_consent_events_account
    ON vowsig_account_consent_events(account_id, recorded_at DESC);

CREATE TABLE IF NOT EXISTS vowsig_account_deletion_requests (
    account_id UUID PRIMARY KEY REFERENCES vowsig_accounts(id) ON DELETE CASCADE,
    requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    status TEXT NOT NULL DEFAULT 'pending_reverification'
      CHECK (status IN ('pending_reverification','under_review','completed','cancelled')),
    review_completed_at TIMESTAMPTZ
);
-- Actual deletion requires separate verified reauthentication, backups/
-- retention reconciliation, processor data handling and owner release.
-- No background deletion worker is included.

-- SOURCE: sql/accounts/006_oidc_auth_transactions.sql
-- P1B-1: bounded, one-time OIDC authorization transactions and rate limits.
-- The verifier holds PKCE/nonce only for 10 minutes; data is not account PII.
-- Migrations MUST run separately with a least-privilege role.
CREATE TABLE IF NOT EXISTS vowsig_oidc_authorizations (
    state_sha256 CHAR(64) PRIMARY KEY CHECK (state_sha256 ~ '^[0-9a-f]{64}$'),
    browser_sha256 CHAR(64) NOT NULL CHECK (browser_sha256 ~ '^[0-9a-f]{64}$'),
    code_verifier TEXT NOT NULL CHECK (length(code_verifier) BETWEEN 43 AND 128),
    nonce TEXT NOT NULL CHECK (length(nonce) BETWEEN 32 AND 128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    CONSTRAINT vowsig_oidc_authorizations_short_lived CHECK (
      expires_at > created_at AND expires_at <= created_at + INTERVAL '10 minutes'
    )
);
CREATE INDEX IF NOT EXISTS vowsig_oidc_authorizations_expiry
 ON vowsig_oidc_authorizations(expires_at);
-- No raw IP address is persisted: HMAC(secret, trusted peer IP) is used
-- only as a short-lived coarse throttle. Not a durable analytics ID.
CREATE TABLE IF NOT EXISTS vowsig_auth_rate_windows (
    subject_digest CHAR(64) NOT NULL CHECK (subject_digest ~ '^[0-9a-f]{64}$'),
    bucket_start TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL CHECK (attempts BETWEEN 1 AND 30),
    PRIMARY KEY(subject_digest,bucket_start)
);
CREATE INDEX IF NOT EXISTS vowsig_auth_rate_windows_expiry
 ON vowsig_auth_rate_windows(bucket_start);
-- No automatic schedulers; a future maintenance job may prune expired rows.

-- SOURCE: sql/accounts/007_restricted_roles_and_grants.sql
-- P1B-2 least privilege access policy. Apply ONLY AFTER:
-- * PostgreSQL roles vowsig_app, vowsig_migrator, vowsig_backup exist;
-- * schema vowsig is owned by vowsig_migrator;
-- * migrations 001-006 ran as vowsig_migrator with search_path vowsig,pg_catalog.
-- * migration 008 applies its OWN grants for the later-created MFA table.
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

-- Owner MFA table is created LATER in migration 008 with explicit grants.

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

-- SOURCE: sql/accounts/008_owner_mfa_stepup.sql
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

-- SOURCE: sql/accounts/009_owner_offline_provisioning_audit.sql
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

-- START_EXACT_MIGRATION sql/accounts/010_single_founder_first_owner_exception.sql
-- Owner-authorized narrow initial-founder exception, 2026-11-06.
-- Apply ONCE under vowsig_migrator to STAGING first, with reviewed SQL.
-- 009 two-person approvals remain REQUIRED for normal first_owner and
-- rotate_factor. Solo never permits recovery or a second owner.
-- Signed one-use approval, exact immutable Auth0 binding, TOTP confirmation,
-- schema migrator and session revocation are still enforced in Python.
SET LOCAL search_path TO vowsig, pg_catalog;
DO $$
BEGIN
    IF current_user <> 'vowsig_migrator' THEN
        RAISE EXCEPTION 'Dedicated migrator required';
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_schema='vowsig'
        AND table_name='vowsig_owner_provisioning_audit'
        AND constraint_name='vowsig_owner_independent_review'
    ) THEN
        RAISE EXCEPTION 'Existing two-person policy constraint absent';
    END IF;
END $$;

ALTER TABLE vowsig_owner_provisioning_audit
    DROP CONSTRAINT vowsig_owner_independent_review;

ALTER TABLE vowsig_owner_provisioning_audit
    DROP CONSTRAINT vowsig_owner_provisioning_audit_operation_check;

ALTER TABLE vowsig_owner_provisioning_audit
    ADD CONSTRAINT vowsig_owner_operation_scope_check CHECK (
        operation IN ('first_owner','first_owner_solo','rotate_factor')
    );

ALTER TABLE vowsig_owner_provisioning_audit
    ADD CONSTRAINT vowsig_owner_actor_policy_check CHECK (
        (
            operation='first_owner_solo'
            AND operator_id=reviewer_id
        )
        OR (
            operation IN ('first_owner','rotate_factor')
            AND operator_id<>reviewer_id
        )
    );

-- No new role grants, runtime DML or HTTP paths.
-- END_EXACT_MIGRATION sql/accounts/010_single_founder_first_owner_exception.sql

-- Checked SQL 001..010 MUST all commit atomically; no earlier transaction boundary.
DO $verify$
BEGIN
 IF current_user<>'vowsig_migrator' OR current_schema()<>'vowsig'
    OR (SELECT count(*) FROM pg_tables WHERE schemaname='vowsig' AND left(tablename,7)='vowsig_')<>16
    OR (SELECT count(*) FROM pg_roles WHERE rolname IN ('vowsig_app','vowsig_migrator','vowsig_backup') AND rolcanlogin AND NOT(rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))<>3
    OR NOT has_table_privilege('vowsig_app','vowsig.vowsig_accounts','SELECT')
    OR has_table_privilege('vowsig_app','vowsig.vowsig_accounts','UPDATE')
    OR has_schema_privilege('vowsig_app','vowsig','CREATE')
    OR has_table_privilege('vowsig_app','vowsig.vowsig_research_outcome_facts','INSERT')
    OR has_table_privilege('vowsig_app','vowsig.vowsig_research_outcome_facts','UPDATE')
    OR has_column_privilege('vowsig_app','vowsig.vowsig_owner_totp_credentials','secret_ciphertext','UPDATE')
    OR NOT has_column_privilege('vowsig_app','vowsig.vowsig_owner_totp_credentials','last_accepted_step','UPDATE')
    OR has_table_privilege('vowsig_backup','vowsig.vowsig_accounts','INSERT')
    OR NOT has_table_privilege('vowsig_backup','vowsig.vowsig_owner_provisioning_audit','SELECT')
    OR NOT EXISTS(SELECT 1 FROM pg_constraint WHERE conname='vowsig_owner_actor_policy_check')
 THEN RAISE EXCEPTION 'Restricted role, MFA, 16-table, signed initial owner boundaries failed'; END IF;
END $verify$;
COMMIT;
SELECT 'PROD_VOWSIG_001_010_COMMITTED=PASS';
VOWSIG_PRODUCTION_SQL
echo 'PRODUCTION_PG18_ROLES_AND_SCHEMA=PASS'
echo 'PRODUCTION_ACCOUNT_FEATURE_ENABLED=NO'
echo 'PRODUCTION_OWNER_PROMOTED=NO'
echo 'TRADING_PUBLISHER_OR_WEB_CHANGED=NO'
echo 'SAVE_THREE_PRIVATE_PASSWORDS_FOR_CUTOVER=REQUIRED'
VOWSIG_PROD_SCHEMA_OPERATOR
