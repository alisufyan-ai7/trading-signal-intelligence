# EXP-2026-009 — S02 Structure Breakout v0.1 Baseline

**Status:** BASELINE COMPLETE — XAU ROBUSTNESS WARRANTED; NOT CANDIDATE  
**Created:** 2026-09-17  
**First results recorded:** 2026-09-17

## Objective

Evaluate the first untouched baseline for S02 Structure Breakout v0.1 using the predeclared four-market universe and frozen local research datasets. The rules and first universe were frozen before any S02 outcome was viewed.

## Predeclared universe

1. EUR/USD
2. GBP/USD
3. USD/JPY
4. XAU/USD

## Frozen S02 v0.1 rules

Authoritative specification: `strategies/S02-structure-breakout/v0.1.md`.

- H1 20-bar prior structure high/low
- close beyond structure by >0.10 ATR14
- gap-open exclusion
- true range >=1.25x prior-20 median
- tick volume >=1.10x prior-20 median
- H4 close/EMA50 regime with 3-H4-bar EMA slope agreement
- next-H1-open entry
- 1.75 ATR stop
- 2.5R target
- 72-H1-bar timeout
- same-bar ambiguity resolves to stop first
- 1.25x known signal-bar spread cost proxy
- one open position per instrument

Fixed splits:

- development: before 2023-01-01 UTC
- validation: 2023-01-01 through 2024-12-31 UTC
- final test: 2025-01-01 onward

These calendar periods were already visible through prior S01 work, but S02 parameters were frozen before S02 outcomes. A candidate still requires robustness and new forward evidence.

## Implementation integrity

- engine: `src/trading_signal_intelligence/backtesting/s02.py`
- runner: `scripts/run_s02_backtest.py`
- audit: `scripts/audit_s02_sample.py`

Candle-level sample audits after all four baseline runs:

- EUR/USD: 10/10 sampled trades passed
- XAU/USD: 10/10 sampled trades passed

The audits checked H4 availability, exact prior-20 structure, breakout margin, gap exclusion, candle direction, TR expansion, volume expansion, next-bar entry, stop math and target math.

Independent ledger checks across all four CSVs found:

- signal before entry;
- entry before/equal exit;
- no overlapping positions;
- holding periods within 1–72 bars;
- stop trades equal -1R gross within floating-point tolerance;
- target trades equal +2.5R gross within floating-point tolerance;
- net-R cost arithmetic is internally consistent.

## First baseline results

| Instrument | Trades | Development net R/trade | Validation net R/trade | Final-test net R/trade | Overall PF |
|---|---:|---:|---:|---:|---:|
| EUR/USD | 1,008 | +0.0114 | +0.0459 | -0.0127 | 1.0215 |
| GBP/USD | 1,021 | +0.0414 | -0.1858 | +0.0444 | 0.9776 |
| USD/JPY | 1,019 | +0.1260 | +0.1764 | -0.1631 | 1.1195 |
| XAU/USD | 1,033 | -0.0337 | +0.0986 | +0.2323 | 1.0813 |

### EUR/USD

- validation: +0.0459R/trade, PF 1.0650
- final: -0.0127R/trade, PF 0.9825
- directional validation long/short: +0.0320 / +0.0614
- directional final long/short: +0.1372 / -0.1749

Interpretation: weak/mixed; no stable OOS edge.

### GBP/USD

- validation: -0.1858R/trade, PF 0.7608
- final: +0.0444R/trade, PF 1.0642
- directional validation long/short: -0.0845 / -0.3013
- directional final long/short: +0.0995 / -0.0147

Interpretation: major regime instability.

### USD/JPY

- validation: +0.1764R/trade, PF 1.2708
- final: -0.1631R/trade, PF 0.7854
- directional validation long/short: +0.2332 / +0.0833
- directional final long/short: -0.0998 / -0.2613

Interpretation: strong 2023–2024 behavior failed to persist into 2025–2026.

### XAU/USD

- development: -0.0337R/trade, PF 0.9537
- validation: +0.0986R/trade, PF 1.1443, max DD -19.54R
- final: +0.2323R/trade, PF 1.3595, max DD -17.51R

Observed OOS annual net expectancy:

- 2023: +0.1306R/trade
- 2024: +0.0667R/trade
- 2025: +0.1973R/trade
- 2026 to data cutoff: +0.2873R/trade

## Directional finding — diagnostic only

XAU OOS performance is carried by longs:

- development long +0.0255; short -0.1100 R/trade
- validation long +0.2196; short -0.0911
- final long +0.4244; short -0.0996

This was learned after the baseline. **Do not retroactively redefine v0.1 as long-only XAU.** A long-only rule is a new hypothesis requiring new evidence.

## Cost-stress diagnostic from frozen XAU ledger

Validation expectancy:

- 1.0x cost: +0.1022R/trade
- 1.25x baseline: +0.0986
- 1.5x: +0.0951
- 2.0x: +0.0880
- 3.0x: +0.0737

Final-test expectancy:

- 1.0x cost: +0.2338R/trade
- 1.25x baseline: +0.2323
- 1.5x: +0.2309
- 2.0x: +0.2279
- 3.0x: +0.2220

XAU is not fragile to spread-cost scaling under the current bar-level model. This does not substitute for tick/slippage validation.

## Current interpretation

**S02 v0.1 is not yet a candidate, but robustness research is warranted.**

1. EUR/USD is mildly positive in validation and slightly negative in final test.
2. GBP/USD reverses from strongly negative validation to mildly positive final test.
3. USD/JPY reverses from strong validation to clearly negative final test.
4. XAU/USD is positive in both OOS splits and all four observed OOS calendar years.
5. XAU remains positive under substantial spread-cost stress.
6. XAU development is negative and OOS strength is long-driven, preventing promotion.
7. Implementation audits are clean.

## Next actions

Without changing v0.1 alpha semantics:

1. run the frozen one-at-a-time parameter-neighborhood sensitivity across all four original markets;
2. run rolling/walk-forward stability summaries;
3. keep long/short decomposition diagnostic only;
4. broaden to additional predeclared markets only after the sensitivity protocol is frozen;
5. require a separately versioned hypothesis for any long-only rule;
6. do not move to immutable forward-test candidate status until robustness work is complete.

The robustness runner is `scripts/run_s02_robustness.py`.

This file supersedes the duplicate-ID file formerly named `EXP-2026-006-s02-structure-breakout-baseline.md`.
