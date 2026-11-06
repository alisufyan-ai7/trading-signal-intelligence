# VowSig — Railway staging, production rebuild, in-place release and recovery runbook

**2026-11-06; repository `alisufyan-ai7/trading-signal-intelligence`.** Read [START HERE](VOWSIG_START_HERE_CURRENT_STATE.md) before acting; old screenshots and commit pins are not necessarily current. **This is operational documentation, not owner consent to rebuild or deploy anything.** For the full seventeen real release gates, consult the [exact-candidate evidence matrix](vowsig-release-gate-evidence-matrix.md).

## 1. Four distinct operations — choose before touching Railway

| Mode | Purpose | Rule |
| --- | --- | --- |
| **A. Existing production in-place launch — NOW** | Introduce PR #93 authenticated member/owner code without disturbing existing public VowSig research beta | Reuse live `tradingtop-early-access`, `Postgres`, `vowsig.com`, existing `/data` volume and ingest token. **No new project, database, publisher, migrations or volume**; require exact-SHA owner merge/deploy approval. |
| **B. New isolated staging from zero** | Fresh QA environment and disposable account testing | New staging app+private PG+secrets+verified CA, no real production data/credentials; no replica publisher unless separately authorized. |
| **C. New production from scratch** | Explicitly approved greenfield or blue/green replacement | New private PG and app persistent volume, validated source-data/identity restoration, production-safe DNS switching, preserved old prod until rollback. Requires separate explicit approval. |
| **D. Disaster recovery** | Service/data loss | Select independently verified backup; cold restore and authenticate in isolated environment before traffic switch. Current Railway PostgreSQL independent cold restore **is not verified**. |

**Don't confuse new infrastructure with a deploy of the existing infrastructure.** A bare fresh schema won't restore customer sessions, identity, watchlists or original VPS evidence, and a Git clone is not a data backup.

## 2. Inventory and owner-held materials for a complete fresh deployment

| Category | Current observed production | New staging/production requirements and ownership |
| --- | --- | --- |
| GitHub source | Private repo; product release in draft PR #93 | Pin code + Dockerfile + commit 40-char SHA, review diff, CI, signed receipts and owner approval; do not use VPS code as authority. |
| Railway app | `positioning-engine-cron / production / tradingtop-early-access`; `vowsig.com` | Recreate a Python 3.12 web service from the repository-root `Dockerfile`, correct GitHub source branch/commit, port and HTTPS domain. Don't use `Dockerfile.owner-operator` for normal app. |
| Railway database | `Postgres`, PostgreSQL 18, separate volume, private `postgres.railway.internal` | Fresh private Postgres 18 plus durable volume; separate environment/roles; **no public TCP proxy**. Staging currently uses its own `vowsig-staging-pg18` and separate CA/DNS. |
| App durable data | `/data` app volume, `/data/public_snapshot.json`, feedback SQLite | Dedicated persistent volume mounted **`/data`**. Never overwrite or unmount during current release. Snapshot volume is not customer Postgres. |
| Publisher | Approved Windows VPS -> sanitized guarded snapshot -> Railway `/api/internal/snapshot` | Preserve existing scheduler, derived-only sanitizer and `TRADINGTOP_INGEST_TOKEN`. Don't create a second publisher or resend raw ticks/ledgers. |
| Identity | Existing Auth0 Regular Web Application, public issuer, verified email | Own tenant/app access, allowed exact callback/origin/logout, server-side client secret, OIDC code+PKCE and identity claims. Distinct staging/production URL entries. |
| Transactional email | Verified `mail.vowsig.com`, existing `VowSig Auth0 Transactional Email` Resend credential | DNS DKIM/SPF/DMARC review, sender and actual delivery/verification acceptance. No need for another key/domain for current release. |
| Owner MFA | Staging owner TOTP enrolled and tested; production owner pending | Fresh **environment-specific** 32-byte master encryption key, offline signer and 160-bit phone factor, verified immutable owner (issuer, subject), one-use signed approval, recovery custody and actual `/admin/` step-up. |
| Recovery | Legacy S02-only AWS S3/B2 backup; separate new Railway PG recovery absent | Independent encrypted PG `pg_dump -Fc`, manifest/retention, scheduled writer, S3/B2 scoped identities and verified isolated cold restore. For this initial launch, owner approved starting immediately after release, with acknowledged risk. |

**Private owner manifest (never committed):** Railway workspace/project/environment/service IDs and permissions; registrar DNS; GitHub access and exact deployed digest; Auth0 application/tenant secure settings; Resend credentials/sender; `POSTGRES_DB` and each DB/user password; 3 private `vowsig_app` / `vowsig_migrator` / `vowsig_backup` passwords; owner MFA encryption key + original factor/signer/recovery material; app CSRF and OIDC client secret; `TRADINGTOP_INGEST_TOKEN` and receiver URL, VPS scheduled publisher setup, AWS/B2 restricted credentials, cold-restore receipts. Record **where** these are securely held, not their values. No passphrase/code/password/client secret/DSN/Auth0 callback query in GitHub or chat.

## 3. Railway app build and runtime (all environments)

The repository-root [Dockerfile](../Dockerfile) is authoritative: `python:3.12-slim`; `COPY pyproject.toml README.md src web config`; `pip install -e ".[app,accounts]"`; `PORT=8000` default; `uvicorn trading_signal_intelligence.product.cloud_app:app --host 0.0.0.0 --port … --no-access-log`. Uvicorn access-line logging is suppressed to prevent OAuth `code`/`state` query strings leaking. Railway reverse proxy/domain remains responsible for TLS to the browser; outbound DB TLS is separately verified. Protect app service-to-service network. Distinguish `/healthz` (process) from `/api/health` (research freshness).

Public site serves `/`, markets, Learn, evidence and legacy APIs. New account routes from `src/trading_signal_intelligence/product/accounts/api.py`, `auth_api.py`, `ui.py` exist only when appropriate feature flags are enabled. A freshly deployed service **without** a snapshot should display missing/unavailable rather than fabricated output.

## 4. Detailed environment-variable/secret matrix

| Variable | Scope | Rules |
| --- | --- | --- |
| `PORT` | App | Railway value or default 8000. |
| `TRADINGTOP_SNAPSHOT_PATH` | App | `/data/public_snapshot.json`, persistent app volume. |
| `TRADINGTOP_INGEST_TOKEN` | Public snapshot receiver | Privately shared with approved VPS publisher; preserve existing token during current cutover. Never frontend or GitHub. |
| `TRADINGTOP_INGEST_URL` | VPS publisher | Approved cloud HTTPS `/api/internal/snapshot` endpoint. Confirm actual URL; historical `.env.example` may name an old domain. |
| `SIGNALPROOF_FEEDBACK_DB_PATH` | App | `/data/feedback.sqlite` on app volume. |
| `SIGNALPROOF_FEEDBACK_OWNER_TOKEN` | App owner feedback | Separate private bearer from ingest token. |
| `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED` | App | `0` by default; `1` only during approved account cutover after secure DB config. |
| `VOWSIG_OIDC_AUTH_ENABLED` | App | `0` by default; `1` only with foundation and trusted OIDC settings. |
| `VOWSIG_ACCOUNTS_APP_ORIGIN` | App | Exact HTTPS origin; no trailing slash (`https://vowsig.com` prod; true staging origin for staging). |
| `VOWSIG_ACCOUNTS_DATABASE_URL` | App **secret** | Restricted `vowsig_app` user only. Private hostname/port/DB; `sslmode=verify-full`, `sslrootcert=/app/config/tls/<pinned-environment-public-ca>.pem`. Never admin/migrator DSN; password percent-encoded. |
| `VOWSIG_ACCOUNTS_CSRF_SECRET` | App **secret** | Random >=32-byte high-entropy string, environment-specific. Preserve/rotate deliberately due to sessions. |
| `VOWSIG_OIDC_ISSUER`, `VOWSIG_OIDC_CLIENT_ID` | App | Exact trusted Auth0 issuer (typically ends slash) and reviewed Regular Web App ID. |
| `VOWSIG_OIDC_AUTHORIZATION_ENDPOINT`, `VOWSIG_OIDC_TOKEN_ENDPOINT`, `VOWSIG_OIDC_JWKS_URI` | App | Discovery-verified HTTPS endpoints. Never derive from browser input. |
| `VOWSIG_OIDC_CLIENT_SECRET` | App **secret** | Matching Auth0 confidential Regular Web Application; never source/chat. |
| `VOWSIG_OWNER_TOTP_MASTER_KEY_B64` | App **secret** | Exactly 43-char canonical URL-safe Base64 of **32 random bytes**; independent per environment; preserve with encrypted owner factor on migration/recovery. |
| `POSTGRES_DB`, `POSTGRES_USER`, `POSTGRES_PASSWORD` | DB service | Original database admin/system identity, NEVER use as web runtime role. |
| Resend sending credential | Auth0 email-provider secret | `mail.vowsig.com` verified sender; keep credential in approved Auth0/provider integration, not unused Railway app var. |
| `OPENAI_API_KEY`, MT5/Exness/Binance credentials | Windows research publisher | Not required for member web app; never exposed to website, signup system or GitHub. |
| AWS/B2 PG recovery keys | Separate postlaunch backup/restore job | Independent least-privilege identities and prefixes, encrypted; not S02 VPS credentials by default. |

For a new environment, record required env names, which ones are configured, and secure custody only. **Never dump values into logs.** Use Railway Variables staged patch, preview all service changes, and deploy only with explicit authority. The current production app has **12 pending staged variables** including the four secret names and both feature switches at `0`; these were not yet applied on Nov 6.

## 5. Fresh staging build from scratch (Mode B)

1. **Isolate** a new Railway project/environment and app service. Pin the exact GitHub SHA, repository root Dockerfile, runtime port, HTTPS staging hostname; do not bind production `vowsig.com`. Do not automatically inherit production secret environment or publisher.
2. **PG18**: provision separately with its own durable disk and internal DNS; no public proxy. Choose reviewed SSL-capable image. Confirm active PostgreSQL private hostname and **server certificate SAN matching that hostname**. The self-signed `CN=localhost` alone is insufficient. Generate approved cert/root CA; pin public CA SHA256, leaf, expiry; prove `sslmode=verify-full` from DB and app networks. Do not copy the production CA into unrelated staging.
3. **Roles**: create distinct `vowsig_app` runtime, `vowsig_migrator` schema owner, `vowsig_backup` read-only with private unique strong passwords and no superuser/createdb/createrole/bypassrls. Apply exact `sql/accounts/001..010` in order **once**, in a reviewed atomic transaction; assert isolation, 16-table/grant expectations, no runtime DDL or owner secret writes. Existing staging operator has fixed 2026-11-05 environment guards: **adapt/review for a truly new environment, never remove fail-closed checks**.
4. **Staging variables**: use staging-only verified `VOWSIG_ACCOUNTS_DATABASE_URL` and pinned *staging* CA, CSRF secret, Auth0 values and client secret, **different TOTP encryption master key**. Enable foundation/OIDC only once real provider/DB acceptance is ready. Default no staging snapshot: missing research data must show N/A safely; do not create a second VPS publisher.
5. **Auth0**: exact staging `https://<host>/auth/callback`, allowed `https://<host>/` logout and `https://<host>` web origin. Preserve other approved callbacks; check real verified/unverified email behavior, Auth0 signing keys, S256 PKCE and cookie state/nonce.
6. **Actual QA**: signup, verified email and Resend delivery, one verified member login, account data isolation, watchlist add/delete/refresh, settings, saved research, history, logout 200→401, fresh login and old-cookie replay rejection, restricted six 403 and guest admin 401. Test mobile 320/375/390/768 and desktop, clear TOTP/signout and no overflow. Confirm public publisher unavailable state is honestly shown.
7. **First-owner enrollment**: only via audited, explicitly authorized one-use offline signed identity, tied to verified immutable Auth0 issuer+subject. The current staging founder `first_owner_solo` path already **PASSed**; no need to recreate it now. If rebuilding later, use [Mac founder workflow](vowsig-founder-mac-private-owner-mfa-workflow-2026-11-06.md) and an *isolated temporary* private Railway operator with reviewed staging CA/host and migrator access. Preview→explicit consent→fresh authenticator→apply→revoke old sessions, test owner /admin after new login, delete operator. Never expose signer private key/factor/one-time code in web app or chat. A separate two-human rotation/recovery test remains mandatory per current gate.
8. Document exact service image SHA, QA receipts, human authorization, cleanup; preserve isolated staging from production customer records.

## 6. Completely new production rebuild from zero (Mode C)

**C1 — determine whether this is greenfield or migration.** If current `vowsig.com` has real accounts, record approved recovery point and produce a separately encrypted authentic `pg_dump -Fc` and independently RESTORE it into an isolated PG18 instance first. Preserve immutable identity/consents/sessions/watchlists/owner factor ciphertext; a code rollback does not restore these writes. The current new Railway PG cold restore has **not** been certified. If there is no valid backup, do not claim a lossless full rebuild.

**C2 — keep old production running.** Inventory current successful app image/digest, domain/HTTPS/DNS, app `/data` volume, Postgres volume, latest sanitized snapshot timestamp, current snapshot ingest token and VPS sender. Build the **new** app+private PG+separate volumes as an isolated environment on temporary domain; do not redirect customers or mutate old publisher/scheduler yet.

**C3 — fresh TLS/roles/schema.** A new PG has different certificate identity and often different service DNS; generate and validate fresh public CA pin and server SAN with app-network verify-full. Do not blindly use current production CA. Apply reviewed exact SQL 001..010 once against pristine database with 3 restricted roles/DB search_path/grants. **Current production one-shot script** [`ops/handoffs/vowsig_production_pg18_one_transaction_accounts_001_010_20261106.sh`](../ops/handoffs/vowsig_production_pg18_one_transaction_accounts_001_010_20261106.sh) is intentionally hardcoded to the **existing** project/env/leaf pin: never paste it into a different production project. Use a separately reviewed equivalent with correct exact guards.

**C4 — secrets and data migration.** Configure all variables from table 4 in new Railway secret store. For owner data migration, carry **owner ciphertext + its correct existing master encryption key** together; rotating just the master key breaks all owners. For fresh empty owner, generate separate new master and perform offline bootstrap. Migrate existing publisher snapshot `/data` only with verified volume backup/export/restore; never copy VPS private ledgers to public web. If switching publisher receiver, coordinate both URL/token sides explicitly and verify continuity with no duplicate scheduled jobs. Rotate only when owner authorizes.

**C5 — domains, Auth0 and email.** Verify registrar DNS and Railway domain ownership/HTTPS. Configure exact production `https://vowsig.com/auth/callback`, web origin `https://vowsig.com`, logout `https://vowsig.com/`; preserve staging callbacks. Existing Auth0 application client ID is recorded in [tenant binding](vowsig-auth0-tenant-binding-2026-11-04.md). Validate RS256 JWKS and email verification. Resend: `mail.vowsig.com` sender, DKIM/SPF and optional DMARC, and test actual delivery. Never assume new app secrets match the old app.

**C6 — release qualification before DNS cutover.** Run exact GitHub SHA CI and actual PG app-role verify-full authenticated SQL, OAuth email signups, negative duplicate/unverified/replay, session cookie/CSRF/owner MFA, member nine-market restrictions, real owner operational UI, safe N/A history, published snapshot health, responsive device smoke, prior image rollback and app schema backward compatibility. Signed release receipt contract in `src/.../release_acceptance.py` does not itself authorize deploy. Obtain exact-40-character SHA owner merge/deploy approval separately. Keep previous production running until new stack is observed healthy; switch DNS/alias in a single approved window.

## 7. Current in-place production cutover — minimal actions (Mode A)

1. **DONE:** production PG18 SQL migrations 001–010, 3 restricted roles, real staging member + first-owner MFA/dashboard UAT, verified Resend domain, public Auth0 issuer/JWKS, existing working public snapshot. **No reruns of completed scripts.**
2. **STAGED ONLY:** twelve production app vars, including `VOWSIG_ACCOUNTS_DATABASE_URL`, `VOWSIG_ACCOUNTS_CSRF_SECRET`, `VOWSIG_OIDC_CLIENT_SECRET`, `VOWSIG_OWNER_TOTP_MASTER_KEY_B64`, public OIDC endpoints and both app flags still `0`. Current existing successful `/data` app untouched. Do not click Apply prematurely.
3. **NEXT user-run single private check:** `ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh`. From approved exact GitHub commit copy full script to Mac clipboard, paste into existing **production Postgres** Railway Console, enter the **saved** `vowsig_app` password privately. It performs SELECT-only `sslmode=verify-full` role/grants check; this proves DB-container private network, not actual app container. Confirm real app-container connection in release window.
4. Confirm real production Auth0 exact callback/origin/logout, verification email via Resend, negative/security flow, new production first owner TOTP enrollment/step-up and separate recovery gate. Current **staging** owner MFA is not the production owner.
5. Freeze exact tested SHA/image and green CI, check domain/volume/ingest invariants and historical metrics N/A. Record rollback-eligible existing public deployment `59afe99e-c590-4db9-b118-b75a8c75bd7e` (verify still present). Confirm old app compatible with new additive PG schema. Owner reviews final signed release receipts and **separately approves exact full SHA for merge/deploy**.
6. Execute **one** coordinated release: approved PR code, all app secrets and correct feature switches enabled together, retain existing /data volume/token and snapshot publisher. Check live HTTPS, PG role/verified TLS, Auth0 login, member watchlist, owner TOTP/admin, restricted six status-only, no broker execution, fresh snapshot. If anything severe fails, roll **app image only** back; do not downgrade Postgres or wipe volume. Preserve audit.
7. **First immediate postlaunch:** encrypted recurring independent PG18 `pg_dump -Fc` to restricted S3/B2, manifest/hash, 30/8/12 retention only with owner-approved safe deletion, delivered alerts and REAL isolated cold restore. Mark `DATABASE_RECOVERY_UNVERIFIED` until proof. Next independently certify source rights/cost/crypto K5/full nine-market history **before** publishing any historical returns.

## 8. Failure/rollback/disaster procedures

**Rollback triggers:** broken `/healthz` or `/api/health`, missing snapshot/volume, bad Auth0 callback, login/owner MFA failures, DB TLS/permissions failure, history falsely showing unverified statistics, forbidden expansion per-signal detail, broker execution flag unexpectedly on. Stop feature activation and minimize customer impact. Roll old **app deployment** back only after checking how Railway handles any staged variables/flags; explicitly preserve Postgres data/schema and attached `/data`, do not stop Windows publisher. Confirm `/api/health`, three programs, fresh public snapshot, shadow-only mode and execution disabled. A rollback NEVER restores lost database writes; if database state incompatible, use separately reviewed forward-fix or incident recovery.

**Credential compromise:** contain, rotate the exact affected credential via secure host controls; two-sided coordination for ingest sender/receiver; invalidate sessions where appropriate. Do not rotate owner TOTP master without separately approved factor decrypt/reencrypt and rollback plan.

**Disaster restore:** identify fault domain (app/volume/PG/VPS/Auth0/Resend), locate last independently verified encrypted backup and recovery manifest, restore to isolated environment, validate `pg_restore` and tables/consents/identities/watchlists/session correctness, validate owner decryption/MFA, source snapshot safety and permitted market visibility; then owner authorizes switchover. Existing Windows **S02-only** AWS/B2 backup is not a Railway PG customer restore. Where cold restore is unverified, openly mark **data loss/recoverability unknown**.

**Operations:** watch health and research freshness (<90 minutes fresh; 90–150 delayed; >=150 stale), account/email delivery errors, OIDC callback loop, TOTP drift/lockout, DB disk/connections, volume saturation, publisher heartbeat/aging, VPS Task Scheduler persistence beyond RDP disconnect, session abuse and backup restore ages. Only owner-approved security-/data-rights-cleared snapshots and research may enter public pipeline.

## 9. Handoff recording

After a meaningful check/change, update [current-state index](VOWSIG_START_HERE_CURRENT_STATE.md), [next-chat execution guide](vowsig-next-chat-execution-handoff.md) and PR #93 comment with **exact HEAD, tested SHA, runtime evidence status and no-secret receipt**, pending vs deployed state, owner's authorization scope and next single step. Preserve old dated evidence, flag superseded claims rather than delete. No work on unrelated repositories or current-chat-invisible context.
