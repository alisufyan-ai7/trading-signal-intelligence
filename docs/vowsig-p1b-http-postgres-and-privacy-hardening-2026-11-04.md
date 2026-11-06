# P1B account signup and privacy hardening — pre-release HTTP/PostgreSQL acceptance

**2026-11-04; consolidated draft PR #93.** This is an owner-independent, isolated code and test increment. No Railway service, live OIDC account, production database, `main` merge, VPS task, trading integration, or customer flag changed.

## Fixes

1. **Consistent fail-closed validation:** API preference patches with non-string, non-hashable `educational_level` values return HTTP 400, rather than leaking a Python `TypeError` and producing a 500. Explicit consent remains boolean-only.
2. **Verified-email collision:** A subject from the configured OIDC issuer that has not previously linked to an account cannot take over an email-bound existing account. PostgreSQL uniqueness violations are translated at the store boundary into `AccountLinkConflict` and the callback returns the generic HTTP 401 `Verified sign-in rejected`. No automatic email-based account linking or raw PostgreSQL exception is exposed.
3. **One realistic isolated test:** Mocked HTTPS token and JWKS endpoints produce a genuinely RSA-signed ID token while the API and account store use a real disposable PostgreSQL 17 database. The test exercises `/auth/start`, PKCE verifier/nonce state loaded from the DB, `/auth/callback`, first verified account signup, server-session cookie, protected `/api/v2/me`, watchlist CSRF, explicit six-market signal denial, owner-route denial, logout/session revocation and duplicate-email/other-subject denial.

This is a *test* of production protocol paths and database integration; it does **not** prove real provider email delivery, MFA enrolment, Railway TLS/certificate/trusted proxy configuration or data retention/legal compliance. The test fixture is not a deployment configuration or an approved way to set an owner role.

## Controlled release gates

- Account routes remain **off** by default via `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=0` and `VOWSIG_OIDC_AUTH_ENABLED=0`.
- Actual Railway Postgres secure, least-privilege connection, approved region and cold restore must be tested at one coordinated integration/release stage.
- A vetted provider must support exactly configured HTTPS issuer, code+PKCE, accepted signing algorithm and claims. Real email verification and owner fresh MFA remain separate signoff.
- Source-signed full historical performance remains quarantined pending independent ledger reconciliation. Research-only customer signal permissions unchanged.
- Owner approval is required for merging the tested exact SHA and any production deployment or feature enablement.

**Only exact-head CI PASS constitutes engineering acceptance**; preserve the run link and test count in PR #93 after the workflow completes.
