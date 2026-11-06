#!/usr/bin/env bash
# One-time production role/TLS acceptance: SELECT-only, PRIVATE Railway Postgres Console.
# Does NOT reinitialize SQL, create owners, read customer rows, deploy app or touch publisher.
bash <<'VOWSIG_READONLY_APP_ROLE_CHECK'
set -Eeuo pipefail
set +x
umask 077

[[ "${RAILWAY_PROJECT_NAME:-}" == "positioning-engine-cron" ]] || { echo REFUSED_PROJECT; exit 1; }
[[ "${RAILWAY_ENVIRONMENT_NAME:-}" == "production" ]] || { echo REFUSED_ENVIRONMENT; exit 1; }
[[ "${RAILWAY_SERVICE_NAME:-}" == "Postgres" ]] || { echo REFUSED_SERVICE; exit 1; }
[[ -n "${POSTGRES_DB:-}" && -n "${POSTGRES_USER:-}" ]] || { echo REFUSED_DATABASE_ENV; exit 1; }
[[ -r /dev/tty ]] || { echo INTERACTIVE_PRIVATE_CONSOLE_REQUIRED; exit 1; }
command -v psql >/dev/null && command -v openssl >/dev/null && command -v mktemp >/dev/null || { echo REQUIRED_TOOLS_MISSING; exit 1; }

tmp="$(mktemp -d)"
trap 'unset PGPASSWORD APP_ROLE_PASSWORD; rm -rf -- "$tmp"' EXIT
cat > "$tmp/pinned-public-ca.pem" <<'VOWSIG_PINNED_PUBLIC_CA'
-----BEGIN CERTIFICATE-----
MIIDBTCCAe2gAwIBAgIUNoqkWtcESBg74oLqzy4TemUYp9gwDQYJKoZIhvcNAQEL
BQAwEjEQMA4GA1UEAwwHcm9vdC1jYTAeFw0yNjExMDQxMjUxNDZaFw0yOTAyMDEx
MjUxNDZaMBIxEDAOBgNVBAMMB3Jvb3QtY2EwggEiMA0GCSqGSIb3DQEBAQUAA4IB
DwAwggEKAoIBAQDVGnIMdoIEQQTyXL7/sj8eB0zhF+kUZzahLxVPGwIoB5C2f2PP
LWUOri5i3LRTW6ZaqgDjBO1bUDKW86n5gLGn5J2RBJgnxvgRIzzbMAQr/0rvUcST
U9BWvk4fML4UjNQxxJuO/srNJgIrIxBC7uFklMIiyUQMcRdKyXF1MYKoktvL6sUg
3sPsnnw7W7Egv6hffw56A4T5PrdwKwgw0+9zTujnnuw7QNY/3HP8vrKi7/OgB5Li
BIkPwgXZORra9W7abIVky7kXtM5Vy0ro+3rAaHW3Ij2mSL2OJQKZnM1T8No+A1V4
rYPz0ax0Xsp1ZVqpRUk/SMeZ5wuzv0U/JUinAgMBAAGjUzBRMB0GA1UdDgQWBBTv
QU2tI4tZvvmlWtT+sYhpiDegazAfBgNVHSMEGDAWgBTvQU2tI4tZvvmlWtT+sYhp
iDegazAPBgNVHRMBAf8EBTADAQH/MA0GCSqGSIb3DQEBCwUAA4IBAQCjl5OBll1w
zIhsQNAK29ts6AXQq67UNisqDSIIi3LOguZoPdVg2kcik1zQ0cAnEk+6uaD8XYVc
P10+VnYS4aQiKNCE0nDT/mG9c6hsCX5sz2zMEPAjEBm9IjrokjTyn3bxg+tsnYmG
5Z7nsWIxEBeCjNR558Pqah2/Y92xvjfa9rKIRFQv+Mu9lLdvd6eYs8bQtpD9uY8A
bD7tWitjBO9FYrMNObyQtCAlVqqztTdRjXCBrJwB4A/b2FI5+HMiXOCx09MLA3fJ
1SZCreK2qa/GCKIdAS23J/QxQ3rRiqWzL3mTx44LEd2of+THjpkwlcGjaKo+uxrW
nbWjrir4eruB
-----END CERTIFICATE-----
VOWSIG_PINNED_PUBLIC_CA
chmod 600 "$tmp/pinned-public-ca.pem"
cert_sha="$(openssl x509 -in "$tmp/pinned-public-ca.pem" -outform DER | openssl dgst -sha256 | awk '{print $NF}')"
[[ "$cert_sha" == "2de2743af645b4ea1780ff9f333bc7e25c1897483ac462ebc8756b4fab11baa8" ]] || {
  echo REFUSED_CA_PIN_CHANGED; exit 1;
}

printf 'Existing VowSig PRODUCTION APP role password (hidden): ' > /dev/tty
IFS= read -r -s APP_ROLE_PASSWORD < /dev/tty
printf '\n' > /dev/tty
[[ "$APP_ROLE_PASSWORD" =~ ^[A-Za-z0-9_-]{44,128}$ ]] || { echo INVALID_APP_ROLE_PASSWORD_FORMAT; exit 1; }
export PGPASSWORD="$APP_ROLE_PASSWORD"
unset APP_ROLE_PASSWORD

# Public CA + private Railway hostname; real libpq sslmode=verify-full verifies
# both trust chain and hostname. This checks from the production Postgres
# service's private Railway network; final app-container connection follows
# during the exact-SHA coordinated deployment, not before.
result="$(psql -XwqAt -v ON_ERROR_STOP=1 \
  "host=postgres.railway.internal port=5432 dbname=$POSTGRES_DB user=vowsig_app sslmode=verify-full sslrootcert=$tmp/pinned-public-ca.pem connect_timeout=8" <<'VOWSIG_READONLY_SQL'
BEGIN READ ONLY;
SELECT CASE WHEN
  current_user = 'vowsig_app'
  AND current_setting('search_path') IN ('vowsig, pg_catalog', 'vowsig,pg_catalog')
  AND EXISTS (SELECT 1 FROM pg_stat_ssl WHERE pid = pg_backend_pid()
     AND ssl AND version IN ('TLSv1.2','TLSv1.3'))
  AND EXISTS (SELECT 1 FROM pg_roles WHERE rolname = current_user
     AND rolcanlogin AND NOT (rolsuper OR rolcreatedb OR rolcreaterole OR rolreplication OR rolbypassrls))
  AND has_schema_privilege(current_user, 'vowsig', 'USAGE')
  AND NOT has_schema_privilege(current_user, 'vowsig', 'CREATE')
  AND has_table_privilege(current_user,'vowsig.vowsig_accounts','SELECT')
  AND NOT has_table_privilege(current_user,'vowsig.vowsig_accounts','UPDATE')
  AND NOT has_table_privilege(current_user,'vowsig.vowsig_research_outcome_facts','INSERT')
  AND NOT has_table_privilege(current_user,'vowsig.vowsig_research_outcome_facts','UPDATE')
  AND NOT has_table_privilege(current_user,'vowsig.vowsig_research_outcome_facts','DELETE')
  AND NOT has_column_privilege(current_user,'vowsig.vowsig_owner_totp_credentials','secret_ciphertext','UPDATE')
  AND has_column_privilege(current_user,'vowsig.vowsig_owner_totp_credentials','last_accepted_step','UPDATE')
THEN 'PASS' ELSE 'HOLD' END;
ROLLBACK;
VOWSIG_READONLY_SQL
)"
[[ "$result" == "PASS" ]] || { echo PRODUCTION_APP_ROLE_TLS_PRIVILEGE=HOLD; exit 1; }
echo PRODUCTION_APP_ROLE_TLS_PRIVILEGE=PASS
echo CONNECTED_ROLE=vowsig_app
echo PRIVATE_DNS_VERIFY_FULL=PASS
echo PRODUCTION_DATABASE_WRITES=NONE
echo PRODUCTION_WEB_APP_DEPLOYED=NO
echo LIVE_PUBLISHER_CHANGED=NO
VOWSIG_READONLY_APP_ROLE_CHECK
