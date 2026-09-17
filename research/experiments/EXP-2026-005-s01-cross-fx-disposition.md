# EXP-2026-005 — S01 v0.1 Cross-FX Disposition

**Status:** COMPLETE — GENERAL FX HYPOTHESIS REJECTED  
**Date:** 2026-09-17

## Objective

Test the unchanged frozen S01 v0.1 trend-pullback rules on additional FX instruments after EUR/USD and XAU/USD, without parameter changes driven by prior results.

New instruments:

- GBP/USD
- USD/JPY

## Data recency note

The first persisted GBPUSD and USDJPY H1 backfills stopped at `2026-08-09 22:00 UTC`, while their H4 datasets extended through `2026-09-17 08:00 UTC`.

A direct MT5 recency probe was run later on 2026-09-17 and showed that the source was then serving current data for both instruments:

### GBPUSD

- live quote: `2026-09-17 14:30:30 UTC`
- latest H1 bar: `2026-09-17 14:00:00 UTC`
- H1 lag vs quote: ~0.51 hours
- latest H4 bar: `2026-09-17 12:00:00 UTC`
- H4 lag vs quote: ~2.51 hours
- both timeframes: `appears_recent = true`

### USDJPY

- live quote: `2026-09-17 14:30:36 UTC`
- latest H1 bar: `2026-09-17 14:00:00 UTC`
- H1 lag vs quote: ~0.51 hours
- latest H4 bar: `2026-09-17 12:00:00 UTC`
- H4 lag vs quote: ~2.51 hours
- both timeframes: `appears_recent = true`

Interpretation: the August H1 cutoff was a transient/local MT5 history-synchronization state during the earlier bulk backfill, not a persistent broker/source limitation. Before new experiments on these symbols, refresh the recent H1 window into the local research store.

This recency issue does not alter the S01 rejection because the negative development/validation evidence and most of the final-test sample were already present, but the experiment should be rerun once after refresh so the archived benchmark ledger is current through the final available research date.

## GBP/USD v0.1 — pre-refresh baseline

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

## USD/JPY v0.1 — pre-refresh baseline

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
6. The transient GBPUSD/USDJPY H1 recency issue does not explain their negative historical OOS results; current direct MT5 probes show both H1 feeds are live and recent.

S01 v0.1 should remain in the repository as a benchmark and research artifact. A future XAU-specific hypothesis must be versioned separately and validated on genuinely new evidence.

## Final housekeeping before S02

1. Refresh the recent GBPUSD and USDJPY H1 windows into the local store.
2. Rerun unchanged S01 once on both so the benchmark ledgers include the restored recent data.
3. Preserve the rerun summaries; do not reinterpret them as a new optimization attempt.
4. Move primary G3 research to S02 Structure Breakout.
5. Do not spend broad optimization effort on S01 v0.1.
