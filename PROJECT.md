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
| G2 | Can each intended production source legally support commercial derived signals? | **OPEN — launch blocker** |
| G3 | Can at least one strategy demonstrate robust positive expectancy after costs? | **IN PROGRESS — first S01 baseline completed on XAU/USD** |
| G4 | Will traders pay for verified and explainable signals? | **NOT STARTED** |

## G1 evidence

Representative audits established multi-year H1 history for EURUSD, XAUUSD, USTEC and USOIL with strictly increasing timestamps, zero duplicate timestamps, populated tick volume and historical spread fields. Binance Spot normalizes to the same internal candle schema and is the primary long-horizon crypto research source.

Exness BTCUSDT currently exposes only ~108 days of H1 history on the tested demo server, so it is comparison-only for long-horizon crypto research.

## G3 evidence so far

S01 Trend Pullback v0.1 was frozen before inspecting results.

First completed instrument: XAU/USD.

- 1,124 trades
- overall net expectancy: +0.083R/trade
- development expectancy: +0.012R/trade
- validation expectancy: +0.005R/trade
- final-test expectancy (2025 onward): +0.363R/trade
- validation is effectively flat, so the strategy is **not yet a candidate**
- ledger-level timing/accounting checks passed
- EUR/USD result remains pending because its first H4 backfill attempt hit a transient MT5 terminal call failure; the backfill tool is now paginated and retried

The strong recent XAU/USD period is interesting but cannot by itself establish robust alpha. Cross-instrument testing, candle-level audit, cost stress, walk-forward testing and parameter-neighborhood analysis remain required.

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

## Initial strategy families

- S01 Trend Pullback — **v0.1 baseline tested on XAU/USD; not candidate**
- S02 Structure Breakout — idea
- S03 Momentum Continuation — idea
- S04 Mean Reversion — idea
- S05 Volatility Expansion — idea

A strategy is promoted only after reproducible evidence. Most hypotheses are expected to be rejected.

## Research-integrity rules

1. Freeze strategy versions before viewing their test results.
2. Do not silently rewrite a failed version.
3. Separate development/validation/test periods.
4. Once a holdout has been viewed, do not reuse it as an untouched holdout for a revised strategy derived from those results.
5. Use source-aware, instrument-specific transaction-cost assumptions.
6. AI does not generate the underlying trading edge; quantitative rules do.
7. Preserve immutable forward evidence before commercial claims.

## Phase status

1. MT5 connection / symbol discovery — **DONE**
2. Normalized MT5/Binance adapters — **DONE for historical research**
3. Representative data-quality/history audit — **DONE / G1 PASS**
4. Local reproducible persistence/backfill — **WORKING; MT5 backfill hardened with pagination/retries**
5. Frozen S01 backtest pipeline — **FIRST XAU/USD RUN COMPLETE**
6. EUR/USD S01 baseline — **PENDING H4 BACKFILL RETRY**
7. OOS / walk-forward / robustness evidence — **PENDING**
8. Live immutable forward test — **PENDING**
9. Customer-value validation / SaaS UI — **PENDING**

## Durable project-state rule

Major decisions, research conclusions, strategy definitions and implementation changes should be written to this repository. Chat is for discussion; the repository is the project source of truth.
