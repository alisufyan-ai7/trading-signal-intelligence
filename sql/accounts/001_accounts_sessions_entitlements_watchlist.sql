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
