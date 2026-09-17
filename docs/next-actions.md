# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

Historical research can proceed. Operational hardening remains queued.

## Current G3 status

S01 v0.1 has produced its first completed baseline on XAU/USD.

Current interpretation:

- overall XAU/USD result is positive;
- development and validation are essentially flat after costs;
- final test (2025 onward) is materially stronger;
- ledger-level accounting/timing checks pass;
- S01 is **not a candidate yet**;
- EUR/USD result is still pending because its H4 backfill failed on a single large MT5 request.

EXP-2026-004 contains the detailed result and interpretation.

## 1. Pull the paginated MT5 backfill + audit tooling

```powershell
git pull
```

The MT5 backfill command now requests history in smaller pages and retries transient terminal IPC failures. A candle-level S01 audit command has also been added.

## 2. Complete EUR/USD H4 and baseline

The EURUSD H1 dataset already exists locally. Re-run only H4:

```powershell
python scripts\backfill_mt5.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --timeframe H4 `
  --bars 50000
```

Then verify:

```powershell
python scripts\dataset_summary.py
```

Then run the unchanged frozen baseline:

```powershell
python scripts\run_s01_backtest.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --output outputs\s01_eurusd_v0_1.csv
```

Do not modify S01 v0.1 based on the XAU/USD result.

## 3. Candle-level engine audit on XAU/USD

Run an evenly spaced sample of S01 trades back through the stored H1/H4 feature frame:

```powershell
python scripts\audit_s01_sample.py `
  --symbol XAUUSD `
  --canonical "XAU/USD" `
  --point-size 0.001 `
  --samples 10
```

The audit reports, for each sampled trade:

- whether the selected H4 regime bar was available by H1 signal close;
- whether entry is the next stored H1 bar;
- whether direction matches the generated signal flag;
- whether the full three-bar pullback window exists;
- H4 EMA regime values;
- H1 signal EMA/ATR values;
- the three prior pullback bars;
- entry/stop/target/exit and net R.

`all_sample_assertions_pass` should be `true`. Preserve/paste the output for review before candidate promotion.

## 4. Broaden unchanged v0.1 evidence

After EUR/USD runs correctly and the XAU audit is clean, backfill and test unchanged v0.1 on:

```powershell
python scripts\backfill_mt5.py --symbol GBPUSD --canonical "GBP/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol GBPUSD --canonical "GBP/USD" --timeframe H4 --bars 50000
python scripts\backfill_mt5.py --symbol USDJPY --canonical "USD/JPY" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol USDJPY --canonical "USD/JPY" --timeframe H4 --bars 50000
```

Then run S01 with the proper point sizes for those instruments.

Do not add USTEC/WTI until the first FX/metals implementation audit is complete.

## 5. Only after the baseline engine is audited

Run the declared robustness work without rewriting v0.1:

- cost stress at 1.0x / 1.5x / 2.0x;
- walk-forward analysis;
- parameter-neighborhood sensitivity;
- long/short diagnostic breakdown;
- per-year and per-regime breakdown;
- broader instruments.

The already viewed 2025–2026 XAU/USD final-test period is no longer an untouched holdout for any new strategy version derived from these results. New versions must use genuinely new cross-instrument or forward evidence.

## 6. Crypto remains separate

Exness BTCUSDT has only ~108 days of H1 history on the tested demo server and includes one unexplained 24-hour gap near the beginning of that history. Binance remains the primary long-horizon crypto research source.

Exness BTCUSD and BTCUSDT are distinct instruments and must not be conflated. Cross-source comparisons should match quote asset where possible, e.g. Exness BTCUSDT vs Binance BTCUSDT.

## G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## G3 tracking

GitHub issue #2 tracks S01 engine verification, broader testing, robustness work and eventual promotion/rejection.

## G4 comes after evidence

Do not spend significant effort on the polished SaaS interface yet. Once a credible immutable forward-test record begins accumulating, prototype the verified signal feed and transparent performance page, then test willingness to pay.
