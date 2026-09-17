# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

The earlier GBPUSD/USDJPY H1 recency issue is closed for current research use. The persisted datasets are current through 2026-09-17.

## Current G3 status

### S01

S01 Trend Pullback v0.1 is **REJECTED AS A GENERAL FX HYPOTHESIS** and retained as a regression benchmark. Do not optimize it in place.

### S02

S02 Structure Breakout v0.1 has completed its frozen four-market baseline and is now:

`RESEARCH — ROBUSTNESS WARRANTED; NOT CANDIDATE`

Baseline OOS net expectancy:

| Instrument | Validation | Final test |
|---|---:|---:|
| EUR/USD | +0.0459R/trade | -0.0127R/trade |
| GBP/USD | -0.1858R/trade | +0.0444R/trade |
| USD/JPY | +0.1764R/trade | -0.1631R/trade |
| XAU/USD | +0.0986R/trade | +0.2323R/trade |

EURUSD and XAUUSD candle-level audits passed 10/10 sampled trades. Independent ledger checks across all four markets also passed timing, overlap, 72-bar hold, stop/target and cost-accounting checks.

XAU/USD is the only market positive in both OOS splits. Its OOS annual net expectancy is positive in 2023, 2024, 2025 and 2026-to-date, and it remains positive under substantial spread-cost stress. However, XAU development is negative and the OOS result is carried by longs; that directional fact was discovered after the baseline and cannot be retrofitted into v0.1.

Detailed evidence: `research/experiments/EXP-2026-006-s02-structure-breakout-baseline.md`.

## 1. Pull the frozen robustness runner

```powershell
git pull
```

## 2. Run the predeclared S02 neighborhood sensitivity

This is a robustness diagnostic, **not an optimizer**. Do not select a winning parameter set from the output.

```powershell
python scripts\run_s02_robustness.py
```

The runner evaluates the baseline plus one-at-a-time lower/higher neighbors for:

- structure window: 15 / 20 / 25;
- breakout margin: 0.05 / 0.10 / 0.15 ATR;
- true-range expansion: 1.10 / 1.25 / 1.40;
- tick-volume expansion: 1.00 / 1.10 / 1.20;
- H4 EMA slope lookback: 2 / 3 / 4;
- stop: 1.50 / 1.75 / 2.00 ATR;
- target: 2.0 / 2.5 / 3.0R;
- timeout: 48 / 72 / 96 H1 bars.

It runs the same frozen neighborhood on all four original markets and writes:

- `outputs/s02_robustness_v0_1.json` — compact market summary + baseline cost stress;
- `outputs/s02_robustness_v0_1.csv` — complete variant table.

Preserve/upload both files and paste the printed JSON summary.

## 3. Interpretation rule

Do not promote S02 from a single attractive XAU result.

What we want from the neighborhood test is **stability**, not a better number:

- nearby XAU settings should remain broadly positive in both validation and final test;
- no narrow parameter cliff should be required;
- trade counts should remain adequate;
- drawdown should not explode under modest perturbations;
- the other markets should be reported honestly even if they remain inconsistent.

If XAU survives this neighborhood broadly, the next step is a frozen rolling/walk-forward stability analysis and then additional predeclared market evidence. If it collapses under small perturbations, S02 remains only a historical research lead.

## 4. Directional finding is diagnostic only

Do not change v0.1 to XAU-long-only. The observed long/short asymmetry was learned after seeing the baseline. Any long-only hypothesis must become a separately versioned strategy and must rely on new evidence rather than the already-viewed 2023–2026 period.

## 5. G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness remains an R&D source rather than an assumed production commercial data source.

## 6. G4 remains deferred

Do not invest heavily in polished SaaS UI until at least one strategy family survives robustness work and an immutable forward-test process is operating.