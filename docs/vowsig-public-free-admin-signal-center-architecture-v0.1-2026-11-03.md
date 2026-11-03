# VowSig product architecture: Public, Free Member, Owner Admin and Signal Center v0.1

**Date:** 2026-11-03. **Status: PROPOSED PRODUCT DESIGN / OWNER REVIEW. NOT APPROVED FOR BUILD OR DEPLOYMENT.** Source of record: only the current chat and private repository alisufyan-ai7/trading-signal-intelligence. No other chats, accounts, competitor websites, or repositories accessed. No change to existing AI inference, immutable ledgers, scanners, publisher, GFS backups, broker execution, user accounts, prices, or live website.

## 0. Executive decision

VowSig should become **one evidence-governed application with three audiences**: unauthenticated visitor (discover and judge), free registered member (explore, save and return), and owner/admin (measure signal validity, model performance, reliability, customer adoption and risk). Maintain a future paid entitlement state in the domain model but launch **no payments, prices or premium promises**. The member destination is **Signal Center**, initially an unmistakably SHADOW_ONLY research workspace. An account does not promote a signal into commercially qualified advice.

Suggested value loop: Discover relevant market -> inspect honest public evidence including losses -> sign up free -> personalize watchlist -> inspect full historical signals, reasons and risk -> revisit / opt into appropriate research notifications only if separately permitted -> provide feedback -> validate engagement and after-cost performance -> later qualify a bounded commercial offering.

Core differentiator: “Find the trade. Explain the trade. Show the risk. Prove the record.” The owner’s October 12 subscription direction is the anchor; do not treat the older “AI research platform” emphasis as the final customer offering.

## 1. Source and confidence audit

Primary existing product source: web/index.html (AI-first hero; core AI status, market cards, decision summaries, shadow signal results, three validation cards, independent S02 benchmark, feedback), web/app.js (renders public signal fields and fetches GET /api/health, /api/markets, /api/signals, /api/ai/insights, /api/validation/programs), web/markets, web/learn, web/evidence; src/trading_signal_intelligence/product/cloud_app.py (public snapshot APIs, publishing ingestion and owner-token feedback summary). The current site also has market-specific URLs and five Learn guides. This is primarily a **single long public research landing page**, not an authenticated workspace.

Backend access reality: the optional beta Basic Auth in product/access.py is a single shared invitation gate, **not customer registration**. Cloud API has token-protected feedback summary/export, **not a multi-user RBAC owner dashboard**. No repository-verified end-user identity store, session service, customer entitlement service, watchlist, member signal-history API, notification preferences/delivery ledger, billing or private signal center. Do not label proposals as deployed.

Source-reviewed product signal fields: AI insight public decisions include BUY/SELL/NO_TRADE, uncalibrated raw confidence, regime, rationale, factors, risk, guard, estimated cost R, status and trimmed hash. Shadow signals include issue/entry timestamp, direction, entry, stop, TP1/TP2, partial TP outcome, exit reason, net R and hashes. Cloud publisher validates absent raw market data, feature snapshots, provider request metadata and hidden reasoning. AI-v1.1 Core: XAUUSD, USTEC, US30. Expansion AI-v1.2.1 EURUSD, XAGUSD, USOIL and separately governed AI-v1.3 crypto BTCUSDT/ETHUSDT/SOLUSDT remain **aggregate research-only** while their own release rules prohibit public per-signal exposure. S02 is a **separate deterministic control**, not an AI model. Broker execution disabled. Legacy v1.0 versus active v1.1 cannot be pooled casually. The current chat’s Nov 3 user screenshot observed a new operational core snapshot with 1,302 valid inferences and 87 completed shadow trades; that is NOT measured profitability or a fresh independent snapshot API acceptance test.

Existing observational performance source (ai_v1/observability.py): completed trades, cumulative net R, average net R, profit factor, max drawdown R and average H1 bars held. These are shadow outcomes, **not client account dollar P&L**. Error and missed-inference counters already exist; closed-market no-current-tick events must not be called missed trades. More analytics proposed below require new **versioned read-only derived views** and explicit denominator/cost methodology.

Competitive evidence is dated snapshots, not presently verified competitor functionality. TradingTop September 27 archive: 34 authenticated screenshots at research/competitors/tradingtop/2026-09-27; docs/tradingtop-authenticated-teardown-and-product-gap-2026-09-28.md plus VIP model memo. Take the signal -> reasoning -> levels -> outcome -> AI history and account packaging. Do NOT copy its TOP credits, broker execution or incompatible aggregate-versus-model return figures. Historical model T2 showed negative P&L despite separate positive headline accuracy. Tradebise Oct 4 archive: 73 redacted screenshots, 64 route/state groups, 39 paths, authenticated Free-account observations, docs/tradebise-authenticated-product-business-seo-audit-2026-10-04.md; learn searchable market pages, watchlist, account settings and free-to-optional-upgrade funnel. Do NOT copy ad intrusiveness, unverifiable broad-universe claims, quota loops or its unreconciled 93% metric. Archive manifests/indexes were read as source text; private JPEG image bytes were not freshly visually re-rendered by the GitHub text connector, so competitor UI details follow the repository's documented capture review.

Earlier plan: docs/vowsig-product-state-and-subscription-direction-2026-10-12.md already proposes Signal Center, Signal Detail, Verified History, Accounts/Alerts and Research/Evidence/Learn. This document refines that proposal, does not supersede the frozen signal/market release boundaries.

## 2. Information architecture and navigation

### A. Public anonymous (SEO and credibility)
Top navigation: Markets | How Signals Work | Evidence | Learn | Sign in | Create free account. Home hero concise: clearly research beta, not live execution; one trusted freshness/status indicator. The “Explore Signal Center” CTA can link to a **public preview/explainer**, not falsely display unapproved actionable suggestions.

Home sections in order: 1) product sentence and market selection; 2) currently supported AI core shadow-market preview with clear timestamps/status; 3) example historical signal walkthrough including both positive and negative cases and NO_TRADE; 4) modest independently labeled outcome snapshot **with denominator and sample period**; 5) “why trust this record” evidence/methodology; 6) free-account benefits (watchlist, full browsing, saved research, filters); 7) Learn links and feedback; 8) S02 independent benchmark behind concise expandable Evidence content. Move detailed operator diagnostics and S02 research tables off the homepage, not out of the evidence archive.

Public Markets directory: only supported **actual** markets, clear lineage/eligibility labels; SEO-dedicated /markets/xau-usd etc with factual method and historical sample + no manufactured “live recommendation” widgets. Index useful canonical public pages; keep authenticated dashboards noindex/private.

Public Evidence and History: definitions, outcome calculation methodology, sample size, open/unresolved count, losses, NO_TRADE and timestamp/gating explanations. Retain a visible immutable track-record digest and audit explanations even if member gets deeper query/filter/detail. Do not erase unfavorable history to drive signups.

### B. Free signed-in customer
Top navigation: Dashboard | Signal Center | History | Markets | Learn; profile menu for Watchlist, Preferences, Notifications (when available), Feedback, Security, Account. Sign-in uses verified individual email and secure session. No “subscription active” or payment expectation. Free member gains *depth, persistence and customization*, not better-looking evidence or disguised signal eligibility.

Dashboard /app: “My markets” cards, last core AI research scan and snapshot freshness, 1–3 watchlist statuses, recent eligible research observations, saved signal/research items, followed markets, recently closed outcomes, recent NO_TRADE, evidence qualification status, and next action (“inspect full history”, “learn stop/target meaning”). Clear empty states before first saved item; no invented signals. Responsive mobile-first.

Signal Center /app/signals: **central customer workflow**. Default active core AI-v1.1 shadow research, not S02, not expansion signals; filters by market, time window, BUY/SELL/NO_TRADE, lifecycle, issue time, guard, source lineage, validity, last updated. Research card shows supported symbol, direction or NO_TRADE, status, issuance time+TZ, bar close, analysis/entry context when legally permitted, stop/TP1/TP2, risk-to-invalidation, contextual rationale, risk factors, model/protocol identity, uncalibrated confidence label, provenance link. A blocked inference, error, expired setup, stale snapshot or NO_TRADE can NEVER be presented as a current eligible BUY/SELL. Treat each as distinct state with explicit reason. Future alerts only for separately approved eligible product class; beta member research updates are distinguishable and opt-in.

Signal Detail /app/signals/{id}: complete lifecycle **timeline** (inference, guard, signal, entry, partial TP1, stop/TP2/timeout/cancel/expiry, closure), immutable references, expected vs observed costs, gross vs net R, original reason/invalidation and what happened; link to relevant market Evidence/Methodology. Maintain no client trade execution claim, no fabricated fill time or USD profit. A later “compare price path” chart requires lawful appropriately licensed data; do not redistribute raw broker candles without rights.

Verified History /app/history: filters and column toggles, all outcomes incl. losses, no-trades, rejected and errors, separate unresolved/open vs completed denominators, model/lineage/time window; downloadable **sanitized derived summary** only after a legal/privacy/rights approval. Privacy-safe pagination and caching. Deeper member history can have more rows, filters and event detail; basic adverse-outcome count and methodology remain public.

Watchlist /app/watchlist: saved supported markets only, user notes and dashboard order; not a personalized managed portfolio. Optional Saved analysis/bookmarks. Preferences /app/settings: email, locale/timezone, selected risk education level, opt-in consents, notifications when separately enabled, account deletion/export and security. No API key/broker connection requested.

### C. Private owner/admin (/admin, protected, hidden from customer menus)
Separate ROLE AND DATA permission, not just a hidden route. Mobile accessible but desktop optimized. Sections below are priority-ordered.

1. **Command Center /admin**: publisher health and last snapshot age; scheduler success/failure by lineage; valid/missed/ERROR ratio; recent credential failure classes and alert state; actual historical run completion; integrity/release gate status; issue #92-style incident stream; next required owner action. Distinguish core/expansion/crypto/S02. Provider secret value NEVER displayed. Include UTC timestamp, sample window and source for every tile; screenshot freshness badge is not evidence of independent API success.

2. **Performance Lab /admin/performance**: market x lineage x version x window panels; completed net R after cost, mean/median R, number closed, wins/losses/breakeven, win rate only closed denominator, payout ratio, profit factor (N/A if zero losses), drawdown measured on chronologically completed normalized R, rolling windows, time in trade, TP1 partial attribution, stop-gap/timeout/TP2/expiry/invalidations, open/censored counts, cost/slippage sensitivity, longest loss streak, time-of-day/session regime breakdown, distribution/histogram. Confidence calibration is an **analysis question**, not a calibrated success probability. Show error bars / uncertainty intervals and minimum sample warnings; compare the S02 independent control only where time windows, markets, costs and trade selection are comparable. Separate shadow P&L, simulated R and **real execution** (currently none). Avoid dollar-equity balances for fictional accounts.

3. **Signal Explorer /admin/signals**: append-only event history per ID; issued, eligible, rejected, blocked, no-trade, open, TP partial, exit, invalidated, expired; mark elapsed publication/notification latency, error classes, missing transitions, unexpected duplicates; source record hash / decision protocol / guard. Admin can annotate investigations in a separate review store, NOT edit immutable signal/ledger events.

4. **AI Quality /admin/models**: inference attempts, provider response class/rate/401/429, parse/schema and guard rejects, timeout, cost per inference and per meaningful signal, token and API spend from sanitized usage telemetry (new feature), prompt/model frozen version, drift or protocol-change checkpoint; candidate release A1/A2/A3/expansion/K5 eligibility and blocked reasons. Do not display raw model secret, request body, provider metadata or hidden reasoning.

5. **Markets & Reliability /admin/markets**: counts and uptime per XAUUSD/USTEC/US30 and each separate expansion program, last data close/tick, no-current-H1-tick versus true process misses, lag histogram, source availability, output states, median issuance delay, signal/NO_TRADE and alerting coverage. Degraded market is not “no trade”.

6. **Publication & Incident Ops /admin/operations**: schedule last/next run and exit, guarded publisher stage and hold reason, public snapshot freshness thresholds (currently delayed >=90m, stale >=150m), cloud acceptance and receipt, archive hash, alert incident queue, recovery runbooks, no one-click unsafe override. Owner actions must be protected explicit state transitions with typed authorization/audit; read-only by default.

7. **Evidence & Release Controls /admin/evidence**: independent lineage timelines, version freezes, immutable hash/provenance verification, comparison cohort rules, historical vs forward periods, owner release decisions, G1–G4, eligible-vs-public flags, protected benchmark, current commercial rights/licenses and unsupported markets. Release cannot be made by changing UI flags alone; validated backend eligibility essential.

8. **Recovery & Backup /admin/recovery**: S02 daily AES backup last successful run, AWS/B2 recoverability evidence time, GFS 30/8/12 inventory and protected-pinned status, owner-approved deletion plan count, 7-day grace, incident latch, provider costs. Current AWS/B2 backup covers only a bounded S02 SQLite; do not imply complete all-IP backup. Cloud delete approvals remain separate controlled workflow; admin view alone cannot enable deletion.

9. **Growth & Customer Research /admin/growth**: anonymous-to-free conversion funnel, eligible visitor counts, activation, watchlist creation, first history view, 1/7/30-day return rates, supported-market interest, feature use, feedback by segment, opt-in preference, support tickets, waitlist, subscription intent only. Acquisition attribution privacy-minimal and opt-in where required. No invented traffic or revenue.

10. **Users, Entitlements & Security /admin/users**: verified accounts, free status, last successful auth, opt-in consents, voluntary feedback, account suspension (audited), support state, session revocation, MFA and admin audit log. Strictly limit personal data; avoid exporting third-party broker or private trading-account details. Future billing is a separate domain.

## 3. Access matrix (launch proposal)

| Capability | Anonymous | Free signed-in | Admin |
| --- | --- | --- | --- |
| Homepage & SEO Markets/Learn | Full | Full | Full |
| Honest method, risks, losses, sample size | Yes | Yes | Yes |
| Core shadow public market state and example historical observations | Short sanitized preview, 3-5 rows | Full entitled sanitized history, filters | Complete read-only evidence drill-down |
| BUY/SELL/NO_TRADE context and status | Overview + public examples | Full eligible **research-only** details when permitted | All states + suppression reasons |
| Active core shadow entry/SL/TP | Existing public contract is historical; any tightening requires separate explicit reviewed API policy | Full research-only scoped data | Full internal analytical context without secrets |
| Validation expansion crypto & S02 | Aggregate allowed only, S02 separate | Same aggregate boundary; accounts grant NO expansion per-signal rights | Authorized internal evidence under owner review |
| Watchlist / bookmarks / saved filters | None | Yes | May inspect anonymized usage aggregate, not impersonate |
| Notifications | None | Preference capture only until channel approved | Delivery health and audit after deployment |
| Signal performance | Honest high-level totals + methods | Complete filtered after-cost research history | Full quality, reliability, per-market/lineage analytics |
| Event/ledger hashes | Public trimmed, methodology | Source-linked sanitized history | Authorized integrity/incident proofs |
| User/account data | None | Own only | Minimum necessary users/ops |
| API keys, raw features, source feed, provider payload, private hash anchor | Never | Never | Not in dashboard; separate protected operator controls |
| Broker execution | Disabled | Disabled | Disabled |
| Billing | Not launched | Free-only | Feature flags/intent only, no charges |

**Critical:** public endpoints currently expose full core shadow detail. Hiding it with CSS, JS, or client routes is ineffective; changing public exposure is a separate backwards-compatibility, ethics and security review. Server must issue explicitly tier-filtered payloads. Every tier still has correct truth about adverse outcomes. No entitlement may bypass privacy/rights/public-signal exposure flags.

## 4. Metrics contract (definitions before claiming “performance”)

One normalized **signal entity** per issued signal ID; one completion only, optional partial exits attributed once. Track inference attempts separately from generated signals, and generated/issued signals separately from completed outcomes. An inference, NO_TRADE or rejected candidate is NOT a losing/completed trade.

Completed win rate = completed exits with net_R > 0 / completed exits with valid net_R; treat zero R as breakeven and report separately. Expectancy = sum(completed signal net_R) / number of completed signals, plus median, confidence interval and sample size. Profit factor = sum(positive completed net_R) / abs(sum(negative completed net_R)); N/A when loss denominator is zero. Normalized R drawdown = peak-to-trough of time-ordered cumulative completed net_R; not actual account drawdown. Net R must include the documented deterministic spread/slippage/fees or explicitly say cost assumptions unverified; an exit's partial TP1 and final combined R cannot be summed twice. Open mark-to-market is not realized return. Dataset population and time bounds must accompany every displayed win rate and return.

Admin views should include: entry-to-exit heatmap, duration distribution, expectancy by market/model/version, BUY vs SELL, TP/stop/timeout distribution, missed/rejected reason, latency/downtime, observed vs estimated provider cost, rolling degradation, baseline comparison on matched conditions, outlier audit and uncertainty warnings. Use *forward* data separate from backtests, AI-v1.0 legacy separate from v1.1 core, S02 separate from AI, crypto/expansion separate from core. No forced comparison of non-overlapping experiments and no speculative “accuracy = profit”.

Every KPI stores: metric_version, program_id, model_version, source window (UTC), as_of_utc, source_snapshot_sha, population filters, realized/open denominator, cost_model_version, units, source lineage, calculation timestamp and validation status. Null/insufficient data is shown as N/A, never fabricated zero. Public headline summaries require additional quality/reliability sample gates and owner review.

## 5. Scalable low-complexity architecture

**Keep the existing Windows scanners, immutable SQLite ledgers and guarded publisher frozen.** Add a product-facing modular-monolith backend instead of premature microservices. Railway-hosted FastAPI remains product API initially; new customer identity/domain database should be **managed PostgreSQL** (choose provider after costs and backups reviewed), not the mutable single-snapshot JSON file or the private Windows research SQLite.

Proposed internal modules:
- Evidence Ingest: versioned sanitized snapshot / lineage proofs; the existing safe publisher remains input, no provider credentials on public host.
- Read Models: incremental idempotent projection from sanitized immutable event IDs into signal_current, signal_events, performance_daily, market_health, snapshot_receipts, release_eligibility. Keep immutable source SHA and projection code version. Rebuild without editing the ledgers.
- Customer Domain: users, roles, sessions, email verification, watchlists, saved_items, preference_consents, research_feedback, activity_events.
- Entitlements: tier/feature/market/source policy engine; public, free, admin and future paid role. Program-level visibility and product qualification are **separate AND conditions**: the user's role never overrides expansion no-exposure or unhealthy/stale state.
- Administration: operator aggregates and read-only incident views via privileged server APIs. Strong RBAC, separate admin identity or MFA + short sessions, second-factor for destructive owner actions, rate limits, immutable admin access audit and least privilege.
- Future Delivery: opt-in alert subscriptions, outbox events, idempotent notification attempts, retries/dead-letter, delivery receipts, preference audit; no actual signal alerts until signal-level commercial release gates pass.
- Future Billing: independent subscriptions, payment provider and webhook state; no billing code required for Free v0.1.

Use one transactional PostgreSQL schema/cluster for MVP with domain table separation, then split workloads only under evidence of scale. Publish/outbox consumers process incremental events; avoid scanning all SQLite ledgers or regenerating full analytics on every user GET. Cache sanitized common public read models/CDN assets. Keep market/lineage/time indexed queries and cursor-pagination; add materialized daily performance summaries (versioned/rebuildable) as volumes grow. No user account, password, private preferences or admin metrics inside public static snapshot. The snapshot remains a signed/hashed sanitized publication projection, not a user datastore.

Key tables (proposal): programs, market_instruments, source_snapshots, immutable_signal_events, projected_signals, trade_outcome_facts, metric_definitions, performance_rollups, publication_incidents; users, sessions, memberships, user_watchlists, user_saved_items, user_preferences, consent_events, activity_events, admin_audit_events, feature_entitlements; later notification_outbox and billing_*.

API proposal: GET /api/v2/public/overview, /api/v2/public/markets/{symbol}, /api/v2/public/history-summary, /api/v2/me, /api/v2/me/watchlist, /api/v2/me/signals, /api/v2/me/signals/{id}, /api/v2/me/history, /api/v2/me/preferences, /api/v2/admin/overview, /api/v2/admin/performance, /api/v2/admin/operations, /api/v2/admin/evidence, /api/v2/admin/growth. Preserve v1 public endpoints during controlled backward-compatible transition. Authorization enforced at each API query, not front-end display; cookie security, CSRF protection, email verification, anti-bot/rate controls, session revocation, audit and data-retention policy required. Admin endpoints noindex and unreachable to public auth. Do not expose passwords or provider keys in admin UI.

Use privacy-minimal analytics: visitor anonymous coarse session, page_event, signup_start, verified_account_created, onboarding_complete, watchlist_saved, signal_detail_view, history_filter_used, return_visit, user_feedback, notification_opt_in. Explain collection/consent and data retention before launch. Avoid capturing raw trading notes and search queries unnecessarily. Exclude internal/admin/test traffic from conversion metrics.

## 6. Signal Center state machine (must be modeled, not inferred from UI copy)

- NO_CURRENT_DATA / STALE / PROVIDER_ERROR: no fresh valid inference; show honest degraded state and previous timestamp, do not synthesize or replay old “active” signal.
- NO_TRADE: intentional valid abstention with rationale and market/time; not a BUY.
- REJECTED / GUARD_BLOCKED: inference recorded but unpublishable; show research-only reason under permitted tier, no alert.
- SHADOW_SIGNAL_ACTIVE: governance-valid *research* signal, with issuance/entry/stop/TP1/TP2 and explicit SHADOW_ONLY. Does not imply subscriber trade eligibility.
- SHADOW_SIGNAL_PARTIAL / CLOSED / EXPIRED / INVALIDATED: evidence lifecycle, archived loss/partial outcome; no silent replacement.
- CUSTOMER_ELIGIBLE (future): separate approved product qualification, fresh source, rights and operational gates, alert eligibility and explicit owner release; unavailable by default.
- CUSTOMER_ALERTED (future): separate delivery event and receipt, not equivalent to execution.
- PAUSED / SUSPENDED_BY_INCIDENT: emergency release gate, no false recency, existing evidence preserved.

Do not use “win” for a TP touched unless a complete accounting convention supports it. No chart candles without commercial redistribution rights. Reference lineages and source issues on every detail.

## 7. Rollout roadmap, tests and owner release gates

**P0 — metric contract and scope freeze.** Implement NO production change yet. Owner approves this access matrix, competitor decisions and first free-member scope; G4 first-cohort observational feedback stays a gating input, not erased by new planning. Admin metric denominator/cost/lineage definitions are versioned; all links to source hashes retained. Acceptance: signed UX/field/data contracts and forbidden-field matrix.

**P1 — identity and Free account MVP.** Managed Postgres + secure auth; verified email; individual account sessions; role/user isolation; onboarding choose only 3 eligible core markets; watchlist/saved filters; /app Dashboard; /admin restricted owner. No paywall or payment gateway. Acceptance: anonymous cannot access member endpoints, member A cannot read B's account, owner-only paths fail closed, deletion/export tests, low-data privacy, audit and rate tests, no effect on scanner/publisher.

**P2 — reliable read models + admin performance lab.** Build snapshot-preserving, source-hash-pinned incremental projections; metrics R definitions, lineage/cost/window filters and sample uncertainty; admin operational triage (including 401 credential expiry cases), protected publisher controls. Acceptance: reconciliation against immutable source count/outcome for all eligible lineages, replay/idempotency, adversarial error/partial TP/unknown data tests, stale snapshot must never appear fresh.

**P3 — Signal Center Free research-only release.** Routes, responsive cards/details/history and status gates; public light preview; member deeper research history; no explicit actionable expansion/crypto exposure. Release gated by privacy/rights/product QA and exact VPS source tests. Acceptance: no false BUY for NO_TRADE/error/stale; history always includes adverse cases; no cross-role leakage; usability research demonstrates lifecycle comprehension and genuine user return intent.

**P4 — customer learning and notifications preparation.** Feedback loop from free member, first-cohort G4, funnel measurement with consent, usability/mobile and accessibility. Collect notification preferences, but do not send trading alerts until approved; design delivery audit and delayed/expired cancellation. Acceptance: meaningful cohorts and activation/retention denominators and privacy-reviewed copy. Test actual interest over survey intent.

**P5 — bounded paid commercial signals (NOT in current release).** Only after per-lineage after-cost forward quality/reliability and usage rights qualify; owner explicitly releases exact actionable markets, delivery channels and legal copy; subscription billing can then be implemented with pricing hypothesis tests, no “guaranteed accuracy/profits” language. Fees, refunds, tax, regional rules and security reviewed separately. Broker execution remains disabled.

Parallel independent operations: resolve current Issue #92 publication incident stability, preserve S02 backup/GFS owner-signature safety, complete remaining provider/backup rights and expand IP backup separately. None grants signal eligibility or product deployment authority.

## 8. Product and commercial success criteria

No fabricated current adoption. Proposed early account KPIs: first successful signup/verification, percentage of new accounts selecting supported watchlist market, first Signal Center use within 24h, first full history/loss view, D1/D7/D30 returns (cohort-qualified), qualitative understanding of “shadow” and stop/target, most valued signal detail, support load and zero privacy leakage. Do not use raw website traffic or site claims as proof of willingness-to-pay. Later commercial readiness: prospective sample size/window, after-cost expectancy stability, low data downtime, deterministic freshness, alert delivery latency, real opt-in and measured willingness-to-pay/paid retention when separately authorized.

## 9. Explicitly excluded/deferred

No paid subscriptions or checkout now; no crypto payments, TOP-like credits, affiliate system, ads adjacent to decision panels, thousands of thin market pages, model marketplace with unvalidated variants, artificial “accuracy” claims, broker connected trades, paid boost, scraping competitor data, personal investment personalization or copy-trading. Expansion/crypto never gain per-signal public exposure by registering. No private raw market feed, model hidden reasoning or credentials in customer/admin APIs. No automatic merging/deployment from this planning memo.

## 10. Reference map

- [Product direction + prior Signal Center](vowsig-product-state-and-subscription-direction-2026-10-12.md)
- [Competitor strategic decisions](competitor-research-strategic-decisions-2026-10-04.md)
- [Competitor synthesis](competitor-synthesis-waqarzaka-tradebise-tradingtop-vowsig-2026-10-04.md)
- [TradingTop authenticated teardown](tradingtop-authenticated-teardown-and-product-gap-2026-09-28.md) and archived images in ../research/competitors/tradingtop/2026-09-27/
- [Tradebise authenticated Free audit](tradebise-authenticated-product-business-seo-audit-2026-10-04.md) and archived images in ../research/competitors/tradebise/2026-10-04/
- [Current UX](../web/index.html), [client render](../web/app.js), [cloud source/API](../src/trading_signal_intelligence/product/cloud_app.py)
- [Public AI projection](../src/trading_signal_intelligence/product/ai_insights.py), [observational performance definitions](../src/trading_signal_intelligence/ai_v1/observability.py)
- [Feedback design](early-access-feedback-customer-discovery-v0.1.md), [SEO research](tradebise-seo-patterns-for-vowsig-v0.1.md)
- GitHub Issues #9 (customer discovery) and #92 (latest public publisher incident)
