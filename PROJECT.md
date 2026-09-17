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
| G3 | Can at least one strategy demonstrate robust positive expectancy after costs? | **IN PROGRESS — S01 baseline not candidate** |
| G4 | Will traders pay for verified and explainable signals? | NOT STARTED |

## G1 evidence

Representative H1 audits completed on 2026-09-17:

- EURUSD: 50,000 bars, ~8.0 years, zero duplicate timestamps, full tick-volume coverage
- XAUUSD: 50,000 bars, ~8.5 years, zero duplicates, full tick-volume coverage
- USTEC: 41,412 bars, ~7.2 years, zero duplicates, full tick-volume coverage
- USOIL: 50,000 bars, ~8.4 years, zero duplicates, full tick-volume coverage
- Exness BTCUSDT: 2,575 bars, ~108 days; insufficient for long-horizon crypto backtests
- Exness vs Binance BTCUSDT: 0.999451 H1 return correlation across 998 consecutive return samples

This is sufficient to proceed with historical strategy research. Binance direct data is the documented alternative for multi-year crypto history.

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
- Broker H4 bars must be checked against H1 reconstruction over overlapping history; unusually deep H4 history is not trusted solely because it is returned by MT5.

## S01 evidence so far

S01 Trend Pullback v0.1 was frozen before first results.

- XAU/USD: overall positive, but development and validation are near flat; 2025–2026 is much stronger.
- EUR/USD: development near flat, validation and final test clearly negative.
- Trade-ledger timing/accounting checks pass on both uploaded ledgers.
- Cross-market generalization is not demonstrated; S01 v0.1 is not a candidate.
- Candle-level feature audit and H1/H4 consistency audit remain before broader unchanged testing on GBPUSD/USDJPY.

Detailed evidence: `research/experiments/EXP-2026-004-s01-baseline.md`.

## Initial strategy families

- S01 Trend Pullback — **v0.1 baseline tested; not candidate**
- S02 Structure Breakout
- S03 Momentum Continuation
- S04 Mean Reversion
- S05 Volatility Expansion

A strategy is promoted only after reproducible evidence. Most hypotheses are expected to be rejected.

## Phase status

1. MT5 connection / symbol discovery — **DONE**
2. Normalized MT5/Binance adapters — **DONE for historical research**
3. Representative data-quality/history audit — **DONE / G1 PASS**
4. Local reproducible persistence/backfill — **DONE for EURUSD/XAUUSD**
5. Frozen S01 backtest pipeline — **RUN on EURUSD/XAUUSD; not candidate**
6. Candle-level / H1-H4 integrity audit — **IN PROGRESS**
7. Cross-instrument / OOS / walk-forward / robustness evidence — **PENDING**
8. Live immutable forward test — **PENDING**
9. Customer-value validation / SaaS UI — **PENDING**

## Durable project-state rule

Major decisions, research conclusions, strategy definitions and implementation changes should be written to this repository. Chat is for discussion; the repository is the project source of truth.
