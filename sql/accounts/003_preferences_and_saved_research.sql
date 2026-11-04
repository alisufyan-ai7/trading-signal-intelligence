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
