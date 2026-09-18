# Current Next Actions

_Last updated: 2026-09-18_

## G1 status

`PASS — RESEARCH DATA`.

## Current G3 status

S01 Trend Pullback v0.1 remains rejected as a general FX hypothesis.

S02 Structure Breakout v0.1 is:

`RESEARCH — PARAMETER ROBUSTNESS PASSED FOR XAU LEAD; TEMPORAL STABILITY NEXT; NOT CANDIDATE`

The frozen four-market baseline, implementation audits, post-baseline local sensitivity, and exact pre-first-result specification neighborhood are complete.

### Exact-spec robustness result

| Instrument | Development-positive | Validation-positive | Final-positive | Positive in both OOS |
|---|---:|---:|---:|---:|
| EUR/USD | 15/23 | 17/23 | 7/23 | 6/23 |
| GBP/USD | 23/23 | 0/23 | 22/23 | 0/23 |
| USD/JPY | 23/23 | 23/23 | 0/23 | 0/23 |
| XAU/USD | 0/23 | 20/23 | 23/23 | 20/23 |

XAU/USD shows a broad parameter plateau in the later periods. Validation expectancy across the exact neighborhood ranges from about -0.0393R to +0.1346R/trade; final-test expectancy ranges from +0.1450R to +0.2765R/trade.

The three XAU validation-negative variants are:

1. structure window 30: approximately -0.0268R/trade;
2. stop 1.50 ATR: approximately -0.0393R/trade;
3. target 2.0R: approximately -0.0192R/trade.

ATR-period 10/20 and H4-EMA 30/80 perturbations remain positive in both OOS splits. So do the wider breakout/filter settings and 2.0x cost multiplier.

Critical caveat: **all 23 XAU exact-spec configurations remain negative in development.** This is parameter-robust but temporally non-stationary historical evidence.

## 1. Pull the frozen temporal runner

```powershell
git pull
```

## 2. Run fixed-rule temporal stability

```powershell
python scripts\run_s02_temporal_stability.py
```

This uses **only the unchanged v0.1 baseline**. No robustness variant is selected.

The frozen temporal protocol reports, for all four original markets:

- complete non-overlapping 6-month calendar blocks beginning 2019-01-01;
- complete rolling 12-month windows stepped every 3 months;
- fixed-rule persistence pairs: prior 12 months versus the immediately following 6 months;
- net expectancy, profit factor, max drawdown, trade count and long/short counts;
- every window, including negative and low-sample windows.

A window with fewer than 30 trades is flagged `low_sample = true`; it is not deleted.

Outputs:

- `outputs/s02_temporal_stability_v0_1.json`
- `outputs/s02_temporal_stability_v0_1.csv`

Upload both files and paste the printed JSON summary.

## 3. Interpretation rule frozen before temporal results

This is not a parameter search and not a classic refit walk-forward. The v0.1 rules stay fixed.

The questions are:

- when does XAU behavior change from negative/flat to positive?
- is the later edge persistent across adjacent half-years and overlapping 12-month windows?
- are there isolated bursts hidden by annual averages?
- does a positive prior 12-month fixed-rule period tend to remain positive over the immediately following 6 months?
- do EUR/GBP/JPY show comparable transitions or continued instability?

No market is promoted solely because a majority of historical windows are positive. Candidate status still requires genuinely new forward evidence.

## 4. After temporal stability

If XAU shows sustained later-period stability rather than a small number of bursts, the next research step will be predeclared additional-market evidence (metals/index/energy) and construction of the immutable forward-test ledger.

Do not create a long-only XAU v0.2 yet. The directional asymmetry remains post-result information.

## 5. G2 and G4

G2 commercial source rights remains independently open. Exness is still an R&D source, not an assumed commercial production source.

G4/customer-facing SaaS work remains deferred until strategy evidence and immutable forward-test infrastructure are stronger.
