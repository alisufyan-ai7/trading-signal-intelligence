# EXP-2026-004 — S01 Trend Pullback v0.1 Frozen Baseline

**Status:** READY TO RUN  
**Created:** 2026-09-17

## Objective

Run the first end-to-end strategy experiment on frozen local research datasets using S01 v0.1 exactly as specified in `strategies/S01-trend-pullback/v0.1.md`.

The goal is not to produce an attractive equity curve. The goal is to verify the research engine and obtain an unbiased baseline result before optimization.

## Initial instruments

1. EUR/USD — Exness MT5 research data
2. XAU/USD — Exness MT5 research data

Both require persisted H1 and H4 closed-bar datasets.

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
- transaction-cost proxy = 1.25 × entry-bar spread price
- zero/missing entry spread falls back to trailing 20-bar non-zero median

## Fixed evaluation splits

- development: through 2022-12-31
- validation: 2023-01-01 through 2024-12-31
- final test: 2025-01-01 onward

No final-test result may be used to rewrite v0.1.

## Commands

Persist data first:

```powershell
python scripts\backfill_mt5.py --symbol EURUSD --canonical "EUR/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol EURUSD --canonical "EUR/USD" --timeframe H4 --bars 50000
python scripts\backfill_mt5.py --symbol XAUUSD --canonical "XAU/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol XAUUSD --canonical "XAU/USD" --timeframe H4 --bars 50000
python scripts\dataset_summary.py
```

Run baseline:

```powershell
python scripts\run_s01_backtest.py --symbol EURUSD --canonical "EUR/USD" --output outputs\s01_eurusd_v0_1.csv
python scripts\run_s01_backtest.py --symbol XAUUSD --canonical "XAU/USD" --output outputs\s01_xauusd_v0_1.csv
```

## Capture for each instrument

- overall trade count
- overall win rate
- gross expectancy R
- net expectancy R
- median net R
- profit factor
- max cumulative-R drawdown
- long/short counts
- target/stop/time-stop counts
- development summary
- validation summary
- final-test summary
- yearly summaries
- any runtime/data errors

## Engine verification before interpreting performance

Before any optimization, inspect a sample of trades to verify:

- H4 data used by each signal was actually available at signal time;
- entry occurs only on the next H1 bar;
- no current/incomplete bars entered the research store;
- spread fallback does not use future data;
- stop/target direction is correct for longs and shorts;
- time stop counts 48 bars as specified;
- overlapping signals are ignored while a position is active;
- final incomplete trades are excluded rather than assigned an artificial result.

## Decision discipline

Possible outcomes:

- **engine bug:** fix implementation without changing strategy logic, rerun same version;
- **strategy fails:** record v0.1 as failed/rejected and formulate a new version/hypothesis;
- **development positive but validation/test weak:** do not promote;
- **OOS positive:** proceed to broader instruments, cost stress, walk-forward and parameter-neighborhood testing before candidate status.

No single backtest can pass G3 by itself.
