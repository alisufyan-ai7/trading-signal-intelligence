# Research Plan

_Last updated: 2026-09-16_

## Phase 0A — Data proof

Objective: prove that our source adapters can create reproducible, source-tagged normalized market data.

### MT5 tasks

- Connect Python to a local Windows MT5 terminal.
- Capture terminal/account metadata without persisting secrets.
- Enumerate all symbols and export instrument metadata.
- Discover actual Exness demo symbol names for the initial universe.
- Pull representative historical bars across M1, M15, H1, H4 and D1.
- Pull a small tick sample.
- Confirm UTC handling.
- Measure history depth and gap rates.
- Record spread/tick-volume behavior by asset class.

### Binance tasks

- Fetch exchange metadata.
- Backfill BTCUSDT, ETHUSDT and SOLUSDT bars.
- Subscribe to a live market stream.
- Normalize into the same canonical schema.
- Add reconnect/rate-limit handling.

### Acceptance criteria

- deterministic normalized schema
- no credentials in source control
- source and source symbol preserved
- duplicate/gap/staleness checks
- clear handling for incomplete candles

## Phase 0B — Backtest framework

Objective: build a research engine that makes it easy to reject weak hypotheses.

Required features:

- no look-ahead access
- configurable spread/commission/slippage assumptions
- entry/exit semantics documented explicitly
- position sizing separated from alpha logic
- deterministic runs with config hashes
- trade ledger output
- equity/R-multiple curves
- in-sample vs out-of-sample splits
- walk-forward evaluation
- parameter sensitivity checks
- per-symbol/per-regime results

Metrics should include at least:

- number of trades
- hit rate (never alone)
- average win/loss in R
- expectancy in R
- profit factor
- max drawdown in R
- MFE / MAE
- exposure/time in market
- results by year/market/regime

## Phase 1 — Strategy hypotheses

Start with simple interpretable families before ML-heavy approaches:

- S01 Trend Pullback
- S02 Structure Breakout
- S03 Momentum Continuation
- S04 Mean Reversion
- S05 Volatility Expansion

Each strategy gets a written specification before code/backtest tuning. Parameter search should be deliberately constrained.

Promotion states:

`IDEA -> RESEARCH -> CANDIDATE -> FORWARD_TEST -> ACCEPTED`

Failure states:

`REJECTED` or `PAUSED`

## Phase 2 — Signal quality model

Once multiple candidates exist, create a score based on measurable factors rather than arbitrary AI confidence.

Potential components:

- trend / timeframe alignment
- structure quality
- momentum
- volatility regime
- spread / execution quality
- reward-to-risk
- distance to invalidation/major levels
- event risk (only when we have an appropriate data source)

Calibrate score buckets against out-of-sample/forward outcomes. A score is useful only if higher buckets demonstrate meaningfully different outcome distributions.

## Phase 3 — Immutable forward test

Before paid launch:

- create signals exactly as production would
- timestamp and version every signal
- persist strategy/config/data-source versions
- never edit original entry/stop/target after issuance
- append lifecycle events separately
- calculate outcome, MFE, MAE and achieved R automatically

Run long enough to gather an informative sample across different regimes. Do not turn a small lucky streak into a marketing claim.

## Phase 4 — Customer-value validation

Test whether the combination of verification + explanation is valued before building an expensive full product.

Prototype experience:

- active signal feed
- signal detail / explanation
- historical transparent ledger
- strategy/performance pages
- Telegram/email alerts
- user-controlled market/score/timeframe filters

Research questions:

- Does transparent loss history increase or decrease conversion?
- Do users care more about fewer high-quality signals or high frequency?
- Which explanation fields change decisions/retention?
- What is the acceptable latency for each timeframe?
- Which asset groups drive actual usage?
- Are users willing to pay for verification vs generic signal channels?

## Phase 5 — SaaS build

Only after evidence supports the product thesis:

- Next.js application
- Postgres/Supabase-class datastore
- authentication/billing
- live signal API
- alert worker
- AI explanation service
- performance/verification pages
- observability

Auto-execution remains a later, separately reviewed phase.
