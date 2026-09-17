# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

Historical research can proceed. Operational hardening remains queued.

## Current G3 status

S01 v0.1 has completed baseline runs on XAU/USD and EUR/USD, plus ledger, sampled candle-level, and H1↔H4 consistency audits.

Current interpretation:

- XAU/USD: development and validation are essentially flat after costs, while 2025–2026 is materially stronger;
- EUR/USD: development is near flat, while validation and final test are clearly negative;
- both trade ledgers pass accounting/timing checks;
- 10/10 sampled trades on each instrument pass H4-availability, next-bar-entry, signal-direction, and pullback-window assertions;
- broker H4 OHLC exactly matches H4 reconstructed from complete groups of stored H1 candles over the shared history for both instruments;
- no current integrity finding explains the performance difference;
- S01 v0.1 is **not a candidate**.

The next evidence should be unchanged cross-instrument testing on GBPUSD and USDJPY.

## 1. Pull latest project state

```powershell
git pull
```

## 2. Backfill GBP/USD

```powershell
python scripts\backfill_mt5.py `
  --symbol GBPUSD `
  --canonical "GBP/USD" `
  --timeframe H1 `
  --bars 50000

python scripts\backfill_mt5.py `
  --symbol GBPUSD `
  --canonical "GBP/USD" `
  --timeframe H4 `
  --bars 50000
```

## 3. Backfill USD/JPY

```powershell
python scripts\backfill_mt5.py `
  --symbol USDJPY `
  --canonical "USD/JPY" `
  --timeframe H1 `
  --bars 50000

python scripts\backfill_mt5.py `
  --symbol USDJPY `
  --canonical "USD/JPY" `
  --timeframe H4 `
  --bars 50000
```

Then verify persisted datasets:

```powershell
python scripts\dataset_summary.py
```

## 4. Run the unchanged frozen S01 v0.1

Do not alter the strategy parameters based on XAU/USD or EUR/USD.

```powershell
python scripts\run_s01_backtest.py `
  --symbol GBPUSD `
  --canonical "GBP/USD" `
  --output outputs\s01_gbpusd_v0_1.csv

python scripts\run_s01_backtest.py `
  --symbol USDJPY `
  --canonical "USD/JPY" `
  --output outputs\s01_usdjpy_v0_1.csv
```

The backtest runner reads point size from `config/instruments.json`; no manual point-size argument is required.

Preserve/paste:

- dataset summary;
- complete GBPUSD JSON result;
- complete USDJPY JSON result;
- generated trade ledgers.

## 5. What happens after GBPUSD/USDJPY

Do **not** optimize v0.1 immediately.

First compare all four instruments on:

- development expectancy;
- validation expectancy;
- final-test expectancy;
- profit factor;
- maximum drawdown;
- long/short behavior;
- year-to-year stability.

If GBPUSD/USDJPY also fail to show stable OOS evidence, S01 v0.1 should likely be formally rejected as a general multi-FX trend-pullback candidate and retained only as a benchmark/research artifact.

If one or both unexpectedly show robust OOS performance, then we can justify cost stress, walk-forward analysis, and parameter-neighborhood sensitivity on the unchanged baseline before making a final disposition.

## 6. Do not add USTEC/WTI yet

FX cross-instrument evidence is the cleanest next comparison because the same strategy semantics, cost model, and market structure are more comparable. Index/energy testing can follow after S01's FX disposition is clearer.

## 7. Crypto remains separate

Exness BTCUSDT has only ~108 days of H1 history on the tested demo server and includes one unexplained 24-hour gap near the beginning of that history. Binance remains the primary long-horizon crypto research source.

Exness BTCUSD and BTCUSDT are distinct instruments and must not be conflated. Cross-source comparisons should match quote asset where possible.

## G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## G3 tracking

GitHub issue #2 tracks S01 evidence and eventual promotion/rejection.

## G4 comes after evidence

Do not spend significant effort on the polished SaaS interface yet. Once a credible immutable forward-test record begins accumulating, prototype the verified signal feed and transparent performance page, then test willingness to pay.
