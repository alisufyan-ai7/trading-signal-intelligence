# AI-1 — Frozen AI-v1 architecture

_Status: FROZEN PRE-ACTIVATION SPECIFICATION — 2026-09-28_

## Objective

Build a genuinely AI-generated market-intelligence engine alongside the existing S02 control without contaminating the active S02 forward evidence.

AI-v1 is a **shadow inference system first**. It may generate BUY, SELL or NO_TRADE decisions, but it does not replace S02, modify an S02 ledger, connect a broker, place an order, or enable auto trading.

The first objective is not to prove that AI is profitable. It is to create a causal, reproducible, auditable AI inference pipeline that can later be evaluated against deterministic baselines.

## Product architecture

```text
MT5 / normalized market data
        |
        v
closed-candle feature snapshot
        |
        v
AI-v1 reasoning model
        |
        v
strict structured decision
        |
        v
deterministic publication guard
        |
        +----> rejected / no-trade inference ledger
        |
        v
shadow AI signal
        |
        v
immutable AI lifecycle ledger
        |
        v
outcome evaluation / AI Insights UI
```

The AI chooses market direction and bounded risk parameters. Deterministic code validates the output, computes executable price levels, applies cost/freshness/concurrency checks, and decides whether the proposal can become a shadow signal.

## First markets

Frozen initial shadow universe:

- XAUUSD
- USTEC
- US30

The AI model must **not** receive the S02 decision, S02 signal state, S02 historical performance, or S02 current position as an input feature. S02 is a benchmark/control, not an upstream feature.

## Decision cadence

AI-v1 is evaluated after each newly completed H1 bar when the market has a valid fresh data snapshot.

The scheduler may skip a closed bar only for a documented operational reason such as:

- market closed / no valid new H1 bar;
- stale source data;
- missing required features;
- inference provider unavailable.

Skipped cycles are recorded.

## Causal input boundary

Only information available at the inference timestamp may be used.

AI-v1 receives **derived features**, not a large raw candle dump.

Frozen feature families:

### Price / return state

- latest completed H1 close;
- H1 returns over 1, 4, 12 and 24 bars;
- H1 ATR(14);
- ATR percentile versus trailing 252 completed H1 bars;
- H1 EMA20 and EMA50 distance from price;
- H1 EMA20/EMA50 slope;
- H4 EMA20 and EMA50 distance / slope from completed H4 bars.

### Structure

- position within prior 20-H1 high/low range;
- distance to prior 20-H1 high;
- distance to prior 20-H1 low;
- distance to previous UTC-day high;
- distance to previous UTC-day low;
- recent true-range expansion ratio;
- tick-volume z-score versus prior 20 completed H1 bars.

### Momentum / regime

- RSI(14);
- 4h / 12h / 24h return-sign agreement;
- realized-volatility regime bucket;
- trend-regime bucket derived deterministically from H1/H4 EMA state.

### Execution context

- source symbol and canonical symbol;
- UTC inference timestamp;
- market session bucket;
- day of week / UTC hour;
- observed spread proxy;
- spread as a fraction of ATR;
- data-age seconds.

## Explicitly excluded from AI-v1.0

To keep the first test reproducible and isolate the value of the AI reasoning layer, AI-v1.0 does **not** use:

- news;
- social sentiment;
- analyst opinions;
- user positions or account balance;
- broker credentials;
- S02 outputs;
- previous AI-v1 PnL as an input;
- future/incomplete candles.

A separately versioned AI-v1.1 or AI-v2 may add external context only after its source, timestamping, licensing and causal-availability rules are frozen before testing.

## AI model role

AI-v1 uses a provider-neutral **reasoning-model adapter**.

The model receives:

1. the immutable system instruction / decision policy;
2. the deterministic feature snapshot;
3. the JSON decision schema.

The first activated provider/model identifier and inference parameters must be committed **before the first performance-bearing shadow inference**.

Until that model identifier is frozen, AI-v1 remains PRE-ACTIVATION.

The model is not asked to expose hidden chain-of-thought. It returns only the concise structured rationale fields defined by the contract.

## Frozen model decision contract

The machine-readable schema is committed separately at:

`config/ai_v1_decision_schema.json`

Decision values:

- `BUY`
- `SELL`
- `NO_TRADE`

For BUY/SELL, the model proposes:

- raw confidence score 0–100;
- stop distance in ATR units;
- TP1 in R;
- TP2 in R;
- regime label;
- concise rationale;
- supporting-factor tags;
- risk-factor tags.

The model does **not** calculate final executable price levels.

## Deterministic entry / level construction

For a publishable BUY/SELL proposal:

- entry policy: next eligible H1 open;
- stop distance: model-selected ATR multiple within the frozen allowed range;
- TP1: model-selected R multiple within range;
- TP2: model-selected R multiple within range;
- maximum holding period: 24 H1 bars;
- only one active AI-v1 shadow position per source symbol.

Executable price levels are calculated deterministically from the actual entry price and the frozen ATR/cost inputs.

This avoids relying on language-model arithmetic for trading levels while preserving an AI-generated directional/risk decision.

## Frozen deterministic publication guard

A BUY/SELL proposal becomes a shadow signal only if all of the following pass:

1. JSON schema valid;
2. source snapshot hash present and unchanged;
3. data age <= 300 seconds at processing;
4. market data/session eligible;
5. no active AI-v1 shadow position for that symbol;
6. stop ATR multiple within 1.00–3.00;
7. TP1 within 0.75–2.00R;
8. TP2 within 1.50–4.00R and TP2 > TP1;
9. estimated round-trip cost <= 0.15R of the proposed stop risk;
10. entry/stop/target arithmetic finite and directionally consistent;
11. signal created from the same completed-bar snapshot used by the AI.

A model confidence score is **not** a calibrated probability and is not a promotion criterion in v1.

The guard never turns BUY into SELL or SELL into BUY. It may only publish the proposal unchanged in direction, reject it, or record NO_TRADE.

Frozen guard values are recorded in:

`config/ai_v1_guardrails.json`

## Shadow trade lifecycle

For a published AI-v1 shadow signal:

- entry: next eligible H1 open;
- 50% of notional evaluated at TP1;
- remaining 50% evaluated at TP2;
- original stop remains for the residual position after TP1;
- no break-even stop move in v1;
- timeout: 24 completed H1 bars after entry;
- costs applied using the project's instrument-specific cost framework;
- ambiguous same-bar stop/target ordering must use a conservative deterministic rule documented in implementation before activation.

The exact lifecycle implementation and tests must be committed before activation.

## Immutable AI ledger

AI-v1 gets a **separate ledger** from S02.

Required record types:

- `ACTIVATION`
- `INFERENCE`
- `NO_TRADE`
- `REJECTED_INFERENCE`
- `SIGNAL`
- `PARTIAL_EXIT`
- `EXIT`
- `MISSED_INFERENCE`
- `ERROR`

Every inference record must carry or reference:

- protocol version;
- source symbol;
- inference timestamp;
- source-bar timestamp;
- feature snapshot hash;
- prompt/policy hash;
- model/provider identifier;
- model-parameter fingerprint;
- raw structured model response;
- normalized decision;
- guard result;
- previous ledger hash / record hash.

Existing S02 databases remain untouched.

## Confidence semantics

The raw 0–100 score is stored as `raw_confidence`.

Before calibration evidence exists, product wording must say **model confidence score**, not probability.

Calibration evaluation will compare score buckets to realized outcomes. A future calibrated probability must be separately versioned.

## Evaluation metrics

Evaluate AI-v1 at both the inference and signal levels.

### Operational

- attempted inference cycles;
- valid inference rate;
- schema failure rate;
- provider failure rate;
- NO_TRADE rate;
- publication-guard rejection rate;
- median inference latency;
- cost per valid inference.

### Signal quality

Per symbol and aggregate:

- completed shadow trades;
- net expectancy in R after costs;
- profit factor;
- win/loss rate;
- TP1 hit rate;
- TP2 hit rate;
- stop rate;
- timeout rate;
- maximum drawdown in R;
- average holding time.

### Confidence quality

- performance by raw-confidence bucket;
- Brier-style directional calibration only after a frozen binary outcome definition is committed;
- monotonicity check: higher confidence should not be assumed useful until observed.

### Benchmark comparison

Compare on overlapping calendar windows with:

- S02-v0.1 control;
- no-trade baseline;
- simple always-long / always-short descriptive baselines where meaningful.

Do not optimize AI-v1 based on early shadow outcomes.

## Predeclared review gates

These gates govern review, not public marketing claims.

### A1 — operational audit

First point where all are true:

- >=100 valid AI inferences;
- >=20 completed AI shadow trades.

Purpose: lifecycle/data/schema audit only. No alpha promotion/rejection based solely on A1.

### A2 — interim evidence

First point where all are true:

- >=500 valid AI inferences;
- >=50 completed shadow trades;
- >=60 calendar days after activation.

Purpose: interim model/economic evaluation. Favorable A2 does not authorize auto trading.

### A3 — first publishability decision

First point where all are true:

- >=1,000 valid AI inferences;
- >=100 completed shadow trades;
- >=120 calendar days after activation.

Purpose: first planned decision on whether AI-v1 may graduate from experimental/shadow status.

A model change before A3 requires a separately versioned activation; old and new evidence must not be pooled as if unchanged.

## Versioning rule

After activation, any change to any of the following creates a new version:

- feature definitions;
- prompt/policy text;
- decision schema;
- model/provider identifier;
- inference parameters;
- guard thresholds;
- entry/exit lifecycle;
- cost model;
- cadence;
- supported-market set when used for pooled claims.

Bug fixes that affect decisions also require a new version.

## Security / privacy boundary

AI-v1 receives no:

- account password;
- broker credential;
- API secret;
- user balance;
- personally identifying customer data.

Only derived market-state inputs are sent to the inference provider.

## AI-v1 activation checklist

Before the first performance-bearing inference:

1. implement deterministic feature builder;
2. implement provider-neutral inference adapter;
3. choose and commit exact provider/model ID and parameters;
4. freeze prompt/policy text;
5. implement and test decision-schema validation;
6. implement guardrail engine;
7. implement separate append-only AI ledger;
8. implement lifecycle evaluator;
9. create activation record with hashes/fingerprints;
10. verify S02 ledgers unchanged;
11. run smoke tests with trading/execution disabled.

Only then may the shadow scheduler start.
