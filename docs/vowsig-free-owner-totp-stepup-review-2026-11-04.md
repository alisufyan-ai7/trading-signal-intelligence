# Owner MFA on Auth0 Free — independent TOTP step-up implementation (review only)

**Decision:** Auth0 must stay on the **Free $0 plan**. VowSig must deliver full secured owner/admin access at the same one-time fully enabled customer launch. Native Auth0 Pro MFA is **not** a dependency. The owner opted to begin new Railway PostgreSQL S3/B2 backups immediately **after** go-live, knowingly accepting temporary data-loss exposure; other authentication and security acceptance is NOT waived.

## Engineering contract

Candidate files:
- \`src/trading_signal_intelligence/product/accounts/owner_mfa.py\` — RFC6238 TOTP (SHA1/30-second/six-digit; ±1 time step), 160-bit random secret generator for an *offline* operator, AES-256-GCM encryption bound to the exact account UUID, 256-bit URL-safe master-key validation, monotonic counter replay protection.
- \`sql/accounts/008_owner_mfa_stepup.sql\` — encrypted owner factor stored per owner account, accepted step/retries/lockout state. Apply migrations 001–006, then **008**, and **007 grants last**. Table must be owned by restricted migrator in \`vowsig\` schema.
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
