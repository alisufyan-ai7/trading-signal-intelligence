# EXP-2026-010 — S02 Robustness Protocol Reconciliation

**Status:** COMPLETE — LOCAL + EXACT PRE-FIRST-RESULT NEIGHBORHOODS RECORDED; XAU ROBUST HISTORICAL LEAD  
**Created:** 2026-09-18

## Objective

Record the first S02 v0.1 one-at-a-time sensitivity result accurately, reconcile it with the broader research neighborhood written in the frozen strategy specification before first result, and prevent accidental parameter selection.

## Completed local sensitivity

Runner: `scripts/run_s02_robustness.py`

This 17-configuration neighborhood was frozen **after** the first S02 baseline was viewed and **before** any sensitivity outcome was generated. It is therefore valid post-baseline local robustness evidence, but it is not the exact pre-first-result neighborhood from the v0.1 strategy specification.

Market summary:

| Instrument | Validation-positive | Final-positive | Positive in both OOS splits |
|---|---:|---:|---:|
| EUR/USD | 13/17 | 6/17 | 6/17 |
| GBP/USD | 0/17 | 16/17 | 0/17 |
| USD/JPY | 17/17 | 0/17 | 0/17 |
| XAU/USD | 15/17 | 17/17 | 15/17 |

### XAU/USD local plateau

Across the 17 local configurations:

- validation median expectancy: approximately +0.0942R/trade;
- validation range: approximately -0.0393R to +0.1271R/trade;
- final-test median expectancy: approximately +0.2323R/trade;
- final-test range: approximately +0.1450R to +0.2544R/trade;
- validation trades: 239–290;
- final-test trades: 204–247;
- worst validation max drawdown: approximately -31.25R;
- worst final-test max drawdown: approximately -21.89R.

The only validation-negative XAU local variants were:

1. stop reduced from 1.75 ATR to 1.50 ATR: approximately -0.0393R/trade validation, +0.1489R/trade final;
2. target reduced from 2.5R to 2.0R: approximately -0.0192R/trade validation, +0.1450R/trade final.

Perturbations to structure window, breakout margin, TR expansion, volume expansion, H4 slope and timeout remained validation- and final-positive in this local neighborhood.

### Critical caveat

Every XAU local configuration remained negative in development:

- development range: approximately -0.1065R to -0.0007R/trade;
- median development expectancy: approximately -0.0300R/trade.

This strongly argues against treating S02/XAU as a stationary full-history edge. A later regime change or market-state dependence remains a live explanation.

## Protocol discrepancy found

The frozen S02 v0.1 specification contains a broader pre-first-result research neighborhood:

- structure window: 15 / 20 / 30;
- ATR period: 10 / 14 / 20;
- breakout margin: 0 / 0.10 / 0.20 ATR;
- TR expansion: 1.0 / 1.25 / 1.5;
- volume expansion: 1.0 / 1.10 / 1.25;
- H4 EMA: 30 / 50 / 80;
- H4 slope lookback: 2 / 3 / 5;
- stop: 1.50 / 1.75 / 2.00 ATR;
- target: 2.0 / 2.5 / 3.0R;
- max hold: 48 / 72 / 96 H1 bars;
- cost multiplier: 1.0 / 1.25 / 2.0x spread.

The completed local runner used narrower/different values for several fields and omitted ATR-period and H4-EMA sensitivity. Therefore it must not be represented as the original predeclared neighborhood.

## Exact pre-first-result neighborhood

Runner: `scripts/run_s02_spec_robustness.py`

The next test runs the exact one-at-a-time low/high values recorded in the frozen strategy specification across the same four original markets.

This is not an optimizer. The full table will be retained and no winning configuration will be selected.

Outputs:

- `outputs/s02_spec_robustness_v0_1.json`
- `outputs/s02_spec_robustness_v0_1.csv`

## Decision discipline

1. Preserve the completed 17-configuration local sensitivity as supplemental evidence.
2. Run the exact pre-first-result neighborhood next.
3. Do not move to temporal/walk-forward analysis until the exact-spec result is reviewed.
4. Do not select a best parameter set.
5. Do not redefine v0.1 as XAU-long-only.
6. Candidate/forward-test status remains blocked pending broader robustness, temporal stability and genuinely new forward evidence.


## Exact pre-first-result neighborhood result — 2026-09-18

The exact one-at-a-time neighborhood from the frozen v0.1 specification was executed across all four original markets.

| Instrument | Development-positive | Validation-positive | Final-positive | Positive in both OOS |
|---|---:|---:|---:|---:|
| EUR/USD | 15/23 | 17/23 | 7/23 | 6/23 |
| GBP/USD | 23/23 | 0/23 | 22/23 | 0/23 |
| USD/JPY | 23/23 | 23/23 | 0/23 | 0/23 |
| XAU/USD | 0/23 | 20/23 | 23/23 | 20/23 |

### XAU exact-spec distribution

- validation median expectancy: approximately +0.0921R/trade;
- validation range: approximately -0.0393R to +0.1346R/trade;
- final-test median expectancy: approximately +0.2245R/trade;
- final-test range: approximately +0.1450R to +0.2765R/trade;
- validation worst max drawdown: approximately -31.25R;
- final-test worst max drawdown: approximately -21.89R.

Validation-negative exact-spec XAU variants:

- structure window 30: approximately -0.0268R/trade;
- stop 1.50 ATR: approximately -0.0393R/trade;
- target 2.0R: approximately -0.0192R/trade.

ATR period 10/20, H4 EMA 30/80, breakout margin 0/0.20, TR expansion 1.0/1.5, volume expansion 1.0/1.25, H4 slope 2/5, timeout 48/96 and cost multiplier 1.0/2.0 all remain positive in both XAU OOS splits.

### Critical temporal finding

All 23 XAU exact-spec configurations remain negative in development. Parameter robustness is therefore strong in the later period, but the strategy is not demonstrated to be stationary across the full history.

## Updated disposition

S02 v0.1 XAU/USD is a **parameter-robust historical research lead**, not a candidate.

Next experiment: EXP-2026-011 fixed-rule temporal stability using the unchanged baseline only. No robustness variant is selected.
