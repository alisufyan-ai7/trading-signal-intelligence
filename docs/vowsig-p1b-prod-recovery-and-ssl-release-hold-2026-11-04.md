# VowSig P1B recovery and Railway release gates — 2026-11-04

**Owner directive:** Continue the next safety checks; Auth0 must remain on Free ($0). Do not imply that a CI database restoration is a production backup. Strict isolation: this chat and `alisufyan-ai7/trading-signal-intelligence` are the work record. Keep consolidated PR #93 in DRAFT; do not merge, deploy the VowSig app, enable account flags, or touch trading runtime until a separately accepted exact release.

## Owner amendment: single full customer + owner + history launch

**2026-11-04: superseding release scope.** The owner rejected a limited-signup first release. The one production launch MUST include free customer identity, full functional owner/admin dashboard with independent free-to-operate MFA, and independently source-reconciled historical analytics. The former suggestion to launch owner/admin or history later is withdrawn. Internal isolated tests/infrastructure rehearsal remain allowed, but no public signup or admin/history activation until all gates pass together.
## 1. Current live status and pending Railway change

Read-only inventory 2026-11-04:
- Railway `positioning-engine-cron` / `production` has online `Postgres` 18.6, Singapore, private service, 5 GB volume; deployment `d9f7a675-175e-4eb4-ba83-2ce9bf4c7bfd` SUCCESS.
- `tradingtop-early-access` remains on GitHub `main`, original production deployment `59afe99e-c590-4db9-b118-b75a8c75bd7e` SUCCESS, `vowsig.com` available.
- **A pre-existing STAGED Railway environment patch** `a18c5bf5-3461-4ba1-a220-49b9cc5d2fd0`, adding `VOWSIG_ACCOUNTS_APP_ORIGIN` to the live app, was discovered. This was **not** applied, changed, accepted or discarded by this run. It must not be accidentally committed by any database/service operation. Before later release, the owner should reconcile this patch with the reviewed variable release plan.
- Account/OIDC feature flags still default OFF in the **currently deployed code**; PR #93 remains separate from production.

## 2. Railway TLS identity: database-container PASS; independent client proof pending

**New 2026-11-04 owner-console evidence supersedes the prior CN-only hold.** PostgreSQL reported `ssl=on`. Its current server certificate has `subject=CN=localhost`, `issuer=CN=root-ca`, and **SAN `DNS:localhost, DNS:postgres.railway.internal`**. It expires 2029-02-01 12:51:47 UTC. The provided command's `PGSSLMODE=verify-full` and `PGSSLROOTCERT` check against `postgres.railway.internal` returned **`PRIVATE_DNS_TLS_VERIFY_FULL=PASS`** from within the database container. PostgreSQL libpq matches a DNS SAN before falling back to CN. The stock image **does provide the required SAN here**; do not create, rotate or replace a certificate to address a non-existent CN mismatch.

Recorded leaf SHA256 `42:57:4E:CA:8C:9A:FA:48:1B:EE:FB:2C:3E:A6:B5:08:BC:D3:E6:C2:7E:1B:28:7D:20:27:4D:72:45:8E:95:26`; root CA SHA256 `2D:E2:74:3A:F6:45:B4:EA:17:80:FF:9F:33:3B:C7:E2:5C:18:97:48:3A:C4:62:EB:C8:75:6B:4F:AB:11:BA:A8`. These are **public certificate fingerprints**, not private keys. The owner paste has some terminal line corruption; the positive reported result is evidence, not a verified application-side result.

**Remaining independent acceptance gate:** extract **only the public CA certificate** from the database container, validate its fingerprint against the above, and supply it as a trusted CA to a diagnostic performed in the VowSig application container or an isolated same-network test client. Connect using the exact `postgres.railway.internal` name, require hostname validation, inspect negotiated TLS protocol/certificate chain, and then repeat via application `psycopg` with `sslmode=verify-full` using a *non-superuser* DB role. Do not copy a private CA key or DB URL into chat/GitHub, disable TLS or expose the DB to the internet. Before the single release, provide a safe way to deploy the public CA and handle rotations/restarts. Database-container PASS is not enough to issue sessions.

**Recovery gate unchanged:** independent encrypted offsite backups, retention and actual separate cold restore before real accounts; no SQL migrations or customer data on the new Railway database until recoverability and role policy are reviewed.

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

## 5. One production go/no-go (no phased release)

The one joint release cannot proceed until: strict authenticated PostgreSQL identity on private DNS, minimal DB roles and migrations, real encrypted offsite cold restore, Auth0 and Resend user flows, owner/admin MFA and secure bootstrap, complete operations/growth/performance paths, independently authorized immutable-source historical reconciliation, adverse-outcome UI/permissions, staging/rollback and exact-SHA owner signoff. Fully unverified cohorts remain explicitly unavailable; never misrepresent partial history as complete. Paid/signal expansion/trading execution remain prohibited.

**No release calendar is yet proven.** The owner wants all features in one launch; treat remaining verification work as parallel implementation tracks and do not promise a second release. No production merge or staged Railway variable acceptance before the exact final review.

## 6. External choices still open

Choose a recoverable, trusted certificate/CA lifecycle and independent encrypted backup destination with cost ceiling before touching the private Railway DB. No public DB proxy, no unapproved paid Auth0 upgrade, and no staged VowSig app variable deploy.
