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
