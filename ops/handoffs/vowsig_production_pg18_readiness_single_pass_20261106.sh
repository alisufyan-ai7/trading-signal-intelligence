#!/usr/bin/env bash
# VowSig one-shot production PG18 readiness ONLY: read-only, private Console.
# This command MUST run in Railway positioning-engine-cron / production / Postgres.
# No credentials/rows/emails are printed; no CREATE/ALTER/DROP/data mutations.
bash <<'VOWSIG_PRODUCTION_READ_ONLY'
set -Eeuo pipefail
set +x
umask 077
[[ "${RAILWAY_PROJECT_NAME:-}" == 'positioning-engine-cron' ]] || { echo REFUSED_PROJECT; exit 1; }
[[ "${RAILWAY_ENVIRONMENT_NAME:-}" == 'production' ]] || { echo REFUSED_ENVIRONMENT; exit 1; }
[[ "${RAILWAY_SERVICE_NAME:-}" == 'Postgres' ]] || { echo REFUSED_SERVICE; exit 1; }
[[ -n "${POSTGRES_DB:-}" && -n "${POSTGRES_USER:-}" && -n "${POSTGRES_PASSWORD:-}" ]] || { echo REFUSED_DATABASE_ENV; exit 1; }
command -v psql >/dev/null || { echo PSQL_NOT_FOUND; exit 1; }
command -v openssl >/dev/null || { echo OPENSSL_NOT_FOUND; exit 1; }
export PGPASSWORD="$POSTGRES_PASSWORD"
identity="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database()||'|'||current_user||'|'||current_setting('ssl')")"
[[ "$identity" == "$POSTGRES_DB|$POSTGRES_USER|on" ]] || { echo REFUSED_SQL_IDENTITY_OR_SSL; exit 1; }
version="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW server_version_num")"
[[ "$version" =~ ^18[0-9]{4}$ ]] || { echo REFUSED_POSTGRES_VERSION; exit 1; }
cert="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW ssl_cert_file")"
data="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SHOW data_directory")"
[[ "$cert" == /* ]] || cert="$data/$cert"
[[ -f "$cert" && -r "$cert" ]] || { echo REFUSED_TLS_CERT_NOT_READABLE; exit 1; }
leaf="$(openssl x509 -in "$cert" -noout -fingerprint -sha256 | sed -E 's/.*=//;s/://g' | tr '[:upper:]' '[:lower:]')"
[[ "$leaf" == "42574eca8c9afa481beefb2c3ea6b508bcd3e6c27e1b287d20274d72458e9526" ]] || { echo PRODUCTION_TLS_CERT_CHANGED_HOLD; exit 1; }
openssl x509 -in "$cert" -noout -ext subjectAltName | grep -Fq 'DNS:postgres.railway.internal' || { echo PRODUCTION_TLS_HOSTNAME_HOLD; exit 1; }

state="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" <<'SQL'
BEGIN TRANSACTION READ ONLY;
SELECT 
  (SELECT COUNT(*) FROM pg_roles WHERE rolname IN ('vowsig_app','vowsig_migrator','vowsig_backup'))::text
  || '|' || (SELECT COUNT(*) FROM pg_namespace WHERE nspname='vowsig')::text
  || '|' || (SELECT COUNT(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace
      WHERE n.nspname='vowsig' AND c.relkind IN ('r','p','v','m','S'))::text
  || '|' || (SELECT COUNT(*) FROM pg_tables WHERE schemaname='public' AND tablename LIKE 'vowsig_%')::text;
ROLLBACK;
SQL
)"
state="$(printf '%s\n' "$state" | grep -E '^[0-9]+\|[0-9]+\|[0-9]+\|[0-9]+$' || true)"
[[ "$state" =~ ^[0-9]+\|[0-9]+\|[0-9]+\|[0-9]+$ ]] || { echo PRODUCTION_SQL_BASELINE_HOLD; exit 1; }
IFS='|' read -r roles schemas objects public_objects <<< "$state"
[[ "$public_objects" == 0 ]] || { echo PRODUCTION_UNEXPECTED_PUBLIC_ACCOUNT_OBJECTS_HOLD; exit 1; }
if [[ "$roles" == 0 && "$schemas" == 0 && "$objects" == 0 ]]; then
  readiness='CLEAN_FOR_SEPARATE_GUARDED_SETUP'
elif [[ "$roles" == 3 && "$schemas" == 1 && "$objects" -ge 10 ]]; then
  readiness='PREEXISTING_SCHEMA_NEEDS_RESTRICTED_ROLE_VERIFICATION'
else
  echo "PRODUCTION_ACCOUNT_SCHEMA_PARTIAL_STATE=HOLD"
  echo "RESTRICTED_ROLE_COUNT=$roles"
  echo "SCHEMA_COUNT=$schemas"
  echo "SCHEMA_OBJECT_COUNT=$objects"
  exit 1
fi
echo 'PRODUCTION_PG18_READONLY_PREFLIGHT=PASS'
echo 'PRODUCTION_PRIVATE_TLS_CERT_PIN=PASS'
echo "RESTRICTED_ROLE_COUNT=$roles"
echo "SCHEMA_COUNT=$schemas"
echo "SCHEMA_OBJECT_COUNT=$objects"
echo "PRODUCTION_ACCOUNT_SCHEMA_STATE=$readiness"
echo 'PRODUCTION_SCHEMA_CHANGED=NO'
echo 'LIVE_PUBLISHER_CHANGED=NO'
VOWSIG_PRODUCTION_READ_ONLY
