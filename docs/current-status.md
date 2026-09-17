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
- S02 one-at-a-time robustness runner: READY
- Live forward immutable ledger: NOT YET IMPLEMENTED
- SaaS UI: DELIBERATELY DEFERRED

## Validation gates

- G1 research data: **PASS**
- G2 commercial source rights: **OPEN / EXNESS PRODUCTION USE BLOCKED PENDING WRITTEN CLARIFICATION**
- G3 strategy evidence: **IN PROGRESS — S02 WARRANTS ROBUSTNESS, NOT CANDIDATE**
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

**Status:** RESEARCH — ROBUSTNESS WARRANTED; NOT CANDIDATE.

The frozen four-market baseline is complete and the EURUSD/XAUUSD candle-level sample audits both passed 10/10 sampled trades.

OOS net expectancy:

- EUR/USD: validation +0.0459R/trade; final test -0.0127R/trade
- GBP/USD: validation -0.1858R/trade; final test +0.0444R/trade
- USD/JPY: validation +0.1764R/trade; final test -0.1631R/trade
- XAU/USD: validation +0.0986R/trade; final test +0.2323R/trade

XAU/USD is the only market positive in both OOS splits and is positive in each observed OOS calendar year 2023–2026. It also remains positive when the existing ledger is repriced at 2x and 3x the baseline spread-cost proxy.

Important caveats:

- XAU development is negative;
- XAU OOS strength is carried by longs, a post-result diagnostic that cannot be retrofitted into v0.1;
- the other three markets show substantial temporal instability;
- historical robustness and genuinely new forward evidence are still required.

Detailed evidence: `research/experiments/EXP-2026-009-s02-structure-breakout-baseline.md`.

## Experiment ID hygiene

Canonical experiment IDs are now unique. The executed data-quality audit is EXP-2026-006, the merged collector soak plan is EXP-2026-007, the S01 cross-FX disposition is EXP-2026-008, and the S02 baseline is EXP-2026-009.

## Immediate next external input

Run `python scripts\run_s02_robustness.py` after `git pull`, preserve `outputs/s02_robustness_v0_1.json` and `outputs/s02_robustness_v0_1.csv`, and review the full one-at-a-time neighborhood without selecting a best parameter set.