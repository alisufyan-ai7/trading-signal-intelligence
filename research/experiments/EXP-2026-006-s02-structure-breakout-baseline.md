# EXP-2026-006 — S02 Structure Breakout v0.1 Baseline

**Status:** BASELINE COMPLETE — XAU ROBUSTNESS WARRANTED; NOT CANDIDATE  
**Created:** 2026-09-17  
**First results recorded:** 2026-09-17

## Objective

Evaluate the first untouched baseline for S02 Structure Breakout v0.1 using the predeclared four-market universe and frozen local research datasets.

The rules and first universe were frozen before any S02 outcome was viewed. No alpha parameter was changed between markets.

## Predeclared universe

1. EUR/USD
2. GBP/USD
3. USD/JPY
4. XAU/USD

## Frozen S02 v0.1 rules

Authoritative specification: `strategies/S02-structure-breakout/v0.1.md`.

Summary:

- H1 20-bar prior structure high/low;
- close must break structure by >0.10 ATR14;
- exclude bars that open already beyond the relevant structure;
- signal true range >=1.25x prior-20 median true range;
- signal tick volume >=1.10x prior-20 median tick volume;
- H4 close/EMA50 regime with 3-H4-bar EMA slope agreement;
- closed-candle signal, next-H1-open entry;
- 1.75 ATR initial stop;
- 2.5R fixed target;
- 72-H1-bar timeout;
- same-bar stop/target ambiguity resolves to stop first;
- baseline cost proxy = 1.25x known signal-bar spread price;
- one open position per instrument.

## Fixed temporal splits

- development: before 2023-01-01 UTC;
- validation: 2023-01-01 through 2024-12-31 UTC;
- final test: 2025-01-01 onward.

These calendar periods had already been viewed during S01 research, so they are not globally pristine. S02 itself was frozen before its own outcomes were known. Any eventual candidate still requires robustness and genuinely new forward evidence.

## Implementation integrity

Implementation:

- `src/trading_signal_intelligence/backtesting/s02.py`
- `scripts/run_s02_backtest.py`
- `scripts/audit_s02_sample.py`

Candle-level sample audits were run on EUR/USD and XAU/USD after all four baseline runs.

- EUR/USD: 10 sampled trades, `all_sample_assertions_pass = true`
- XAU/USD: 10 sampled trades, `all_sample_assertions_pass = true`

Every sampled trade passed the implemented checks for:

- H4 regime availability by H1 signal close;
- exact prior-20 structure levels;
- breakout margin;
- gap-open exclusion;
- signal candle direction;
- true-range expansion;
- tick-volume expansion;
- next stored H1 bar entry;
- 1.75ATR stop math;
- 2.5R target math.

Independent ledger checks across all four generated CSVs also found:

- every signal precedes entry;
- entry precedes or equals exit;
- no overlapping positions;
- holding periods remain within 1–72 bars;
- stop trades are -1R gross within floating-point tolerance;
- target trades are +2.5R gross within floating-point tolerance;
- reported net R matches gross R minus the stored cost model.

No current implementation-integrity finding explains the differences between markets.

## First baseline results

| Instrument | Trades | Development net R/trade | Validation net R/trade | Final-test net R/trade | Overall PF |
|---|---:|---:|---:|---:|---:|
| EUR/USD | 1,008 | +0.0114 | +0.0459 | -0.0127 | 1.0215 |
| GBP/USD | 1,021 | +0.0414 | -0.1858 | +0.0444 | 0.9776 |
| USD/JPY | 1,019 | +0.1260 | +0.1764 | -0.1631 | 1.1195 |
| XAU/USD | 1,033 | -0.0337 | +0.0986 | +0.2323 | 1.0813 |

### EUR/USD

- validation: 254 trades, +0.0459R/trade, PF 1.0650
- final test: 202 trades, -0.0127R/trade, PF 0.9825
- interpretation: weak/mixed; no stable OOS edge demonstrated.

Directional OOS diagnostic:

- validation long +0.0320R/trade; short +0.0614R/trade
- final long +0.1372R/trade; short -0.1749R/trade

### GBP/USD

- validation: 261 trades, -0.1858R/trade, PF 0.7608
- final test: 207 trades, +0.0444R/trade, PF 1.0642
- interpretation: major regime instability; validation failure is too large to treat the final period as robust evidence.

Directional OOS diagnostic:

- validation long -0.0845R/trade; short -0.3013R/trade
- final long +0.0995R/trade; short -0.0147R/trade

### USD/JPY

- validation: 256 trades, +0.1764R/trade, PF 1.2708
- final test: 199 trades, -0.1631R/trade, PF 0.7854
- interpretation: strong 2023–2024 behavior failed to persist into 2025–2026.

Directional OOS diagnostic:

- validation long +0.2332R/trade; short +0.0833R/trade
- final long -0.0998R/trade; short -0.2613R/trade

### XAU/USD

- development: 550 trades, -0.0337R/trade, PF 0.9537
- validation: 262 trades, +0.0986R/trade, PF 1.1443
- final test: 221 trades, +0.2323R/trade, PF 1.3595
- validation max drawdown: -19.54R
- final-test max drawdown: -17.51R

Annual OOS net expectancy is positive in each observed OOS calendar year:

- 2023: +0.1306R/trade
- 2024: +0.0667R/trade
- 2025: +0.1973R/trade
- 2026 through the data cutoff: +0.2873R/trade

This is the strongest S02 evidence in the predeclared universe. It is still not a candidate because development was negative, the positive OOS result is market-specific, and the directional decomposition was learned only after viewing the baseline.

## Directional finding — diagnostic only

XAU/USD OOS performance is carried by longs:

- development long: +0.0255R/trade; short: -0.1100R/trade
- validation long: +0.2196R/trade; short: -0.0911R/trade
- final test long: +0.4244R/trade; short: -0.0996R/trade

This finding is post-result information. **Do not retroactively redefine v0.1 as XAU-long-only.** A long-only rule would be a new strategy version/hypothesis and would require new evidence.

## Cost-stress diagnostic from the frozen ledgers

The stored baseline uses a 1.25x signal-spread proxy. Repricing the existing trades without changing signals/exits gives the following XAU/USD results:

### Validation

- 1.0x spread cost: +0.1022R/trade
- 1.25x baseline: +0.0986R/trade
- 1.5x: +0.0951R/trade
- 2.0x: +0.0880R/trade
- 3.0x: +0.0737R/trade

### Final test

- 1.0x spread cost: +0.2338R/trade
- 1.25x baseline: +0.2323R/trade
- 1.5x: +0.2309R/trade
- 2.0x: +0.2279R/trade
- 3.0x: +0.2220R/trade

The XAU baseline is therefore not fragile to reasonable spread-cost scaling under this bar-level cost model. This does not substitute for slippage/tick-level execution validation.

## Current interpretation

**S02 v0.1 is not yet a candidate, but it warrants robustness research.**

Evidence:

1. EUR/USD is only mildly positive in validation and slightly negative in the final test.
2. GBP/USD reverses from strongly negative validation to mildly positive final-test behavior.
3. USD/JPY reverses from strong validation to clearly negative final-test behavior.
4. XAU/USD is positive in both validation and final test, with four consecutive positive observed OOS calendar years.
5. XAU/USD remains positive under substantial spread-cost stress.
6. XAU development is negative and OOS gains are concentrated in the long side; those facts prevent promotion from the first baseline.
7. Candle-level and ledger audits pass, so robustness work is scientifically justified rather than an attempt to repair a known software defect.

## Next actions

Without changing v0.1 alpha semantics:

1. run a predeclared one-at-a-time parameter-neighborhood sensitivity test across all four original markets;
2. run rolling/walk-forward stability summaries;
3. preserve XAU long/short decomposition as a diagnostic only;
4. broaden to additional predeclared non-FX markets only after the sensitivity protocol is frozen;
5. do not create a long-only XAU version unless it is explicitly versioned as a new hypothesis with genuinely new validation requirements;
6. do not move to immutable forward-test candidate status until robustness work is complete.

No historical baseline alone passes G3.