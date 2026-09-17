# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`, with one new operational recency issue to diagnose.

GBPUSD and USDJPY H1 backfills unexpectedly stopped at `2026-08-09 22:00 UTC`, while their H4 datasets extended through `2026-09-17 08:00 UTC`. This does not invalidate the historical S01 rejection, but future experiments should not rely on stale H1 data without understanding the cause.

## Current G3 status

S01 v0.1 has now been tested unchanged across EUR/USD, GBP/USD, USD/JPY and XAU/USD.

Disposition:

- EUR/USD: validation/final test clearly negative;
- GBP/USD: development, validation and final test all negative;
- USD/JPY: development, validation and final test all negative;
- XAU/USD: near-flat through validation, then unusually strong in 2025–2026;
- integrity audits on the original EUR/XAU pipeline are clean;
- **S01 v0.1 is rejected as a general FX strategy hypothesis**;
- the XAU result is retained only as a separate market/regime research lead.

See `research/experiments/EXP-2026-005-s01-cross-fx-disposition.md`.

## 1. Pull latest project state

```powershell
git pull
```

## 2. Diagnose GBPUSD/USDJPY H1 recency

Run:

```powershell
python scripts\mt5_recency_probe.py `
  --symbol GBPUSD `
  --canonical "GBP/USD"

python scripts\mt5_recency_probe.py `
  --symbol USDJPY `
  --canonical "USD/JPY"
```

The probe compares the latest quote timestamp with the most recent H1 and H4 bars returned directly by MT5.

Interpretation:

- if H1 now appears current, re-run the H1 backfills to fill the missing recent history;
- if H1 is still stuck near 2026-08-09 while quotes/H4 are current, diagnose terminal history synchronization before new strategy work on these symbols.

Do not rerun or optimize S01 merely because recent H1 bars become available. Its cross-FX disposition is already negative over large OOS samples.

## 3. Preserve S01 as a benchmark

Do not tune S01 v0.1 in place.

Keep it for:

- regression testing of the backtest engine;
- cost-model comparisons;
- future XAU-specific hypothesis generation;
- checking whether future infrastructure changes alter known results unexpectedly.

## 4. Move primary strategy research to S02

After the recency probe is understood, freeze and implement **S02 Structure Breakout v0.1** before viewing results.

The S02 specification should define in advance:

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

## 5. G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## 6. G4 remains intentionally deferred

Do not invest heavily in the polished SaaS UI until at least one strategy family demonstrates credible OOS evidence and an immutable forward-test process is running.
