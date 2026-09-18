# EXP-2026-011 — S02 Fixed-Rule Temporal Stability

**Status:** COMPLETE — RECENT XAU REGIME PERSISTENT; NOT CANDIDATE  
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


## Result — 2026-09-18

All windows met the 30-trade interpretability threshold.

### Summary

| Market | Positive half-years | Positive rolling 12m | Positive-reference -> positive-forward |
|---|---:|---:|---:|
| EUR/USD | 11/15 | 19/27 | 7/10 |
| GBP/USD | 7/15 | 15/27 | 3/7 |
| USD/JPY | 9/15 | 21/27 | 8/11 |
| XAU/USD | 10/15 | 21/27 | 7/10 |

The aggregate fractions alone are not sufficient because USDJPY demonstrates strong historical persistence followed by a clear 2025–2026 breakdown.

### XAU/USD calendar sequence

Complete half-year expectancy:

- 2019-H1 +0.0651
- 2019-H2 -0.0553
- 2020-H1 +0.0303
- 2020-H2 +0.2013
- 2021-H1 -0.0500
- 2021-H2 -0.2733
- 2022-H1 -0.2010
- 2022-H2 +0.3599
- 2023-H1 -0.1178
- 2023-H2 +0.3471
- 2024-H1 +0.1218
- 2024-H2 +0.0107
- 2025-H1 +0.1839
- 2025-H2 +0.2101
- 2026-H1 +0.3710 R/trade

The key recent feature is **six consecutive positive half-years from 2023-H2 through 2026-H1**.

Rolling 12-month expectancy is positive for every quarterly-start window from 2022-01 through 2025-07, a 15-window streak.

The six most recent fixed-rule reference/forward pairs (reference starts 2022-07 through 2025-01) are all positive-reference followed by positive-forward.

### Interpretation

XAU historical strength is not merely one isolated annual burst. It is persistent across adjacent recent calendar blocks and overlapping annual windows.

However:

- 2021 through 2022-H1 is materially negative;
- 2023-H1 is also negative;
- all 23 exact-spec parameter variants remain negative in development;
- USDJPY shows that even high historical persistence can break abruptly.

Therefore the result supports a **recent-regime historical lead**, not a stationary or guaranteed future edge.

## Disposition

Historical parameter and temporal robustness stages are complete for the XAU lead.

Next:
1. frozen transfer test on XAGUSD, USTEC, US500, US30 and USOIL;
2. immutable live forward-test infrastructure;
3. no XAU-long-only rule change;
4. no candidate/G3 pass until genuinely new forward evidence exists.
