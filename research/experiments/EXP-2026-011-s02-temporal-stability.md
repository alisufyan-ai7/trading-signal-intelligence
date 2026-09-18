# EXP-2026-011 — S02 Fixed-Rule Temporal Stability

**Status:** PROTOCOL FROZEN — READY TO RUN  
**Created:** 2026-09-18

## Objective

Determine whether the parameter-robust XAU/USD S02 v0.1 historical lead reflects a sustained later regime or a small number of concentrated performance bursts.

This experiment uses the **unchanged baseline S02 v0.1 configuration only**. It does not select any robustness variant and does not refit parameters.

## Pre-result protocol

Frozen before viewing temporal-window output:

1. Analyze all four original markets: EUR/USD, GBP/USD, USD/JPY, XAU/USD.
2. Start calendar-window analysis at 2019-01-01 UTC so every market has a full common calendar start after the stored H1 histories begin.
3. Non-overlapping complete 6-month windows:
   - Jan 1 to Jul 1;
   - Jul 1 to Jan 1;
   - partial final windows are excluded from summary but not fabricated.
4. Rolling complete 12-month windows stepped every 3 months.
5. Fixed-rule persistence pairs:
   - reference = prior 12 complete months;
   - forward = immediately following 6 complete months;
   - step = 6 months;
   - no parameter fitting or selection occurs in the reference period.
6. Report every eligible window. Do not delete negative windows.
7. Flag `low_sample = true` when a window has fewer than 30 trades; retain the row.
8. Report trade count, net expectancy R, profit factor, maximum cumulative-R drawdown, long count and short count.
9. No long-only reinterpretation.
10. No candidate promotion from historical temporal statistics alone.

## Interpretation questions

- When does XAU behavior transition from negative/flat to positive?
- Is the later XAU edge persistent across adjacent six-month blocks?
- Do rolling 12-month windows show a broad positive plateau or isolated bursts?
- Does a positive prior fixed-rule 12-month period tend to remain positive in the next six months?
- Do EUR/GBP/JPY remain unstable or show comparable regime transitions?

## Implementation

Runner: `scripts/run_s02_temporal_stability.py`

Outputs:

- `outputs/s02_temporal_stability_v0_1.json`
- `outputs/s02_temporal_stability_v0_1.csv`

## Promotion discipline

A favorable temporal result does not by itself make S02 a candidate. Genuinely new forward evidence and immutable signal tracking remain mandatory.
