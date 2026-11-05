#!/usr/bin/env bash
# Read-only: STAGING DB ONLY. Public CA certificate and restricted role acceptance.
bash <<'VOWSIG_STAGING_ROOT'
set -Eeuo pipefail
set +x
[[ "${RAILWAY_PROJECT_NAME:-}" == "vowsig-staging-20261105" && "${RAILWAY_ENVIRONMENT_NAME:-}" == "staging" && "${RAILWAY_SERVICE_NAME:-}" == "vowsig-staging-pg18" ]] || { echo STAGING_IDENTITY_REFUSED; exit 1; }
[[ "${POSTGRES_DB:-}" == "vowsig_staging" && "${POSTGRES_USER:-}" == "vowsig_staging_admin" ]] || { echo STAGING_DATABASE_REFUSED; exit 1; }
export PGPASSWORD="${POSTGRES_PASSWORD:?Missing staging admin password}"
identity="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c "SELECT current_database()||'|'||current_user||'|'||current_setting('ssl')")"
[[ "$identity" == 'vowsig_staging|vowsig_staging_admin|on' ]] || { echo STAGING_SSL_OR_ROLE_REFUSED; exit 1; }
leaf="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SHOW ssl_cert_file')"
ca_setting="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SHOW ssl_ca_file')"
data_dir="$(psql -XwAt -v ON_ERROR_STOP=1 -U "$POSTGRES_USER" -d "$POSTGRES_DB" -c 'SHOW data_directory')"
[[ "$leaf" == /* ]] || leaf="$data_dir/$leaf"
[[ -r "$leaf" ]] || { echo STAGING_LEAF_NOT_READABLE; exit 1; }
leaf_pin="$(openssl x509 -in "$leaf" -noout -fingerprint -sha256 | sed -E 's/.*=//;s/://g' | tr '[:upper:]' '[:lower:]')"
[[ "$leaf_pin" == 'aa98817c212a1b080fa6af1a96691fb5e4ad878231d6e477faeb381a0febc7f0' ]] || { echo STAGING_LEAF_FINGERPRINT_CHANGED; exit 1; }
[[ -n "$ca_setting" && "$ca_setting" != 'none' ]] && { [[ "$ca_setting" == /* ]] || ca_setting="$data_dir/$ca_setting"; } || ca_setting=''
root_file=''
if [[ -n "$ca_setting" && -r "$ca_setting" ]]; then
  if openssl x509 -in "$ca_setting" -noout -text 2>/dev/null | grep -q 'CA:TRUE' && openssl verify -CAfile "$ca_setting" "$leaf" >/dev/null 2>&1; then root_file="$ca_setting"; fi
fi
if [[ -z "$root_file" ]]; then
  for candidate in /etc/postgresql/ssl/root-ca.crt /etc/postgresql/ssl/root-ca.pem /etc/ssl/certs/root-ca.crt /etc/ssl/certs/root-ca.pem /certs/root-ca.crt /certs/ca.crt /var/lib/postgresql/data/root-ca.crt "$data_dir/root-ca.crt" "$data_dir/ca.crt" /tls/root-ca.crt /ssl/root-ca.crt; do
    [[ -r "$candidate" ]] || continue
    if openssl x509 -in "$candidate" -noout -text 2>/dev/null | grep -q 'CA:TRUE' && openssl verify -CAfile "$candidate" "$leaf" >/dev/null 2>&1; then root_file="$candidate"; break; fi
  done
fi
if [[ -z "$root_file" ]]; then
  while IFS= read -r candidate; do
    [[ -r "$candidate" ]] || continue
    if openssl x509 -in "$candidate" -noout -text 2>/dev/null | grep -q 'CA:TRUE' && openssl verify -CAfile "$candidate" "$leaf" >/dev/null 2>&1; then root_file="$candidate"; break; fi
  done < <(find /etc /var/lib/postgresql /certs /tls /ssl -maxdepth 5 -type f \( -name '*root*ca*.crt' -o -name '*root*ca*.pem' -o -name 'ca.crt' -o -name 'ca.pem' -o -name 'root.crt' \) 2>/dev/null || true)
fi
if [[ -z "$root_file" ]]; then
  echo 'STAGING_CA_DISCOVERY=HOLD'
  echo 'No database changes were made.'
  exit 1
fi
root_pin="$(openssl x509 -in "$root_file" -noout -fingerprint -sha256 | sed -E 's/.*=//;s/://g' | tr '[:upper:]' '[:lower:]')"
echo "STAGING_CA_ROOT_SHA256=$root_pin"
echo "STAGING_LEAF_SHA256=$leaf_pin"
echo '-----BEGIN VOWSIG PUBLIC ROOT CA-----'
openssl x509 -in "$root_file" -outform PEM
echo '-----END VOWSIG PUBLIC ROOT CA-----'
if PGPASSWORD="${VOWSIG_APP_ROLE_PASSWORD:?Missing staging app password}" psql -XwAt -v ON_ERROR_STOP=1 -d "host=vowsig-staging-pg18.railway.internal port=5432 dbname=vowsig_staging user=vowsig_app sslmode=verify-full sslrootcert=$root_file" -c "SELECT current_user||'|'||(SELECT ssl::text FROM pg_stat_ssl WHERE pid=pg_backend_pid())||'|'||current_setting('search_path')"; then
  echo 'STAGING_RESTRICTED_ROLE_WITH_VERIFY_FULL=PASS_FROM_DB_CONTAINER_ONLY'
else
  echo 'STAGING_RESTRICTED_ROLE_WITH_VERIFY_FULL=HOLD'
fi
echo 'LIVE_APP_CONTAINER_TLS_AND_AUTH0=NOT_YET_TESTED'
echo 'PRODUCTION_MODIFIED=NO'
VOWSIG_STAGING_ROOT
