# EXP-2026-005 — S01 v0.1 Cross-FX Disposition

**Status:** COMPLETE — GENERAL FX HYPOTHESIS REJECTED  
**Date:** 2026-09-17

## Objective

Test the unchanged frozen S01 v0.1 trend-pullback rules on additional FX instruments after EUR/USD and XAU/USD, without parameter changes driven by prior results.

New instruments:

- GBP/USD
- USD/JPY

## Data note

The persisted GBPUSD and USDJPY H1 datasets unexpectedly stop at `2026-08-09 22:00 UTC`, while their H4 datasets extend through `2026-09-17 08:00 UTC`.

This does not explain their negative validation history, but it is a pipeline recency issue that must be diagnosed before future experiments. `scripts/mt5_recency_probe.py` was added for this purpose.

## GBP/USD v0.1

Overall:

- trades: 1,003
- net expectancy: **-0.0463R/trade**
- profit factor: **0.9329**
- max drawdown: **-67.95R**

Splits:

- development: **-0.0357R/trade**, PF 0.9479
- validation: **-0.0543R/trade**, PF 0.9216
- final test: **-0.0647R/trade**, PF 0.9079

Directional diagnostics:

- validation long: approximately -0.0006R/trade
- validation short: approximately -0.1297R/trade
- final-test long: approximately -0.1311R/trade
- final-test short: approximately +0.0278R/trade

Interpretation: no robust edge. Overall and every evaluation split are negative after costs.

## USD/JPY v0.1

Overall:

- trades: 1,074
- net expectancy: **-0.0937R/trade**
- profit factor: **0.8679**
- max drawdown: **-109.72R**

Splits:

- development: **-0.0443R/trade**, PF 0.9364
- validation: **-0.1232R/trade**, PF 0.8284
- final test: **-0.1804R/trade**, PF 0.7517

Directional diagnostics:

- validation long: approximately -0.1040R/trade
- validation short: approximately -0.1823R/trade
- final-test long: approximately -0.1378R/trade
- final-test short: approximately -0.2812R/trade

Interpretation: clearly negative, with deterioration outside development.

## Cross-instrument summary

| Instrument | Development net R/trade | Validation net R/trade | Final-test net R/trade | Disposition |
|---|---:|---:|---:|---|
| EUR/USD | +0.0099 | -0.1568 | -0.1992 | fail |
| GBP/USD | -0.0357 | -0.0543 | -0.0647 | fail |
| USD/JPY | -0.0443 | -0.1232 | -0.1804 | fail |
| XAU/USD | +0.0120 | +0.0049 | +0.3631 | separate XAU/regime lead only |

The three FX pairs all fail the OOS standard. XAU/USD is an outlier: it is near-flat through validation and strong only in the already-observed 2025–2026 period.

## Disposition

**Reject S01 v0.1 as a general FX strategy hypothesis.**

Reasons:

1. EUR/USD, GBP/USD and USD/JPY all have negative validation and final-test expectancy.
2. The failure is not confined to one currency pair or one direction.
3. Existing ledger, sampled candle, and H1/H4 consistency audits have not identified an engine defect that explains the pattern.
4. XAU/USD's recent strength is market/regime-specific evidence and is not sufficient to rescue the general hypothesis.
5. The XAU period is already observed and cannot be used as an untouched holdout for retroactive rule selection.

S01 v0.1 should remain in the repository as a benchmark and research artifact. A future XAU-specific hypothesis must be versioned separately and validated on genuinely new evidence.

## Next actions

1. Diagnose the GBPUSD/USDJPY H1 recency cutoff before using those persisted datasets for future experiments.
2. Do not spend broad optimization effort on S01 v0.1.
3. Preserve XAU behavior as a separate research lead.
4. Move primary G3 research to the next predeclared strategy family, S02 Structure Breakout, after the data-recency diagnostic is clean.
