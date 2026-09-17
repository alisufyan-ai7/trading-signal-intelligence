# EXP-2026-006 — S02 Structure Breakout v0.1 Baseline

**Status:** READY TO RUN — RULES FROZEN BEFORE FIRST RESULT  
**Created:** 2026-09-17

## Objective

Evaluate the first untouched baseline for S02 Structure Breakout v0.1 using the predeclared four-market universe and frozen local research datasets.

This experiment must not change S02 parameters after any result is viewed.

## Predeclared universe

1. EUR/USD
2. GBP/USD
3. USD/JPY
4. XAU/USD

All four are included before S02 outcomes are known to reduce market-selection bias.

## Frozen S02 v0.1 rules

See `strategies/S02-structure-breakout/v0.1.md` for the authoritative specification.

Summary:

- H1 20-bar prior structure high/low;
- close must break structure by >0.10 ATR14;
- exclude bars that open already beyond the relevant structure;
- signal true range >=1.25× prior-20 median true range;
- signal tick volume >=1.10× prior-20 median tick volume;
- H4 close/EMA50 regime with 3-H4-bar EMA slope agreement;
- closed-candle signal, next-H1-open entry;
- 1.75 ATR initial stop;
- 2.5R fixed target;
- 72-H1-bar timeout;
- same-bar stop/target ambiguity resolves to stop first;
- baseline cost proxy = 1.25× known signal-bar spread price;
- one open position per instrument.

## Fixed temporal splits

- development: before 2023-01-01 UTC;
- validation: 2023-01-01 through 2024-12-31 UTC;
- final test: 2025-01-01 onward.

These market periods have been seen through prior S01 research, so they are not globally pristine. S02 parameters, however, are frozen before viewing S02 outcomes. Candidate claims still require robustness and genuinely new forward evidence.

## Data state before first run

As of the S02 freeze:

- EURUSD H1: through 2026-09-17 11:00 UTC;
- GBPUSD H1: refreshed through 2026-09-17 13:00 UTC;
- USDJPY H1: refreshed through 2026-09-17 13:00 UTC;
- XAUUSD H1: through 2026-09-17 11:00 UTC;
- H4 datasets are available for all four instruments and the EURUSD/XAUUSD H1↔H4 reconstruction audit passed exactly over complete overlapping four-H1 groups.

## Implementation

- engine: `src/trading_signal_intelligence/backtesting/s02.py`
- runner: `scripts/run_s02_backtest.py`
- sample integrity audit: `scripts/audit_s02_sample.py`

## First-run procedure

Run all four frozen baselines before any parameter changes:

```powershell
python scripts\run_s02_backtest.py --symbol EURUSD --canonical "EUR/USD" --output outputs\s02_eurusd_v0_1.csv
python scripts\run_s02_backtest.py --symbol GBPUSD --canonical "GBP/USD" --output outputs\s02_gbpusd_v0_1.csv
python scripts\run_s02_backtest.py --symbol USDJPY --canonical "USD/JPY" --output outputs\s02_usdjpy_v0_1.csv
python scripts\run_s02_backtest.py --symbol XAUUSD --canonical "XAU/USD" --output outputs\s02_xauusd_v0_1.csv
```

Then run candle-level sample audits using source point sizes:

```powershell
python scripts\audit_s02_sample.py --symbol EURUSD --canonical "EUR/USD" --point-size 0.00001 --samples 10
python scripts\audit_s02_sample.py --symbol XAUUSD --canonical "XAU/USD" --point-size 0.001 --samples 10
```

If either audit reports `all_sample_assertions_pass = false`, investigate implementation integrity before interpreting strategy performance. Do not alter alpha parameters to fix a software bug.

## Required reporting

For every instrument preserve:

- overall summary;
- development / validation / final-test summary;
- annual results;
- complete trade ledger.

Initial interpretation should focus on after-cost expectancy, profit factor, drawdown, sample size, cross-market consistency and whether performance is concentrated in one year/direction.

## Promotion discipline

No market or strategy family is promoted from this baseline alone.

Before candidate status require at minimum:

- positive OOS evidence that is not isolated to one year;
- candle-level audit pass;
- cost stress;
- parameter-neighborhood sensitivity;
- walk-forward analysis;
- cross-market evidence or a separately justified market-specific hypothesis;
- immutable forward testing.

## Result

Pending. No S02 v0.1 backtest result had been viewed when this experiment file was created.