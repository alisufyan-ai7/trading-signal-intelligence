# EXP-2026-008 — S01 v0.1 Cross-FX Disposition

**Status:** COMPLETE — GENERAL FX HYPOTHESIS REJECTED  
**Date:** 2026-09-17

## Objective

Test the unchanged frozen S01 v0.1 trend-pullback rules on GBP/USD and USD/JPY after the EUR/USD and XAU/USD baseline, without parameter changes driven by prior results.

## Data recency note

The first persisted GBPUSD and USDJPY H1 backfills stopped at `2026-08-09 22:00 UTC`, while H4 extended through 2026-09-17. A direct MT5 recency probe later showed current H1/H4 bars for both symbols, and a 5,000-H1-bar refresh extended both local H1 datasets through `2026-09-17 13:00 UTC`.

The August cutoff was therefore a transient/local MT5 history-synchronization state, not a persistent source limitation.

## Final refreshed GBP/USD result

Overall:

- trades: 1,016
- net expectancy: **-0.04734R/trade**
- PF: **0.93145**
- max drawdown: **-67.95R**

Splits:

- development: -0.03567R/trade, PF 0.94786
- validation: -0.05434R/trade, PF 0.92156
- final test: -0.06864R/trade, PF 0.90253

Directional diagnostics:

- validation long ≈ -0.00058R/trade
- validation short ≈ -0.12972R/trade
- final long ≈ -0.12391R/trade
- final short ≈ +0.01525R/trade

## Final refreshed USD/JPY result

Overall:

- trades: 1,081
- net expectancy: **-0.09409R/trade**
- PF: **0.86727**
- max drawdown: **-112.78R**

Splits:

- development: -0.04432R/trade, PF 0.93640
- validation: -0.12316R/trade, PF 0.82844
- final test: -0.17982R/trade, PF 0.75251

Directional diagnostics:

- validation long ≈ -0.10396R/trade
- validation short ≈ -0.18229R/trade
- final long ≈ -0.13783R/trade
- final short ≈ -0.26919R/trade

## Refreshed ledger integrity

Both refreshed ledgers passed checks for signal/entry ordering, non-overlapping positions, and the frozen 1–48 bar holding rule.

## Cross-instrument final S01 summary

| Instrument | Development net R/trade | Validation net R/trade | Final-test net R/trade | Disposition |
|---|---:|---:|---:|---|
| EUR/USD | +0.0099 | -0.1568 | -0.1992 | fail |
| GBP/USD refreshed | -0.0357 | -0.0543 | -0.0686 | fail |
| USD/JPY refreshed | -0.0443 | -0.1232 | -0.1798 | fail |
| XAU/USD | +0.0120 | +0.0049 | +0.3631 | separate XAU/regime lead only |

## Disposition

**Reject S01 v0.1 as a general FX strategy hypothesis.**

Reasons:

1. EUR/USD, GBP/USD and USD/JPY all have negative validation and final-test expectancy.
2. The failure is not confined to one currency pair or one direction.
3. Ledger, sampled candle and H1/H4 integrity audits found no engine defect explaining the pattern.
4. XAU/USD's recent strength is market/regime-specific evidence and cannot rescue the general hypothesis.
5. The XAU period is already observed and cannot be reused as an untouched holdout for retroactive rule selection.
6. Repairing the transient GBPUSD/USDJPY H1 recency issue did not change the conclusion.

S01 v0.1 remains a regression benchmark. Primary G3 research moves to S02 Structure Breakout.

This file supersedes the duplicate-ID file formerly named `EXP-2026-005-s01-cross-fx-disposition.md`.
