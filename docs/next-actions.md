# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

Historical research can proceed. Operational hardening remains queued.

## Current G3 status

S01 v0.1 has now completed baseline runs on XAU/USD and EUR/USD.

Current interpretation:

- XAU/USD: development and validation are essentially flat after costs, while 2025–2026 is materially stronger;
- EUR/USD: development is near flat, while validation and final test are clearly negative;
- both uploaded trade ledgers pass accounting/timing integrity checks;
- the current rule set does **not** demonstrate robust cross-market generalization;
- S01 v0.1 is **not a candidate**;
- candle-level feature audits and H1/H4 consistency checks are the next priority before broader testing.

EXP-2026-004 contains the detailed evidence.

## 1. Pull the latest audit fixes

```powershell
git pull
```

The S01 sample-audit field-name bug is fixed and a new H1/H4 consistency audit is available.

## 2. Rerun candle-level S01 audit

Run on XAU/USD:

```powershell
python scripts\audit_s01_sample.py `
  --symbol XAUUSD `
  --canonical "XAU/USD" `
  --point-size 0.001 `
  --samples 10
```

Optionally run the same audit on EUR/USD:

```powershell
python scripts\audit_s01_sample.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --point-size 0.00001 `
  --samples 10
```

`all_sample_assertions_pass` should be `true`.

## 3. Verify broker H4 against H1 reconstruction

EURUSD H4 history reaches back to 1977 while the stored H1 series begins in 2018. This may be valid deep broker history, but it is unusual enough to verify rather than assume.

Run:

```powershell
python scripts\audit_h1_h4_consistency.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --point-size 0.00001

python scripts\audit_h1_h4_consistency.py `
  --symbol XAUUSD `
  --canonical "XAU/USD" `
  --point-size 0.001
```

The script compares stored broker H4 OHLC with H4 reconstructed from exact groups of four stored H1 bars over their shared history. Frequent/material mismatches must be understood before the H4 regime feed is considered fully verified.

## 4. Only after the integrity audits are clean: broaden unchanged v0.1

Backfill GBPUSD and USDJPY:

```powershell
python scripts\backfill_mt5.py --symbol GBPUSD --canonical "GBP/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol GBPUSD --canonical "GBP/USD" --timeframe H4 --bars 50000
python scripts\backfill_mt5.py --symbol USDJPY --canonical "USD/JPY" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol USDJPY --canonical "USD/JPY" --timeframe H4 --bars 50000
```

Then run unchanged S01 v0.1 on both. Do not change the rules based on the XAU/USD or EUR/USD evidence.

## 5. Robustness work after baseline integrity is confirmed

Without rewriting v0.1:

- cost stress at 1.0x / 1.5x / 2.0x;
- walk-forward analysis;
- parameter-neighborhood sensitivity;
- long/short diagnostics;
- per-year and per-regime breakdown;
- broader instruments.

The already viewed 2025–2026 XAU/USD and EUR/USD periods are no longer untouched holdouts for any new version influenced by these results. New strategy versions require genuinely new cross-instrument or forward evidence.

## 6. Crypto remains separate

Exness BTCUSDT has only ~108 days of H1 history on the tested demo server and includes one unexplained 24-hour gap near the beginning of that history. Binance remains the primary long-horizon crypto research source.

Exness BTCUSD and BTCUSDT are distinct instruments and must not be conflated. Cross-source comparisons should match quote asset where possible.

## G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## G3 tracking

GitHub issue #2 tracks S01 engine verification, broader testing, robustness work and eventual promotion/rejection.

## G4 comes after evidence

Do not spend significant effort on the polished SaaS interface yet. Once a credible immutable forward-test record begins accumulating, prototype the verified signal feed and transparent performance page, then test willingness to pay.
