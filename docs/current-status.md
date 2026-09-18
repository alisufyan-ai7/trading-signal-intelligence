# Current Status

**Phase:** 1 — Strategy evidence research  
**Date:** 2026-09-18

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
- S02 exact predeclared-neighborhood runner: COMPLETE
- S02 temporal-stability runner: COMPLETE
- S02 new-market transfer runner: COMPLETE
- Immutable hash-chained forward ledger: IMPLEMENTED / NOT YET ACTIVATED
- S02 live forward scanner: IMPLEMENTED / WAITING FOR ACTIVATION HASH ANCHOR
- SaaS UI: DELIBERATELY DEFERRED

## Validation gates

- G1 research data: **PASS**
- G2 commercial source rights: **OPEN / EXNESS PRODUCTION USE BLOCKED PENDING WRITTEN CLARIFICATION**
- G3 strategy evidence: **IN PROGRESS — S02 XAU HISTORICAL ROBUSTNESS PASSED; TRANSFER PARTIAL; IMMUTABLE FORWARD EVIDENCE NEXT; NOT CANDIDATE**
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

**Status:** RESEARCH — XAU HISTORICAL ROBUSTNESS PASSED; FORWARD ACTIVATION NEXT; NOT CANDIDATE.

The frozen four-market baseline is complete and the EURUSD/XAUUSD candle-level sample audits both passed 10/10 sampled trades.

OOS net expectancy:

- EUR/USD: validation +0.0459R/trade; final test -0.0127R/trade
- GBP/USD: validation -0.1858R/trade; final test +0.0444R/trade
- USD/JPY: validation +0.1764R/trade; final test -0.1631R/trade
- XAU/USD: validation +0.0986R/trade; final test +0.2323R/trade

XAU/USD is the only market positive in both OOS splits and is positive in each observed OOS calendar year 2023–2026. It also remains positive when the existing ledger is repriced at 2x and 3x the baseline spread-cost proxy.

Post-baseline local sensitivity (17 configurations per market) is now complete. XAU/USD remained positive in both OOS splits for 15/17 variants and positive in the final test for 17/17. The only validation-negative XAU neighbors were the tighter 1.50 ATR stop (-0.0393R/trade) and lower 2.0R target (-0.0192R/trade). Final-test expectancy across all XAU local variants stayed between +0.1450R and +0.2544R/trade. OOS trade counts remained substantial and the worst validation drawdown was -31.25R.

Exact pre-first-result specification sensitivity is now complete (23 configurations per market):

- EURUSD: 6/23 positive in both OOS splits;
- GBPUSD: 0/23;
- USDJPY: 0/23;
- XAUUSD: 20/23.

For XAUUSD, validation expectancy ranges from approximately -0.0393R to +0.1346R/trade and final-test expectancy from +0.1450R to +0.2765R/trade. The three validation-negative variants are structure window 30, stop 1.50 ATR, and target 2.0R. ATR 10/20, H4 EMA 30/80, wider breakout/filter settings and cost multiplier 2.0x all remain positive in both OOS splits.

Temporal analysis with the unchanged baseline is now complete. XAU has 10/15 positive complete half-years overall, but the recent sequence is more informative: six consecutive positive half-years from 2023-H2 through 2026-H1. Its rolling 12-month windows are positive for every start from 2022-01 through 2025-07 (15 consecutive windows). The six most recent fixed-rule prior-12m -> next-6m pairs are all positive-to-positive.

New-market transfer is complete. USTEC and US30 satisfy the pre-frozen descriptive transfer-support flag, with validation/final net expectancy of approximately +0.124/+0.012R and +0.094/+0.012R per trade respectively. XAGUSD, US500 and USOIL do not satisfy the rule.

Important caveats:

- the USTEC/US30 final-test margins are small and should not be promoted from this result;
- XAGUSD, the closest same-asset-class transfer market to XAU, is validation-negative after costs despite positive 2025–2026 results;
- US500 turns negative in the final test and USOIL is negative in both OOS splits;
- all 23 XAU exact-spec variants remain negative in development, so the XAU edge is not stationary over the full history;
- genuinely new forward evidence is still required.

Detailed evidence:

- `research/experiments/EXP-2026-009-s02-structure-breakout-baseline.md`
- `research/experiments/EXP-2026-010-s02-robustness-reconciliation.md`

## Experiment ID hygiene

Canonical experiment IDs are now unique. The executed data-quality audit is EXP-2026-006, the merged collector soak plan is EXP-2026-007, the S01 cross-FX disposition is EXP-2026-008, and the S02 baseline is EXP-2026-009.

## Immediate next external input

Pull the forward-ledger implementation, run the ledger tests, then activate the primary S02/XAU v0.1 forward test. Preserve and report the activation record hash before starting hourly signal scans.