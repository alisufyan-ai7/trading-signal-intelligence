# Railway Postgres public CA pin and application-network TLS probe — 2026-11-04

## Evidence / permitted scope

The owner ran a read-only command in the existing private Railway PostgreSQL 18 container. The current server certificate reported `CN=localhost` **plus SAN `DNS:postgres.railway.internal`**, signed by a locally generated `CN=root-ca`; libpq reported `PRIVATE_DNS_TLS_VERIFY_FULL=PASS` from *inside the database container*. Owner then supplied the **public root CA PEM**. Its X.509 SHA256 certificate fingerprint was independently decoded and verified:

```
2D:E2:74:3A:F6:45:B4:EA:17:80:FF:9F:33:3B:C7:E2:5C:18:97:48:3A:C4:62:EB:C8:75:6B:4F:AB:11:BA:A8
```

The public CA has `CN=root-ca`, `CA:TRUE`, and expires **2029-02-01T12:51:46Z**. Only public information is stored under `config/tls/railway-postgres-root-ca-20261104.pem`; no private CA key, client secret, database password or DSN is committed. The certificate is tied to **this exact current Railway Postgres deployment** and is **not** a permanent globally trusted root. A database regeneration/replacement can invalidate its trust: fail closed, re-verify the new root out of band and rotate with a reviewed deployment.

## PR #93 code changes (NOT yet deployed)

- The Dockerfile previously installed `.[app]` **without** `.[accounts]`. It now includes the account-specific OIDC, cryptographic JWT, HTTP and psycopg dependencies: `pip install --no-cache-dir -e ".[app,accounts]"`.
- The existing `COPY config ./config` places the **public** CA in the candidate app image at `/app/config/tls/railway-postgres-root-ca-20261104.pem`.
- `src/trading_signal_intelligence/product/accounts/tls_probe.py` implements a read-only PostgreSQL SSLRequest (no password, startup message, SQL or database mutation), validates the root certificate SHA256, and requires Python `ssl.CERT_REQUIRED` + `check_hostname=True` against **`postgres.railway.internal`**. Run only in an independently verified app-network environment: `python -m trading_signal_intelligence.product.accounts.tls_probe`. It prints safe TLS status/version and public cert fingerprints; it does **not** prove database authentication or least privileges.
- `tests/test_vowsig_railway_tls_p1b.py` checks public CA integrity, expiry, CA role, target pin, fail-closed overrides and Dockerfile packaging. Isolated CI tests do not connect to real Railway.

## Actual Railway acceptance sequence

1. With the currently deployed app still unchanged, use **Railway > production > tradingtop-early-access > Console** (NOT the Postgres Console) and a one-time, self-contained Python snippet using this same public CA to validate the real private-network SSLRequest and hostname. Do not print passwords or `env`. This is the last independent application-network **TLS-only** check. Since the candidate code is not yet deployed, the packaged module cannot be called in the live application until the coordinated release.
2. In isolated preproduction, build the exact candidate app image; assert `/app/config/tls/railway-postgres-root-ca-20261104.pem` exists with the expected certificate hash, and run the packaged probe. No customer data.
3. Once restricted PostgreSQL app/migration identities and independently proven encrypted offsite backup+restore exist, securely supply an app-only DSN with `host=postgres.railway.internal`, `sslmode=verify-full`, and `sslrootcert=/app/config/tls/railway-postgres-root-ca-20261104.pem` using Railway's secret store. A full `psycopg` authenticated connection and `pg_stat_ssl` check from the app network is still required. Do not post raw DSNs, passwords or secrets to chat/GitHub.
4. Record server identity, certificate renewal/restart behavior and CA rotation/rollback; do not rely on blind dynamic trust or downgrade to `sslmode=require`, `verify-ca` or `disable`.

The original Railway environment has an unrelated **staged** live-app variable patch for `VOWSIG_ACCOUNTS_APP_ORIGIN`. Never commit or discard it as a side effect of TLS verification. No merge, production deployment, real account, Windows VPS or trading change is authorized by this file.

**Single release:** free Auth0 customer login, verified email, full owner/admin dashboard with free-to-operate fresh MFA, independently source-certified historical research analytics, recovery and strict TLS must all pass before one coordinated public launch.
