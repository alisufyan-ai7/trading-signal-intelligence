# P1B PostgreSQL baseline and scoped role policy — 2026-11-04

## Owner-provided read-only baseline

The owner executed a read-only `psql` inventory from Railway `production > Postgres > Console` and reported:

```text
pg_version=18.6 (Debian 18.6-1.pgdg13+2)
tls_enabled=on
existing_vowsig_tables=0
vowsig_app / vowsig_migrator / vowsig_backup roles=NONE
```

The actual database is **clean** with respect to new account schema and roles; this is not evidence that the entire database is empty. No production SQL writes, migrations, role creation or user accounts were authorized or performed by this review. Prior evidence already proved both independent DB-container `sslmode=verify-full` and application-container TLS 1.3 + private DNS certificate chain/SAN, but not authenticated restricted-role SQL.

## Review-only role design

New file `sql/accounts/007_restricted_roles_and_grants.sql` explicitly requires:
- Dedicated PostgreSQL schema `vowsig` owned by `vowsig_migrator`; migration files 001–006 applied **as migrator** to that schema, not public. The current app SQL is unqualified, so restricted roles must have a **server-side `search_path=vowsig,pg_catalog`** configured for their database, verified in an isolated test. A query-path check is required before release.
- `vowsig_app`: private schema USAGE; SELECT on table data for controlled server-side membership/admin routes; INSERT/UPDATE/DELETE on specifically enumerated account, session, preference, watchlist and OIDC tables only. It must not CREATE/ALTER/DROP schema, manage roles, elevate its own `role` column, or write historical source snapshots/outcomes.
- `vowsig_backup`: SELECT on all `vowsig` tables and relevant sequences for `pg_dump` metadata/data. It cannot INSERT/UPDATE/DELETE/TRUNCATE, own schema or alter source ledgers.
- `vowsig_migrator`: separate restricted migration identity owning the new schema and objects. It is not used by the runtime application or backups, and it should not be globally superuser, CREATEDB, CREATEROLE or BYPASSRLS.
- `PUBLIC` gets no privileges on the dedicated schema or its tables/sequences. Future migrations must explicitly review runtime DML privileges. Backup SELECT on new tables is permitted through migrator default privileges.

## Disposable PG18 proof (no Railway access)

`scripts/vowsig_accounts_ci_pg18_role_boundaries.py` requires the exact GitHub Actions runner/repo and fixed local disposable database DSN. It creates an isolated throwaway database `vowsig_roles_test` and three passwordless `NOLOGIN` **CI-only** roles, applies all seven SQL migrations/policies under a schema owner, and actually checks app INSERT, immutable historical tables, app owner-role elevation denial, schema DDL denial and backup read-only enforcement using separate effective session authorizations. It prints only synthetic PASS/FAIL. It does not create any role on Railway, install schema in `public`, use real credentials or connect to external systems.

**Caveat:** this isolated policy proof is not yet a live role-bootstrap, encrypted backup/restore, migrations rehearsal, app login, historical source reconciliation, or a production approval.

## Actual Railway next gates

1. Establish a low-cost approved encrypted offsite backup destination and recovery key custody, then test an exact scheduled dump, integrity manifest, retention policy, failure alert and separate cold restore of the real database. The current Railway native backup panel showed Pro-only options; no paid plan upgrade is authorized. The ability to back up a database with zero VowSig tables does not establish a recoverable production routine.
2. Only after recoverability and a reviewed idempotent deployment script: create separate LOGIN roles with **privately generated distinct credentials** in Railway only, `CREATE SCHEMA vowsig AUTHORIZATION vowsig_migrator`, `ALTER ROLE ... IN DATABASE ... SET search_path TO vowsig,pg_catalog`; then perform schema migrations 001–006 as migrator, apply policy 007, check object ownership, table counts, DDL/DML constraints and recovery. Never put passwords in GitHub, chat or Console output.
3. Supply app-only `VOWSIG_ACCOUNTS_DATABASE_URL` with exact `host=postgres.railway.internal`, `sslmode=verify-full`, and bundled public `sslrootcert` from PR #93. Verify an authenticated `psycopg` app connection with separate login, `pg_stat_ssl` and actual `current_user/search_path`. No app feature enablement until the **one full production release** after owner security/history verification.
4. Reconcile the unrelated **pending** Railway app variable patch `VOWSIG_ACCOUNTS_APP_ORIGIN` before any accept-deploy: current production app must not change by accident.

**Release scope:** single coordinated public release with verified customer accounts, Resend, complete owner/admin with secure free MFA, verified source history and accurate cost-normalized analytics, recovery, app+DB security and rollback; no paid Auth0 feature or broker execution.
