# P1B-0 — Railway PostgreSQL target and identity-provider integration contract

**Date:** 2026-11-04. **Status:** Draft engineering, disabled. The owner explicitly chose to proceed with P1B and asked to use Railway PostgreSQL. This document records **Railway PostgreSQL as the selected target for VowSig customer account data**. It does NOT claim that a Railway project/database exists, a paid plan was selected, credentials were issued, networking/TLS was tested, or costs/backup guarantees were verified.

**One PR policy:** P0/P1A/P1B work stays in draft [PR #93](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93), not a new PR. New identity provider and external provisioning require separate review. Only this current chat and the private GitHub repository are project authority.

## 1. Separation of responsibilities

- **Railway PostgreSQL (selected target):** durable account IDs, verified-email state, session hashes, roles, entitlements, watchlists, OAuth/OIDC provider identity bindings and account audit. **Never** store raw identity-provider tokens, magic-link plaintext secrets, trading-provider credentials or raw market data in this database.
- **Managed customer identity provider (not yet selected):** OIDC authorization code with PKCE, cryptographically verified signed ID tokens/JWKS, issuer/audience/nonce/state and anti-replay validation, verified email, account recovery, actual MFA and delivery/anti-abuse. Railway PostgreSQL itself does not constitute user authentication or transactional email.
- **VowSig application:** server session authorization and revocation, account-level entitlements/market access, HTTP-only Secure cookies, CSRF, role isolation, audit and research-only signal exposure.
- **Research runtime:** Windows and immutable research ledgers remain independent. Customer account schema does not alter AI inference, guarded publisher, S02 benchmark or crypto/expansion per-signal exposure.

The account database uses **plan-neutral** tables: `vowsig_accounts`, `vowsig_account_sessions`, `vowsig_account_entitlements`, `vowsig_watchlist_items`, `vowsig_account_audit`, and new `vowsig_account_identities`. Initial entitlement value is `research_free`; upgrading later should update entitlement state, not rename the database.

## 2. New provider-binding contract (P1B-0, code only)

New `accounts/identity_contract.py` defines `OidcVerifier` and verified-claims validation. A future selected provider adapter MUST perform real OAuth2/OIDC code exchange with PKCE, store and consume one-time authorization state, validate signed token/JWKS/algorithm/issuer/audience/nonce/expiry/auth_time and anti-replay, then return claims. The current code **does not** validate provider JWT signatures by itself and MUST NOT be called on unverified raw HTTP data.

P1B-0 verifies consistency of already verified claims (exact HTTPS issuer, client ID audience, nonce, verified email, bounded timestamp, immutable subject); lookup binds by **(issuer, subject)** only. Identical email across providers or an email change **must not** auto-link accounts. Schema `sql/accounts/002_verified_identity_binding.sql` uniquely constrains issuer/subject and one subject per provider per account. No registration callback, token issuer or owner role escalation is exposed.

## 3. Railway-specific connection and recovery acceptance — HOLD until verified

**Service design:** create an isolated Railway PostgreSQL service for VowSig accounts in the approved project/environment/region; choose region after confirming actual app hosting location, latency, data-residency obligations and owner budget. Do NOT put DB credentials in GitHub, plaintext deployment logs, issue comments or a Windows VPS PowerShell command.

**Connection safety:** existing `PostgresAccountStore` requires `sslmode=verify-full` with a genuinely validated hostname and CA. Railway-generated private/internal and/or public connection strings **may not provide the same TLS and host-verification behavior**; this has NOT been verified here. Do not simply append `sslmode=verify-full` and presume success, or silently downgrade to `sslmode=disable`/unverified TLS. Determine the exact Railway endpoint, runtime topology, server certificate chain, CA/trust model and documented transport security in a separate provider validation. If unsupported, keep the feature off and explicitly review an alternative documented secure private-network model or compatible architecture. CI's local loopback PostgreSQL deliberately uses `sslmode=disable` **only** for ephemeral tests; it does not relax production enforcement.

**Database operations:** dedicated least-privilege app role, no admin/migration DDL privilege for runtime service, separate migration executor, connection pooling limits, statement/idle timeouts, transaction isolation, durable migrations and rollback strategy. Test account session invalidation/transaction atomicity and default-deny when identity/entitlement missing.

**Backups and security:** Railway plan-specific backup/PITR availability, retention, cold restore, network access, capacity and pricing must be checked against current provider account and documentation before promising them. Conduct a real isolated cold-restore exercise before storing user data. Store secret references in provider managed secret settings; never paste in this chat or commit secrets.

**Privacy/cost review:** email/account data retention, export/deletion, user consent, breach response, email deliverability, spam/signup rate limits, DPA and region decision, DB+auth+email cost and caps. No subscription charges until separately reviewed.

## 4. CI and next release gates

P1A baseline passed 51 focused tests at reviewed `5c1862d1708a1199d0aec6c0fd3f54575dad927c`. P1B-0 adds provider-subject negative tests and isolated **local** PostgreSQL v17 service testing: applying the two reviewed SQL migration files, exact issuer-subject uniqueness, account-isolated watchlists, session/entitlement read, entitlement revocation and role/tier independence.

The CI database test uses an explicit `YES_THROWAWAY_DATABASE` marker, accepts loopback host and `/vowsig_test` database only, and can **never target Railway**. It validates schema semantics, **not** Railway service TLS, network or disaster recovery. No production activation from CI success.

**Next P1B-1, after provider selection/security proof:** implement real email-verified OIDC code+PKCE callback and atomic account creation/binding, single-use authorization state/nonce; secure app session issuance and logout/revocation; signup abuse controls and user deletion/export. Add provider-mocked and integration tests. No status or preview may claim registered user access while feature flag OFF. Do not merge to `main` or deploy until exact reviewed SHA and owner release gate.

## 5. Product restrictions preserved

Nine catalogued markets available for discovery/watchlists; only XAUUSD, USTEC, US30 have existing-permitted Core AI-v1.1 research details. Six expansion and crypto research markets remain aggregate-only, even for hypothetical paid account. No customer alerts, subscription billing, broker execution, unlicensed candle redistribution or publication-gate override.
