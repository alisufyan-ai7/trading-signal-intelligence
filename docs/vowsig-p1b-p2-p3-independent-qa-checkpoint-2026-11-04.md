# P1B/P2/P3 integrated owner-independent engineering checkpoint

**Date:** 2026-11-04. **Scope:** single draft PR #93, no production changes. This checkpoint is an implementation specification, **not a pass claim until exact-head CI is recorded in the PR**.

## P1B — optional real protocol mechanics, no provider procurement

- New `accounts/oidc_provider.py` implements fixed-endpoint OIDC authorization code + PKCE S256, bounded browser-bound state and nonce, RSA/JWKS signature verification, exact issuer/audience/nonce/email_verified/auth_time/iat/exp, multi-audience azp and server session issue. Only RS256 is admitted; other provider algorithms require reviewed code changes.
- `accounts/auth_api.py` adds `/auth/start` and `/auth/callback` only when BOTH `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=1` and `VOWSIG_OIDC_AUTH_ENABLED=1`, and all static HTTPS endpoint/client variables validate. Callback cannot accept a user-supplied redirect destination. Login response uses Secure, HttpOnly, SameSite=Lax, Path=/ host-only cookie.
- `sql/accounts/006_oidc_auth_transactions.sql` stores short-lived one-time state-hash, browser-cookie-hash, nonce and PKCE verifier for <=10 min, atomically deletes matching state on use, and limits login starts to 30 per 10 min per hashed trusted peer. No raw IP/forwarded user-controlled header used for rate limit.
- `tests/test_vowsig_oidc_p1b.py` uses generated local RSA and mocked token/JWKS HTTP endpoints (no real external requests) to test signature verification/tampering, issuer/audience/nonce/expiry, cookies, callback one-use and throttling. Disposable Postgres tests check state/browser mismatch, expired state, replay and rate counter. Actual provider, sender, owner MFA and Railway database remain unconfigured.

## P2 — deterministic quarantine-only full-population replay

- Existing strict `check_sanitized_bundle` now rejects duplicate JSON keys, nonfinite numeric literals and malformed completed/noncompleted outcome cost fields; requires externally specified exact artifact digest, head hash and expected total count.
- New `accounts/read_model_replay.py` takes only offline sanitized bytes and explicit externally sourced pins. It replays a full input batch transactionally into `vowsig_research_source_snapshots`/`vowsig_research_outcome_facts` with `ingest_status='quarantined'`, `completeness_verified=FALSE`. Subsequent exact replay is idempotent; changed same-count record hash/net R triggers rollback. No HTTP ingest, no Windows ledger access, no scheduler/publisher change, no verified-history promotion and no public/paid signal release.
- Hash+count compliance **does not** independently verify immutable source ledger authenticity, licensing or all historical events. Those remain explicit audit gates before enabling complete histories, public claims or owner Performance Lab metrics.

## P3 — isolated browser UI regression

- `tests/test_vowsig_member_browser_p3.py` uses mocked same-origin network routes and a local headless Chromium browser. Checks desktop Signal Center, mobile all-nine directory and watchlist, adverse/NO_TRADE record presentation, stale active-state label, unauthenticated private error UI, owner limitation, XSS-resilient text rendering, opt-in preference without email/billing/alert delivery.
- Browser fixture serves only static member HTML/CSS/JS and in-memory mocked API responses; it is **not** actual production login. Separate FastAPI tests validate server auth and source gates.
- An additional front-end defense-in-depth filter rejects restricted-six per-signal and per-decision payloads even if a future API regression sends them; the real security enforcement remains the backend's six-market-denial policy.

## Remaining owner-independent QC / launch dependencies

Run the exact SHA in GitHub Actions with both native Python/PostgreSQL and Chromium jobs. Only then claim green CI and review defects. Actual Railway region/TLS/CA/backups, managed OIDC verified-email service, real provider callback email and MFA, launch UI navigation, verified full-ledger source rights/coverage, cross-browser/accessibility manual review, cutover/rollback and owner-approved production merge are release-phase gates. No live trading/billing/customer alerts.
