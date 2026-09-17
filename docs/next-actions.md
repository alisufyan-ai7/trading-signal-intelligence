# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

The earlier GBPUSD/USDJPY H1 cutoff at `2026-08-09 22:00 UTC` has been diagnosed as a transient/local MT5 history-synchronization state rather than a persistent source limitation.

Direct recency probes on 2026-09-17 showed for both GBPUSD and USDJPY:

- live quotes current near `14:30 UTC`;
- latest H1 bar at `14:00 UTC`;
- latest H4 bar at `12:00 UTC`;
- H1 and H4 both `appears_recent = true`.

Before new strategy work on these symbols, refresh the recent H1 window into the local research store.

## Current G3 status

S01 v0.1 has been tested unchanged across EUR/USD, GBP/USD, USD/JPY and XAU/USD.

Disposition:

- EUR/USD: validation/final test clearly negative;
- GBP/USD: development, validation and final test negative in the pre-refresh benchmark;
- USD/JPY: development, validation and final test negative in the pre-refresh benchmark;
- XAU/USD: near-flat through validation, then unusually strong in 2025–2026;
- integrity audits on EUR/XAU are clean;
- **S01 v0.1 is rejected as a general FX strategy hypothesis**;
- XAU remains a separate market/regime research lead only.

See `research/experiments/EXP-2026-005-s01-cross-fx-disposition.md`.

## 1. Pull latest project state

```powershell
git pull
```

## 2. Refresh only the recent GBPUSD/USDJPY H1 windows

A 5,000-bar refresh is enough to overlap the stale cutoff and include the current H1 history. Existing rows are upserted; this does not discard older stored history.

```powershell
python scripts\backfill_mt5.py `
  --symbol GBPUSD `
  --canonical "GBP/USD" `
  --timeframe H1 `
  --bars 5000

python scripts\backfill_mt5.py `
  --symbol USDJPY `
  --canonical "USD/JPY" `
  --timeframe H1 `
  --bars 5000
```

Then verify:

```powershell
python scripts\dataset_summary.py
```

Expected: GBPUSD and USDJPY H1 `last_timestamp_utc` should now be near the current trading hour instead of 2026-08-09.

## 3. Rerun unchanged S01 once for archival completeness

This is not an optimization attempt and does not reopen the rejected general-FX hypothesis. It simply makes the stored benchmark results include the restored recent H1 data.

```powershell
python scripts\run_s01_backtest.py `
  --symbol GBPUSD `
  --canonical "GBP/USD" `
  --output outputs\s01_gbpusd_v0_1_refreshed.csv

python scripts\run_s01_backtest.py `
  --symbol USDJPY `
  --canonical "USD/JPY" `
  --output outputs\s01_usdjpy_v0_1_refreshed.csv
```

Preserve/paste:

- refreshed dataset summary;
- complete GBPUSD JSON result;
- complete USDJPY JSON result.

## 4. Preserve S01 as a benchmark

Do not tune S01 v0.1 in place.

Keep it for:

- regression testing of the backtest engine;
- cost-model comparisons;
- future XAU-specific hypothesis generation;
- checking whether infrastructure changes alter known results unexpectedly.

## 5. Move primary strategy research to S02

After the refreshed benchmark is archived, freeze and implement **S02 Structure Breakout v0.1** before viewing any S02 results.

The S02 specification must define in advance:

- exact breakout structure/window;
- higher-timeframe trend/regime rule, if any;
- confirmation rule;
- entry timing;
- ATR/structure stop;
- target or trailing-exit logic;
- timeout;
- same-bar ambiguity policy;
- cost model;
- fixed development/validation/final-test splits;
- promotion/rejection criteria.

Do not reuse parameters selected from S01 outcomes unless they are justified independently.

## 6. G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## 7. G4 remains intentionally deferred

Do not invest heavily in the polished SaaS UI until at least one strategy family demonstrates credible OOS evidence and an immutable forward-test process is running.
