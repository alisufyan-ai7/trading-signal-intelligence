# VowSig full-feature single-release plan — backup implementation immediately AFTER go-live (2026-11-04)

## Binding decision log (authoritative, later decisions supersede earlier)

- **D-01 — Single complete production launch:** The owner requires customer signup, verified email and sessions, Signal Center, full functional owner/admin dashboard with free-to-operate fresh MFA, and independently audited full historical analytics together. No partial/beta/public phase, no feature-disabled predeployment, no paid Auth0 features, no broker execution or billing.
- **D-02 — Build features before database recovery:** Complete and rigorously test the product, original-ledger reconciliation, authorizations and operational views first. The Railway PostgreSQL backup integration is explicitly DEFERRED until AFTER the fully enabled production release.
- **D-03 — Launch without new database backups, knowingly accepting exposure:** Owner explicitly accepts a period immediately after launch during which the Railway PostgreSQL service has **no independently verified automated offsite backup or tested cold restore**. Risks include permanent loss of customer identity bindings, consent/watchlists and saved research, inability to recover recent writes after storage/DB failures, extended outage and potential privacy/compliance and customer-trust impact. Neither SSL nor Railway persistent volumes nor the Windows S02 backup covers this risk. A code rollback does NOT restore lost data. Do not label the launch “backup protected” or “fully recoverable” until verified.
- **D-04 — Start recovery immediately after go-live:** Reuse pre-existing S3 and/or Backblaze B2 infrastructure where authorized, but deploy a **separately scoped Railway PostgreSQL backup job**, distinct storage permissions/prefix, encrypted `pg_dump -Fc` output, integrity manifest, recurring scheduler, retention, alerts and an actual isolated cold restore. Prior S02 SQLite backup is not a PostgreSQL backup. Owner expectation: first post-launch work, measured in hours, not an indefinite backlog. If blocked, report the unprotected status and escalate for owner action; do not falsely assert it is solved.
- **D-05 — Other controls are NOT waived:** Exact tested SHA, admin MFA/recovery, end-to-end Auth0, identity/email and privacy, real authenticated least-privilege DB TLS connection, verified and authorized original historical source ledger/after-cost metric completeness, negative signal/market exposure tests, deploy rollback plan and healthy production smoke checks remain mandatory for launch. Enabling unverified data or bypassing MFA remains prohibited.
- **D-06 — GitHub is authoritative:** Keep this document and PR #93 checkpoints updated; use only this chat and `alisufyan-ai7/trading-signal-intelligence`. Keep PR DRAFT, no merge/app deployment/feature switch until complete implementation, verification and exact-SHA release approval. The live app has a separate existing staged `VOWSIG_ACCOUNTS_APP_ORIGIN` change; reconcile it before Railway accept-deploy.

## Execution order

1. Complete all features (user experience, full owner/admin read-only operations/growth/model/performance analytics, secure free owner MFA/seed/recovery, privacy/security, original immutable ledger complete-source reconciliation).
2. Run isolated DB/UI/auth/permission integration, official Auth0 user-verification test and source/provenance test, complete tests and test rollback, and document the candidate release bill of materials, configuration and acceptance receipts.
3. After exact owner release approval, **one full-feature launch to production with features enabled**. No intentional feature-disabled preliminary production deployment; preserve existing public publishing and broker-off status. Document that disaster recovery is pending.
4. **Immediately after full launch**, implement and test the Railway Postgres-to-S3/B2 encrypted recurring backup and separate restore. Record first successful copy/restore, schedule, retention, alerts, costs, encryption-key custody and provider parity in GitHub. Until those receipts exist the operational status must show `DATABASE_RECOVERY_UNVERIFIED`.
5. Independently verify recovery in ongoing operations and close the incident/risk entry; no new paid Auth0 subscription.

## Transparent risk treatment and post-launch minimum operations

Launch status must distinguish `FEATURES_LIVE` from `POSTGRES_RECOVERY_VERIFIED`. Log backup readiness as false, show an owner-visible warning, ensure issue monitoring and availability alerts, verify DB storage health and capacity, keep account privileges minimal, avoid risky migrations while unprotected, and limit exposure of secrets. A one-time pre-launch snapshot could reduce risk if an approved method already exists, but **it is not a launch prerequisite under D-03**. A last-minute cutover should not falsely imply this produces zero RPO.

**Unchanged:** Auth0 current plan Free $0, Resend sender/domain verified, TLS chain/SAN verified from application container, restricted PG18 roles tested in isolated CI. Latest complete CI evidence at last checkpoint was 162 tests. Production DB has no VowSig tables/roles so migrations and authenticated SQL are still pending. Original sources for independent full-history attestation are not yet shown in this chat/repo; no historical profitability claim may be generated from bounded public snapshots.

## Current owner dashboard development progress

PR #93 contains fail-closed account APIs, preliminary member UX and an owner-only `/api/v2/admin/evidence` that displays projection inventory but explicitly marks it **not independently verified**. All other owner dashboards, real owner MFA, source-ledger ingestion/validation and full after-cost history remain under active work, not yet production-ready.

**This change records a conscious owner risk decision; it does not mean the current draft is approved for launch.**

## Latest engineering scope (2026-11-04)

Owner-specific free TOTP step-up and privacy-safe owner growth/security reporting have been prepared as independent review tracks in PR #93. The implementation still requires verified external owner bootstrap, real authenticator enrollment/recovery testing, signed original-ledger research auditing and actual production DB authentication before launch. A complete one-time customer-facing release remains the directive; PostgreSQL offsite backup is the first post-launch task with `DATABASE_RECOVERY_UNVERIFIED` explicitly acknowledged until a real restore.
