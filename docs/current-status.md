# Current Status

**Phase:** 1 — Strategy evidence research  
**Date:** 2026-09-17

## Infrastructure

- Repository initialized: YES
- MT5 historical research connector: WORKING
- Binance historical research connector: WORKING
- Normalized candle model: WORKING
- Local SQLite research store/backfill: WORKING
- Historical backtest framework: WORKING
- Candle-level strategy audit tooling: WORKING
- H1↔H4 consistency audit tooling: WORKING
- S02 post-baseline local-sensitivity runner: COMPLETE
- S02 exact predeclared-neighborhood runner: READY
- Live forward immutable ledger: NOT YET IMPLEMENTED
- SaaS UI: DELIBERATELY DEFERRED

## Validation gates

- G1 research data: **PASS**
- G2 commercial source rights: **OPEN / EXNESS PRODUCTION USE BLOCKED PENDING WRITTEN CLARIFICATION**
- G3 strategy evidence: **IN PROGRESS — S02 XAU LOCAL SENSITIVITY ROBUST; EXACT SPEC NEIGHBORHOOD PENDING; NOT CANDIDATE**
- G4 customer value: **NOT STARTED**

## Data state

Research data is sufficient for historical testing. EURUSD, GBPUSD, USDJPY and XAUUSD have current H1 research datasets through 2026-09-17, with H4 regime data available.

The earlier GBPUSD/USDJPY August H1 cutoff was a transient MT5 history-synchronization state and has been repaired in the local research store.

EURUSD and XAUUSD broker H4 OHLC matched exact four-H1 reconstruction over every complete overlapping group tested.

## S01 Trend Pullback v0.1

**Disposition:** REJECTED AS A GENERAL FX HYPOTHESIS.

S01 remains a regression benchmark. Its already-observed XAU behavior is retained only as a separate research lead.

Evidence:

- `research/experiments/EXP-2026-003-s01-baseline.md`
- `research/experiments/EXP-2026-008-s01-cross-fx-disposition.md`

## S02 Structure Breakout v0.1

**Status:** RESEARCH — ROBUSTNESS IN PROGRESS; NOT CANDIDATE.

The frozen four-market baseline is complete and the EURUSD/XAUUSD candle-level sample audits both passed 10/10 sampled trades.

OOS net expectancy:

- EUR/USD: validation +0.0459R/trade; final test -0.0127R/trade
- GBP/USD: validation -0.1858R/trade; final test +0.0444R/trade
- USD/JPY: validation +0.1764R/trade; final test -0.1631R/trade
- XAU/USD: validation +0.0986R/trade; final test +0.2323R/trade

XAU/USD is the only market positive in both OOS splits and is positive in each observed OOS calendar year 2023–2026. It also remains positive when the existing ledger is repriced at 2x and 3x the baseline spread-cost proxy.

Post-baseline local sensitivity (17 configurations per market) is now complete. XAU/USD remained positive in both OOS splits for 15/17 variants and positive in the final test for 17/17. The only validation-negative XAU neighbors were the tighter 1.50 ATR stop (-0.0393R/trade) and lower 2.0R target (-0.0192R/trade). Final-test expectancy across all XAU local variants stayed between +0.1450R and +0.2544R/trade. OOS trade counts remained substantial and the worst validation drawdown was -31.25R.

Important caveats:

- all 17 XAU local variants remained negative in development (best approximately -0.0007R/trade);
- XAU OOS strength is carried by longs, a post-result diagnostic that cannot be retrofitted into v0.1;
- GBPUSD and USDJPY had zero local variants positive in both OOS splits; EURUSD had 6/17;
- the executed local neighborhood was frozen after the first baseline and is narrower/different from the broader neighborhood recorded in the v0.1 strategy specification before first result;
- therefore the exact original specification neighborhood must be run before temporal/walk-forward work;
- genuinely new forward evidence is still required.

Detailed evidence: `research/experiments/EXP-2026-009-s02-structure-breakout-baseline.md`.

## Experiment ID hygiene

Canonical experiment IDs are now unique. The executed data-quality audit is EXP-2026-006, the merged collector soak plan is EXP-2026-007, the S01 cross-FX disposition is EXP-2026-008, and the S02 baseline is EXP-2026-009.

## Immediate next external input

Run `python scripts\run_s02_spec_robustness.py` after `git pull`. Preserve `outputs/s02_spec_robustness_v0_1.json` and `outputs/s02_spec_robustness_v0_1.csv`. This runner implements the exact one-at-a-time neighborhood that was written in the frozen v0.1 specification before the first S02 result. Do not select a best parameter set.