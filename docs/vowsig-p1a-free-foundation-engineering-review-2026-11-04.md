# VowSig P1A — Free-account backend foundation, review checklist

**Date:** 2026-11-04. **Status:** BOUNDED DRAFT ENGINEERING / NOT DEPLOYED / NO LIVE ACCOUNTS. **Authorized direction:** owner approved P0 in [PR #94 discussion](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/94#issuecomment-6625491588); PR #93 remains original architecture. P1A implementation does **not** claim identity/login/production release approval. Source boundary: current chat and repo only.

## Scope delivered by this draft
- A fixed **nine-market** public v2 directory contract with model-version-free customer names, plus visibility/readiness flags. Three Core AI-v1.1 markets may return already-public, sanitized recent SHADOW_ONLY details **only** when source snapshot is fresh (<90 minutes), runtime/health/publisher and core program gates explicitly pass. Six expansion/crypto markets never get signal-level output from new member endpoints, even if internal snapshot contains such data.
- New v2 routes are **entirely disabled unless** \`VOWSIG_FREE_FOUNDATION_ENABLED=1\`: \`GET /api/v2/public/markets\`, \`GET /api/v2/me\`, \`GET/PUT/DELETE /api/v2/me/watchlist[/{symbol}]\`, \`GET /api/v2/me/signals?symbol=XAUUSD\`, \`GET /api/v2/admin/overview\` (owner/MFA snapshot-only).
- Server-side cookie token digest check against session/user records; account must be **email-verified**, unexpired, not revoked or disabled. Member user ID derives from database, never a request header. Owner route demands owner role and a recent MFA marker. No role allows access to six restricted markets.
- Cookie-authenticated state mutations require exact configured HTTPS origin plus HMAC-CSRF token, served privately by \`GET /api/v2/me\`; HMAC secret must be at least 32 bytes. Responses with per-user details explicitly forbid caching and indexing. Account issuer in future must create a 32-byte random session token and set \`__Host-vowsig_session\` with \`Secure; HttpOnly; Path=/; SameSite=Lax or Strict\`, without Domain.
- PostgreSQL 1st schema migration (not applied) has users, hashed sessions, user-isolated 9-market watchlists and append-only watchlist activity audit. No passwords or secrets are persisted by this draft. Database connection uses parameterized queries; no DB opened on module import.
- Existing /api v1, Windows runtime, immutable SQLite research ledgers, snapshot exporter, guarded publisher, S02 benchmark, expansion/crypto exposure and broker execution are untouched.

## Explicitly **NOT implemented**; mandatory before production registration

1. **Identity provider/issuer**: signup/login/email verification/password-reset or passwordless chosen provider and verification-email delivery, secure short-lived session issuance, revocation/logout and session rotation; no user/session can be created by these routes. The review foundation is thus deliberately **not an end-to-end working customer signup**. No test user or owner account is seeded.
2. **Provider decision / legal and budget**: approve hosting/PostgreSQL provider, data residency, DB backups and restore, email vendor, consent/privacy/retention/export/deletion, security access and operating budget. No external service was provisioned by this PR.
3. **Owner MFA and access**: reviewed issuer must set/verify \`mfa_verified_at\` via real MFA proof and demonstrate the admin role can only be granted by an audited owner-controlled action. Never permit an owner role through a user-submitted field.
4. **Infrastructure operational safety**: DB migration via separate approved infrastructure rollout; least-privilege role, TLS connection validation, secret storage, connection pooling, backups, failed query handling, monitoring and session cleanup. New sessions must have <=7-day TTL, strict secure-cookie attributes and rate-limited sign-in, with recovery and abuse controls.
5. **Member UX**: actual registration/login forms, responsive member shell, signal details/history, education links and watchlist UI belong to subsequent bounded PRs. The current public homepage is intentionally unchanged.
6. **True full history / owner analytics**: legacy public AI snapshot truncates to 12 recent decisions / 20 shadow signals; do not pretend it is a complete history, or calculate Performance Lab aggregates from that subset. A separately approved, source-hash-reconciled read-model export and v1 metric contract is required. Admin overview v2 is explicitly **snapshot-only** and does not assert VPS scheduler/backup health.

## Feature activation guards (for *later* approved deployment only)

Default is **OFF**. When enabled, cloud app requires:
- \`VOWSIG_FREE_FOUNDATION_ENABLED=1\`
- \`VOWSIG_FREE_DATABASE_URL\`: PostgreSQL URL for the isolated customer database (no credentials printed anywhere).
- \`VOWSIG_FREE_CSRF_SECRET\`: secret, 32+ bytes, securely generated, never committed.
- \`VOWSIG_FREE_APP_ORIGIN\`: exact HTTPS origin, scheme+host only.

Activation is prohibited until issuer, email verification, database security and privacy gates are completed. A feature flag is **not** a commercial signal release switch. Database schema is not auto-migrated and sessions are not auto-issued. Do not set these variables on production by reading this document.

## Security acceptance tests and evidence expectations

\`tests/test_vowsig_free_foundation_p1a.py\` contains deterministic synthetic tests for:
- Exactly nine catalog markets, exactly three core detail permissions and zero commercial eligibility;
- Anonymous and invalid-cookie requests denied, six restricted symbols denied even for Free, forbidden nested payload never forwarded;
- Fresh-vs-stale, source-health false, missing snapshot fail closed; historical rows explicitly incomplete;
- User A/B watchlist isolation, unknown market rejection, exact Origin+CSRF required, verified/expired/revoked/disabled account rejection;
- Owner endpoint blocked without owner role and MFA, no-store responses and snapshot-only health disclaimer.

Existing v1 response regression must be verified with \`tests/test_cloud_snapshot_durability.py\`, \`tests/test_product_ai_insights.py\`, \`tests/test_cloud_ai_runtime_validation.py\`, \`tests/test_vowsig_multilineage_public_observability.py\`. All tests should run in a disposable checkout. No reliance on live VPS, API keys or provider calls.

**Required code review before approval:** verify no field leak from validation programs or snapshot aliases, no login endpoint generated by P1A, no implicit cloud costs, and no risky production service activation. Add endpoint fuzzing, injection/CSRF/cookie browser tests, DB migration dry-run, real PostgreSQL transaction/integration tests, provider fail/rotation, multi-worker session revocation, deletion/export and email verification contract tests in follow-up PR before any deployment.

## Next work after separate review
P1B chooses a mature managed identity/email provider and a PostgreSQL environment/region, then implements audited verification, session issuance/revocation, logout and onboarding. P1C adds the responsive /app Signal Center shell/watchlists with all nine **cataloged** but only the three permitted Core details. P2 source-reconciled Performance Lab and P3 full permitted history remain separate quality-gated increments. Zero pricing/billing, subscriber alerts or broker execution.
