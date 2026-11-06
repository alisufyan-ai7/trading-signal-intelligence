# VowSig — current product contract, user journeys, boundaries and launch scope

**Current on 2026-11-06.** Source of truth is this repository's PR #93 candidate and [current-state index](VOWSIG_START_HERE_CURRENT_STATE.md). This document describes what is **implemented in the candidate**, what has **real staging evidence**, what remains **unavailable**, and what is explicitly **future**. It is not permission to publish signals, enable payments or merge/deploy.

## 1. Product proposition and commercial direction

**Brand:** **VowSig**, AI-first market research and signal intelligence. Historical TradingTop/SignalProof identifiers remain in code, env names, task names and provenance, not customer messaging. Intended positioning: **“See the setup. Understand the risk. Prove the record.”** The current service is **SHADOW_ONLY research**, not a regulated investment adviser, copy-trading system, account-connected execution bot, guarantee of profit, or already-validated subscription product.

**Longer-term business objective:** customer access to timely eligible BUY/SELL opportunities with entry reference, stop, TP1/TP2, concise rationale, risk and persistent lifecycle/after-cost record; **only after** external after-cost/source-rights/history and eligibility evidence warrants it and owner approves monetization. The initial owner-authorized release is **Free verified signup**, no paid plans/checkout, no alerts, no broker execution, no new markets. Strategy/AI work stays internal infrastructure serving the product, not a promise that all markets have commercial-quality signals.

**Value differentiation:** preserve rejected/NO_TRADE and losing research observations instead of curating wins, explain model/protocol and actual data freshness, prohibit unsupported accuracy/ROI claims. Shadow signal records and S02 benchmark are **different lineages**. The public homepage’s legacy AI research and benchmark data contracts continue to exist, even though new member/owner routes have stricter permission controls.

## 2. Exact nine markets and release permission matrix

| Program | Symbols | Public research / member directory | Detailed current/recent shadow signal access |
| --- | --- | --- | --- |
| **Core AI-v1.1 / `core-ai-shadow`** | **XAUUSD, USTEC, US30** | All listed; freshness / methodology / permitted high-level record status | Sanitized research-only signal detail **only when snapshot fresh, core program allowed, record lifecycle eligible and server permission passes**. Never interpret an old active record as live unless timestamp/hold checks pass. |
| **Expansion AI-v1.2.1 / `market-expansion-1`** | **EURUSD, XAGUSD, USOIL** | Listed with validation/research progress and truthful unavailable/delayed state | **NO** customer per-signal BUY/SELL, entry, stop, target, record/hidden reasoning. Noncore endpoint returns forbidden. |
| **Crypto AI-v1.3 / `crypto-expansion-1`** | **BTCUSDT, ETHUSDT, SOLUSDT** | Listed with validation/research status | **NO** customer per-signal details, regardless of observed internal trade counts. |
| **Separate S02 deterministic benchmark** | Independent of the nine AI directory/programs | Existing benchmark/evidence v1 public API only | Not a tenth AI signal product; never pool S02 history/performance with AI programs. |

**Never infer eligibility from catalog presence, watchlist selection, user's role, AI confidence, lifecycle counts, broker available market data, or program status.** Source: `src/trading_signal_intelligence/product/accounts/policy.py`; `market_directory`, `core_signal_available`, `permitted_core_recent_signals`. All market rows declare `commercial_customer_eligible=false` in this release. Current/eligible means the actual snapshot is fresh (**<90 minutes**) and the particular signal’s issue time + maximum H1 hold has not expired. An absent, delayed, stale or malformed snapshot fails closed to *unavailable* with no invented signals. The existing public legacy `/api/markets` nine-symbol list is **not identical** to the new authenticated nine-market `/api/v2/public/markets`; do not silently change that historical v1 contract or pretend it represents the new directory.

## 3. Personas, roles, permissions and route contract

| Persona | Journey | Allowed data | Access boundary |
| --- | --- | --- | --- |
| **Anonymous / public** | Landing → methodology/markets/Learn/evidence → sign in/create Free account | Public sanitized beta preview, facts about nine researched markets via new v2 public catalog, older v1 public core/benchmark evidence | No private member watchlist/preferences, owner metrics or customer records. Public legacy core detail remains subject to its existing v1 allowlist; don't claim signup magically hides older public payloads. |
| **Verified Free member** | Auth0 email signup → verified callback → Dashboard/Signal Center → All Markets → permitted core research details → History → Save/watch → Learn → Account & Settings → Logout → Re-login | Own watchlist/saved research, preferences, permitted sanitized core recent signals and history, market status for all nine | Backend authentication, membership, consent, 3-versus-6 permission; no per-signal noncore details, no live brokerage or paid entitlements. |
| **Owner** | Existing verified account → one-use offline approval and TOTP enrollment → fresh verified session → Account & Settings owner code step-up → /admin | Owner-only aggregate operations, model/version, market reliability, evidence status, growth/security and available verified history read model; **not** raw broker feeds or secret export | Real server-side role + recent (15-min) MFA proof, audit, CSRF, no-store private responses. Not an owner just because email matches; no web-owner-enroll endpoint. |
| **Publisher/operator** | Windows VPS guarded scanner/derived publisher and narrowly scoped DB/backup operations | Sanitized snapshots or controlled raw private source evidence under rights and custody | Separate service credentials and roles; never impersonates member/admin, never accepts browser trades. |

**Actual new API surface:** `src/trading_signal_intelligence/product/accounts/api.py` mounts `/api/v2/public/markets`, `/api/v2/public/overview`, `/api/v2/public/history-summary`; `/api/v2/me`, `/me/watchlist`, `/me/signals`, `/me/signals/{entity_id}`, `/me/history`, `/me/preferences`, `/me/saved`, `/me/export`, `/me/deletion-request`, `/me/logout`, `/me/owner-mfa/verify`; and owner `/api/v2/admin/overview`, `/admin/operations`, `/admin/models`, `/admin/market-reliability`, `/admin/performance`, `/admin/evidence`, `/admin/growth`. The `/api/v2` prefix is set by router implementation; the corresponding UI is `/app/` and `/admin/`. See source before naming new endpoints. Auth `/auth/start` and `/auth/callback` in `auth_api.py`. The **production version on main is not necessarily serving these yet**—PR #93 remains DRAFT/UNMERGED.

## 4. Information architecture and UX

### Public website (existing live research beta)

- **Hero/positioning:** AI-first research beta, clear **SHADOW_ONLY** and not execution/guaranteed-return notice.
- **Signal/research examples:** source-limited latest core AI decisions/approved shadow entries and outcomes, timestamps/freshness; no invented precision.
- **Programs:** core, expansion, crypto validation summaries **without** customer expansion/crypto signal detail.
- **Markets, Learn, Evidence:** SEO pages and grounded explanation of BUY/SELL/NO_TRADE, entry/stop/TP, validation and immutable record; retain current public SEO routes and sitemap.
- **Independent S02 benchmark:** visual/semantic separation from AI-v1.x; never label it AI or conflate cohort performance.
- **Feedback/early access:** existing public endpoint and token-protected owner feedback API, prior beta telemetry. Email verification and customer sign-in as separate upcoming release capabilities.

### Logged-in member product (candidate code)

- **Dashboard:** concise “what is known now,” real data freshness/availability, links to Signals and watched markets, disclosure of research-only.
- **Signal Center:** permitted core shadows only when truly eligible; status, direction, issue time, entry/stop/TP1/TP2 and rationales/risk where source+gate allow. If stale or absent, explicitly say no current research signal; NEVER synthesize a WAIT/BUY alert.
- **All Markets:** searchable/filterable nine symbols by category. Core detail permissions depend on live publication gate; restricted six show validation/status/unavailable and cannot leak signal payload.
- **History:** existing sanitized/short public-research history only. No claim of fully complete source population or independently audited after-cost record; losses and NO_TRADE remain in appropriately scoped evidence.
- **Watchlist/Saved:** add/remove permitted market watchlist, preserve across refresh/relogin, save permitted research IDs; saving a noncore market is **not** permission to disclose signals.
- **Learn:** conceptual literacy and provenance, linked to evidence; avoid investment instructions and unsupported predictions.
- **Account & Settings:** consent/security, preferences, export/deletion request, clearly visible sign out; for owner only, TOTP step-up input and secure link to admin.
- **Mobile-first UX:** desktop left sidebar; phones (320–390px) bottom navigation Home/Signals/Markets/Saved/More with sign out reachable from More, 44px touch targets, safe-area padding, keyboard/focus and no horizontal overflow. Tested in CI, actual staging screenshots also observed. Code: `web/member/index.html`, `web/member/member.css`, `web/member/member.js`. Competitor teardown is **presentation reference**, not proof of competitor performance or licensing.

### Owner / Command Center (candidate, real staging UI PASS)

The owner-only `/admin/` contains:
1. **Source-limited operational overview:** snapshot status, freshness, runtime/publisher evidence boundaries and backup recovery truth.
2. **Runtime observability & operating boundaries:** known core/expansion/crypto program states, no-current-H1-tick vs processing misses where source can legitimately support denominator; no “missed trades” reinterpretation.
3. **Model versions & projected lifecycle populations:** program attribution, source status and counts **not** automatically independently reconciled P&L.
4. **All-market reliability diagnostic:** nine cards, known/unknown counters, missed cycles only where actually known, unavailable states otherwise.
5. **Performance Lab:** view remains enabled; without independent signed full-history rights/after-cost/K5/matched cohort evidence it **must** show **Source-reconciled performance unavailable** / N/A, not a fabricated track record. This is the explicitly approved first-launch exception.
6. **Independent history evidence & reconciliation:** manifest/custody/reviewer states and limits; do not confuse hash-chain passes with full economic verification.
7. **Growth, access security & recovery:** privacy-safe verified account/session/retention aggregates; no unproven revenue/D7 retention or backup coverage claims. Owner TOTP/role safeguards apply to all privileged API routes.

**No new chart families, speculative KPI estimates, subscriptions/payment conversion forecasts or inferred ROI are authorized before release.** Existing owner dashboard can render N/A until a real source fulfills its contract; real staging screenshot PASS is visual/API access evidence, not proof of the absent historical source.

## 5. Account/auth/privacy contract

- Auth0 Regular Web App, verified email, **Authorization Code + PKCE S256**; enforce exact issuer/client ID/nonce/state/browser binding, callback claim signature via JWKS RS256, immutable provider issuer+subject; do not grant owner by matching email. Auth0 paid MFA is **not** needed for owners.
- Database-backed users, identities, verified entitlement, sessions, watchlists, saved research, preferences, consent, deletion request, OIDC one-use code flow, owner encrypted factor and audit. SQL `001..010` with only restricted `vowsig_app` runtime grants and SSL `verify-full`; migrator offline only.
- Role+MFA fresh 15 minutes for admin; TOTP RFC6238 30-second six-digit, encrypted AES-256-GCM per-account associated data, 5 attempts/15-minute lockout, replay/step reuse prevention. Initial staging founder `first_owner_solo` was separately authorized and audited; future recovery distinct-person condition remains.
- Secure HTTP-only cookies with appropriate SameSite/Secure behavior (confirm actual source/hosting), origin/CSRF for writes, no-store private responses, rate guards, old-session revocation on privilege changes and logout. **Do not log OAuth callback query parameters**; candidate Dockerfile disables Uvicorn request-line access logs.
- Backend prevents cross-account access and noncore detail access; frontend visual hiding is insufficient. Exports/deletion requests should match stored private data and documented manual handling; no automatic deletion completion claim when merely requested.

## 6. Data, validation, visibility and evidence ownership

**Two fundamentally different stores:**
- VPS evidence: original SQLite source ledgers plus frozen copies, hash chain/lineage and known failures. The owner-reported 12/12 frozen chain/11,103 rows and 298 internal cost legs are scoped technical checks **not full external sign-off**. The VPS is the source; no raw data/hidden reasoning or broker credentials go to public.
- Railway public sanitized snapshot: `TRADINGTOP_INGEST_TOKEN`-guarded `/api/internal/snapshot`, mounted `/data/public_snapshot.json`, generated UTC and program flags. Supports core public research and **aggregate** expansion/crypto validation. Must report missing/delayed/stale accurately. Staging intentionally has no independent snapshot; production publisher already exists and is not duplicated.

**Historical certification deferral:** Explicit owner approval 2026-11-06 only defers the *timing* of independent source rights, after-cost economic validation, crypto K5 natural H1/H4 opportunity census and signed nine-market complete cohort manifest. **No historical net-R, returns, win rate, equity, growth projection or commercial eligibility is authorized** until separate signed proof and owner-reviewed change. Separate S02 forward results may be shown only under original benchmark contract, never as core AI record.

**Data quality and lifecycle:** AI inference, shadow trade open/close, rejected/NO_TRADE, timestamps/errors/missed cycles and statuses must remain distinct. Snapshot time is not proof of external VPS Task Scheduler health; a fresh public snapshot does not guarantee original-source completeness. Preserve bad trades/failures, do not cherry-pick or invent closed outcomes; confidence is uncalibrated and not a probability of profit.

## 7. Current implementation versus acceptance

| Capability | GitHub implementation | Live acceptance at 2026-11-06 |
| --- | --- | --- |
| Public existing research beta and snapshot publisher | `web/`, `cloud_app.py`, Windows publisher in repo | Hosted public /api/health and validation programs recently observed live/fresh. |
| Member Free account/Signal Center/watchlist/permissions | PR #93 candidate; account API, UI, SQL | Real staging member browser acceptance PASS; exact current PR code HEAD has CI PASS. **Production not enabled**. |
| Owner TOTP and admin | PR #93 candidate, owner API/MFA and audited one-use offline helpers | Real staging founder enrollment, TOTP owner admin screenshot/guest deny PASS. Production owner not yet provisioned. |
| Owner full history | Views + guarded read-model/evidence contracts | N/A / unverified, explicitly accepted for first launch. Not a success metric. |
| Production Postgres schema | SQL 001–010 and reviewed one-time operator | Owner supplied `PROD_VOWSIG_001_010_COMMITTED=PASS`; **do not rerun**. Real app-role private TLS SQL acceptance pending. |
| Production Auth0, Resend and app vars | Code/config + secure provider identity | Auth0 public discovery and verified sender present; four secrets staged but values not externally validated; callback real verified delivery and live signup pending. |
| Backup/cold recovery of Railway customer PG | Design/postlaunch plan | **NOT verified**; owner accepted first postlaunch task, risk label remains. |
| Paid tiers/alerts/execution/new markets | Historically researched concepts only | **Not approved**, disabled; not first launch scope. |

## 8. Product acceptance and future roadmap

**Must pass prelaunch:** positive + negative Auth0 verified/free login/callback and Resend actual email; production app role private verify-full/TLS and no DDL; owner factor bootstrap/step-up/recovery, guest/nonowner deny, account watchlist persistence/CSRF/logout/replay, nine-market three-vs-six signal permissions and no hidden data, mobile overflow/nav/accessibility, original publisher snapshot freshness, all uncertified history N/A, exact release evidence + rollback plan + owner exact-commit approval.

**Immediate postlaunch:** independent encrypted recurring Railway PostgreSQL backups to S3/B2 and cold restore under explicit temporary-risk exception; monitor operator audit/recovery and user consent; then source rights/cost/K5/complete independent history certification before publishing returns.

**Later only on explicit new approval:** paid memberships/payments/pricing; user alerts and delivery, market additions or per-signal expansion access; calibrated performance scorecards, truly source-verified charts and outcome pages; richer admin analytic drilldowns, alternative app/mobile skins; execution/broker integrations. Do not treat brainstormed possibilities as approved implementation.

**Code and legacy reference map:** `README.md`, `PROJECT.md`, [nine-market contract](vowsig-p0-nine-market-signal-center-customer-access-contract-v0.1-2026-11-04.md), [mobile competitor UX](vowsig-mobile-first-experience-and-competitor-design-review-2026-11-06.md), [owner diagnostics](vowsig-owner-ops-model-market-source-reconciliation-2026-11-04.md), [owner deferral](vowsig-owner-approved-first-launch-history-deferral-2026-11-06.md) and [release gate](../src/trading_signal_intelligence/product/accounts/release_acceptance.py). Historical docs may contain older goals or stale PASS/HOLD labels; see [START HERE](VOWSIG_START_HERE_CURRENT_STATE.md) for precedence.
