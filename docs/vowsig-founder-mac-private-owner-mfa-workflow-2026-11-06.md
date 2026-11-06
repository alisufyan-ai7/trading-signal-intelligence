# VowSig — founder Mac staging MFA preparation and private identity handoff

**2026-11-06. Strictly staging; initial owner only; PR #93 DRAFT UNMERGED.** Staging SQL 010 was already owner-run and returned `COMMIT` and `STAGING_OWNER_SOLO_MIGRATION_010=PASS`. **Never rerun 010**. The following private setup does not promote an account or contact Railway; the separate secure staging provisioning operator is not yet active.

## Mac command A — one-time local private preparation

Use the user's personal Mac Terminal, **not** the production VPS and not the Railway staging web-app or DB container. Keep the workstation private and FileVault enabled. Prerequisites: system `git`, `python3` (with `venv`), a GitHub-authorized clone of the owner's own private repository, and internet to obtain the reviewed `cryptography` package.

```bash
set -euo pipefail
umask 077
ROOT="$HOME/.vowsig-owner-private"
SRC="$ROOT/source"
PIN="2dd1025efcef3698ae86485fb7df0b31a7f23bdf"
BRANCH="planning/vowsig-admin-free-account-signal-center-v0-1-20261103"
REPO_URL="https://github.com/alisufyan-ai7/trading-signal-intelligence.git"

command -v git >/dev/null || { echo "GIT_REQUIRED"; exit 1; }
command -v python3 >/dev/null || { echo "PYTHON3_REQUIRED"; exit 1; }
mkdir -p "$ROOT"
chmod 700 "$ROOT"
if [ ! -d "$SRC/.git" ]; then
  [ ! -e "$SRC" ] || { echo "EXISTING_SOURCE_NOT_GIT"; exit 1; }
  git clone --filter=blob:none --single-branch --branch "$BRANCH" "$REPO_URL" "$SRC"
fi
[ "$(git -C "$SRC" remote get-url origin)" = "$REPO_URL" ] || {
  echo "REFUSED_UNTRUSTED_REPOSITORY"; exit 1;
}
git -C "$SRC" -c advice.detachedHead=false checkout --detach "$PIN"
[ "$(git -C "$SRC" rev-parse HEAD)" = "$PIN" ] || { echo "SOURCE_SHA_MISMATCH"; exit 1; }
if [ ! -x "$ROOT/python/bin/python" ]; then
  python3 -m venv "$ROOT/python"
fi
"$ROOT/python/bin/python" -m pip install --disable-pip-version-check --quiet "cryptography>=42,<47"
PYTHONPATH="$SRC/src" "$ROOT/python/bin/python" "$SRC/scripts/vowsig_owner_founder_mac_prepare.py" prepare
```

This command copies only the **reviewed private repo** into the founder's restricted Mac directory, checks out the specific exact-HEAD CI-green `2dd1025efcef3698ae86485fb7df0b31a7f23bdf`, sets up a local Python venv, then runs the local-only first-owner `prepare`. User enters and confirms a long private encryption passphrase via hidden terminal input; a newly random VowSig Staging 160-bit TOTP key appears **only in their own terminal** and must be entered manually as a NEW Time-Based entry in Google Authenticator. A fresh hidden 6-digit code confirms successful phone enrollment.

**Expected safe status:** `FOUNDER_MAC_PRIVATE_PREP=PASS`, `MASTER_AND_FACTOR_PERSISTED_ENCRYPTED=YES`, `SIGNED_APPROVAL_CREATED=NO`, `STAGING_OWNER_PROMOTED=NO`. The rest of the printed information includes an OS-private folder path and a public reviewer key hash, not the encrypted secret; never paste the displayed TOTP enrollment secret, vault files or six-digit code into chat/GitHub.

**No unintended regenerate:** Once prepared, rerunning `prepare` refuses existing keys. To check without touching credentials: `PYTHONPATH="$SRC/src" "$ROOT/python/bin/python" "$SRC/scripts/vowsig_owner_founder_mac_prepare.py" status`.

## Staging DB Console command B — read-only exact verified member binding

This command stays **inside the existing Railway staging PostgreSQL service** with the same project/environment/service/DB guards previously used for migration 010. It does not need access to an Auth0 management API; it reads the member/identity/entitlement rows already linked to the verified, logged-in staging account. It does not grant privileges, modify members or print the raw OIDC subject or account email.

```bash
set -euo pipefail
[ "${RAILWAY_PROJECT_NAME:-}" = "vowsig-staging-20261105" ] || { echo "REFUSED_PROJECT"; exit 1; }
[ "${RAILWAY_ENVIRONMENT_NAME:-}" = "staging" ] || { echo "REFUSED_ENVIRONMENT"; exit 1; }
[ "${RAILWAY_SERVICE_NAME:-}" = "vowsig-staging-pg18" ] || { echo "REFUSED_SERVICE"; exit 1; }
[ "${POSTGRES_DB:-}" = "vowsig_staging" ] || { echo "REFUSED_DB"; exit 1; }
[ "${POSTGRES_USER:-}" = "vowsig_staging_admin" ] || { echo "REFUSED_ADMIN"; exit 1; }
read -r -p "Your verified staging VowSig sign-in email (private): " OWNER_EMAIL
[ -n "$OWNER_EMAIL" ] || { echo "EMAIL_REQUIRED"; exit 1; }
RESULT="$(psql -qXwAt -v ON_ERROR_STOP=1 -v "owner_email=$OWNER_EMAIL" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
SET ROLE vowsig_migrator;
BEGIN TRANSACTION READ ONLY;
SET LOCAL search_path TO vowsig, pg_catalog;
SELECT a.id::text || '|' || i.issuer || '|' ||
       encode(sha256(convert_to(i.subject, 'UTF8')), 'hex')
FROM vowsig_accounts a
JOIN vowsig_account_identities i ON i.account_id=a.id
JOIN vowsig_account_entitlements e ON e.account_id=a.id
WHERE lower(btrim(a.email))=lower(btrim(:'owner_email'))
  AND a.email_verified_at IS NOT NULL
  AND a.disabled_at IS NULL
  AND a.role='member'
  AND e.status='active';
ROLLBACK;
SQL
)"
unset OWNER_EMAIL
[ -n "$RESULT" ] && [[ "$RESULT" != *$'\n'* ]] || { echo "EXACT_SINGLE_VERIFIED_MEMBER_REQUIRED"; exit 1; }
IFS='|' read -r ACCOUNT_UUID OIDC_ISSUER OIDC_SUBJECT_SHA256 <<< "$RESULT"
[[ "$ACCOUNT_UUID" =~ ^[0-9a-f-]{36}$ ]] || { echo "ACCOUNT_UUID_INVALID"; exit 1; }
[[ "$OIDC_ISSUER" = https://* ]] || { echo "OIDC_ISSUER_INVALID"; exit 1; }
[[ "$OIDC_SUBJECT_SHA256" =~ ^[0-9a-f]{64}$ ]] || { echo "SUBJECT_HASH_INVALID"; exit 1; }
echo "STAGING_EXACT_VERIFIED_MEMBER=PASS"
printf 'ACCOUNT_UUID=%s\nOIDC_ISSUER=%s\nOIDC_SUBJECT_SHA256=%s\n' "$ACCOUNT_UUID" "$OIDC_ISSUER" "$OIDC_SUBJECT_SHA256"
echo "Copy these only to Mac PRIVATE sign prompts; do not post the identity receipt in chat."
```

**Note:** The hash uses PostgreSQL built-in SHA256 over UTF-8 OIDC subject and matches the existing Python provisioning predicate. The unique one-row and verified membership requirements are enforced before printing. The source account id/hash/issuer are *private identifiers*, not secrets but not to be published.

## Deferred until private Railway operator is ready

**Do not sign the approval now.** Its maximum validity is one hour; the helper uses a 35-minute expiry. Once an isolated one-time staging operator with exact private host `vowsig-staging-pg18.railway.internal`, pinned staging root CA, dedicated `vowsig_migrator` identity, and no public ingress is ready, run the Mac helper `sign` and enter the three read-only identity fields privately. It will verify a current Google Authenticator code locally, sign the exact `first_owner_solo` approval, and create an encrypted-key-backed private approval file.

The staging operator must only read a signed approval + reviewer *public* key (never the signing private key), get the approved master key and factor secret through secure local prompts/private transfer, run **PREVIEW** then explicit **APPLY** exactly once, and emit only the audited receipt; the user must perform the interactive TOTP action. Before authenticated admin UAT, configure the **same** private master encryption key in Railway staging app's approved secret settings and verify owner TOTP step-up, logout, old-session denial, nonowner 403 and actual dashboards.

**STOP:** Never use production VPS or expose a Railway database TCP proxy; never call the owner CLI inside an always-on web application. Never put signer private PEM, vault JSON, TOTP secret, current code, database DSN/password or raw subject in ChatGPT, GitHub, source control or application logs. The existing separate two-person recovery policy still applies; external crypto K5, rights, historical sign-off remain unrelated and pending. No PR merge or production deploy is authorized by Mac preparation.
