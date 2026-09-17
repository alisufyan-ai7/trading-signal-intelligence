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
- Binance direct market data for crypto
- Historical backtesting with spread/transaction-cost assumptions
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
| G1 | Can MT5/Exness and Binance reliably provide the research data we need? | **PROTOTYPE PASS — robustness validation in progress** |
| G2 | Can each intended production source legally support commercial derived signals? | OPEN — Exness requires caution/written clarification |
| G3 | Can at least one strategy demonstrate robust positive expectancy after costs? | NOT STARTED |
| G4 | Will traders pay for verified and explainable signals? | NOT STARTED |

## G1 evidence so far

On 2026-09-17 the Windows MT5 probe successfully connected to `Exness-MT5Trial15`, discovered 357 instruments, returned a live EURUSD bid/ask quote, and returned 100 normalized H1 candles with UTC timestamps, tick volume, spread, and open/closed state. A separate Binance Spot probe returned 100 normalized BTCUSDT H1 candles on the same UTC timeline.

This proves the adapter concept, not long-run production reliability. Remaining G1 work includes symbol inventory/canonical mapping, maximum history depth, gaps/duplicates, representative multi-asset checks, spread/session behavior, and cross-source crypto comparison.

## Initial research universe

- FX: EURUSD, GBPUSD, USDJPY
- Metals: XAUUSD, XAGUSD
- Indices: NAS100/USTEC, US500, US30
- Energy: USOIL
- Crypto: BTCUSDT, ETHUSDT, SOLUSDT (Binance direct); broker CFD equivalents may be used only for comparison/research

Broker symbols must be discovered dynamically and mapped to canonical internal symbols.

## Data-model rule discovered during G1

Do not derive canonical symbols from broker `currency_base` / `currency_profit` fields alone. Exness crypto metadata showed inconsistent base-currency values for some token symbols. Canonical mapping must be explicit and source-aware, using source symbol, broker path, description, and verified mappings.

## Initial strategy families

- S01 Trend Pullback
- S02 Structure Breakout
- S03 Momentum Continuation
- S04 Mean Reversion
- S05 Volatility Expansion

A strategy is promoted only after reproducible evidence. Most hypotheses are expected to be rejected.

## Success criteria for Phase 0

1. MT5 probe can connect to a local terminal and enumerate instruments. **DONE**
2. Historical bars can be collected with UTC-safe timestamps and source metadata. **PROTOTYPE DONE**
3. Binance historical/live crypto data can be normalized to the same schema. **HISTORICAL PROTOTYPE DONE; LIVE STREAM PENDING**
4. Data-quality checks detect gaps, stale prices and obviously divergent feeds. **PENDING**
5. One reproducible backtest pipeline runs end-to-end with costs and no look-ahead leakage. **PENDING**

## Durable project-state rule

Major decisions, research conclusions, strategy definitions and implementation changes should be written to this repository. Chat is for discussion; the repository is the project source of truth.
