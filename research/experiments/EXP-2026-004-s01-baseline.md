# EXP-2026-004 — S01 Trend Pullback v0.1 Frozen Baseline

**Status:** BASELINE COMPLETE ON XAU/USD + EUR/USD — NOT CANDIDATE  
**Created:** 2026-09-17  
**Latest result recorded:** 2026-09-17

## Objective

Run the first end-to-end strategy experiment on frozen local research datasets using S01 v0.1 exactly as specified in `strategies/S01-trend-pullback/v0.1.md`.

The purpose is to obtain an unbiased baseline and verify the research engine before optimization.

## Frozen rules

S01 v0.1 remained unchanged after the first XAU/USD result and before the EUR/USD run.

Core baseline:

- H4 EMA50/EMA200 trend regime
- EMA50 3-H4-bar slope agreement
- 3-H1-bar pullback window around H1 EMA20
- H1 EMA50 guard
- signal candle must resume momentum beyond previous H1 extreme
- next-H1-open entry
- 1.5 ATR14 stop
- 2R target
- 48-H1-bar time stop
- one position per instrument at a time
- same-bar target+stop ambiguity resolves to stop first
- transaction-cost proxy = 1.25 × signal-bar spread price
- zero/missing signal spread falls back to trailing 20-bar non-zero median using only prior information

## Fixed evaluation splits

- development: through 2022-12-31
- validation: 2023-01-01 through 2024-12-31
- final test: 2025-01-01 onward

## Data notes

### BTCUSDT gap detail

The observed Exness BTCUSDT H1 gap is:

- previous bar: `2026-06-02 07:00 UTC`
- next bar: `2026-06-03 07:00 UTC`
- duration: 24 hours

Binance remains the primary long-horizon crypto source.

### Frozen local datasets

Persisted:

- EURUSD H1: 49,999 closed bars, 2018-09-04 13:00 UTC through 2026-09-17 11:00 UTC
- EURUSD H4: 49,999 closed bars, 1977-09-28 20:00 UTC through 2026-09-17 08:00 UTC
- XAUUSD H1: 49,999 closed bars, 2018-03-28 14:00 UTC through 2026-09-17 11:00 UTC
- XAUUSD H4: 16,194 closed bars, 2014-01-14 00:00 UTC through 2026-09-17 08:00 UTC

The unusually deep EURUSD H4 start date is now an explicit integrity question. It is not assumed invalid, but H4 OHLC must be compared with H4 reconstructed from the overlapping H1 bars before relying on the regime feed without qualification. `scripts/audit_h1_h4_consistency.py` performs this check.

## XAU/USD v0.1 result

### Overall

- trades: **1,124**
- win rate: **37.46%**
- gross expectancy: **+0.1102R/trade**
- net expectancy: **+0.0834R/trade**
- median net trade: **-1.0134R**
- profit factor: **1.1297**
- maximum cumulative-R drawdown: **-37.12R**

### Development — through 2022

- trades: 625
- net expectancy: **+0.0120R/trade**
- profit factor: 1.0179

Essentially flat after costs.

### Validation — 2023–2024

- trades: 265
- net expectancy: **+0.00495R/trade**
- profit factor: 1.0074

Effectively flat after costs.

### Final test — 2025 onward

- trades: 234
- net expectancy: **+0.3631R/trade**
- profit factor: **1.6719**
- max drawdown: -11.14R

The final period is materially stronger, but this strength is not present consistently in development/validation.

### Directional diagnostic

Diagnostic only; v0.1 is unchanged.

- development long: +0.0575R/trade; short: -0.0424R/trade
- validation long: +0.1560R/trade; short: -0.3323R/trade
- final-test long: +0.4322R/trade; short: +0.1435R/trade

## EUR/USD v0.1 result

### Overall

- trades: **1,021**
- win rate: **32.52%**
- gross expectancy: **-0.0354R/trade**
- net expectancy: **-0.0786R/trade**
- median net trade: **-1.0290R**
- profit factor: **0.8888**
- maximum cumulative-R drawdown: **-112.25R**
- long trades: 460
- short trades: 561
- targets: 324
- stops: 688
- time stops: 9

### Development — through 2022

- trades: 534
- net expectancy: **+0.00986R/trade**
- profit factor: 1.0146
- max drawdown: -27.52R

Essentially flat after costs.

### Validation — 2023–2024

- trades: 272
- net expectancy: **-0.1568R/trade**
- profit factor: **0.7862**
- max drawdown: -46.58R

Clearly negative out of sample.

### Final test — 2025 onward

- trades: 215
- net expectancy: **-0.1992R/trade**
- profit factor: **0.7356**
- max drawdown: -49.57R

Negative and worse than development.

### Directional diagnostic

Both directions are negative outside development:

- validation long: approximately -0.161R/trade
- validation short: approximately -0.153R/trade
- final-test long: approximately -0.190R/trade
- final-test short: approximately -0.212R/trade

This argues against explaining EUR/USD failure as only one bad direction.

## Trade-ledger integrity checks

Both uploaded XAUUSD and EURUSD trade ledgers passed the following independent checks:

- every signal timestamp precedes entry;
- entry precedes or equals exit;
- no overlapping positions under the one-position rule;
- bars held are within 1–48;
- stop distance is exactly 1R gross within floating-point tolerance;
- target distance is exactly 2R gross within floating-point tolerance;
- reported gross R matches price arithmetic;
- reported net R matches gross P&L minus cost;
- cost uses the configured 1.25 multiplier and source point size.

## Candle-level audit results

The corrected `scripts/audit_s01_sample.py` was run on 2026-09-17 for both completed baseline instruments.

### XAU/USD

- total trades: 1,124
- sampled trades: 10 evenly spaced across the ledger
- `all_sample_assertions_pass`: **true**

### EUR/USD

- total trades: 1,021
- sampled trades: 10 evenly spaced across the ledger
- `all_sample_assertions_pass`: **true**

Every sampled trade passed all implemented assertions:

- the selected H4 regime bar was available by H1 signal close;
- entry was the next stored H1 bar;
- entry occurred after the signal bar open timestamp;
- trade direction matched the strategy signal flag;
- the prior pullback window contained all three required H1 bars.

The sampled records also show the expected closed-bar EMA/ATR values, prior-three-bar pullback features, H4 regime values, signal-bar known spread, and entry/exit parameters. No sample-level evidence of look-ahead or H1/H4 timing leakage was found.

This is still a sample audit, not a formal proof over every generated feature row. The remaining data-integrity check is H1→H4 reconstruction consistency.

## H1/H4 consistency status

`scripts/audit_h1_h4_consistency.py` is ready but has not yet been run for EURUSD/XAUUSD.

The next integrity gate is to compare broker H4 OHLC against H4 reconstructed from exact groups of H1 candles over the overlapping history. This is especially important for EURUSD because the broker-provided H4 dataset extends back to 1977 while the persisted H1 dataset begins in 2018.

## Current interpretation

**S01 v0.1 is not a candidate.**

Evidence so far:

1. XAU/USD is near-flat in development and validation, then strong in 2025–2026.
2. EUR/USD is near-flat in development but clearly negative in validation and final test.
3. Therefore the current rule set does not demonstrate robust cross-instrument generalization.
4. XAU/USD's recent strength remains interesting as a possible market/regime-specific phenomenon, but it is already observed data and cannot justify retroactive rule selection.
5. Ledger-level and sampled candle-level audits do not reveal an obvious engine/timing defect.
6. H1/H4 reconstruction consistency still needs to be verified before broader strategy conclusions.

The 2025–2026 periods already viewed are no longer untouched holdouts for any future strategy version influenced by these results.

## Next actions

1. Run H1/H4 consistency audit on EURUSD and XAUUSD.
2. If consistency is clean, backfill and run unchanged v0.1 on GBPUSD and USDJPY.
3. Only after engine/data integrity is confirmed: cost stress, walk-forward and parameter-neighborhood diagnostics.
4. Do not optimize v0.1 in place. Any revised idea becomes a new strategy version with new evidence requirements.

No single backtest passes G3 by itself.
