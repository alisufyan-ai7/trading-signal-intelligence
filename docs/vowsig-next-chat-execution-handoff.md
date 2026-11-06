# VowSig — next-chat execution handoff (2026-11-06)

**Use only the new current chat and GitHub repository `alisufyan-ai7/trading-signal-intelligence`.** Do not use unrelated repos, memories, earlier conversations or accounts. GitHub is the authoritative durable record. This is a checkpoint, not an automatic grant of production authority.

## Start here — refresh, never assume a dated HEAD is current

1. Open draft [PR #93](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93); refresh its actual HEAD, base, draft/merge state, latest comments and exact-HEAD GitHub Actions. A doc commit changes the HEAD without deploying the app.
2. Read [canonical current state](VOWSIG_START_HERE_CURRENT_STATE.md), [full Railway staging/production rebuild and cutover runbook](vowsig-railway-zero-to-production-rebuild-runbook.md), [current product contract](vowsig-product-contract-current.md), [explicit owner policy amendment](vowsig-owner-approved-first-launch-history-deferral-2026-11-06.md), and [signed evidence gate](../src/trading_signal_intelligence/product/accounts/release_acceptance.py).
3. Keep **one fully enabled authenticated production release** as the goal, with no scope creep, new publisher, paid features, alerts, execution, new markets or unauthorized noncore signal details.
4. Owner explicitly approved independent historical rights/cost/crypto K5/full-history certification **AFTER** initial launch while historical numbers remain **N/A**. Owner approved encrypted recurring Railway PostgreSQL S3/B2 backup+real isolated restore as the **first immediate postlaunch task**, accepting temporary potential unrecoverable customer-data loss. Both choices already recorded in code/documents; **do not reopen them**.
5. **Separate exact 40-character SHA owner approval** is still required to merge PR #93, deploy production app or switch feature flags. Staging testing or a signed CI fixture never gives automatic launch approval.

## Current operator checkpoint — do not repeat completed steps

**DONE, real owner-reported PASS:** staging verified Auth0 member signup/login, watchlist persistence, preferences, logout/relogin, noncore 403, and member mobile/browser acceptance; staging SQL migration 010; founder Mac Google Authenticator enrollment and audited one-use `first_owner_solo` promotion with one session revoked; true owner MFA step-up/admin UI; removal of isolated privileged staging Railway operator. Staging currently contains only its app and PG. No current staging research snapshot; do not build another publisher. No need to rerun these.

**DONE, real owner-reported PASS:** **production** Railway Postgres SQL **001–010 single transaction** and separate restricted `vowsig_app`, `vowsig_migrator`, `vowsig_backup` roles. Sanitized receipt:
```
PROD_VOWSIG_001_010_COMMITTED=PASS
PRODUCTION_PG18_ROLES_AND_SCHEMA=PASS
PRODUCTION_ACCOUNT_FEATURE_ENABLED=NO
PRODUCTION_OWNER_PROMOTED=NO
TRADING_PUBLISHER_OR_WEB_CHANGED=NO
```
**DO NOT RERUN 001–010**. Owner has privately stored three DB role passwords; never request their values.

**DONE, Railway staged but NOT applied:** existing `positioning-engine-cron / production / tradingtop-early-access` holds **12 pending variable changes** on the same service, including new production `VOWSIG_ACCOUNTS_DATABASE_URL` using the restricted role, CSRF secret, existing Auth0 client secret, distinct production TOTP master key, public OIDC endpoints and two feature switches left OFF. Variable names were verified read-only; values were NOT read. No Deploy/Apply Changes, no customer signups yet; existing successful production image and original `/data` snapshot volume still intact.

**DONE, recent CI PASS:** exact tested code/doc SHA **`737ec740023f3b20fe7256cff18d182f37a4934c`**, [GitHub Actions #42222013331](https://github.com/alisufyan-ai7/trading-signal-intelligence/actions/runs/42222013331), both account/security/PG18 and browser-qa SUCCESS. This doc batch later changes the PR HEAD; refresh CI before any release. Production main last observed `13aeb2bfe2560d3afef63019e4282361fd552faf`; prior healthy public app deployment `59afe99e-c590-4db9-b118-b75a8c75bd7e`, rollback-eligible at inspection.

**NEXT owner action currently in progress:** ONE read-only role and TLS verification from **Railway production Postgres Console**, script [`ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh`](../ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh). The owner has the Mac one-paste copy instructions from exact tested `737ec740023f3b20fe7256cff18d182f37a4934c`. The script accepts the existing private `vowsig_app` role password via hidden input, proves `sslmode=verify-full` to `postgres.railway.internal` and SELECT-only restricted grants, and does not change SQL, app or publisher. **NO USER-REPORTED PASS YET** at this writing. Ask for sanitized status if they have run it, then record only that outcome; otherwise do not assume CI did live SQL.

Expected safe receipt:
```
PRODUCTION_APP_ROLE_TLS_PRIVILEGE=PASS
CONNECTED_ROLE=vowsig_app
PRIVATE_DNS_VERIFY_FULL=PASS
PRODUCTION_DATABASE_WRITES=NONE
PRODUCTION_WEB_APP_DEPLOYED=NO
LIVE_PUBLISHER_CHANGED=NO
```

## Next actions only after user reports real TLS/role result

1. If PASS: mark exactly that as owner-run DB-service-private-network evidence, **not** proof of final released app-container DSN bytes. If HOLD, diagnose focused error, never disable TLS or rerun PG migration.
2. Verify production Auth0 Regular Web Application allowed callback `https://vowsig.com/auth/callback`, origin `https://vowsig.com`, allowed logout `https://vowsig.com/`, preserve staging. Real verified-email/Auth0 callback and negative login/replay tests remain necessary.
3. Verified Resend domain `mail.vowsig.com` and existing transactional key are present; **actual production email delivery not yet proved**. Never create another credential/domain unnecessarily or expose secrets in chat.
4. Prepare a **single coordinated, approved** production application cutover with source SHA + image rollback, existing `/data` and `TRADINGTOP_INGEST_TOKEN` preserved, runtime app-network DB role and signed owner release receipts. Production owner must be enrolled separately from staging with distinct production MFA key, audited owner-factor proof and recovery requirements; don't assume staging proves production.
5. Reuse already passed staged member/owner tests except for changed release-specific functionality. Complete bounded real login/permissions/watchlist/owner TOTP, public snapshot freshness, N/A historical panels, mobile/security and previous-image rollback compatibility.
6. Only when remaining mandatory gates pass, request **separate explicit owner approval of full exact 40-character PR SHA to merge and deploy**. The user wants no second feature-disabled public release.
7. Immediately after launch create **Railway PostgreSQL** encrypted scheduled S3/B2 offsite backups + actual isolated cold restore and monitor; S02-only historical backups do not protect new accounts. Only later independently certify nine-market rights, costs, K5 and complete history to publish performance.

## Strong operational boundaries

- Existing production research beta `https://vowsig.com` had a genuine fresh snapshot, 3 core collectors ready and 3 SHADOW_ONLY validation programs across the approved nine lineages at last read-only check; freshness MUST be rechecked before production cutover. Existing Windows VPS is the sole approved upstream publisher. No duplicate staging publisher.
- Keep broker execution OFF, expansion/crypto six signal details blocked, all uncertified returns N/A; don't convert 11,103 source ledger rows or 298 internal cost legs into externally verified performance.
- Use GitHub PR #93 for progress/decisions, no separate branches unless explicitly approved. Document owner-supplied versus independently observed evidence honestly.
- Use ONE full Mac/Railway Console paste for any necessary private operator. Never paste passwords, keys, TOTP setup code, callback `code/state`, database DSN, raw immutable Auth0 identifiers or credential screenshots to chat/GitHub. Do not request previously completed owner steps again.

## Copy into new chat

> Continue VowSig toward the **earliest safe one-time full authenticated production launch**. Strict context: ONLY this new chat and GitHub `alisufyan-ai7/trading-signal-intelligence`. Fetch PR #93 current HEAD/CI/comments. First read `docs/VOWSIG_START_HERE_CURRENT_STATE.md`, `docs/vowsig-next-chat-execution-handoff.md`, `docs/vowsig-railway-zero-to-production-rebuild-runbook.md`, `docs/vowsig-product-contract-current.md`, Nov 6 owner-approved history deferral, and `release_acceptance.py`. Existing staging verified Free/owner MFA PASS; production SQL 001–010 PASS, don't rerun; 12 production Auth0/DB/CSRF/TOTP variables STAGED but NOT deployed. The owner is performing ONE read-only production `vowsig_app` private verify-full SQL check—take its sanitized result and continue. Preserve live `vowsig.com`, `/data` and Windows publisher. No feature creep or duplicate publisher. Historical certification was explicitly moved after launch with unverified returns N/A; Railway PG S3/B2 backups+cold restore first immediately after launch. Finish real Auth0/Resend, final app-role acceptance, production owner TOTP, security/rollback and exact-SHA release evidence. **Do not merge/deploy until separate full-SHA owner approval**. Update GitHub handoff after every real verified milestone.

**Update rule:** when the owner reports the pending TLS check, revise this doc and [current-state index](VOWSIG_START_HERE_CURRENT_STATE.md), link the latest PR comment/CI and preserve old receipt text. A new chat must never need a remembered answer to locate the next action.
