# Owner MFA on Auth0 Free — independent TOTP step-up implementation (review only)

**Decision:** Auth0 must stay on the **Free $0 plan**. VowSig must deliver full secured owner/admin access at the same one-time fully enabled customer launch. Native Auth0 Pro MFA is **not** a dependency. The owner opted to begin new Railway PostgreSQL S3/B2 backups immediately **after** go-live, knowingly accepting temporary data-loss exposure; other authentication and security acceptance is NOT waived.

## Engineering contract

Candidate files:
- \`src/trading_signal_intelligence/product/accounts/owner_mfa.py\` — RFC6238 TOTP (SHA1/30-second/six-digit; ±1 time step), 160-bit random secret generator for an *offline* operator, AES-256-GCM encryption bound to the exact account UUID, 256-bit URL-safe master-key validation, monotonic counter replay protection.
- \`sql/accounts/008_owner_mfa_stepup.sql\` — encrypted owner factor stored per owner account, accepted step/retries/lockout state. Apply migrations **001–008 in numeric order**. The 008 migration grants only owner-MFA challenge-state updates to the app and SELECT access to the backup role when installed in the approved migrator-owned schema. Table must be owned by restricted migrator in \`vowsig\` schema.
- \`PostgresAccountStore.verify_owner_totp\` — performs cross-worker atomic row locking on credential+session, only for still-active verified owner accounts/sessions, checks encrypted factor, records per-account failed attempts with five-try/fifteen-minute lockout, rejects reuse of the same 30s counter, updates *that* session's \`mfa_verified_at\` only after success. The existing \`require_owner\` enforces the 15-minute freshness window for all admin endpoints.
- \`POST /api/v2/me/owner-mfa/verify\` — verified session, owner role, exact HTTPS Origin, CSRF, strict JSON payload. No public enrollment endpoint; no owner role promotion; no bypass on missing/invalid key. Responds no-store.
- The owner member settings screen provides a six-digit authenticator-code verification form and link to \`/admin/\`. Browser cannot retrieve enrollment secrets, migration credentials or the AES key.
- \`sql/accounts/007_restricted_roles_and_grants.sql\` explicitly allows only SELECT and UPDATE of the three owner challenge-state columns. Runtime role **cannot INSERT or change encrypted credentials/key versions**. Offline migrator owns and provisions them.

## Full production prerequisites STILL OPEN

1. **Owner identity bootstrap (out of band):** owner completes normal Auth0 verified email signup first. The human owner then confirms their *exact* immutable Auth0 (issuer,subject) bound account and authorizes a migrator-only role assignment. No self-service promotion; no “same email” linking.
2. **Factor enrollment and recovery (out of band):** a trusted operator using the migrator role generates the 160-bit TOTP secret locally, provisions the AES-GCM ciphertext for that exact account and securely supplies the authenticator secret once to the actual owner. It must never be pasted into chat, GitHub or app logs. The production master key \`VOWSIG_OWNER_TOTP_MASTER_KEY_B64\` must be generated as 32 cryptographically random bytes, stored in Railway's private secret store only and backed up separately from DB ciphertext. App must never log the key. Owner needs independent second-device backup/recovery procedure; lost factor recovery requires offline documented re-verification, explicit rotation, audit and session revocation.
3. **End-to-end testing:** a real verified Auth0 owner logs in, enters the authenticator code, opens admin, attempts replay/concurrent sessions, hits lockout, waits out lockout, then observes expiry and session revocation. Verify no paid Auth0 feature was activated. Require a staged secure recovery rehearsal and review by a second person.
4. **Audit and hardening:** audit admin operations and factor rotations; review security headers, privacy, rate control and per-session behavior; validate canonical key handling, time sync, controlled setup and encryption-key rotation. No role/secret/SQL has been applied to Railway.

This PR is *not* evidence of operational enrollment/recovery, nor permission to enable owner access. All automation and tests use synthetic keys, identities, and disposable PostgreSQL. A comprehensive owner security review remains a release gate.

## Exact rollout boundary

Do NOT merge draft PR #93 or change the live Railway database/app as an effect of this review. Only the owner can authorize the final exact tested SHA. Production site, broker execution (off), Auth0 Free plan and separately staged Railway variable patch remain unchanged.

## Session rotation security correction

A successful TOTP response atomically replaces the original session token SHA-256 with a new unpredictable 32-byte token and sets `mfa_verified_at`. The backend returns the replacement in a `Secure; HttpOnly; SameSite=Lax; Path=/` `__Host-` cookie; the old token cannot fetch a session or enter admin. The member settings UI refreshes `/api/v2/me` to obtain the new session-specific CSRF value. The production owner still needs an independently tested offline bootstrap and recovery procedure.


## 2026-11-04 — next engineering priority: signed offline owner identity bootstrap & recovery

Draft PR #93 now includes an offline-only, **independently signed** first-owner bootstrap / owner-factor recovery workflow, to close the prior unimplemented owner enrollment/recovery gap:

- Separate human reviewer signs a short-lived Ed25519 approval pinning the **exact existing Auth0 issuer and immutable subject digest**, reviewer identity, explicit owner re-verification/consent and a random one-time operation UUID. Reviewer's signing key stays OFFLINE and is not part of the web app or this repository.
- Separate database migrator/operator must use the strict Railway private hostname with `sslmode=verify-full`, an independently pinned public reviewer key and a two-person approval. Script defaults to **read-only preview**; apply additionally requires an interactive unrecorded terminal, fresh TOTP code and explicit session-revocation acknowledgment. No public owner enrollment/promotion is exposed.
- Migration `009_owner_offline_provisioning_audit.sql` adds a migrator-only single-use audit and enforces different reviewer/operator IDs. The action checks global first-owner uniqueness, the exact existing identity, the approved factor, performs an atomic factor enrollment/rotation and role change only where permitted, and revokes all existing sessions. New login and TOTP are mandatory.
- New disposable PG18 tests must prove exact-source identity, replay denial, first-owner invariants, factor rotation, separation, and no runtime audit DML. These operations have **not been executed on Railway**, and no genuine signing key, verified owner or real account PII was provisioned. This is code/test implementation, not operational acceptance.
- Canonical runbook: `docs/vowsig-owner-bootstrap-recovery-signed-operator-2026-11-04.md`. Still required: owner/security-reviewed real identity verification, secret custody, independent reviewer trust setup, actual Auth0 owner onboarding and recovery drill, CI exact-HEAD success.

**Release scope unchanged:** one complete enabled public release; PostgreSQL S3/B2 automated backup/recovery is first post-launch work by explicit owner risk acceptance. Real original ledger reconciliation, full admin and Auth0 + SQL role integration remain distinct release gates.

