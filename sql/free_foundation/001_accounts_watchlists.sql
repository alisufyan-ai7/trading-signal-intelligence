-- REVIEW-ONLY P1A. NEVER EXECUTED BY APPLICATION STARTUP.
-- Owner-approved PostgreSQL provider/region/retention/security and issuer still required.
-- No plaintext session token is stored. External verified issuer must hash 32
-- cryptographically random bytes as sha256(base64url_no_padding(token)).
CREATE TABLE IF NOT EXISTS vowsig_free_users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'free' CHECK (role IN ('free', 'owner')),
    email_verified_at TIMESTAMPTZ,
    disabled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT free_email_nonempty CHECK (length(btrim(email)) > 3)
);
CREATE UNIQUE INDEX IF NOT EXISTS vowsig_free_users_email_ci
    ON vowsig_free_users (lower(btrim(email)));

CREATE TABLE IF NOT EXISTS vowsig_free_sessions (
    token_sha256 CHAR(64) PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES vowsig_free_users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    mfa_verified_at TIMESTAMPTZ,
    CONSTRAINT free_session_sha_hex CHECK (token_sha256 ~ '^[0-9a-f]{64}$'),
    CONSTRAINT free_session_expiry CHECK (
        expires_at > created_at AND expires_at <= created_at + INTERVAL '7 days'
    )
);
CREATE INDEX IF NOT EXISTS vowsig_free_sessions_user
    ON vowsig_free_sessions(user_id);

CREATE TABLE IF NOT EXISTS vowsig_free_watchlist (
    user_id UUID NOT NULL REFERENCES vowsig_free_users(id) ON DELETE CASCADE,
    symbol TEXT NOT NULL CHECK (symbol IN (
        'XAUUSD','USTEC','US30','EURUSD','XAGUSD','USOIL','BTCUSDT','ETHUSDT','SOLUSDT'
    )),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY(user_id, symbol)
);

CREATE TABLE IF NOT EXISTS vowsig_free_audit (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    user_id UUID REFERENCES vowsig_free_users(id) ON DELETE SET NULL,
    action TEXT NOT NULL CHECK (action IN ('watchlist_saved','watchlist_removed')),
    market_symbol TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
-- Provisioning must separately define least-privilege DB roles, encryption,
-- backups, connection limits, deletion/export policy, migration rollback.
