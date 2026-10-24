# VowSig — Current Product State and Signal-Subscription Direction (2026-10-12)

**Status:** Documentation-only owner review candidate. **No code, release, scheduling, trading, source-data access, pricing launch, customer outreach, cloud setup or merge authority.**

**Owner-confirmed primary product objective (current chat, 2026-10-12):** A **subscription-based AI trading-signal service** providing timely, high-quality, actionable BUY/SELL opportunities with **entry, stop loss, take profit(s), supporting reasoning and verifiable outcomes**. The **AI trading-research capability is primarily internal infrastructure**, not a separately prioritized customer research platform. A sellable customer-facing research product is optional and deferred. Signal quality and customer willingness to pay are evidence questions, not proven claims.

## 1. Provenance, authority and time boundaries

- Sole repository: `alisufyan-ai7/trading-signal-intelligence`.
- Reviewed GitHub production `main` at `a4f00578c00c5e23eb4fae073cf2df18c78d9a0a`, tree `a1d4f12738eeb1865d298a15583c77d6180c95ec` (PR #54 already merged).
- Owner-supplied full-length homepage screenshot was inspected in the current chat on 2026-10-12. Its precise local observation and limitations are documented in [the screenshot observation record](../research/product/vowsig-homepage-observation-2026-10-12.md).
- The screenshot visually establishes **rendered section presence**; its narrow 344 px screenshot and tiny text do not authenticate exact counters, HTTP requests, individual signal quality, current server state or a continuing scheduler run.
- Direct independent public-site HTTP/browser verification was **not completed** in this documentation pass. Latest hosted production evidence is a **historical checkpoint** from [Issue #47 first naturally scheduled guarded publisher PASS](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/47#issuecomment-6112078271), not a 2026-10-12 uptime attestation.
- Read newer merged PRs, immutable published evidence and Issue #57 [canonical 2026-10-12 handoff](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/57#issuecomment-6112967700) before treating dated earlier `PROJECT.md`, `docs/current-status.md`, Issue prose or historical draft PR descriptions as live state.
- This memo proposes future **priorities**, not new owner approval. Preserve immutable historical failures, activation/correction lineage, failed and superseded research, frozen validation gates and separately bounded private data rights.

## 2. Product positioning: present vs target

**Today:** VowSig is a **public AI-first research beta** with structured AI BUY/SELL/NO_TRADE decisions, governed **shadow** signal outcomes, deterministic filters, verifiable research evidence and a public website. It is **not** yet a proven-profitable, generally released or paid actionable-signal subscription.

**Target:** Customers subscribe to access *eligible, timely, explainable* BUY/SELL signal opportunities: market and source context, issue timestamp, status/freshness and expiry, entry reference/zone, stop/invalidation, TP1/TP2, risk/reward or sizing-neutral risk context, rationale/risk factors, lifecycle updates and full after-cost performance history. NO_TRADE and losing outcomes remain visible. No guarantee of returns and no personalized broker execution.

**Brand proposition:** “Find the trade. Explain the trade. Show the risk. Prove the record.” Existing AI-first phrasing “AI finds the setup. Risk rules verify it. Every signal stays on the record.” represents the desired trust differentiation, **not** a claim that all research signals have passed commercial qualification.

## 3. What is already implemented (source + dated operational evidence)

### Website / customer product

- `web/index.html` and `web/app.js` implement hero/status, core AI shadow overview, per-market panels, AI decision rationale/risk factors, core AI shadow-signal lifecycle including entry/stop/TP levels, separate validation-program cards, supporting S02 benchmark, and the Early Access feedback form.
- `web/markets/`, `web/learn/`, `web/evidence/` implement market/educational/evidence pages, with SEO metadata and sitemap/robots provisions in `src/trading_signal_intelligence/product/cloud_app.py`.
- The cloud FastAPI application exposes public health, evidence, markets, AI insights, validation-program and signal-history APIs; `POST /api/feedback` has schema validation and persistent submission handling; owner feedback summary/export is token-protected. Live endpoint parity with current source was **not independently retested here**.
- Latest documented natural guarded publish on 2026-10-11 closed PASS: three independent public programs and nine public market-catalog rows; raw market data and private provider payloads excluded; broker execution disabled. Hosted *server-stored full-byte* snapshot SHA was **not** proven by that checkpoint.

### Signal generation / research platform beneath the product

- Normalized broker-neutral market data interfaces for MT5/Exness and Binance, causal closed H1/H4 feature derivation, structured OpenAI AI-v1.0 decision contract and deterministic risk/publication guards; local SQLite hash-chained evidence, lifecycle accounting, frozen policy/version identity and shadow scanners.
- `config/ai_v1_decision_schema.json`: `BUY`/`SELL`/`NO_TRADE`, raw *uncalibrated* confidence, regime, bounded stop ATR / TP multiples, rationale and risk factors. `src/trading_signal_intelligence/ai_v1/signals.py` derives entry, stop, TP1 and TP2 after guard approval and records shadow exit outcomes. Raw confidence **must not be sold as a calibrated success probability**.
- **Core AI-v1.1**: XAUUSD, USTEC and US30; AI-v1.0 frozen decision protocol; customer-visible shadow decisions and outcomes; `core-ai-shadow` public program.
- **Expansion AI-v1.2.1**: EURUSD, XAGUSD and USOIL; `market-expansion-1`, aggregate public validation only; **no public actionable entry/stop/target/alert exposure**.
- **Crypto AI-v1.3**: BTCUSDT, ETHUSDT and SOLUSDT via separately governed Binance-based research; `crypto-expansion-1` public card is fixed, **DELAYED historical aggregate-only evidence** last verified 2026-10-11T12:07:21.257601+00:00, not a live/current signal. `CRYPTO_WRITER_INTERLOCK_READY=False`; no current actionable crypto details or customer crypto alerts.
- **S02 Structure Breakout**: frozen deterministic XAUUSD-primary, USTEC/US30-secondary forward **benchmark/control**, not AI and not an input into the AI engine. S01 was rejected as a general FX strategy; S03/S04/S05 remain hypotheses, not qualified customer offerings.
- User-visible current snapshot freshness, research lifecycle status, failure/NO_TRADE accounting and separate AI/S02 attribution are existing distinctive assets.

## 4. What is verified about quality — and what is not

- The [2026-10-07 core public verification checkpoint](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/23#issuecomment-6044647959) observed 348 core valid inferences and 26 completed shadow trades; this establishes a functional outcome-measurement path **as of that date**, **not profitable expectancy or current counts**.
- The [2026-10-08 S02 forward checkpoint](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/3#issuecomment-6056078661) reported XAUUSD 6/20 F1 completed trades, plus separate USTEC/US30 observations; S02 remains research, not promoted candidate.
- The [2026-10-11 private K5 aggregate observation](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/57#issuecomment-6112515769) reported 132 total valid crypto inferences, 1 completed SOL shadow trade at -1.1441308433399684R, zero BTC/ETH completed trades; this is **economically inconclusive** and C1/C2/C3 ineligible. The one-time private read authority was consumed.
- Historic AI-v1.2 failed campaigns, historical quota errors and artifact incompatibility records are not overwritten by later healthy operations.
- Paid-signal suitability needs **prospective, after-cost evidence**, causal reproducibility, calibrated claims where appropriate, adequate observations, reliability/latency checks, source rights and a **separate release decision**. Passing a count threshold alone never implies guaranteed profitability or public signal exposure.
- Owner-confirmed Exness rights apply to the intended *commercial derived-signal* use and do **not** automatically authorize raw-feed redistribution, third-party offsite SQLite backup, or new jurisdictions/processors. Binance commercial-source terms remain separately scoped.

## 5. Screenshot-grounded UX assessment (not a live functional test)

Observed homepage ordering: hero and freshness/status → “What VowSig is seeing” core AI overview → per-market core collection → AI decision summaries → core shadow signal outcomes → three validation program blocks/market summaries → S02 independent control → feedback. The dated screenshot shows those rendered groups in one long mobile-width page.

**Strengths to retain:** genuinely AI-first hierarchy; explicit abstentions, risk context and lifecycle; separate lineages; fixed S02 comparison; visible failure/evidence concepts; user feedback and non-guarantee disclaimers.

**Future subscription UX gap:** A prospective paying trader must scroll through numerous research statistics to discover the current actionable opportunity. Present `shadow` and `delayed` signals must **not** be visually relabeled as live commercial recommendations. Clear visibility of *currently eligible vs invalid/expired vs research-only* states is essential. A mobile-width screenshot does not establish desktop usability, conversion rates or actual subscriber comprehension.

**Proposed post-qualification information architecture (design proposal, not current functionality):**
1. **Signal Center**: eligible time-stamped opportunity status by instrument; BUY/SELL/NO_TRADE; entry, SL, TP1/TP2, risk and validity; explicit alert/subscriber eligibility. If no approved signals, state “No eligible signal” without simulating activity.
2. **Signal Detail**: methodology/strategy and source identity, concise rationale, invalidation, expected risk/reward, lifecycle and historical context.
3. **Verified History**: **all** opened/completed/invalidated/losing signals, realized net R, fees/cost assumptions, lineage/version and audit information; no cherry-picking.
4. **Accounts / Subscription / Alerts**: customer-controlled authenticated access, entitlements, opt-in channels, delivery audit/retries and clear research-only vs actionable rights.
5. **Research, Evidence, Learn and public SEO pages**: preserved as transparent supporting context, without turning the homepage into a strategy laboratory.

## 6. Commercial reality / current missing evidence

- Existing public product feedback collection, persistent owner-only reporting, research beta and SEO foundation are implemented. GitHub Issue [#9](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/9) documents first-wave customer prospect outreach; three submitted outreach messages do **not** establish responses, conversions or real-user feedback completions.
- `docs/first-cohort-recruitment-and-pricing-plan-v0.1.md` treats $25–$100/month as **hypotheses**; no chosen active recurring price, paid subscription checkout, customer billing lifecycle or paid-retention proof is established in current hosted code/evidence.
- Customer account/entitlement service, end-user alert preferences and reliably delivered paid notification channel are **not proven commercially deployed** by the reviewed cloud API; local Telegram/S02 notifications or future runbooks are **not** equivalent to subscriber delivery.
- Product/business comparison: **TradingTop** primary product/monetization comparator, **Tradebise** primary SEO/discovery comparator, **WaqarZaka** membership/community comparator. See `docs/competitor-research-strategic-decisions-2026-10-04.md`. Do not copy performance claims, ad pressure, credit complexity or execution features without separate evidence.
- Repo has code and plans for backups and one verified local S02 copy/reopen, but **zero verified off-VPS backup**; preserve rights HOLD and prioritize a proportionate independent protection milestone without allowing it to displace core product discovery indefinitely.

## 7. Proposed next priorities — not authority to execute

| Priority | Milestone | Measurable acceptance before the next stage |
| --- | --- | --- |
| P0 | **Reconcile product truth** and present this memo for owner review | Distinguish current website/source/runtime evidence from commercial claims; no code changes |
| P1 | **Core AI signal-quality decision support** using *already authorized public/sanitized* evidence, and separately scope any further private read | Per-market after-cost results, signal timeliness/expiration, invalidation, distribution and independent baseline; preserve frozen gates and no tuning based on early results |
| P2 | **Signal Center UX specification/prototype** from synthetic/public safe data, retaining research-only status and lineage boundaries | Customer comprehension tests; no falsely actionable live signals; focused tests and separate approval for production |
| P3 | **Customer value / G4 evidence** from existing Issue #9 first cohort | Real feedback, return intent, alert preferences, price sensitivity and eventual actual paid conversion; outreach approvals remain separate |
| P4 | **Subscription foundation** only after P1/P3 evidence supports bounded pilot | Auth, checkout/billing, subscriber entitlements, cancellation, secure alert preferences and delivery receipts; licensing/security/privacy review |
| P5 | **Gradual actionable rollout** per eligible lineage and approved source rights | Independent product and operational release gates; separate explicit permission to expose live actionable setups; execution remains disabled |
| Parallel | **Modest rights-compliant backup/recovery** to protect irreplaceable ledgers | First off-VPS encrypted recoverable copy only after rights/provider/key/budget permissions, then broader recovery independently proven |

The subscription business objective **does not change any existing activated decision policy**. New strategy hypotheses, cost/risk changes or model revisions require prospective new versioning and their own evidence; no post-result selection. Broker auto-execution is out of scope. Do not provision cloud accounts, alter production, read private ledgers, trigger scanners, change publishing gates or contact customers on the authority of this document.

## 8. Follow-up review questions (no decision assumed)

- Is the first paid offering *access to **qualified actionable signals***, or a clearly labeled lower-stakes research-only founding tier while the evidence matures?
- What after-cost signal-quality standard and latency/expiry behavior must be achieved for the first public actionable signal release?
- Which user segment, supported markets and notification methods earn recurring subscription value with minimum complexity?
- Which limited on-site analytics should remain prominent, and which should move into expandable Evidence/Research pages?

## 9. Immutable links / specific source references

- [VowSig homepage source](../web/index.html), [client renderer](../web/app.js), [cloud routes](../src/trading_signal_intelligence/product/cloud_app.py), [AI public insights](../src/trading_signal_intelligence/product/ai_insights.py), [AI decision contract](../config/ai_v1_decision_schema.json), [signal lifecycle](../src/trading_signal_intelligence/ai_v1/signals.py).
- [Product thesis](product-thesis.md), [AI-first homepage hierarchy](vowsig-ai-first-homepage-hierarchy-v0.1.md), [business benchmarks](competitor-research-strategic-decisions-2026-10-04.md), [cohort pricing hypothesis](first-cohort-recruitment-and-pricing-plan-v0.1.md), [S02 strategy status](../strategies/STATUS.md).
- [Issue #47 natural guarded publication](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/47#issuecomment-6112078271), [Issue #57 crypto assessment](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/57#issuecomment-6112515769), [Issue #57 October 12 handoff](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/57#issuecomment-6112967700).
- [Image observation/provenance](../research/product/vowsig-homepage-observation-2026-10-12.md). **The actual image bytes are not represented as committed unless independently verified in a later change.**

**Review boundary:** This is proposed product-direction documentation only. Any PR containing it must remain DRAFT until the owner separately approves its exact reviewed scope and commits. **No automatic merge, VPS sync or site publication.**
