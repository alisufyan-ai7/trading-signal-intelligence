# VowSig integrated customer-product execution plan — P1 through P5

> **OWNER-APPROVED SUPERSEDING RELEASE POLICY (2026-11-04):** Full-feature public production go-live is approved **in principle without the new Railway Postgres automated offsite backups already complete**, with recovery implementation the **first activity immediately after launch**. This consciously creates temporary irreversible customer-data loss exposure; do not imply data is recoverable. No feature-disabled deployment. All other safety/functional/source-accuracy gates and exact-SHA owner deployment approval remain. **See** `docs/vowsig-one-release-backup-last-feature-first-2026-11-04.md` (binding D-01 to D-06). Statements below that call database backups a pre-launch hard gate are superseded; they remain requirements for post-launch completion. This does not authorize a merge or live deployment yet.

**2026-11-04. Owner direction:** Complete all owner-independent work before requesting infrastructure/production decisions. Use one draft PR (#93) and few coordinated production deployments. Keep project evidence in this repository; do not depend on other conversations/repositories. This plan documents deliverables honestly, not a blanket release approval.

## Binding scope amendment — ONE production launch (owner decision 2026-11-04)

The owner explicitly requires a SINGLE coordinated VowSig production release. Do not defer the full owner/admin dashboard or independently source-verified historical analytics to a second launch. Earlier language proposing a limited signup beta and later owner/history releases is superseded. Internal CI, isolated staging, TLS probes, source audits and dress rehearsals may occur separately; they do not constitute customer-facing releases.

**Required scope at the one launch:** Auth0 Free $0 verified customer signup/session/consent; Resend transactional email; Signal Center and nine-market directory (per-signal exposure still only for permitted XAUUSD/USTEC/US30 unless separately approved); fully functional authorized owner/admin operations, growth and Performance Lab; independently reconciled immutable-source historical results with costs, adverse outcomes and completeness reports; read-only operational controls. No paid Auth0 features, premium MFA, broker execution, trading alerts, payments or invented performance claims.

**Admin is not complete today:** the /api/v2/admin/performance route deliberately returns performance=null and verified_full_history=false; /admin/operations is snapshot-limited; owner require_owner rejects sessions without a fresh MFA proof. Implement an independently tested and free-to-operate owner step-up MFA mechanism, secure owner bootstrap/recovery, admin audit and full read-model integration before the one release. Do not bypass the fresh-MFA guard.

**Historical analytics are not complete today:** a hashed sanitized bundle in quarantine is NOT independently verified source history. Obtain authorized read-only source-ledger manifests, complete exact event/count coverage, immutable hashes and after-cost normalized R, independent replay/reconciliation and owner provenance acceptance before promoting any cohort. Missing or inconsistent cohorts must fail closed. The capped public snapshot is not a legitimate substitute.

**Railway/TLS update (owner evidence 2026-11-04):** PostgreSQL's server certificate SAN includes `postgres.railway.internal`, with owner-pinned public root CA. A verified-hostname `sslmode=verify-full` query from the PostgreSQL container PASSed, and a separate **live application-container read-only TLS probe PASSED TLSv1.3**, the exact hostname and the matching leaf SHA256. The original suspected `CN=localhost` SAN conflict is resolved. **Still required:** final application-image root CA packaging verification, authenticated `psycopg` SQL login under restricted app role, migrations, independent offsite encrypted backup/restore, and rotation plans; do not downgrade TLS.

**Controlled release:** Final exact-SHA green CI + independent source verification + free owner MFA + actual Auth0 login testing + Railway TLS and recoverability + staged/rollback UAT are all PASS before one merge/deploy/feature enablement. Preserve the existing unrelated staged Railway VOWSIG_ACCOUNTS_APP_ORIGIN variable until explicitly reconciled. The live site and trading runtime stay unchanged until the single coordinated cutover.

**What owner can do immediately:** In Railway > production > Postgres > Console, inspect the server's PUBLIC certificate subject/issuer/SAN/dates/fingerprint and report only the non-secret metadata. Never share database passwords, connection strings, CA private keys or client secrets. The actual Postgres private hostname and public root CA certificate must be validated later from an independent application-network probe.

**Timing:** No certified production date until actual TLS/backup/source-ledger evidence is available. No second release is planned and no safety gates may be silently weakened to force the date.

---
## Scope and order

| Priority | Workstream | Implementation status in consolidated PR #93 | Independent work remaining | Owner/infrastructure gate at end |
| --- | --- | --- | --- | --- |
| P0 | Nine-market/three-permitted-core contract, entitlement and metrics definitions | Implemented in docs + backend negative tests | Regression checks and traceability review | Any market release permission expansion is separately owner-controlled |
| P1A | Permanent account identity, verified sessions, isolated watchlist, entitlements | Implemented, feature OFF; PostgreSQL schema and integration tests | Complete operational safeguards, session expiry/revoke/error paths, account data handling | Railway service credentials/region/TLS and security release |
| P1B | OIDC verified identity and onboarding | Immutable issuer+subject, strict verified-claims contract; provider-neutral backend session issue/rotation and logout tested | Generic OIDC adapter tests and provider-specific mapping after identity provider selected | Managed identity provider/verified email, redirect URI, actual JWT/PKCE/state/nonce configuration, owner MFA, Railway connection |
| P2 | Evidence-safe read models, Performance Lab, operations | Complete-population after-cost net R calculator, strict finite denominators, source projection schema, read-only owner diagnostics; strict off-line sanitized-source bundle validation | Reconciliation protocol and read-model ingestion adapter prepared for *verified authorized source*; negative/DB tests | Production-origin immutable source hashes, source-rights/publisher permissions, source/count reconcilability, exact performance owner signoff |
| P3 | Customer-facing Signal Center | Server-filtered nine-market directory, bounded permitted core signal/history and NO_TRADE; responsive /app shell, signal cards, watchlist, saved research, protected /admin UI | UX/manual browser/accessibility reviews, adjust display to actual live source fields | Real signup identity provider and Railway persistence + privacy/security before enabling route |
| P4 | Learning, feedback, preferences, adoption | Public Learn articles linked; member timezone/education/preferences, opt-in captured (no outbound sending); account export/deletion-request queue; read-only owner signup/watchlist aggregates | Consent analytics schema and real user-cohort data only with privacy approval; email deliverability test after provider hookup | Legal copy, opt-in processing policy, D1/D7/D30 consent/retention, abuse controls and deletion/reverification processor |
| P5 (deferred) | Paid trading signals, subscriptions, alerts or broker execution | **NOT implemented or authorized** | None is required for research-only Free signup | Separate legal/commercial/reliability/rights evidence, owner release, billing/taxes/refunds and alert security; broker execution remains disabled |

## Parallel engineering tracks, without parallel open PRs

**Track A — Account / privacy:** P1A/B verified-login plumbing, session rotation/revocation, account isolation, CSRF, saved preferences/bookmarks, export and deletion intents. It remains feature OFF until provider and security gates. Provider-specific OIDC/email integration is last, not prerequisite for research UI work.

**Track B — Research data:** P2 static, deterministic metrics and offline, source-hash-enforced read models; fail closed if source coverage/record hashes/combined net R missing. No fabricated win rate, cash equity, profits or model precision. Expose only "source incomplete" in owner dashboard until legitimate full-history reconciliation. Protect S02 as a separate benchmark, not part of AI signal feed.

**Track C — Customer:** P3 accessible responsive Signals -> Market -> History -> Learn -> Watchlist pathways; all nine discoverable; only XAUUSD/USTEC/US30 currently allow sanitized per-signal details, only when snapshot permission/health/freshness gates pass. Enforce before returning any data, not just CSS. NO_TRADE/blocked/failed/expired signal never rendered as an active market trade; record adverse cases.

**Track D — Growth / learning:** P4 preferences and research learning; no outbound trading alerts, phantom traffic, subscriber revenue or invented analytics. Account aggregates when database is live; D7 retention/real funnel remain N/A until consent-approved event capture.

All tracks converge into **one customer-product release candidate** on PR #93. No unrelated AWS/B2/GFS backup code, immutable Windows scanners, guarded publisher or separate freeze-safety PR is modified. Issue #92 health, publication stability and source-rights gates are independent of customer UI.

## Planned acceptance, in order

1. Static/unit tests, synthetic negative permission checks, JavaScript syntax, database migrations on disposable PostgreSQL; no live credentials. Confirm exact SHA and no old Free-named database entities.
2. Integration: exact immutable verified IDP issuer/subject; successful first-signup/returning-login, duplicate-email collision (no auto-link), verification pending/expired/revoked/disabled, CSRF, secure __Host cookie, logout/session rotation, owner MFA; Rails/Postgres connection SSL verified and least privileges.
3. UI: nine discoverable, six forbidden details even on paid tier; only eligible core research, NO_TRADE, negative outcomes, missing/stale source, no unverified active signal, accessibility on mobile/desktop; signed-out and forbidden routes private/noindex.
4. P2: independently review source data rights/coverage/immutable-head pins; verify full cohort hashes, event/exit uniqueness, after-cost partial attribution, time window and denominators; release full histories only after source corroboration. No public inference of full history from capped snapshots.
5. Operations: Railway region/TLS/CA, least privilege, backups/restore, secret rotation; IDP email sender/domain/MFA/abuse throttling, privacy+deletion obligations; canary/staging tests; no broker execution.
6. Owner review exact tested SHA, provider selections/cost and one coordinated production deployment, with disabled flag/reversible cutover and rollout monitor. Treat this as a *single gated customer release*, not a series of live experiments.

## One consolidated production cutover target

Build/test/review on isolated GitHub runners and disposable PostgreSQL now; then one dry-run in a separately approved nonproduction environment for real Railway connection and auth provider; then one production release with all code, DB migrations and frontend assets. Provisioning or test deployments need not hold up independent development. Start with feature disabled until external identity/prod verification succeeds. Publish a separate explicit enablement approval; don't automatically unlock all markets, alerts, paid plans or trading.

### Handoff information to ask the owner only after independent work is verified

- The existing Railway project/environment to host accounts, selected geographic region, budget cap and whether to provision a new isolated Postgres service (no credentials shared in chat).
- The identity provider choice (or allow recommendation after vetted current provider comparison), verified email sender domain, redirect URL and allowed app hostname; owner MFA enrollment path.
- Approve data-retention/privacy wording and exact production release SHA, deployment rollback window, monitoring and source-hash access for complete history. These are not daily coding blockers; collect once near launch.

**Operational honesty:** No Railway service has been provisioned here, no real login, verified email or production registration is active. CI tests against a disposable local PostgreSQL do not prove real Railway TLS/CA and restore behavior. Full-history/performance source reconciliation requires approved evidence, not just software code. P5 is intentionally not part of this research-only release.
