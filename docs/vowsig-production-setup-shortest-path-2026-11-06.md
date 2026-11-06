# VowSig — Production setup, shortest approved path

2026-11-06. **STATUS: PRODUCTION PREPARED, NOT YET CUT OVER.** The owner requested only launch-critical production PostgreSQL, Auth0, Resend, owner factor and rollback work. Do not start another feature, report, crypto signal, staging publisher, VPS source audit or payment service. **No production SQL operator has been executed as a result of committing this document.** Merge/new live app deploy still requires explicit owner exact SHA approval.

## Resolved safely without touching the currently running public app

1. **Real production beta healthy:** existing Railway `positioning-engine-cron` / `production` / `tradingtop-early-access` has a SUCCESS image at baseline Git SHA `13aeb2bfe2560d3afef63019e4282361fd552faf`, the `vowsig.com` custom domain, the original persistent volume mounted `/data`, and its existing snapshot ingestion token. Never replace/unmount `/data` or rotate publisher credentials casually. The existing `vowsig.com/api/health` and validation program discovery were previously observed genuine, fresh and SHADOW_ONLY for three core plus six research-restricted expansion/crypto symbols. The legacy public `/api/markets` list differs from the new nine-market member catalog; published validation programs do match new policy.
2. **Auth0 issuer verified publicly:** discovered `https://dev-b1aqc523agud2k4p.us.auth0.com/` (trailing slash), `/authorize`, `/oauth/token`, `/.well-known/jwks.json` with current RSA signing keys; discovery advertises RS256 and `client_secret_post`. This verifies *public tenant metadata only*. Confirm in the actual Auth0 **Regular Web Application** dashboard the production `https://vowsig.com/auth/callback`, allowed origin `https://vowsig.com`, logout `https://vowsig.com/`, exact client `FMhkJa8azUSjflmNBTDb3keWNCUv6b3w`, email verification, confidential auth-code/PKCE and sender configuration. Real production signup/callback is NOT yet proven. Never share Auth0 client secret.
3. **Resend domain/key reused:** connected Resend account returned `mail.vowsig.com` **verified**, sending enabled, tracking disabled, and existing key named **VowSig Auth0 Transactional Email**. Do not create another sending domain or API key. Actual Auth0 verification email **delivery** is not yet tested. Link only the existing restricted Resend key in the Auth0 email provider's approved secure configuration, never in GitHub or as an unused VowSig runtime variable. No email was sent in this setup check.
4. **Non-secret Auth0 production app configuration STAGED ONLY:** Railway app variable patch `a18c5bf5-3461-4ba1-a220-49b9cc5d2fd0` includes the exact public issuer/endpoints/client ID/app origin, explicitly `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED=0` and `VOWSIG_OIDC_AUTH_ENABLED=0`. It remains pending, not committed, not deployed; app SHA/volume untouched. Never click Apply Changes prematurely. At final one-shot release merge/deploy, reconcile these variables alongside restricted database DSN, private CSRF/client secret and owner factor encryption key, and flip flags only with all gates reviewed.

## Production PostgreSQL — one actual console operation, not repeated micro-checks

- Existing `Postgres` service `74a3e855-d97c-4b81-8a27-092f048f9af3` is healthy, **private** with no public TCP proxy and one existing volume. The repository records a genuine 2026-11-04 production app-network TLSv1.3/hostname/CA/leaf identity PASS at `postgres.railway.internal`, public CA `config/tls/railway-postgres-root-ca-20261104.pem`, server leaf SHA256 `42574eca8c9afa481beefb2c3ea6b508bcd3e6c27e1b287d20274d72458e9526`. That certificate must still match during schema bootstrap. No certificate/image replacement is required.
- Old owner's read-only PostgreSQL baseline found zero account schema and roles, but **must not be assumed still true**. The one-shot operator **checks actual DB state again and refuses any prior/partial installation**.
- The reviewed single transaction operator is `ops/handoffs/vowsig_production_pg18_one_transaction_accounts_001_010_20261106.sh`. It embeds exact previously reviewed `sql/accounts/001…010` migrations (the `010` wrapper is removed solely to keep ONE transaction), creates restricted `vowsig_app`, `vowsig_migrator` and `vowsig_backup` LOGIN roles, assigns `vowsig` as migrator-owned schema, configures their database-specific search_path, enforces table/role/owner-factor privacy grants, and COMMITs only if all checks pass. It **does not** populate an account, enable an app flag, send mail, touch any existing public table, or perform a Railway deployment. Failed preconditions/errors abort and roll back that transaction. **DO NOT rerun after PASS**.
- Exact environment guards `RAILWAY_PROJECT_NAME=positioning-engine-cron`, `RAILWAY_ENVIRONMENT_NAME=production`, `RAILWAY_SERVICE_NAME=Postgres`, PostgreSQL 18, TLS on, previously pinned leaf and hostname SAN; verifies no `vowsig` schema, no 3 restricted roles, no prefixed public account tables; needs three freshly created, **distinct** 44–128 character URL-safe random role passwords saved privately. It prompts through TTY (passwords never stored in the repo or echoed) and requires an explicit typed `INIT_PROD_VOWSIG_001_010`.
- The standalone `ops/handoffs/vowsig_production_pg18_readiness_single_pass_20261106.sh` is **OPTIONAL diagnostic only**. **Skip it** for the normal case since the one-shot production setup already includes its preflight; owner requests minimal scripts.

### Single copy/paste setup transport — Mac to Railway Console

On the personal Mac where this private GitHub branch is already cloned (from prior owner MFA work), AFTER reviewing the exact latest candidate/CI SHA:

```bash
set -euo pipefail
SRC="$HOME/.vowsig-owner-private/source"
SHA="<EXACT_CI_GREEN_PR_93_SHA>"
git -C "$SRC" fetch --no-tags origin planning/vowsig-admin-free-account-signal-center-v0-1-20261103
git -C "$SRC" cat-file -e "$SHA^{commit}" || { echo "PIN_NOT_FOUND"; exit 1; }
git -C "$SRC" show "$SHA:ops/handoffs/vowsig_production_pg18_one_transaction_accounts_001_010_20261106.sh" | pbcopy
echo 'One-shot reviewed production SQL setup script copied to clipboard; no passwords included.'
```

On Railway dashboard, open **existing production** project `positioning-engine-cron` → environment `production` → service `Postgres` → **Console**, and paste the clipboard's single script **once**. First ensure you have saved three strong, distinct URL-safe credentials in your password manager. Enter them only at the hidden prompts; then type the explicit one-time confirmation. **Do not paste passwords/output containing secrets in chat or GitHub.**

**Expected sanitized PASS receipt:** `PROD_VOWSIG_001_010_COMMITTED=PASS`, `PRODUCTION_PG18_ROLES_AND_SCHEMA=PASS`, `PRODUCTION_ACCOUNT_FEATURE_ENABLED=NO`, `PRODUCTION_OWNER_PROMOTED=NO`, `TRADING_PUBLISHER_OR_WEB_CHANGED=NO`.

Next: use one real authenticated app-network `vowsig_app` verified-full TLS and least-privilege SQL check with the pinned public production CA and private DSN; add application-only secrets through the Railway secret store, under exact production cutover staging/approval. Do not reuse staging DB credentials or initial MFA key material in production.

## Remaining bounded release sequence

1. Production PG restricted SQL **real PASS** via owner-only Console and app-network privilege check, with separate secret custody. The new schema is account-only and additive; production app stays public research-beta unchanged until approved exact SHA cutover.
2. Auth0 real verified/unverified signup and email send/delivery with the *already verified* Resend sender; no new email implementation or additional providers. New customer accounts only after the final coordinated production app deploy.
3. Private founder-first owner TOTP enrollment for the production account **separate from staging secret key**, subsequent owner/admin live step-up and distinct-recovery-person gate; don't claim a staging owner account implies production MFA.
4. Minimal same-candidate mobile/navigation/session/watchlist/restricted market and *unverified performance N/A* smoke; use the existing 2026-11-05/06 member/owner staging PASS receipts rather than rerunning unchanged flows.
5. **Read-only rollback readiness:** Existing live Railway deployment `59afe99e-c590-4db9-b118-b75a8c75bd7e` from `main=13aeb2bfe2560d3afef63019e4282361fd552faf` is marked rollback-eligible. Keep it available during the new release; any rollback switches the **application image only**, preserving the `/data` publisher volume and newly added Postgres schema (no downgrade), with account flags fail-closed until restored. Actual staged rollback proof is still required before an exact SHA launch.
6. Request **separate explicit exact 40-char commit SHA production merge/deploy approval**. Owner's authorization to prepare production setup and to defer historical certification was **not** deploy authorization.
7. **FIRST immediate postlaunch task**: encrypted recurring PostgreSQL S3/B2 offsite backup, retention and independently proven cold restore; `DATABASE_RECOVERY_UNVERIFIED` until complete, under accepted temporary data-loss risk.
8. Independent complete nine-market historical source rights/cost/K5/census certification **after launch before any historical returns are published**. Owner Performance Lab honestly shows N/A until a distinct signed evidence release. No duplicated staging publisher.

**Release feature freeze remains in effect.**


## 2026-11-06 follow-up: production secrets staged, private role/TLS check prepared

The owner confirmed the private production DSN, CSRF secret, separate production-only TOTP master key, and existing Auth0 client secret were added to Railway **pending** changes. The read-only Railway service inventory verifies all four **variable names**, 12 pending edits only on `tradingtop-early-access`, current production image still **SUCCESS** and `/data` mounted. **Secret values were never fetched, inspected or verified**. Feature switches remain OFF in the staged change.

The production schema/roles SQL 001–010 **already returned owner-executed PASS; do not rerun**.

Before live cutover, use **one** read-only private-role authentication check: [`ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh`](../ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh). It embeds the repository-pinned *public* root CA, checks private DNS + actual libpq `verify-full` trust/hostname, `vowsig_app` login and least-privilege `SELECT`-only SQL. It never reads customer records, alters roles, deploys a service, creates a key, remigrates a database or touches the Windows VPS.

**One copy transfer to existing production Postgres Railway Console:** from the authorized Mac GitHub clone, `git fetch` the existing PR branch and use `git show <EXACT_GREEN_COMMIT>:ops/handoffs/vowsig_production_app_role_tls_readonly_20261106.sh | pbcopy` to copy the script. Paste it **only** in `positioning-engine-cron / production / Postgres / Console`, enter the **existing** `vowsig_app` password once in a hidden prompt and share **only** `PRODUCTION_APP_ROLE_TLS_PRIVILEGE=PASS` or a nonsecret failure label. There is no app restart, and it must not be used as evidence of *app-container* networking or the uninspected staged DSN's actual bytes; the final released app container must still authenticate with the configured DSN under `sslmode=verify-full`.

**Remaining launch gates:** the Auth0 Regular Web Application must allow `https://vowsig.com/auth/callback`, origin `https://vowsig.com`, logout `https://vowsig.com/` alongside staging. Real verified signup/Resend email delivery and production owner MFA can only be evidenced on a running production-compatible candidate, then record session/security + read-only rollback and require separate owner exact-SHA authorization. Never deploy the current pending variable patch prematurely; the customer research publisher and snapshot `/data` volume are currently working. Historical performance remains N/A under the Nov 6 owner waiver; offsite PostgreSQL restore work is first immediate postlaunch.
