# TradingTop authenticated teardown and product-gap synthesis — 2026-09-28

## Scope and provenance

This synthesis uses only:

- the current TradingTop Analysis chat;
- the private repository `alisufyan-ai7/trading-signal-intelligence`;
- the 34 authenticated TradingTop screenshots archived under `research/competitors/tradingtop/2026-09-27/`;
- the route-by-route findings recorded by the Work-mode research pass.

It does not use account-level memory, other chats/projects, other repositories, or unrelated connected-app data.

The Work-mode pass added 12 commits after the context-isolation checkpoint, including 34 screenshot captures, an authenticated capture index, a VIP/business-model analysis and updates to the public competitor audit / next actions.

## What TradingTop actually presents as a product

The authenticated UI is best understood as two related products rather than one monolithic signal engine.

### 1. AI Insights / manual signal product

The signed-in `/tgai` flow exposes multi-asset AI signal cards and narrative analysis.

Observed XAUUSD example:

- direction: Buy;
- inference time: 26 Sep 2026 00:19 Asia/Shanghai (UTC+8);
- analysis price: 4290.61;
- suggested entry: 4283.4;
- TP1: 4302.5;
- TP2: 4311.2;
- SL: 4267.5;
- confidence: 58.8%;
- qualitative strategy-analysis and risk text;
- optional email-reminder flow;
- links to Connect Account, AI Trading and View AI Logs.

The interface therefore sells more than a direction call: it packages timing, entry, two targets, stop, confidence, narrative reasoning and notification.

The aggregate AI Execution Log provides:

- symbol/timeframe;
- predicted direction;
- inference time;
- inference price;
- suggested entry;
- target 1;
- target 2;
- stop loss;
- outcome heatmap / rows;
- aggregate performance cards.

This creates a visible feedback loop from AI inference -> signal -> outcome -> history.

### 2. AI Trading model product

A separate Model Marketplace exposes named trading models with their own:

- overview;
- subscribers;
- balance/equity/deposit/withdrawal tiles;
- equity curve;
- open trades;
- trade history;
- per-model performance;
- Enable AI Trading action.

Observed models:

- T1 — Defensive Alpha;
- T2 — Precision Sniping, gold-specific;
- T3 — Forex Trend.

The model-trade history shows concrete order-like fields: symbol, order ID, source=AI, predicted direction, volume, entry, exit, open time and an AI Execution Logic detail control.

One captured T2 detail panel returned `no data`, so the UI label does not prove that a detailed explanation exists for every executed trade.

## Performance presentation — important reconciliation finding

TradingTop displays metrics at different scopes that must not be conflated.

Aggregate AI log, selected 30-day / short-term view:

- Inference Accuracy: 74.00%;
- Expected Return per Signal: +31.86;
- Realized Risk-Reward Ratio: 1.13;
- Total Pips Gained: +196,001.96;
- Signal Stability Score: 8.5;
- average signal duration: 9h.

Separate model pages, selected last-three-month view:

| Model | Trades | Realized PnL | Inference accuracy | Avg profit | Avg loss | Avg hold |
|---|---:|---:|---:|---:|---:|---:|
| T1 | 41 | +$115.66 | 56.1% | $33.77 | $36.73 | 18.2h |
| T2 | 53 | -$441.30 | 37.7% | $55.89 | $47.25 | 5.0h |
| T3 | 30 | +$143.50 | 70.0% | $14.42 | $17.70 | 11.6h |

The T2 result is particularly important: the gold-specific model is negative over the displayed three-month window despite the separate aggregate AI page showing a 74% headline accuracy figure.

These are site-displayed figures only. Costs, accounting basis, model capital assumptions and independent verification are not established by the captures.

## TradingTop business model

TradingTop combines five loops.

### A. Subscription revenue

Observed pricing:

| Tier | Price | Included TOP |
|---|---:|---:|
| Free Trial | $0 | 300 one-time |
| Access | $69/month | 5,000/month |
| Advanced | $199/quarter | 10,000/month |
| Pro | $399/year | 20,000/month |
| Elite | $1,599 lifetime | 50,000/month |

The plan cards also gate higher-value capabilities such as custom configuration, faster signal generation, analytics, AI strategies, faster execution, support/community and auto trading.

### B. Metered AI usage through TOP

TradingTop describes TOP as an AI compute unit.

Manual signal consumption:

- Gold / Bitcoin / indices: 100 TOP each;
- Forex / non-Bitcoin crypto / non-gold commodities / US stocks: 50 TOP each.

AI trading model consumption:

- T1: 200 TOP/day;
- T2: 200 TOP/day;
- no T3 cost was shown in the captured TOP table.

This means the subscription is not only feature access; it also supplies a recurring compute/usage allowance.

Illustrative allowance equivalence, before any other usage rules:

| Allocation | Gold/Bitcoin/index signals at 100 TOP | 50-TOP signals | 200-TOP model-days |
|---:|---:|---:|---:|
| 300 trial | 3 | 6 | 1.5 |
| 5,000 | 50 | 100 | 25 |
| 10,000 | 100 | 200 | 50 |
| 20,000 | 200 | 400 | 100 |
| 50,000 | 500 | 1,000 | 250 |

Fractional model-days may not be usable in practice; this table is only arithmetic on the displayed unit costs.

### C. Referral / affiliate distribution

The captured agency agreement displays:

- fewer than 10 paid users: 20% commission;
- 10–49: 30%;
- 50–99: 35%;
- 100+: 40%.

It also states five signal-access opportunities per referred registration, commission on net receipts after third-party platform fees, credit after a 30-day non-refund period, $100 minimum withdrawal and staff verification.

This is a substantial acquisition mechanism, not a minor referral coupon.

### D. Rewarded activation / broker funnel

TOP rewards displayed:

- new registration: 300 TOP, 7 days;
- phone bind: 50 permanent;
- referred registration + phone bind: 100;
- quarterly referral conversion: 1,990;
- annual referral conversion: 3,990;
- lifetime referral conversion: 9,990;
- complete account opening/transfer: 500;
- successfully bind auto-trading account: 1,000.

The broker-account and auto-trading rewards strongly incentivize movement from signal consumption toward connected execution. The screenshots do not establish whether TradingTop receives broker referral revenue, so that remains an inference/unknown.

### E. Retention

The product creates repeat usage through:

- per-symbol email-update switches;
- AI execution logs;
- model performance / equity curves;
- model open trades / trade history;
- recurring TOP allocations;
- compute consumption;
- model subscriptions / auto-trading connection.

## Functional funnel

The observed product funnel is approximately:

`free registration -> 300 TOP trial -> manual AI signal -> email reminder / AI log -> paid subscription -> recurring TOP -> model marketplace -> AI trading model -> broker/account connection -> retention through alerts + performance pages`

Parallel acquisition loop:

`existing user -> referral/agency link -> referred registration -> TOP reward -> paid conversion -> 20-40% commission`

## What is known vs unknown about their AI

The UI clearly presents AI inference and AI-sourced model trades. It also produces narrative reasoning text.

However, the authenticated pages do **not** disclose enough to determine:

- the underlying model family;
- training dataset;
- whether manual signals and T1/T2/T3 share one model or separate models;
- whether an LLM, time-series model, rules, or ensemble generates direction/levels;
- how confidence is calibrated;
- whether model execution logic is generated before or after the decision;
- transaction-cost treatment in the displayed performance.

Therefore we can reproduce the *functional product contract* without claiming to know or copy TradingTop's hidden model internals.

## Where our product stands

### What we already have that maps well

| Capability | Our current state |
|---|---|
| live market collection | working through Windows MT5 / Exness |
| normalized multi-market data | working |
| multi-market scanner | working |
| concrete entry / stop / target | working |
| cloud publishing | working |
| immutable signal ledger | working and stronger provenance than TradingTop visibly exposes |
| historical evidence | working with explicit OOS separation |
| forward lifecycle | working |
| public signal history | working |
| losses shown | yes |
| public research-beta UI | live |
| data-rights path | G2 passed per owner-confirmed Exness permission |

### Core product gaps relative to the observed TradingTop experience

| Capability | TradingTop observed | Our current state |
|---|---|---|
| AI-first signal generation | presented as core | **missing**; S02 rules generate signals |
| AI reasoning narrative | present | missing |
| confidence score | present | missing |
| TP1 + TP2 | present | one target |
| explicit inference time / analysis price | present | issue time/entry exist but not framed as AI inference |
| broad manual AI signal universe | present | only 3 live-signal launch markets |
| aggregate AI log UX | present | immutable ledger exists, but no AI inference log |
| named AI model marketplace | present | missing |
| per-model PnL/equity/open trades | present | strategy evidence exists, but not packaged as a model marketplace |
| auto-trading broker connection | present/gated | intentionally absent |
| user accounts | present | absent in current public beta |
| subscription billing | present | absent |
| usage credits | TOP present | absent |
| per-symbol alerts | present | Telegram implementation exists but not user-facing/configured |
| referral program | present | absent |
| affiliate commission | present | absent |
| acquisition rewards | present | absent |
| durable customer database | present in some form | not yet established for our beta |

## Important advantage we should preserve

Our project should **not** discard its strongest differentiation while becoming AI-first.

TradingTop's captured UI demonstrates why scope discipline matters: the aggregate AI log headline and the T2 model page can show very different performance pictures.

Our product can combine:

`AI-first user experience + deterministic risk controls + immutable per-model provenance + clearly scoped after-cost evidence`

That is stronger than either:

- a rule-only dashboard with no AI product experience; or
- an AI-marketed product whose aggregate headline can obscure a weak individual model period.

## Recommended product architecture

### Layer 1 — AI Insights

Create a user-facing AI signal product with a strict structured output:

- symbol;
- horizon;
- inference timestamp;
- analysis price;
- decision: BUY / SELL / NO_TRADE;
- entry zone;
- stop;
- TP1;
- TP2;
- confidence;
- validity/expiry;
- market regime;
- concise reasoning;
- risk / invalidation notes;
- model version;
- immutable input/output hashes.

Inputs should combine deterministic market features with optional news/sentiment/context. Do not ask an LLM to infer directly from raw candles alone.

### Layer 2 — deterministic publication guard

Before an AI output becomes public:

- stale-data check;
- spread/cost check;
- minimum reward-risk check;
- volatility / stop-distance check;
- conflicting-position check;
- output-schema validation;
- max-age / expiry check.

The AI proposes; deterministic code decides whether the proposal is publishable.

### Layer 3 — immutable AI inference ledger

Extend the existing ledger rather than replacing it.

Store:

- input feature-state hash;
- model/prompt/version identifier;
- raw structured AI response;
- normalized published signal;
- publication decision;
- lifecycle events;
- outcome;
- after-cost result.

This creates an auditable AI track record.

### Layer 4 — strategy/model catalog

Keep S02 as a benchmark/control, not the public centerpiece.

Introduce separately versioned AI models later, for example:

- AI-XAU-v1;
- AI-MultiAsset-v1;
- future defensive / trend / mean-reversion models only after their own evidence exists.

Each model page should show its own evidence window, sample size, costs, PnL/expectancy and recent losses.

### Layer 5 — accounts, subscription and usage metering

Only after AI Insights works end-to-end:

- user accounts;
- free inference allowance;
- monthly/quarterly/annual plans;
- included AI credits;
- per-symbol alert preferences;
- durable usage ledger.

Do not copy TradingTop's TOP name or exact tiers. Use an original product identity and transparent compute-credit semantics.

Avoid a lifetime plan initially: AI inference and notification costs recur indefinitely, so lifetime pricing creates long-tail cost risk before unit economics are known.

### Layer 6 — referrals

After paid conversion is demonstrated:

- referral credits first;
- cash/percentage affiliate commissions only after fraud, attribution, refund and payout operations exist;
- disclose incentives clearly.

### Layer 7 — broker-connected execution

Last, not first.

Automated execution should require:

- a validated AI model;
- deterministic risk/execution layer;
- execution-specific forward evidence;
- explicit broker permissions/integration;
- user authorization;
- kill switch / reconciliation / incident controls.

## Proposed execution sequence

### Milestone AI-0 — product correction / naming

Before external user acquisition:

1. choose a product name distinct from TradingTop;
2. remove `TradingTop Early Access` naming from our UI/service;
3. preserve the current beta as the evidence/control surface.

### Milestone AI-1 — AI signal contract + shadow engine

Build a new AI pipeline **alongside** S02.

Initial markets: XAUUSD, USTEC, US30.

Run in shadow mode first:

- scheduled derived-feature snapshot;
- AI structured inference;
- deterministic guard;
- append-only AI inference ledger;
- no alteration to S02's frozen ledgers.

### Milestone AI-2 — AI Insights UI

Add:

- AI signal card;
- inference time;
- analysis price;
- entry / TP1 / TP2 / SL;
- confidence;
- reasoning;
- expiry;
- AI log;
- explicit NO_TRADE states.

Keep historical / forward / AI-model evidence visibly separated.

### Milestone AI-3 — evaluation gate

Compare AI-v1 against:

- no-trade baseline;
- S02 control;
- simple deterministic baselines.

Evaluate after costs, by symbol, regime and time split.

Do not promote based on aggregate accuracy alone.

### Milestone AI-4 — accounts + credits + alerts

Once AI-v1 is usable:

- durable account database;
- free AI credits;
- paid plan scaffolding;
- per-symbol alerts;
- usage ledger;
- basic privacy / retention policy.

### Milestone AI-5 — model catalog

Expose multiple **validated** model versions as a model catalog only when there are genuinely distinct strategies/models with separate evidence.

### Milestone AI-6 — referrals / growth loop

Add referral credits, then potentially cash affiliate economics after first paid conversion data.

### Milestone AI-7 — auto trading

Consider broker-connected execution only after AI models and the execution layer have their own forward evidence.

## Immediate recommendation

The previous next-action ordering — feedback form first — is no longer the highest-value product move if the intended product is TradingTop-like AI intelligence.

The correct immediate engineering focus is:

1. rename away from the competitor brand;
2. freeze an AI-v1 signal schema and evaluation protocol;
3. implement the AI-v1 shadow inference pipeline on the existing three launch markets;
4. add immutable AI inference logging;
5. then expose AI Insights in the UI.

Do **not** modify or stop the active S02 forward tests. They become the benchmark/control against which the new AI engine is measured.

## Owner decisions required before implementation

1. Approve the pivot from “rule-based signal product with AI explanation later” to “AI-first signal product with deterministic guardrails and verified evidence.”
2. Approve keeping S02 unchanged as a benchmark/control rather than removing it.
3. Choose whether the first AI engine should be:
   - LLM reasoning over engineered market features;
   - a trained quantitative/time-series model plus LLM explanation; or
   - an ensemble of both.
4. Choose an original product/brand name before external launch.
