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
- Live forward immutable ledger: NOT YET IMPLEMENTED
- SaaS UI: DELIBERATELY DEFERRED

## Validation gates

- G1 research data: **PASS**
- G2 commercial source rights: **OPEN / EXNESS PRODUCTION USE BLOCKED PENDING WRITTEN CLARIFICATION**
- G3 strategy evidence: **IN PROGRESS**
- G4 customer value: **NOT STARTED**

## Data state

Research data is sufficient for historical testing. EURUSD, GBPUSD, USDJPY and XAUUSD have current H1 research datasets through 2026-09-17, with H4 regime data available.

The earlier GBPUSD/USDJPY August H1 cutoff was diagnosed as a transient MT5 history-synchronization state. A 5,000-bar refresh restored both through 2026-09-17 13:00 UTC.

EURUSD and XAUUSD broker H4 OHLC matched exact four-H1 reconstruction over every complete overlapping group tested.

## S01 Trend Pullback v0.1

**Disposition:** REJECTED AS A GENERAL FX HYPOTHESIS.

Final archived evidence:

- EUR/USD validation/final test: negative;
- GBP/USD refreshed validation/final test: negative;
- USD/JPY refreshed validation/final test: negative;
- XAU/USD: near-flat through validation, then strong in the already-observed 2025–2026 period.

S01 remains a regression benchmark. XAU behavior is retained only as a separate market/regime research lead.

See:

- `research/experiments/EXP-2026-004-s01-baseline.md`
- `research/experiments/EXP-2026-005-s01-cross-fx-disposition.md`

## S02 Structure Breakout v0.1

**Status:** RESEARCH — FROZEN BEFORE FIRST RESULT.

Rules were frozen on 2026-09-17 before any S02 result was viewed. The initial predeclared universe is EUR/USD, GBP/USD, USD/JPY and XAU/USD.

Implementation is ready:

- `src/trading_signal_intelligence/backtesting/s02.py`
- `scripts/run_s02_backtest.py`
- `scripts/audit_s02_sample.py`
- `research/experiments/EXP-2026-006-s02-structure-breakout-baseline.md`

## Immediate next external input

Run the unchanged S02 v0.1 baseline on all four predeclared instruments and preserve the complete JSON summaries + ledgers. Then run sample candle-level audits before interpreting/promoting the strategy.
