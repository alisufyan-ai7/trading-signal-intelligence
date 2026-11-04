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
