# EXP-2026-003 — S01 Trend Pullback v0.1 Frozen Baseline

**Status:** COMPLETE — NOT CANDIDATE  
**Created:** 2026-09-16  
**Executed:** 2026-09-17

## Objective

Run the first end-to-end strategy experiment on frozen local research datasets using S01 v0.1 exactly as specified in `strategies/S01-trend-pullback/v0.1.md`, without tuning after viewing results.

## Frozen baseline

- H4 EMA50/EMA200 trend regime
- EMA50 3-H4-bar slope agreement
- 3-H1-bar pullback window around H1 EMA20
- H1 EMA50 guard
- signal candle resumes momentum beyond previous H1 extreme
- next-H1-open entry
- 1.5 ATR14 stop
- 2R target
- 48-H1-bar timeout
- one position per instrument
- same-bar stop/target ambiguity resolves to stop first
- transaction-cost proxy = 1.25x known signal-bar spread price
- prior-only median fallback when signal spread is zero/missing

Fixed splits:

- development: through 2022-12-31
- validation: 2023-01-01 through 2024-12-31
- final test: 2025-01-01 onward

## XAU/USD result

Overall:

- trades: 1,124
- net expectancy: **+0.0834R/trade**
- PF: **1.1297**
- max drawdown: **-37.12R**

Splits:

- development: +0.0120R/trade, PF 1.0179
- validation: +0.00495R/trade, PF 1.0074
- final test: +0.3631R/trade, PF 1.6719

Interpretation: essentially flat through development/validation, then materially stronger in 2025–2026. This does not establish a stable baseline edge.

Directional diagnostic:

- development long +0.0575; short -0.0424 R/trade
- validation long +0.1560; short -0.3323
- final long +0.4322; short +0.1435

## EUR/USD result

Overall:

- trades: 1,021
- net expectancy: **-0.0786R/trade**
- PF: **0.8888**
- max drawdown: **-112.25R**

Splits:

- development: +0.00986R/trade, PF 1.0146
- validation: -0.1568R/trade, PF 0.7862
- final test: -0.1992R/trade, PF 0.7356

Both long and short directions are negative outside development.

## Integrity evidence

Uploaded EURUSD and XAUUSD trade ledgers passed checks for:

- signal before entry;
- entry before/equal exit;
- no overlapping positions;
- 1–48 bar hold limit;
- exact -1R gross stops and +2R gross targets within floating-point tolerance;
- gross/net R arithmetic and cost accounting.

Candle-level sample audits:

- XAU/USD: 10/10 sampled trades passed all implemented assertions
- EUR/USD: 10/10 sampled trades passed all implemented assertions

H1↔H4 reconstruction audit:

- EUR/USD: 12,068 complete four-H1 groups compared; max OHLC difference 0.0 points
- XAU/USD: 10,862 complete four-H1 groups compared; max OHLC difference 0.0 points

No engine/timing/data-integrity defect was found that explains the performance difference.

## Disposition

**S01 v0.1 is not a candidate.**

The frozen rules do not demonstrate robust cross-market generalization. XAU's already-observed recent strength is retained only as a market/regime research lead and cannot justify retroactive rule selection.

Cross-FX extension and final rejection are recorded in `EXP-2026-008-s01-cross-fx-disposition.md`.

This file supersedes the later duplicate-ID file formerly named `EXP-2026-004-s01-baseline.md`.
