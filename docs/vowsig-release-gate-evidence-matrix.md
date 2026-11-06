# VowSig — exact-candidate release evidence matrix and GO / HOLD decision sheet

**2026-11-06, updated from PR #93 source.** The authoritative executable evidence contract is [`src/trading_signal_intelligence/product/accounts/release_acceptance.py`](../src/trading_signal_intelligence/product/accounts/release_acceptance.py), not this table. Read [current state](VOWSIG_START_HERE_CURRENT_STATE.md) and refresh the PR's latest HEAD/CI before recording actual run-specific evidence. The owner-approved history deferral changes **only history certification timing**, not the requirement for truthful N/A or the other release gates.

**Meaning of labels:** `IMPLEMENTED` is code only; `CI PASS` is isolated fixtures; `PRIOR STAGING PASS` refers to actual older staging receipts/screenshots; `OWNER-REPORTED PASS` is owner-run operator output; `HOSTED READ-ONLY PASS` is an anonymous live check; `HOLD` means **no complete exact-candidate real receipt**. None of those automatically satisfies the signed gate until reviewed full private receipt, custody, timestamp, signer/owner and exact candidate hash are actually bound.

## 1. Required 17 evidence gates and where proof must come from

| Exact key in `REQUIRED_GATES` | Most recent known evidence, limitations | Remaining proof / current release readiness |
| --- | --- | --- |
| `exact_head_ci` | Candidate pre-document code SHA `737ec740023f3b20fe7256cff18d182f37a4934c` passed security/PG and browser QA in Actions #42222013331 | **RECHECK** final PR HEAD and exact-HEAD CI after all docs/code commits, then sign that SHA's real run receipt. |
| `auth0_public_oidc_jwks` | Public Auth0 discovery/RS256 JWKS/issuer metadata checked; **owner screenshot 2026-11-06** shows existing `VowSig Web` production callback, logout and origin correctly set. | Configuration screenshot is not a real production callback. Screen displays **production URLs only**; preserve the known staging Railway hostname URLs if sharing this Auth0 client, then revalidate exact issuer/release identity. |
| `auth0_verified_email_signup` | Real staging verified member sign-in PASS on earlier deployed candidate | Production/Auth0 correct app config, verified customer onboarding after approved cutover; exact candidate receipt needed. |
| `auth0_unverified_duplicate_replay_denial` | CI synthetic negatives; real staging negative flow only partially evidenced | Real unverified email, duplicate identity/collision, stale code/state/cookie replay refusal without leaking claims. |
| `auth0_return_login_logout` | Staging live verified login, watchlist, logout then protected 401, fresh re-login PASS on earlier candidate | Confirm same release candidate security and production cookie/callback settings. |
| `resend_actual_delivery` | `mail.vowsig.com` verified, sending-enabled; **owner screenshot 2026-11-06** shows Auth0 Resend provider `accounts@mail.vowsig.com` plus masked key. **CONFIGURED, NOT DELIVERED.** | First run `Send Test Email` to owner-controlled inbox and confirm receipt; still require actual release-time Auth0 verification message / verified email sign-in. Don't mark this signed gate PASS on config screenshots. |
| `railway_authenticated_app_role_verify_full` | SQL roles/schema owner-run production 001–010 PASS; previous credentials-free app-network TLS handshake PASS. **Owner-reported actual DB-service read-only `vowsig_app`/`sslmode=verify-full` and restricted privileges PASS on Nov 6**, with `PRODUCTION_DATABASE_WRITES=NONE`. | **Partial real evidence now PASS from DB Console; full signed gate remains HOLD** until candidate **application-container** uses the staged DSN to authenticate via actual `psycopg`, verifies CA/host and denies DDL. Do not rerun the DB Console script. |
| `railway_migration_role_isolation` | Owner-run 001–010 atomic migration/roles PASS with production-only guards; CI privilege tests PASS | Independently review restricted app/migrator/backup grants and real release receipt; **no rerun of migration**. |
| `owner_initial_mfa_enrollment_solo_exception` | Actual staging owner one-use signed founder self-authorization and TOTP/pass result + audit | Truthfully label as **solo initial**; production requires separate existing account's approved bootstrap, not staging secret reuse. |
| `owner_mfa_stepup_real_staging` | Real staging /admin screenshot and owner API load after fresh TOTP PASS; guest owner 401 | Preserve exact release candidate role/session/MFA negative tests and owner time freshness. |
| `owner_mfa_rotation_recovery` | Source implements offline distinct-human recovery protocol; **actual required 2-human acceptance NOT independently proven** | HOLD until real required recovery factor custody/rotation/approval/old-session revoke is completed under current policy, or separate explicit owner-authorized policy amendment. Do not claim founder first-owner solo satisfies it. |
| `uncertified_historical_performance_suppressed` | Staging real owner Performance Lab rendered **N/A** with source reconciliation HOLD | Verify exact candidate and actual production owner/guest responses do not publish uncertified returns, win rates or equity; sign receipt. |
| `owner_admin_operational_market_reliability` | Real staging /admin operational overview, models, nine-market cards, evidence and growth rendered | Verify true data freshness statuses and privacy, no fabricated external source or broker stats; final deployed state with public snapshot. |
| `customer_signal_center_entitlements_and_privacy` | Real staging watchlist persistence and six forbidden market details 403; CI mobile | Final release candidate 3-core permission, six status-only, CSRF/account isolation, saved history and logout. |
| `public_publisher_latest_reliability` | Existing production `vowsig.com/api/health` was fresh with three core collectors at Nov 6 check, programs 3, execution off | Repeat ONE read-only **at cutover**; ensure no stale/missing snapshot, ingester/data volume and protected publisher unaffected. |
| `staging_security_browser_permissions` | Actual member/owner staging positives plus guest 401; CI browser/mobile/CSRF PASS | Exact candidate browser and security/replay negative receipt; no need to rerun unchanged earlier positives without reason. |
| `staging_rollback_rehearsal` | Prior production image `59afe99e-c590-4db9-b118-b75a8c75bd7e` rollback-eligible at inspection; **no real same-candidate rollback verified** | HOLD for bounded actual release-candidate rollback/compatibility proof without dropping schema/volume or Windows publisher. |

All gates require one real `PASS` receipt bound to **actual exact candidate SHA**, current UTC, appropriate evidence type/human reviewer ID, 64-digit receipt hash and declared private receipt custody. The signature on the evidence bundle does **not** make an unverified external claim true. Reuse older real receipts only where still applicable and explicitly reviewed against the same changed behavior.

## 2. Release invariants and approved exceptions

- `repository=alisufyan-ai7/trading-signal-intelligence`, `pull_request_number=93`, candidate and main exact 40-char SHAs, `release_scope=ONE_AUTHENTICATED_RESEARCH_BETA_WITH_UNCERTIFIED_HISTORY_UNAVAILABLE`.
- `mode=SHADOW_ONLY`; `research_only=true`; `broker_execution_disabled=true`; `six_noncore_public_signal_details_disabled=true`.
- `historical_performance_requires_independent_source_attestation=true` and `independent_history_certification_deferred_by_owner=true`, `uncertified_historical_performance_unavailable_at_launch=true`, `independent_source_review_required_before_history_publication=true`. These do **not** imply independent source-rights/cost/K5 sign-off already occurred.
- `new_railway_postgres_backup_unverified=true` + `owner_accepted_recovery_risk=true` + `first_postlaunch_action=RAILWAY_PG_ENCRYPTED_S3_B2_BACKUP_AND_COLD_RESTORE`. Explicitly accepted for first release only; risk must be visible.
- Signed evidence gate returns `production_release_automatically_authorized=false` and still requires **independent owner exact-SHA merge/deploy approval**.

## 3. Bound acceptance rehearsal with the fewest operations

1. Confirm final exact-HEAD CI and complete PR diff/release image. No feature additions.
2. **DONE / do not repeat:** owner's one-pass production PG `vowsig_app` SELECT-only verify-full/least-privilege check PASS. Final **app-container** verified-full check remains necessary at cutover; do not rerun migrations or the Postgres Console check.
3. Confirm production Auth0 allowed callback/origin/logout and Resend **actual** verification email; then private app-container DB and owner/security acceptance at exact candidate.
4. One coordinated staging rollback candidate/old image, no data volume or PG downgrade. Confirm current public publisher health/SHADOW_ONLY at cutover.
5. Human trusted reviewer examines real receipts and signs the full exact candidate evidence; owner separately approves the **full SHA** for merge and production deploy. Without either, **HOLD**.
6. One approved live enablement, real customer/owner smoke, then first immediate postlaunch encrypted Railway PG backups+isolated cold restore.

**NO duplicate staging publisher, NO additional source ledger replay/freeze, NO customer broker execution, NO paid checkout, NO faked performance, and NO production change without explicit authorization.**
