# Project Brief

_Last updated: 2026-09-17_

## Goal

Create a low-cost trading-signal SaaS that continuously scans markets, generates quantitatively defined setups, explains them with AI, and keeps an immutable verified performance record.

## Core positioning

This is **not** an "AI predicts the market" product. The intended positioning is:

> Broker-neutral verified signal intelligence: discover setups, explain the reasoning, quantify the risk, and prove the track record.

## Current product boundaries

### In scope for research / v1

- Forex, metals, indices, energy and crypto signal research
- MT5 + Python research connector on Windows
- Exness demo account as an initial R&D feed
- Binance direct market data as the primary long-horizon crypto research source
- Historical backtesting with instrument-specific spread/transaction-cost assumptions
- Walk-forward and out-of-sample validation
- Signal quality scoring calibrated to historical outcomes
- Immutable live forward-test ledger
- AI-generated explanations and contextual risk summaries after a quantitative signal exists
- Web dashboard, alerts and subscriptions only after the research gates are satisfied

### Out of scope for v1

- Holding customer funds
- Fully automated copy trading
- Portfolio management
- Native mobile apps
- Rebuilding a full charting terminal
- Redistributing raw broker market data without explicit rights
- Marketing unsupported accuracy/win-rate claims

## Four validation gates

| Gate | Question | Status |
|---|---|---|
| G1 | Can MT5/Exness and Binance reliably provide the research data we need? | **PASS — RESEARCH DATA** |
| G2 | Can each intended production source legally support commercial derived signals? | OPEN — Exness production assumption blocked pending clarification |
| G3 | Can at least one strategy demonstrate robust positive expectancy after costs? | **IN PROGRESS — S01 rejected for general FX; S02 frozen and ready** |
| G4 | Will traders pay for verified and explainable signals? | NOT STARTED |

## G1 evidence

Representative H1 audits completed on 2026-09-17:

- EURUSD: ~8 years, zero duplicate timestamps, full tick-volume coverage
- XAUUSD: ~8.5 years, zero duplicates, full tick-volume coverage
- USTEC: ~7.2 years, zero duplicates, full tick-volume coverage
- USOIL: ~8.4 years, zero duplicates, full tick-volume coverage
- Exness BTCUSDT: only ~108 days; insufficient for long-horizon crypto backtests
- Exness vs Binance BTCUSDT: 0.999451 H1 return correlation across 998 consecutive return samples

The initial GBPUSD/USDJPY bulk H1 backfills temporarily stopped at 2026-08-09, but direct recency probes showed live current H1/H4 data and a later 5,000-bar refresh restored both stored H1 datasets through 2026-09-17 13:00 UTC.

EURUSD and XAUUSD broker H4 OHLC matched exact four-H1 reconstruction over every complete overlapping group tested.

Operational hardening remains separate: session-aware gap classification, the single observed 24h Exness BTCUSDT gap, and a long-running collector soak test.

## Initial research universe

- FX: EURUSD, GBPUSD, USDJPY
- Metals: XAUUSD, XAGUSD
- Indices: USTEC, US500, US30
- Energy: USOIL
- Crypto: BTCUSDT and ETHUSDT primarily via Binance direct; broker CFD equivalents are comparison/execution-environment research feeds

The authoritative source mappings live in `config/instruments.json`.

## Data-model rules

- Canonical symbols are explicit and source-aware; do not derive identity from broker currency metadata alone.
- Strategies consume normalized Candle objects and must not import source-specific broker APIs directly.
- Historical MT5 bar spread is preserved as a cost proxy, not assumed to be perfect executable bid/ask history.
- Cost assumptions are instrument-specific and must be stress-tested.
- Research datasets are persisted locally so strategy runs can be reproduced from frozen inputs.
- Broker H4 bars must be checked against H1 reconstruction over overlapping history when integrity is in doubt.

## Strategy evidence

### S01 Trend Pullback v0.1

Frozen before first result and tested unchanged across EUR/USD, GBP/USD, USD/JPY and XAU/USD.

Final disposition: **REJECTED AS A GENERAL FX HYPOTHESIS**.

- EUR/USD: validation and final test clearly negative.
- GBP/USD refreshed: validation -0.0543R/trade; final test -0.0686R/trade.
- USD/JPY refreshed: validation -0.1232R/trade; final test -0.1798R/trade.
- XAU/USD: near-flat through validation, then strong in the already-observed 2025–2026 period; retained only as a separate XAU/regime research lead.

Ledger mechanics, sampled candle-level feature checks, and EUR/XAU H1↔H4 consistency audits did not identify an engine/data defect explaining the FX failures.

Detailed evidence:

- `research/experiments/EXP-2026-004-s01-baseline.md`
- `research/experiments/EXP-2026-005-s01-cross-fx-disposition.md`

### S02 Structure Breakout v0.1

**Status: RESEARCH — FROZEN BEFORE FIRST RESULT.**

Predeclared first universe:

- EUR/USD
- GBP/USD
- USD/JPY
- XAU/USD

Baseline design:

- H1 20-bar prior structure breakout;
- 0.10 ATR breakout margin;
- gap-open exclusion;
- true-range and tick-volume expansion confirmation;
- H4 EMA50 regime/slope filter;
- next-H1-open entry;
- 1.75 ATR stop;
- 2.5R target;
- 72-H1-bar timeout;
- conservative same-bar ambiguity;
- same signal-bar spread cost convention as the research engine.

Implementation and audit tooling are ready. No S02 result had been viewed when v0.1 was frozen.

See:

- `strategies/S02-structure-breakout/v0.1.md`
- `research/experiments/EXP-2026-006-s02-structure-breakout-baseline.md`

## Initial strategy families

- S01 Trend Pullback — **v0.1 rejected for general FX; XAU lead retained**
- S02 Structure Breakout — **v0.1 frozen, ready to run**
- S03 Momentum Continuation — IDEA
- S04 Mean Reversion — IDEA
- S05 Volatility Expansion — IDEA

Most hypotheses are expected to be rejected. Promotion requires reproducible after-cost evidence, robustness and forward testing.

## Phase status

1. MT5 connection / symbol discovery — **DONE**
2. Normalized MT5/Binance adapters — **DONE for historical research**
3. Representative data-quality/history audit — **DONE / G1 PASS**
4. Local reproducible persistence/backfill — **DONE for initial FX/XAU research universe**
5. S01 frozen backtest + integrity audits + cross-FX disposition — **DONE / GENERAL FX REJECTED**
6. S02 frozen specification + implementation — **DONE / READY TO RUN**
7. S02 baseline / OOS / robustness evidence — **NEXT**
8. Live immutable forward test — **PENDING**
9. Customer-value validation / SaaS UI — **PENDING**

## Durable project-state rule

Major decisions, research conclusions, strategy definitions and implementation changes should be written to this repository. Chat is for discussion; the repository is the project source of truth.
