# Five-Day Early Access Launch Plan

**Created:** 2026-09-21  
**Target:** Public/invite Early Access Beta within 3–5 days  
**Constraint:** Product launch is separate from G3 strategy validation. S02/XAUUSD remains an active forward-tested research strategy and must not be marketed as proven.

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

Exness remains an internal R&D / forward-validation source unless separate written commercial permission exists.

For external production data, use either:

1. a provider/account with explicit commercial/derived-data rights; or
2. documented written permission from the source owner.

Fast candidate: Twelve Data business service for XAU/forex/commodities, subject to selecting the subscription/add-on that explicitly covers our client-facing derived-signal use.

Do not expose raw Exness quotes/bars or Exness-derived public signals under the ordinary retail Client Agreement.

## MVP scope

### Must ship

1. Landing page
   - concise value proposition;
   - research-beta label;
   - risk disclosure;
   - sign-up / waitlist.

2. User authentication.

3. XAU/USD signal dashboard
   - current state: active setup or "no active setup";
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

### Day 2 — production market-data adapter + signal parity

- implement XAU/USD production-data adapter;
- normalize into existing Candle model;
- compare recent H1/H4 candles with the Exness research feed;
- run unchanged S02 v0.1 on the production feed;
- document any signal/bar divergence;
- do not silently retune S02 for the new source.

Exit condition: source parity is understood and the production scanner can run deterministically.

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
- one primary market: XAU/USD;
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

1. launch free/invite Early Access;
2. collect 20–50 real user interviews/usage sessions;
3. add a simple paid founding tier only after commercial-data and applicable financial-regulatory positioning are confirmed;
4. keep pricing subscription-based.

## Decision

Launch velocity is now a first-class project objective.

Historical research will no longer block UI/product beta work. Strategy research and forward validation continue in parallel and constrain claims, not product-development speed.
