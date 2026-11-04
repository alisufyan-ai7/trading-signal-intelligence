# VowSig P1A account and entitlement foundation (2026-11-04)

**Status: review only. Not deployed, not merged.** User approved the P0 direction and asked for stable engineering names independent of the current Free business tier. This file supersedes the prior P1A Free-named documentation and accompanies the single consolidated Signal Center PR.

## Permanent domain model

| Platform domain | Permanent code/database names | Current business entitlement |
| --- | --- | --- |
| Identity | `product/accounts`, `vowsig_accounts` | role = `member` / `owner` |
| Sessions | `vowsig_account_sessions` | verified, bounded sessions and owner MFA |
| Plan | `vowsig_account_entitlements`, `access_tier` | initial `research_free`, future values may represent paid access |
| Saved interests | `vowsig_watchlist_items` | nine markets watchlisted |
| User audit | `vowsig_account_audit` | account-scoped changes |

Account ID, email, sessions and watchlist survive future upgrade. Business tier/price/payment are separate entitlement policy, not the identity or database object name. No `free_foundation` module, `free-app` dependency or `vowsig_free_*` table remains in this PR. Because the first version was never merged/deployed, no data migration is required to perform this naming correction. Future real schema changes still require migrations.

## Code and security boundary

The gated `/api/v2` router exposes the nine-market catalog; protected account profile/watchlist; permitted sanitized recent XAUUSD, USTEC and US30 SHADOW_ONLY research details; and a source-limited MFA-guarded owner overview. For EURUSD, XAGUSD, USOIL, BTCUSDT, ETHUSDT and SOLUSDT, detailed BUY/SELL levels/records remain forbidden regardless of Free or future Paid tier. S02 remains an independent rule benchmark, not an AI signal program. Existing public v1 endpoints remain unchanged.

`accounts/security.py` verifies a hashed opaque session cookie, email verification, stable role, active entitlement, expiry, not-revoked/not-disabled status, a fresh owner MFA marker and exact HTTPS Origin+HMAC CSRF for writes. `accounts/store.py` uses parameterized PostgreSQL SQL with `sslmode=verify-full`; no DB connection during import. The optional PostgreSQL dependency is called `accounts`. Database schema under `sql/accounts/` stores identity, entitlement, session, account-isolated watchlist and activity audit. No user password storage or account/session issuer exists in this phase.

The new optional router is **OFF by default**. No signup, login, verification email sender, cookie issuance, password-reset, MFA enrollment, logout, real provider connection, active billing or real-money execution is implemented. No database migration is automatically executed. Member responses are private/no-store and noindex. Snapshot history remains truncated (12 decisions, 20 signals), so no claims of full history or independently verified owner Performance Lab are possible without a separately approved source-hash read model.

## Runtime activation: NOT authorized in P1A

Feature OFF unless separately approved runtime configuration is installed:
- `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=1`
- `VOWSIG_ACCOUNTS_DATABASE_URL` with `sslmode=verify-full` and trusted CA.
- `VOWSIG_ACCOUNTS_CSRF_SECRET` with at least 32 random secret bytes.
- `VOWSIG_ACCOUNTS_APP_ORIGIN` for an exact HTTPS origin.

Before actual registration, review identity/email provider and session token issuance; the issuer must set a secure `__Host-vowsig_session` HttpOnly Secure cookie, no Domain, Path=/, SameSite, and persist only hashed token. Admin role grant and MFA must not be user-writable. Approve Postgres vendor/region, budget, TLS, user-data retention, deletion/export, DB backups and tested restores, rate limiting, logging hygiene and abuse response. Do not enable the feature flag merely because code is merged.

## Test and release checklist

`tests/test_vowsig_accounts_foundation_p1a.py` contains synthetic negative tests for nine-vs-three permissions, six disallowed symbol requests, tier/role separation (a hypothetical paid tier cannot unlock restricted signals), malformed/stale snapshot behavior, cross-account isolation, CSRF and origin denial, expiry/revocation/verification, owner MFA, TLS DSN and feature-off public v1 parity. Run in isolated checkout with the existing cloud/publisher regression suites before review. Test real PostgreSQL schema/transactions and identity issuance/revocation as a separate P1B gate. No CI results or disposable test run are yet claimed.

**Next P1B:** select managed identity/email and isolated Postgres based on current owner-approved provider evidence, security, residency and cost. Implement verified signup/login/recovery/revoke and first responsive member shell as separate review steps, without altering scanner/Windows publisher/signal permissions. No broker execution, alerts or charges.

## PR hygiene

P0 and P1A are part of the same workstream as PR #93. Consolidate PR #94/#95 commits into PR #93 and close only those two redundant drafts after verifying ancestry/contents. Preserve review discussion URLs. Leave PR #93 draft pending test, security and owner release sign-off. Do not fold unrelated backup/GFS or frozen AI guard PRs into this product PR. No untested authentication code goes to `main`.
