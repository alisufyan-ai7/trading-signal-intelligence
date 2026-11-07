# VowSig — first production owner MFA enrollment, minimal secure execution (2026-11-07)

**Current authority:** PR #93 already merged and deployed on 2026-11-06. Owner-only routes exist in the production code, but the prior deployment receipt did **not** verify a production owner promotion. The product owner reports they can currently sign in only as a customer. Existing PostgreSQL migrations 001–010, production Auth0 settings and staging founder enrollment are complete and MUST NOT be repeated. Use only this repository and the active chat. Never consult or mutate other projects.

## Why owner dashboard still rejects the existing customer

- The source checks the database identity role. Normal verified Auth0 sign-in produces a **member**, not an owner: src/trading_signal_intelligence/product/accounts/security.py require_owner. Admin HTML is /admin/ and the owner API is /api/v2/admin/*, requiring role owner AND a recent independent TOTP step-up (15-minute window).
- The owner step-up form is already implemented at /app/settings, as a POST to /api/v2/me/owner-mfa/verify, visible only after owner promotion. It is **not** the Auth0 provider's ordinary MFA switch or a customer self-service enrollment route.
- Production Railway app tradingtop-early-access contains the required variable *name* VOWSIG_OWNER_TOTP_MASTER_KEY_B64; its actual value was deliberately NOT retrieved. Do not overwrite or rotate it. The production factor's ciphertext must be encrypted under precisely the same existing master key. Staging founder factor/master MUST NOT be reused. The production app, PG18 and /data volume are online.
- Existing staging-only helpers are intentionally forbidden from writing production. This PR adds **separate, isolated production helpers** and does not weaken those staging constraints.

## Stage 0 — first run only the existing production DB READ-ONLY identity preflight (one copy-paste)

Inside **Railway > positioning-engine-cron > production > Postgres > Console**, copy the complete script from:

ops/handoffs/vowsig_production_first_owner_verified_member_readonly_20261107.sh

It verifies the exact existing project/environment/service IDs, uses existing Postgres environment authentication, runs SELECT-only via restricted migrator context, asks for the existing verified production sign-in email **privately in Console**, and returns:

    PRODUCTION_FIRST_OWNER_PREFLIGHT=READY
    EXISTING_VERIFIED_MEMBER=YES
    EXISTING_OWNER_COUNT=0
    PRIVATE_ACCOUNT_UUID=<private>
    PRIVATE_OIDC_ISSUER=<private>
    PRIVATE_SUBJECT_SHA256=<private>
    PRODUCTION_DATABASE_WRITES=NONE

Do NOT send the three PRIVATE fields or email into chat or GitHub. Save them **locally** for the Mac step. If owner_count is already nonzero or exactly one verified member is not found, STOP rather than force-promotion; investigate with owner approval. Never perform identity binding by email only. This preflight confirms an existing member + immutable OIDC binding, not permission for a role change.

## Stage 1 — founder's existing trusted Mac (separate new PRODUCTION authenticator)

From a GitHub-authorized copy of this repository on the founder's Mac, check out the reviewed production-owner PR's **exact tested commit**, then invoke scripts/vowsig_owner_founder_mac_production.py (requires Python 3.11+, cryptography and real Mac interactive terminal). Keep the source copy and the new private vault in user-owned directories with chmod 700/600, full-disk encryption. This helper always refuses CI, Railway and Linux/Windows. Do not run it on the Windows VPS.

1. Command prepare: creates NEW encrypted private signing key and 160-bit **production-specific** TOTP factor in ~/.vowsig-owner-private/production, not staging, and asks the founder to enter the displayed factor manually into Google Authenticator as **VowSig Production**. The founder confirms a hidden six-digit code. The master key already held by the production application is neither read nor regenerated. Do not repeat prepare once the vault exists.
2. Command status is read-only and safe to rerun.
3. Command handoff (only after Stage 0 and the temporary operator are available): asks privately for PRIVATE_ACCOUNT_UUID, PRIVATE_OIDC_ISSUER and PRIVATE_SUBJECT_SHA256, confirms a fresh Google Authenticator code, truthfully signs the founder's ONE-USE / 35-minute first_owner_solo approval, encrypts the approval/public key/factor bundle with a new separate 20+ char transfer passphrase, and places only the encrypted bundle in the Mac clipboard for one private operator console. The founder retains the encrypted signing key and factor recovery information off-platform.

Never paste phone factor secret, vault, six-digit TOTP, signer private key, encrypted transfer bundle, transfer passphrase or private OIDC binding into a chat or GitHub issue. Do not reuse staging factor.

## Stage 2 — isolated temporary PRODUCTION owner operator, privileged action

Only after explicit owner authorization to create a **temporary** production Railway service, provision one new isolated service in the EXISTING positioning-engine-cron / production project named exactly vowsig-owner-production-operator, built from the reviewed branch Dockerfile.owner-production-operator (no ingress or public domains; uses no app persistent volume, no publisher and no database migrations). **Do not merge this PR to main merely to build the operator:** that might redeploy the live main-linked application.

Configure just two variable references on this temporary operator, through the Railway variables UI, NOT literal private secrets:

- VOWSIG_OWNER_TOTP_MASTER_KEY_B64 → **reference to existing tradingtop-early-access.VOWSIG_OWNER_TOTP_MASTER_KEY_B64**. Copy neither the value nor a new generated key. This ensures the offline operation writes ciphertext the running app can decrypt.
- VOWSIG_OWNER_PRODUCTION_DATABASE → **reference to existing Postgres.POSTGRES_DB**. The operator also hard-requires exact production Railway project/environment/service IDs.

Use Railway's terminal/SSH into the temporary operator container and run interactively:

    python scripts/vowsig_owner_production_operator.py

The helper prompts for the **existing saved vowsig_migrator password in a hidden input** (not a Railway variable or command argument), asks for the Mac encrypted bundle and transfer passphrase in hidden inputs, verifies the signed exact production immutable OIDC identity, checks the restricted migrator SQL role and SSL verify-full with the existing pinned public CA, verifies **zero existing owner**, and prints a sanitized READ-ONLY PREVIEW. It will perform **NO WRITE** until the founder types the exact confirmation:

    PROMOTE_PRODUCTION_FIRST_OWNER

It then asks for the new production Google Authenticator six-digit code in a hidden prompt and performs one audited transaction through existing owner_offline_provisioning.py: encrypt the factor with the existing live master, bind it to the verified identity, promote only that member to role owner, revoke all existing sessions for that account, and record first_owner_solo truthful self-authorization with non-independent-review label.

Required sanitized success:

    PRODUCTION_FIRST_OWNER_APPLY=PASS
    OWNER_ROLE_ACTIVATED=YES
    NEW_AUTH0_LOGIN_AND_TOTP_REQUIRED=YES
    SOLO_FOUNDER_EXCEPTION_AUDITED=YES
    APP_AND_PUBLISHER_CHANGED=NO

Delete/stop the **temporary** operator service after confirmation and preserve a sanitized receipt. Do not change the existing production Postgres roles, credentials or migrations. Never create a public Postgres TCP proxy or generic endpoint for self-promotion. This operation changes one account's owner role and invalidates its previous sessions; it does NOT require a web app redeploy.

## Stage 3 — actual production acceptance (owner)

1. Existing customer session is intentionally revoked by promotion. Sign into https://vowsig.com again using the **same verified production Auth0 account**; do not create another customer.
2. Visit https://vowsig.com/app/settings. The already-present "Owner MFA · authenticator app" area should now appear.
3. Enter a fresh Google Authenticator **VowSig Production** six-digit code. The application rotates the existing session cookie after successful step-up; the owner can then open https://vowsig.com/admin/ for the following **15 minutes**. Later step-up prompts are expected.
4. Confirm the owner dashboard works, ordinary member account cannot access owner routes, public snapshot and main client dashboard still work, and no protected market research is exposed.
5. Preserve encrypted owner factor recovery and master-key custody separately; do NOT run the solo first-owner path for MFA recovery or additional owners. Later recovery is a distinct approved two-person policy operation.

## No operation has been executed by preparing this PR

This PR changes only GitHub source, tests and documentation. Production member role, TOTP factor, real second factor, and actual owner /admin access remain **NOT YET VERIFIED**. Do not label the owner account MFA-enabled based on code or CI. Backup PR #96 remains a separate draft priority that resumes AFTER production owner acceptance. If owner preflight fails, stop at that specific result instead of doing a new migration, creating another account, or bypassing the security gate.
