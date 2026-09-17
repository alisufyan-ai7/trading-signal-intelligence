# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

The earlier GBPUSD/USDJPY H1 recency issue is closed for current research use. A recent-window refresh restored both stored H1 datasets through `2026-09-17 13:00 UTC`.

## Current G3 status

### S01

S01 Trend Pullback v0.1 is **REJECTED AS A GENERAL FX HYPOTHESIS**.

Final archived OOS evidence:

- EUR/USD validation/final: negative;
- GBP/USD refreshed validation/final: negative;
- USD/JPY refreshed validation/final: negative;
- XAU/USD: near-flat validation, strong only in already-observed 2025–2026 period.

Do not optimize S01 v0.1 in place. Keep it as a regression benchmark and retain XAU only as a separate research lead.

### S02

S02 Structure Breakout v0.1 is now **FROZEN BEFORE FIRST RESULT**.

The specification, engine, runner and sample-audit tool are in `main`. No S02 result had been viewed when the parameters were frozen.

Predeclared first universe:

- EUR/USD
- GBP/USD
- USD/JPY
- XAU/USD

## 1. Pull the frozen S02 implementation

```powershell
git pull
```

## 2. Run all four untouched S02 baselines

Do not change parameters between instruments or after seeing the first result.

```powershell
python scripts\run_s02_backtest.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --output outputs\s02_eurusd_v0_1.csv

python scripts\run_s02_backtest.py `
  --symbol GBPUSD `
  --canonical "GBP/USD" `
  --output outputs\s02_gbpusd_v0_1.csv

python scripts\run_s02_backtest.py `
  --symbol USDJPY `
  --canonical "USD/JPY" `
  --output outputs\s02_usdjpy_v0_1.csv

python scripts\run_s02_backtest.py `
  --symbol XAUUSD `
  --canonical "XAU/USD" `
  --output outputs\s02_xauusd_v0_1.csv
```

Preserve the complete JSON output and each CSV ledger.

## 3. Run candle-level implementation audits

Run at least EUR/USD and XAU/USD samples after the four baseline runs:

```powershell
python scripts\audit_s02_sample.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --point-size 0.00001 `
  --samples 10

python scripts\audit_s02_sample.py `
  --symbol XAUUSD `
  --canonical "XAU/USD" `
  --point-size 0.001 `
  --samples 10
```

Expected integrity result:

`all_sample_assertions_pass: true`

The audit checks:

- H4 regime availability by H1 signal close;
- exact prior-20 H1 structure levels;
- breakout margin;
- gap-open exclusion;
- candle direction;
- true-range expansion;
- tick-volume expansion;
- next-bar entry;
- 1.75ATR stop math;
- 2.5R target math.

If an audit fails, diagnose the implementation before interpreting performance. Correcting a software bug does not authorize changing frozen alpha rules.

## 4. Interpret before optimizing

After all four results and the audits are available, compare:

- development / validation / final-test expectancy;
- profit factor;
- drawdown;
- trade count;
- long/short asymmetry;
- year concentration;
- market concentration.

Do **not** run parameter-neighborhood searches yet.

If baseline evidence is broadly negative, retain v0.1 as a failed benchmark and move on rather than searching for an attractive parameter island.

If one or more markets show credible OOS evidence, first run the predeclared robustness work:

- 1.0x / 1.5x / 2.0x cost stress;
- parameter-neighborhood sensitivity;
- walk-forward analysis;
- regime/year breakdown;
- broader market evidence where scientifically justified.

## 5. G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## 6. G4 remains intentionally deferred

Do not invest heavily in polished SaaS UI until at least one strategy family demonstrates credible OOS evidence and an immutable forward-test process is operating.
