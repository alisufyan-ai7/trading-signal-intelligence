# EXP-2026-004 — S01 Trend Pullback v0.1 Frozen Baseline

**Status:** PARTIAL RESULT — XAU/USD COMPLETE, EUR/USD PENDING  
**Created:** 2026-09-17  
**First result recorded:** 2026-09-17

## Objective

Run the first end-to-end strategy experiment on frozen local research datasets using S01 v0.1 exactly as specified in `strategies/S01-trend-pullback/v0.1.md`.

The goal is not to produce an attractive equity curve. The goal is to verify the research engine and obtain an unbiased baseline result before optimization.

## Initial instruments

1. EUR/USD — Exness MT5 research data — **pending because H4 backfill failed on a single large MT5 IPC request**
2. XAU/USD — Exness MT5 research data — **completed**

The MT5 backfill script has since been changed to paginate in smaller chunks and retry transient terminal failures. EUR/USD must be rerun after pulling that fix.

## Frozen rules

Do not change S01 v0.1 after seeing the result.

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
- transaction-cost proxy = 1.25 × **signal-bar** spread price
- zero/missing signal spread falls back to a trailing 20-bar non-zero median using only prior information

## Fixed evaluation splits

- development: through 2022-12-31
- validation: 2023-01-01 through 2024-12-31
- final test: 2025-01-01 onward

No final-test result may be used to rewrite v0.1.

## Data collection result

### BTCUSDT gap detail

The previously observed 24-hour Exness BTCUSDT H1 gap is:

- previous bar: `2026-06-02 07:00 UTC`
- next bar: `2026-06-03 07:00 UTC`
- duration: 24 hours

This occurs near the start of the currently exposed Exness BTCUSDT history and remains unexplained. It is not a blocker for S01 because Binance is the primary long-horizon crypto research source.

### Frozen local datasets

Successfully persisted:

- EURUSD H1: 49,999 closed bars, 2018-09-04 13:00 UTC through 2026-09-17 11:00 UTC
- XAUUSD H1: 49,999 closed bars, 2018-03-28 14:00 UTC through 2026-09-17 11:00 UTC
- XAUUSD H4: 16,194 closed bars, 2014-01-14 00:00 UTC through 2026-09-17 08:00 UTC

EURUSD H4 failed with `MT5 copy_rates_from_pos() failed ... Terminal: Call failed` when 50,000 bars were requested in one call. This is treated as an operational backfill issue, not a data-quality conclusion. The backfill code now pages through MT5 in smaller chunks with retries.

## XAU/USD v0.1 result

### Overall

- trades: **1,124**
- win rate: **37.46%**
- gross expectancy: **+0.1102R/trade**
- net expectancy: **+0.0834R/trade**
- median net trade: **-1.0134R**
- profit factor: **1.1297**
- maximum cumulative-R drawdown: **-37.12R**
- long trades: 701
- short trades: 423
- targets: 408
- stops: 701
- time stops: 15

### Development — through 2022

- trades: 625
- win rate: 35.36%
- net expectancy: **+0.0120R/trade**
- profit factor: 1.0179
- max drawdown: -26.78R

Interpretation: essentially flat after costs.

### Validation — 2023–2024

- trades: 265
- win rate: 34.34%
- net expectancy: **+0.00495R/trade**
- profit factor: 1.0074
- max drawdown: -29.82R

Interpretation: effectively flat after costs and does **not** establish a stable validation edge.

### Final test — 2025 onward

- trades: 234
- win rate: 46.58%
- net expectancy: **+0.3631R/trade**
- profit factor: **1.6719**
- max drawdown: -11.14R
- cumulative net result over the observed final-test sample: approximately +84.97R

The final-test period is materially stronger than development/validation. This is interesting but must not be treated as proof of a generally robust strategy because the earlier samples are near flat.

### Directional diagnostic

This is diagnostic evidence only; it does not modify v0.1.

- development long: +0.0575R/trade; short: -0.0424R/trade
- validation long: +0.1560R/trade; short: -0.3323R/trade
- final-test long: +0.4322R/trade; short: +0.1435R/trade

The validation sample shows substantial long/short asymmetry. Any future directional hypothesis must be a new strategy version and may not retroactively replace v0.1.

## Trade-ledger integrity checks completed

The uploaded 1,124-trade XAUUSD ledger was checked independently after the run.

Passed checks:

- every signal timestamp precedes its entry timestamp;
- entry precedes or equals exit;
- no positions overlap under the one-position-at-a-time rule;
- bars held range from 1 to 48 as specified;
- all trade cost inputs are positive;
- `cost_price = spread_points × 0.001 × 1.25` exactly within floating-point tolerance;
- `net_R = gross_R - cost_price / risk_price` exactly within floating-point tolerance;
- ordinary stop exits are exactly -1R gross;
- ordinary target exits are exactly +2R gross;
- gap stops can lose more than -1R, as intended;
- same-bar stop/target ambiguity is resolved to stop first.

Observed exit-reason counts in the ledger:

- ordinary stop: 688
- ordinary target: 403
- time stop: 15
- gap stop: 7
- same-bar stop first: 6
- gap target: 5

## What remains unverified

The trade ledger alone cannot independently prove every candle-level feature decision. Before promoting any strategy, still verify against persisted candles that:

- H4 features used at each H1 signal were genuinely available at signal close;
- signal-candle indicator values have no future leakage;
- session gaps do not create unintended feature behavior;
- a manual sample of trades reproduces the strategy conditions from stored H1/H4 candles.

The code currently uses H4 bar availability time = H4 open timestamp + 4 hours and a backward as-of merge into H1 signal-close time. This design is intended to prevent look-ahead and should be spot-checked against actual stored candles.

## Current interpretation

**S01 v0.1 is promising but not promotable.**

Why not promotable yet:

1. development and validation are essentially flat after costs;
2. the strong result appears only in the most recent final-test regime;
3. EUR/USD baseline is still missing;
4. broader cross-instrument evidence, cost stress, walk-forward testing and candle-level audit remain incomplete.

Do not optimize v0.1 in place. Any revised hypothesis becomes a new version.

## Next actions

1. Pull the paginated MT5 backfill fix.
2. Re-run EURUSD H4 backfill and EURUSD v0.1.
3. Perform candle-level sample verification on XAUUSD.
4. Run unchanged v0.1 on GBPUSD and USDJPY as additional cross-instrument evidence.
5. Run declared cost stress and walk-forward tests before any candidate decision.

No single backtest can pass G3 by itself.
