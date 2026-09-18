# Current Next Actions

_Last updated: 2026-09-18_

## G1 status

`PASS — RESEARCH DATA`.

## Current G3 status

S01 Trend Pullback v0.1 remains rejected as a general FX hypothesis.

S02 Structure Breakout v0.1 is:

`RESEARCH — ROBUSTNESS IN PROGRESS; NOT CANDIDATE`

The frozen four-market baseline and implementation audits are complete. The 17-configuration post-baseline local sensitivity test is also complete.

### Local-sensitivity result

| Instrument | Validation-positive variants | Final-positive variants | Positive in both OOS splits |
|---|---:|---:|---:|
| EUR/USD | 13/17 | 6/17 | 6/17 |
| GBP/USD | 0/17 | 16/17 | 0/17 |
| USD/JPY | 17/17 | 0/17 | 0/17 |
| XAU/USD | 15/17 | 17/17 | 15/17 |

XAU/USD forms a broad local plateau rather than a single attractive parameter point. Its final-test expectancy across the 17 local variants ranges from approximately +0.145R to +0.254R/trade. The two validation-negative neighbors are the tighter 1.50 ATR stop and lower 2.0R target.

However, all 17 XAU variants remain negative in development. The behavior is therefore not a stationary full-history edge and must be investigated as a possible later regime/market effect.

## Protocol reconciliation

The completed `scripts/run_s02_robustness.py` neighborhood was frozen after the first S02 baseline and before its own sensitivity results. It is valid supplemental local sensitivity evidence, but it is **not identical** to the broader research neighborhood recorded in `strategies/S02-structure-breakout/v0.1.md` before the first S02 result.

The original specification also predeclared ATR-period and H4-EMA perturbations and used broader values for several other parameters. We will run that exact specification neighborhood before moving to temporal analysis.

## 1. Pull the exact-spec runner

```powershell
git pull
```

## 2. Run the exact originally predeclared S02 neighborhood

```powershell
python scripts\run_s02_spec_robustness.py
```

This is one-at-a-time sensitivity, not optimization. It evaluates the baseline plus the exact low/high values recorded before first result for:

- structure window: 15 / 20 / 30;
- ATR period: 10 / 14 / 20;
- breakout margin: 0 / 0.10 / 0.20 ATR;
- true-range expansion: 1.0 / 1.25 / 1.5;
- tick-volume expansion: 1.0 / 1.10 / 1.25;
- H4 EMA: 30 / 50 / 80;
- H4 slope lookback: 2 / 3 / 5;
- stop: 1.50 / 1.75 / 2.00 ATR;
- target: 2.0 / 2.5 / 3.0R;
- timeout: 48 / 72 / 96 H1 bars;
- cost multiplier: 1.0 / 1.25 / 2.0x spread.

It runs all four original markets and writes:

- `outputs/s02_spec_robustness_v0_1.json`
- `outputs/s02_spec_robustness_v0_1.csv`

Upload both files and paste the printed JSON summary.

## 3. Interpretation rule

Do not select whichever setting looks best. We are testing whether the baseline sits inside a broad stable region.

For XAU/USD, strong evidence would mean most of the exact predeclared neighboring configurations remain positive in both OOS splits with adequate sample size and without a drawdown explosion. Failure of the broader ATR/H4-EMA or wider breakout/filter perturbations would weaken the local-plateau finding.

GBPUSD and USDJPY remain regime-unstable unless the exact predeclared test provides materially different evidence; do not rescue them by selecting variants.

## 4. After the exact-spec neighborhood

Only if the XAU evidence remains broad will we freeze and run temporal stability:

- non-overlapping 6-month blocks;
- rolling 12-month windows stepped every 3 months;
- fixed-rule prior-period versus next-period persistence;
- no parameter refitting or selection.

The purpose will be to locate and quantify the apparent regime transition, especially because development is negative while 2023–2026 is positive.

## 5. Directional finding remains diagnostic only

Do not change v0.1 to XAU-long-only. That asymmetry was learned after the baseline.

## 6. G2 and G4

G2 commercial source rights remains independent and open. Exness remains an R&D source, not an assumed commercial production source.

G4/customer-facing SaaS work remains deferred until strategy evidence and immutable forward-test infrastructure are stronger.
