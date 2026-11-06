# VowSig Railway PostgreSQL provisioning and isolation receipt — 2026-11-04

**Scope and authorization:** The owner explicitly approved a **private Railway PostgreSQL service in the existing `positioning-engine-cron` project, Singapore region**, with **no changes to the existing VowSig production deployment or account feature flags**. Work was limited to Railway environment inventory, isolated database provisioning and read-only verification. Auth0 and Resend setup have **not** started. This receipt supersedes the earlier planning-document assumption that no Railway database existed.

## Provisioning result — COMPLETE, runtime ONLINE

| Field | Verified value |
| --- | --- |
| Railway project | `positioning-engine-cron` (ID `af8ed976-9971-4f5a-a304-3d8984df1565`) |
| Environment | `production` (ID `fb429ace-7b81-432f-a9d2-32e2044f4392`) |
| Database service | `Postgres` (ID `74a3e855-d97c-4b81-8a27-092f048f9af3`) |
| Template/image | Railway `postgres` template, `ghcr.io/railwayapp-templates/postgres-ssl:18` |
| Runtime observed in startup logs | PostgreSQL **18.6** |
| Region | `asia-southeast1-eqsg3a` (Singapore), 1 running replica |
| Persistent volume | `postgres-volume` (ID `d371c3eb-87fe-4409-a308-fae1f10fde85`); **5,000 MB**, mount `/var/lib/postgresql/data`; Singapore |
| Private networking | Private endpoint `postgres`, internal Railway network only; **zero public domains and zero TCP proxies** |
| Database deployment | `d9f7a675-175e-4eb4-ba83-2ce9bf4c7bfd`, **SUCCESS** |
| Runtime health | **ONLINE**, 1/1 running, 0 crashed, no open warning/critical alerts or reported failures when checked |
| Generated database credentials | Railway-generated; stored only in Railway environment variables. **No values read, printed, committed, or copied into VowSig app** |
| Pending Railway changes | None after commit |

**Method:** Checked environment had no pre-existing staged patch. Described the PostgreSQL template; staged a **database service + volume only**; checked the staged changes had no destructive operation and that the database and volume were both in `asia-southeast1-eqsg3a`. Confirmed **zero staged changes to the existing VowSig service**, then accepted only that isolated database/volume patch. Deployment became successful and its logs reported `database system is ready to accept connections`. This is runtime readiness, **not an authenticated SQL or TLS connection proof**.

## Existing VowSig production isolation — VERIFIED UNCHANGED

| Field | Before and after |
| --- | --- |
| Service | `tradingtop-early-access` (ID `9925f480-e2a6-4384-a886-43f5a7a0a335`) |
| Latest deployment | `59afe99e-c590-4db9-b118-b75a8c75bd7e` — unchanged, SUCCESS, created 2026-10-26 |
| Source | `alisufyan-ai7/trading-signal-intelligence`, branch `main` — unchanged |
| Region / replicas | Singapore, 1 — unchanged |
| Application volume | `/data`, same original volume — unchanged |
| Domains | `vowsig.com`, same Railway service domain — unchanged |
| Existing app variables | Same seven pre-existing names; **no `VOWSIG_ACCOUNTS_FOUNDATION_ENABLED`, `VOWSIG_OIDC_AUTH_ENABLED`, or customer-account DB connection set** |
| Runtime status | ONLINE, 1/1, no warnings or reported recent failures |
| GitHub | PR #93 still **DRAFT and unmerged**. No `main` merge or source changes to the application in this step |

## Critical TLS/hostname mismatch — FAIL CLOSED

The image's initialization logs explicitly show a locally generated self-signed certificate with **`subject=CN=localhost`**. The Railway private endpoint is a service name under Railway's internal DNS, **not `localhost`**. Thus, **do not treat `DATABASE_URL` plus `sslmode=verify-full` as working**, and do not attach the default secret to the VowSig app. The repository's `PostgresAccountStore` deliberately requires a hostname-validated PostgreSQL TLS connection.

**Required before connecting customer data:** provide an approved certificate/trust arrangement with a certificate whose SAN matches the actual internal database hostname and whose CA/trust material is pinned in the app runtime; then **actively test `sslmode=verify-full`**, server identity and certificate validity from the app network. If Railway's default template cannot support it without a custom cert/image, explicitly design and review that compatible solution. **Never** bypass with `sslmode=disable`, `allow`, `require`, or `verify-ca` as a silent downgrade. No automatic image or TLS change was performed; no new production app deployment was authorized.

## Incomplete configuration / release gate — NOT DONE

1. **Authenticated SQL verification:** no in-network SQL execution tool was available through this connected Railway API. Authentication against the generated database, PostgreSQL roles, session TLS status (`pg_stat_ssl`), schema migration dry-run/rollback and app-role isolation have **not** been tested. No SQL migrations or application data were written.
2. **Least-privilege identities:** the application-specific `vowsig_app` role and separately controlled migration role are **not** created. The template's default admin account must not be used as application runtime identity.
3. **Backups and cold restore:** the new 5 GB volume exists, but automatic backup/PITR plan, retention, encryption coverage and an isolated restore **have not been configured or verified by this integration**. Do not claim restored recoverability from the service's online status. Review Railway backup feature/plan and perform an explicit restore test before collecting personal account data.
4. **Network and secrets:** keep database private. No TCP proxy, public domain, application variable reference, external database access, email provider, identity provider or trading connection. Set the future connection string in Railway Secret/Variables only after TLS, role and backup acceptance; do not paste into chat/GitHub/VPS logs.
5. **Costs:** the allocated 5 GB volume and one database replica can incur resource/volume costs. No verified account-specific monthly quote or usage cap is attested here; review Railway usage dashboard before substantial traffic.
6. **Product release:** P0–P4 code remains on GitHub PR #93, feature flags OFF, broker execution OFF, and six non-core markets remain aggregate-only. OIDC/email setup and source-ledger reconciliation are separate stages.

## Next safe actions (no more provisioning automatically)

- Arrange Railway-private-network SQL and certificate/SAN proof without exposing secrets: validate TLS with the exact hostname, trusted CA, and `sslmode=verify-full`.
- Confirm Railway backup policy and complete isolated cold restore for the provisioned Postgres service; document costs and retention.
- Set up non-superuser runtime and migration roles, apply versioned `sql/accounts/001`–`006` only after validated recovery/TLS, with migration/rollback results.
- Only then integrate the Railway app account connection under disabled flags, proceed with managed OIDC and transactional email, and request a separate production feature enable/canary approval.

**Production invariants:** No changes to VowSig application deployment, domains, environment variables, `main`, scheduled tasks, publisher, VPS, trading controls or user access. The database alone was provisioned.
