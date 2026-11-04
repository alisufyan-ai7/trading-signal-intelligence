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
