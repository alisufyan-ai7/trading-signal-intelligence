# Five-Day Early Access Launch Plan

**Created:** 2026-09-21  
**Target:** Public/invite Early Access Beta within 3–5 days  
**Constraint:** Product launch is separate from G3 strategy validation. XAUUSD remains the primary active forward-tested S02 market; USTEC and US30 launch as secondary S02 signal markets with weaker evidence labels.

## Launch positioning

Launch as:

> **TradingTop Early Access — verified rule-based market setups with transparent historical and forward performance.**

Do not launch as:

- guaranteed profitable signals;
- AI market prediction;
- investment advice tailored to the user;
- copy trading or automated execution;
- a claim that S02 has completed forward validation.

## Data-source launch rule

G2 is passed for the initial Exness-based commercial derived-signal launch use case because the project owner confirms separate Exness permission has already been obtained.

Use Exness for launch. Do **not** buy a replacement market-data subscription before the application is generating revenue.

Keep the product centered on derived outputs rather than raw-feed redistribution, and keep the normalized adapter layer so a paid institutional/commercial feed can be substituted later if needed.

## MVP scope

### Must ship

1. Landing page
   - concise value proposition;
   - research-beta label;
   - risk disclosure;
   - sign-up / waitlist.

2. User authentication.

3. Multi-market signal dashboard
   - XAU/USD, NASDAQ 100 / USTEC, and DOW 30 / US30 live-signal cards;
   - current state per market: active setup or "no active setup";
   - direction;
   - issued UTC;
   - entry reference;
   - stop/invalidation;
   - target;
   - R:R;
   - strategy version.

4. Signal history
   - immutable signal ID;
   - issued time;
   - lifecycle status;
   - exit/result;
   - net R when complete.

5. Evidence page
   - historical backtest clearly labelled historical;
   - forward record clearly separated;
   - visible losses as well as wins;
   - strategy/version methodology link.

6. Alerts
   - one channel for beta: email or Telegram;
   - no broker execution.

7. Admin/ops
   - health status;
   - last scanner run;
   - ledger validity/head hash;
   - signal count.

### Explicitly defer

- multi-strategy portfolio;
- personalized suitability;
- auto-execution/copy trading;
- native mobile app;
- advanced charting;
- AI chat over the full market;
- complex billing tiers;
- broker account linking.

## Day-by-day plan

### Day 1 — production foundation

- choose/confirm commercially usable production data source;
- create cloud application skeleton;
- create production database;
- define user, signal, lifecycle, performance and audit tables;
- expose read-only internal API for current/history/health;
- preserve local immutable forward ledger as the research source of truth.

Exit condition: cloud app deploys and can render a health page from production database.

### Day 2 — multi-market live signal plumbing

- keep the existing XAUUSD immutable forward collector untouched;
- activate separately fingerprinted USTEC and US30 forward collectors;
- normalize all three through the same internal Candle model;
- expose per-market evidence labels and active/no-active state;
- do not silently retune S02 for any market.

Exit condition: XAUUSD, USTEC and US30 can each produce deterministic live signal lifecycle records.

### Day 3 — user-facing MVP

- landing page;
- auth;
- active/no-active signal card;
- signal-history table;
- evidence/performance page;
- responsive mobile layout.

Exit condition: an invited user can sign in and understand exactly what the system is showing.

### Day 4 — alerts, disclosures and QA

- email or Telegram alert delivery;
- risk/disclosure copy;
- rate limiting and error handling;
- production logging;
- smoke tests;
- verify no Exness raw data leaks into the public surface;
- verify historical and forward results are labelled separately.

Exit condition: end-to-end signal -> database -> UI -> alert path passes.

### Day 5 — Early Access launch

Launch to an initial small cohort.

Recommended initial mode:

- free Early Access or waitlist-gated beta;
- three live-signal launch markets: XAU/USD, NASDAQ 100 / USTEC, DOW 30 / US30;
- no performance guarantee;
- transparent historical/forward evidence;
- feedback collection built into the product.

Do not wait for F3/100 trades to launch the application.

## Forward validation continues after launch

The existing S02/XAUUSD forward test continues unchanged.

- F1: 20 completed forward trades — execution audit;
- F2: 50 trades + 90 days — interim evidence review;
- F3: 100 trades + 180 days — first candidate-status decision.

These gates control claims about strategy validation, not whether the software is allowed to exist in beta.

## First-week product success criteria

Measure:

- sign-ups;
- activated users;
- percentage who understand the signal card;
- alert opt-in;
- return visits;
- qualitative trust in the verified record;
- willingness to pay / requested price;
- which fields users actually care about.

Do not optimize on vanity traffic.

## Monetization

Recommended sequence:

1. launch free/invite Early Access quickly;
2. collect first real usage and feedback;
3. introduce a simple paid founding tier as soon as the product demonstrates user value and payment flow is ready;
4. use revenue to fund any future paid data source rather than buying data before revenue;
5. keep pricing subscription-based.

## Decision

Launch velocity is now a first-class project objective.

Historical research will no longer block UI/product beta work. Strategy research and forward validation continue in parallel and constrain claims, not product-development speed.
