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

A direct MT5 recency probe later on 2026-09-17 showed current H1/H4 bars for both symbols. A 5,000-H1-bar refresh then extended both local H1 datasets through `2026-09-17 13:00 UTC` and brought each stored H1 series to 50,000 bars.

Interpretation: the August cutoff was a transient/local MT5 history-synchronization state during the earlier bulk backfill, not a persistent source limitation.

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

## Archival refresh after H1 synchronization

The unchanged frozen v0.1 strategy was rerun after the recent H1 windows were refreshed. No strategy parameter changed.

### GBP/USD refreshed

Overall:

- trades: **1,016**
- net expectancy: **-0.04734R/trade**
- profit factor: **0.93145**
- max drawdown: **-67.95R**

Splits:

- development: **-0.03567R/trade**, PF 0.94786, 545 trades
- validation: **-0.05434R/trade**, PF 0.92156, 257 trades
- final test: **-0.06864R/trade**, PF 0.90253, 214 trades

Directional diagnostics from the refreshed ledger:

- validation long: approximately **-0.00058R/trade**
- validation short: approximately **-0.12972R/trade**
- final-test long: approximately **-0.12391R/trade**
- final-test short: approximately **+0.01525R/trade**

The refresh added 13 trades and made the final-test result slightly more negative.

### USD/JPY refreshed

Overall:

- trades: **1,081**
- net expectancy: **-0.09409R/trade**
- profit factor: **0.86727**
- max drawdown: **-112.78R**

Splits:

- development: **-0.04432R/trade**, PF 0.93640, 556 trades
- validation: **-0.12316R/trade**, PF 0.82844, 306 trades
- final test: **-0.17982R/trade**, PF 0.75251, 219 trades

Directional diagnostics from the refreshed ledger:

- validation long: approximately **-0.10396R/trade**
- validation short: approximately **-0.18229R/trade**
- final-test long: approximately **-0.13783R/trade**
- final-test short: approximately **-0.26919R/trade**

The refresh added 7 trades and leaves the final-test result essentially unchanged and clearly negative.

### Refreshed ledger integrity

Both refreshed ledgers were checked after upload:

- every signal timestamp precedes entry;
- entry precedes or equals exit;
- positions do not overlap;
- bars held remain within the frozen 1–48 rule.

No new mechanical anomaly was identified.

## Cross-instrument summary — final archived S01 evidence

| Instrument | Development net R/trade | Validation net R/trade | Final-test net R/trade | Disposition |
|---|---:|---:|---:|---|
| EUR/USD | +0.0099 | -0.1568 | -0.1992 | fail |
| GBP/USD refreshed | -0.0357 | -0.0543 | -0.0686 | fail |
| USD/JPY refreshed | -0.0443 | -0.1232 | -0.1798 | fail |
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
6. Refreshing the transiently stale GBPUSD/USDJPY H1 windows did not change the scientific conclusion.

S01 v0.1 remains in the repository as a regression benchmark and research artifact. A future XAU-specific hypothesis must be versioned separately and validated on genuinely new evidence.

## Next action

Primary G3 research moves to the independently frozen S02 Structure Breakout v0.1 baseline. Do not spend broad optimization effort on S01 v0.1.