# Railway Postgres public CA pin and application-network TLS probe — 2026-11-04

## Evidence / permitted scope

The owner ran a read-only command in the existing private Railway PostgreSQL 18 container. The current server certificate reported `CN=localhost` **plus SAN `DNS:postgres.railway.internal`**, signed by a locally generated `CN=root-ca`; libpq reported `PRIVATE_DNS_TLS_VERIFY_FULL=PASS` from *inside the database container*. Owner then supplied the **public root CA PEM**. Its X.509 SHA256 certificate fingerprint was independently decoded and verified:

```
2D:E2:74:3A:F6:45:B4:EA:17:80:FF:9F:33:3B:C7:E2:5C:18:97:48:3A:C4:62:EB:C8:75:6B:4F:AB:11:BA:A8
```

The public CA has `CN=root-ca`, `CA:TRUE`, and expires **2029-02-01T12:51:46Z**. Only public information is stored under `config/tls/railway-postgres-root-ca-20261104.pem`; no private CA key, client secret, database password or DSN is committed. The certificate is tied to **this exact current Railway Postgres deployment** and is **not** a permanent globally trusted root. A database regeneration/replacement can invalidate its trust: fail closed, re-verify the new root out of band and rotate with a reviewed deployment.

## Application-container independent TLS identity — PASS (owner execution 2026-11-04)

Owner executed the credentials-free PostgreSQL SSLRequest/TLS handshake from the **currently running** Railway `tradingtop-early-access` application Console (`/app`), using the previously validated public root CA:

```text
APP_NETWORK_TLS_VERIFICATION=PASS
TLS_VERSION=TLSv1.3
VERIFIED_HOST=postgres.railway.internal
SERVER_SAN=(('DNS', 'localhost'), ('DNS', 'postgres.railway.internal'))
SERVER_SHA256=42574eca8c9afa481beefb2c3ea6b508bcd3e6c27e1b287d20274d72458e9526
```

That leaf SHA256 **exactly matches** the preceding PostgreSQL Console fingerprint `42:57:4E:CA:8C:9A:FA:48:1B:EE:FB:2C:3E:A6:B5:08:BC:D3:E6:C2:7E:1B:28:7D:20:27:4D:72:45:8E:95:26`. The certificate's DNS SAN, trusted owner-supplied CA and TLS 1.3 were verified from a separate application container with explicit hostname verification. Terminal paste echo has some line scrambling, but the expected TLS success fields, hostname, SAN and matching leaf fingerprint appeared.

**Status:** Independent application-network *TLS certificate identity* is now **PASS**; this supersedes the earlier TLS-only pending status. No custom DB image/certificate replacement needed. **Not yet certified:** a complete PostgreSQL authenticated libpq/psycopg connection using non-superuser account, correct `sslrootcert` in the final candidate image, privileges/schema migrations, cert rotation, scheduled encrypted offsite backups and cold restore. Do not infer account readiness or actual SQL auth from the SSLRequest handshake.

## PR #93 code changes (NOT yet deployed)

- The Dockerfile previously installed `.[app]` **without** `.[accounts]`. It now includes the account-specific OIDC, cryptographic JWT, HTTP and psycopg dependencies: `pip install --no-cache-dir -e ".[app,accounts]"`.
- The existing `COPY config ./config` places the **public** CA in the candidate app image at `/app/config/tls/railway-postgres-root-ca-20261104.pem`.
- `src/trading_signal_intelligence/product/accounts/tls_probe.py` implements a read-only PostgreSQL SSLRequest (no password, startup message, SQL or database mutation), validates the root certificate SHA256, and requires Python `ssl.CERT_REQUIRED` + `check_hostname=True` against **`postgres.railway.internal`**. Run only in an independently verified app-network environment: `python -m trading_signal_intelligence.product.accounts.tls_probe`. It prints safe TLS status/version and public cert fingerprints; it does **not** prove database authentication or least privileges.
- `tests/test_vowsig_railway_tls_p1b.py` checks public CA integrity, expiry, CA role, target pin, fail-closed overrides and Dockerfile packaging. Isolated CI tests do not connect to real Railway.

## Actual Railway acceptance sequence

1. **PASS from deployed app Console:** independently verified TLS 1.3, chain, exact private hostname, and leaf certificate fingerprint using a one-time, self-contained credentials-free Python probe. Packaged candidate module still requires build-stage smoke proof when its release image is available.
2. In isolated preproduction, build the exact candidate app image; assert `/app/config/tls/railway-postgres-root-ca-20261104.pem` exists with the expected certificate hash, and run the packaged probe. No customer data.
3. Once restricted PostgreSQL app/migration identities and independently proven encrypted offsite backup+restore exist, securely supply an app-only DSN with `host=postgres.railway.internal`, `sslmode=verify-full`, and `sslrootcert=/app/config/tls/railway-postgres-root-ca-20261104.pem` using Railway's secret store. A full `psycopg` authenticated connection and `pg_stat_ssl` check from the app network is still required. Do not post raw DSNs, passwords or secrets to chat/GitHub.
4. Record server identity, certificate renewal/restart behavior and CA rotation/rollback; do not rely on blind dynamic trust or downgrade to `sslmode=require`, `verify-ca` or `disable`.

The original Railway environment has an unrelated **staged** live-app variable patch for `VOWSIG_ACCOUNTS_APP_ORIGIN`. Never commit or discard it as a side effect of TLS verification. No merge, production deployment, real account, Windows VPS or trading change is authorized by this file.

**Single release:** free Auth0 customer login, verified email, full owner/admin dashboard with free-to-operate fresh MFA, independently source-certified historical research analytics, recovery and strict TLS must all pass before one coordinated public launch.
