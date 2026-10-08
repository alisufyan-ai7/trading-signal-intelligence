# AI-v1.3 crypto expansion compatibility plan v0.1

_Status: DESIGN / PREACTIVATION / READINESS NOT AUTHORIZED — 2026-10-08_

Tracker: Issue #40

Canonical preregistration:

`research/experiments/EXP-2026-017-ai-v1.3-crypto-expansion-preregistration.md`

## Objective

Prepare BTCUSDT / ETHUSDT / SOLUSDT for a separately versioned crypto shadow
lineage without modifying active AI-v1.1, AI-v1.2.1 or S02.

This document defines what must be proven before an implementation package can
be considered activation-ready.

## Source architecture

### Primary

`binance_spot`

Required primary symbols:

- BTCUSDT -> BTC/USDT
- ETHUSDT -> ETH/USDT
- SOLUSDT -> SOL/USDT

Primary H1/H4 OHLCV comes from Binance Spot klines.

### Secondary / comparison-only

Exness MT5 may be used only where an explicitly comparable instrument exists and
only for non-gating read-only sanity checks.

Current repository support:

- BTCUSDT CFD can be compared with Binance BTCUSDT Spot;
- ETHUSD is not ETHUSDT;
- SOLUSD is not SOLUSDT.

Do not map USD-quoted CFDs into USDT canonical identities.

## Canonical registry change

The authoritative instrument registry must contain dedicated canonical
ETH/USDT and SOL/USDT instruments with Binance Spot as primary.

Existing ETH/USD and SOL/USD Exness entries remain separate instruments.

## Compatibility classes

### Reusable without semantic change

The following AI feature formulas are intended to remain numerically identical:

- H1 returns;
- Wilder ATR;
- ATR percentile;
- H1/H4 EMA state/slopes;
- RSI;
- prior-20 structure;
- previous UTC-day structure;
- true-range expansion;
- return-sign agreement;
- realized-volatility percentile buckets;
- deterministic trend regime;
- UTC hour/day-of-week.

The compatibility verifier must eventually prove formula identity mechanically
rather than relying only on documentation.

### Reusable with explicit source-semantic annotation

`volume_z_20`

Formula remains the same z-score, but the source observation changes from MT5
tick volume to Binance base-asset volume.

This requires:

- crypto feature-schema versioning;
- explicit `volume_kind=base_asset_volume` or equivalent immutable metadata;
- no claim that values are comparable in absolute scale with MT5 tick volume.

### Reusable only as descriptive metadata

ASIA / LONDON / NEW_YORK / LATE UTC buckets.

For crypto these remain fixed UTC labels only and must not be presented as
exchange-session-open claims.

### Not reusable unchanged

Spread/execution-cost context.

Current AI-v1 requires finite completed-bar spread.

Current Binance Spot kline adapter provides no spread.

A crypto-specific execution-context path is mandatory.

## Prospective top-of-book design

Implementation must add a read-only Binance Spot best-bid/best-ask observation
for each market at the live decision point.

Minimum prospective record:

- source = binance_spot;
- source symbol;
- observed_at_utc;
- best_bid;
- best_ask;
- spread_price = best_ask - best_bid;
- midpoint;
- data age / request timing metadata as required for deterministic validation.

Rules:

- best ask must be >= best bid;
- spread must be finite and non-negative;
- no zero substitution when endpoint/read fails;
- no reconstruction from OHLC;
- no cross-source substitution;
- no post-hoc repair of a missed live cost observation.

The exact endpoint/request implementation must be bound into the future
activation artifact.

## All-in cost model design

Before activation, freeze a versioned crypto research-cost profile.

At minimum it must define:

- fee-rate source;
- fee rate per side;
- whether the rate is symbol-independent;
- spread treatment;
- slippage buffer;
- entry/exit cost allocation;
- all-in round-trip cost in price units;
- conversion to R;
- maximum acceptable round-trip cost-R guard.

The current design intentionally does not invent numeric fee/slippage values.

The future profile should expose a deterministic function conceptually equivalent
to:

`all_in_cost = spread_component + fee_component + slippage_component`

The exact arithmetic, price reference and one-way/two-way treatment must be
frozen before the first provider inference.

## Feature snapshot timing

Working scheduler target:

UTC minute 04 after each completed H1 bar.

The runtime must:

1. synchronize/read all three completed H1/H4 states;
2. capture prospective execution context;
3. construct/freeze all three crypto feature snapshots;
4. only then begin provider inference calls.

This creates one batch decision timestamp and avoids later markets receiving a
newer snapshot merely because earlier provider calls were slower.

Working maximum data age remains 300 seconds.

If read-only readiness cannot satisfy this deterministically, fix scheduling or
batching before activation. Do not relax the threshold after performance
evidence.

## Historical compatibility research

Historical Binance Spot candles may be used before activation to prove:

- pagination correctness;
- closed-bar handling;
- chronological ordering;
- duplicate detection;
- missing-interval behavior;
- weekend continuity;
- H1/H4 feature-construction stability;
- deterministic feature hashes.

Historical observations are research inputs only.

They may not be written into future prospective crypto AI ledgers as live
inferences/signals/outcomes.

## Readiness probe specification

A future owner-approved read-only readiness probe must, for all three markets:

1. require a clean exact Git commit;
2. prove no crypto activation anchor exists;
3. prove no planned crypto ledger exists;
4. hash active AI-v1.1 / AI-v1.2.1 / S02 ledgers before the probe;
5. perform only public Binance reads;
6. retrieve sufficient H1/H4 completed bars;
7. prove latest completed H1 freshness <=300 seconds;
8. build the crypto feature snapshot without provider calls;
9. capture finite top-of-book bid/ask context;
10. verify all-in cost inputs once numeric cost policy is frozen;
11. prove weekend behavior when a natural weekend observation is available;
12. re-hash all existing active ledgers and require byte identity;
13. reconfirm no crypto ledger/anchor appeared;
14. report provider_call_made=false;
15. report scheduler_changed=false;
16. report broker_execution_enabled=false.

A readiness failure remains evidence and must not trigger silent symbol
replacement.

## Offline implementation requirements

Before any live readiness approval is requested, the repository package should
contain:

- crypto source/config validator;
- crypto feature-schema profile;
- Binance top-of-book read-only adapter;
- deterministic execution-cost module;
- crypto preactivation verifier;
- crypto readiness probe;
- crypto ledger/runtime module;
- activation schema/builder/executor;
- runtime verifier;
- observability/gate-report module;
- task runner/installer in non-installed state;
- focused tests;
- full regression pass.

Implementation files may be prepared on an isolated branch without activating
them.

## Isolation requirements

The future implementation must mechanically reject:

- any AI-v1.1 database path;
- any AI-v1.2/AI-v1.2.1 database path;
- any S02 database path;
- any non-Binance primary source for crypto;
- any gate-count carry-forward;
- any calendar carry-forward;
- any pre-activation performance record;
- public signal exposure;
- broker execution.

## Current blockers

The design is not activation-ready until all of these are closed prospectively:

1. canonical ETHUSDT/SOLUSDT registry mappings;
2. crypto feature schema;
3. top-of-book adapter;
4. numeric fee/slippage/all-in cost policy;
5. cost guard semantics;
6. offline compatibility tests;
7. exact implementation package;
8. owner-approved live read-only readiness;
9. activation preview/anchor package.

## Safety boundary

This compatibility plan authorizes no live call or production mutation.

It is repository-side design only.
