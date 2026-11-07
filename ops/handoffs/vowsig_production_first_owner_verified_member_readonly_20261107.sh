#!/usr/bin/env bash
# VowSig FIRST production owner: read-only exact verified member binding.
# Run ONCE in existing positioning-engine-cron / production / Postgres Console.
# The private identity receipt is transferred ONLY to the founder's offline Mac,
# NEVER into GitHub, chat, PR comments, logs or another account.
bash <<'VOWSIG_PRIVATE_PRODUCTION_OWNER_IDENTITY'
set -euo pipefail
[[ "${RAILWAY_PROJECT_ID:-}" == "af8ed976-9971-4f5a-a304-3d8984df1565" ]] || { echo REFUSED_PROJECT; exit 1; }
[[ "${RAILWAY_ENVIRONMENT_ID:-}" == "fb429ace-7b81-432f-a9d2-32e2044f4392" ]] || { echo REFUSED_ENVIRONMENT; exit 1; }
[[ "${RAILWAY_ENVIRONMENT_NAME:-}" == production ]] || { echo REFUSED_ENVIRONMENT_NAME; exit 1; }
[[ "${RAILWAY_SERVICE_NAME:-}" == Postgres ]] || { echo REFUSED_NOT_POSTGRES_SERVICE; exit 1; }
[[ -n "${POSTGRES_DB:-}" && -n "${POSTGRES_USER:-}" && -n "${POSTGRES_PASSWORD:-}" ]] || { echo REFUSED_DB_ENV; exit 1; }
export PGPASSWORD="$POSTGRES_PASSWORD"
trap 'unset OWNER_EMAIL PGPASSWORD' EXIT
printf 'Existing verified PRODUCTION VowSig member email (private): ' >/dev/tty
IFS= read -r OWNER_EMAIL </dev/tty
[[ -n "$OWNER_EMAIL" && "$OWNER_EMAIL" != *$'\n'* ]] || { echo EMAIL_REQUIRED; exit 1; }
rows="$(psql -qXwAt -v ON_ERROR_STOP=1 -v "owner_email=$OWNER_EMAIL" -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'VOWSIG_OWNER_READONLY_SQL'
SET ROLE vowsig_migrator;
BEGIN TRANSACTION READ ONLY;
SET LOCAL search_path TO vowsig,pg_catalog;
SELECT 'OWNER_COUNT|' || count(*) FROM vowsig_accounts WHERE role='owner';
SELECT 'EXACT_MEMBER|' || a.id::text || '|' || i.issuer || '|' ||
       encode(sha256(convert_to(i.subject,'UTF8')),'hex')
FROM vowsig_accounts a
JOIN vowsig_account_identities i ON i.account_id=a.id
JOIN vowsig_account_entitlements e ON e.account_id=a.id
WHERE lower(btrim(a.email)) = lower(btrim(:'owner_email'))
  AND a.email_verified_at IS NOT NULL
  AND a.disabled_at IS NULL
  AND a.role='member'
  AND e.status='active'
ORDER BY a.id;
ROLLBACK;
VOWSIG_OWNER_READONLY_SQL
)"
unset OWNER_EMAIL
[[ "$(printf '%s\n' "$rows" | wc -l | tr -d ' ')" == 2 ]] || { echo EXACT_SINGLE_VERIFIED_MEMBER_REQUIRED; exit 1; }
first="$(printf '%s\n' "$rows" | head -n 1)"
second="$(printf '%s\n' "$rows" | tail -n 1)"
[[ "$first" == "OWNER_COUNT|0" ]] || { echo FIRST_OWNER_NOT_AVAILABLE; exit 1; }
IFS='|' read -r kind account issuer subhash <<< "$second"
[[ "$kind" == EXACT_MEMBER && "$account" =~ ^[0-9a-f-]{36}$ && "$issuer" == https://* && "$subhash" =~ ^[0-9a-f]{64}$ ]] || { echo INVALID_PRIVATE_IDENTITY; exit 1; }
echo PRODUCTION_FIRST_OWNER_PREFLIGHT=READY
echo EXISTING_VERIFIED_MEMBER=YES
echo EXISTING_OWNER_COUNT=0
printf 'PRIVATE_ACCOUNT_UUID=%s\nPRIVATE_OIDC_ISSUER=%s\nPRIVATE_SUBJECT_SHA256=%s\n' "$account" "$issuer" "$subhash"
echo 'Copy the PRIVATE_* identity fields into local Mac prompts only. Do not send to chat or GitHub.'
echo PRODUCTION_DATABASE_WRITES=NONE
VOWSIG_PRIVATE_PRODUCTION_OWNER_IDENTITY
