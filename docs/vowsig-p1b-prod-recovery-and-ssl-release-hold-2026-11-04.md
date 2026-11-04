# VowSig P1B recovery and Railway release gates — 2026-11-04

**Owner directive:** Continue the next safety checks; Auth0 must remain on Free ($0). Do not imply that a CI database restoration is a production backup. Strict isolation: this chat and `alisufyan-ai7/trading-signal-intelligence` are the work record. Keep consolidated PR #93 in DRAFT; do not merge, deploy the VowSig app, enable account flags, or touch trading runtime until a separately accepted exact release.

## 1. Current live status and pending Railway change

Read-only inventory 2026-11-04:
- Railway `positioning-engine-cron` / `production` has online `Postgres` 18.6, Singapore, private service, 5 GB volume; deployment `d9f7a675-175e-4eb4-ba83-2ce9bf4c7bfd` SUCCESS.
- `tradingtop-early-access` remains on GitHub `main`, original production deployment `59afe99e-c590-4db9-b118-b75a8c75bd7e` SUCCESS, `vowsig.com` available.
- **A pre-existing STAGED Railway environment patch** `a18c5bf5-3461-4ba1-a220-49b9cc5d2fd0`, adding `VOWSIG_ACCOUNTS_APP_ORIGIN` to the live app, was discovered. This was **not** applied, changed, accepted or discarded by this run. It must not be accidentally committed by any database/service operation. Before later release, the owner should reconcile this patch with the reviewed variable release plan.
- Account/OIDC feature flags still default OFF in the **currently deployed code**; PR #93 remains separate from production.

## 2. Proven limitation: Railway stock TLS certificate

PostgreSQL logs showed **`CN=localhost`** and the stock `postgres-ssl:18` image; that is not an exact match for `postgres.railway.internal`. The application store requires PostgreSQL `sslmode=verify-full`. The stock `DATABASE_URL` does not itself prove matching SAN or trusted CA, and Railway does not expose the internally generated root CA via this connected tool.

**Fail closed.** No app `VOWSIG_ACCOUNTS_DATABASE_URL` secret, no `sslmode=require`/unverified TLS downgrade, no customer schema migrations or auth issuance.

Review an isolated, recoverable database-side certificate solution where:
- A controlled CA trust anchor and server cert are managed securely; server SAN covers the exact private hostname and is checked from the app network with `sslmode=verify-full`, `sslrootcert`, TLS protocol and cert expiry evidence.
- A deterministic cert renewal/redeploy and client-CA rotation procedure is tested. Never distribute the CA private key or DB passwords.
- The current unbacked DB server is not modified in place to fix TLS until a reversible restore-safe path is available.
- The design can be validated on an isolated synthetic database before migration of actual accounts; no public TCP proxy required.

**Reference only:** Railway public provider documentation and discussions identify `CN=localhost` as a known property of their stock image. A `PGHOSTADDR` / `PGHOST=localhost` workaround is fragile due to private IP rotation; treat as an experiment, not the release certificate identity design.

## 3. Independent low-cost recovery

The owner's screenshot confirms Railway's native backup creation/schedules require an upgrade. Do **not** upgrade Railway or Auth0 on this evidence.

For customer launch, implement a separate least-privilege logical-backup identity and a scheduled job exporting a complete, consistent `pg_dump -Fc` to durable storage **outside the database volume**, with encryption before upload, integrity manifest, retention, alarms and an **actual cold restore to another isolated DB**. Review destination trust, monthly cost, access controls, RPO/RTO, encrypted-key recovery and data deletion policy before enabling. DB volume persistence is not an independent backup. No provider bucket or scheduled backup job was provisioned by this PR.

### New *disposable CI-only* acceptance test

PR adds `scripts/vowsig_accounts_ci_pg18_recovery.py` and a step in `.github/workflows/vowsig-accounts-review.yml`, after the existing PG18 account and OIDC tests:
1. Requires GitHub Actions, exact repository, explicit `YES_THROWAWAY_DATABASE`, a fixed loopback-only `vowsig_test` DSN with fixed CI-only password, and exactly one `postgres:18-alpine` container.
2. Uses the native PostgreSQL **18** `pg_dump -Fc`, `createdb`, and `pg_restore --single-transaction --exit-on-error` to create **`vowsig_restore_test`**, separate from the original disposable database. No external database, cloud credentials or network endpoint.
3. Cryptographically fingerprints all `vowsig_` tables, their column contracts, and row content **in memory only**, comparing source and restored DB without logging synthetic emails, hashed session tokens or OIDC state.
4. Creates an isolated CI-only non-login **`vowsig_runtime_ci`** role, grants runtime DML/sequence access, and proves the role can read accounts but cannot `CREATE TABLE` in the shared schema.

**A CI PASS means the current schema can roundtrip through a logical PG18 backup and the proposed restricted role denies schema creation. It DOES NOT prove offsite encryption, scheduled backups, production restore, physical PITR, exact least-privilege DML coverage or a Railway TLS connection.** Do not claim production-ready from this alone.

## 4. Authentication / email gates

- Auth0 tenant shows **Free $0**; standard Regular Web Application, code+PKCE, Client Secret (Post), email-required and Verify email on sign up checked. Owner/admin route still needs independently evidenced fresh MFA; do not buy premium MFA or bypass the requirement.
- Resend `mail.vowsig.com` provider DNS verified, Auth0 test email delivered. This confirms delivery, not real customer verification / authorization-code flow into VowSig.
- Actual Auth0 discovery/JWKS public endpoints, Auth0 login/user confirmation, session rotation, bad-callback denial and logout should be exercised from a **nonproduction test origin** after TLS, DB roles and recovery.

## 5. Go/no-go by release scope

**Limited free customer signup beta** can go only after TLS identity proof, restricted DB credentials and account schema migration/audit, independent scheduled encrypted backups with real restore, Auth0 end-to-end verified email/session tests, real app/UI/CSRF/rate-limit smoke tests, and one controlled canary with documented rollback. Operator should approve the exact tested PR HEAD and staging-to-production plan. No payment collection or broker execution.

**Owner/admin dashboard** additionally requires free-to-operate, security-reviewed step-up MFA and real owner role bootstrap, plus analytics provenance and private admin privacy controls. **Full-history performance** additionally requires independently reconciled immutable history, source pins and reporting accuracy signoff; quarantined replay is not completeness proof. These may launch *after* the limited free signup beta.

**Date/time:** A release calendar can be set only after actual TLS/recovery/identity checks pass. No production completion date is certified or promised from CI alone.

## 6. External choices still open

Choose a recoverable, trusted certificate/CA lifecycle and independent encrypted backup destination with cost ceiling before touching the private Railway DB. No public DB proxy, no unapproved paid Auth0 upgrade, and no staged VowSig app variable deploy.
