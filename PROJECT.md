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
| G3 | Can at least one strategy demonstrate robust positive expectancy after costs? | **IN PROGRESS — S02 XAU passes historical parameter + recent temporal robustness; new-market transfer and live forward evidence next; not candidate** |
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
- GBP/USD refreshed: validation -0.0543R/trade; final -0.0686R/trade.
- USD/JPY refreshed: validation -0.1232R/trade; final -0.1798R/trade.
- XAU/USD: near-flat through validation, then strong in already-observed 2025–2026; retained only as a separate research lead.

Integrity audits did not identify an engine/data defect explaining the FX failures.

Detailed evidence:

- `research/experiments/EXP-2026-003-s01-baseline.md`
- `research/experiments/EXP-2026-008-s01-cross-fx-disposition.md`

### S02 Structure Breakout v0.1

**Status: RESEARCH — ROBUSTNESS IN PROGRESS; NOT CANDIDATE.**

Frozen before first S02 result on the predeclared universe EUR/USD, GBP/USD, USD/JPY and XAU/USD.

Baseline OOS net expectancy:

- EUR/USD: validation +0.0459R/trade; final -0.0127R/trade
- GBP/USD: validation -0.1858R/trade; final +0.0444R/trade
- USD/JPY: validation +0.1764R/trade; final -0.1631R/trade
- XAU/USD: validation +0.0986R/trade; final +0.2323R/trade

EUR/USD and XAU/USD candle-level audits passed 10/10 sampled trades, and all four trade ledgers passed mechanical/accounting checks.

XAU/USD is the only market positive in both OOS splits and each observed OOS calendar year 2023–2026. Repricing the frozen XAU ledger at 2x and 3x the baseline spread proxy remains positive. However:

- XAU development is negative;
- OOS gains are carried by longs, a post-result diagnostic that cannot be retrofitted into v0.1;
- the other markets show strong temporal instability;
- the 17-configuration post-baseline local sensitivity test kept XAU positive in both OOS splits for 15/17 variants and positive in the final test for 17/17 variants;
- all 17 XAU local variants remained negative in development, reinforcing the possibility of a later regime change rather than a stationary full-history edge;
- the exact 23-configuration pre-first-result specification neighborhood is now complete: XAU is positive in both OOS splits for 20/23 variants and positive in the final test for 23/23;
- the three XAU validation-negative exact-spec variants are structure window 30, stop 1.50 ATR, and target 2.0R;
- all 23 XAU variants remain negative in development, so the evidence is parameter-robust but temporally non-stationary;
- fixed-rule temporal analysis is complete: XAU has six consecutive positive half-years from 2023-H2 through 2026-H1, 15 consecutive positive rolling-12m windows beginning 2022-01 through 2025-07, and six consecutive recent positive-reference -> positive-forward persistence pairs;
- USDJPY demonstrates the regime-risk caution: historically strong persistence can still fail abruptly, as it did from 2025 onward;
- new-market transfer evidence and genuinely new forward evidence remain required before candidate status.

See:

- `strategies/S02-structure-breakout/v0.1.md`
- `research/experiments/EXP-2026-009-s02-structure-breakout-baseline.md`

## Initial strategy families

- S01 Trend Pullback — **v0.1 rejected for general FX; XAU lead retained**
- S02 Structure Breakout — **v0.1 baseline complete; robustness warranted; not candidate**
- S03 Momentum Continuation — IDEA
- S04 Mean Reversion — IDEA
- S05 Volatility Expansion — IDEA

Most hypotheses are expected to be rejected. Promotion requires reproducible after-cost evidence, robustness and forward testing.

## Experiment ID map

Canonical IDs are unique:

- EXP-2026-001 — MT5 symbol discovery
- EXP-2026-002 — Binance normalization
- EXP-2026-003 — S01 frozen baseline
- EXP-2026-004 — source-rights research
- EXP-2026-005 — customer-value research plan
- EXP-2026-006 — data-quality / G1 audit
- EXP-2026-007 — collector soak test
- EXP-2026-008 — S01 cross-FX disposition
- EXP-2026-009 — S02 frozen baseline
- EXP-2026-010 — S02 robustness protocol reconciliation + exact-spec result
- EXP-2026-011 — S02 temporal stability protocol + result
- EXP-2026-012 — S02 new-market transfer protocol

## Phase status

1. MT5 connection / symbol discovery — **DONE**
2. Normalized MT5/Binance adapters — **DONE for historical research**
3. Representative data-quality/history audit — **DONE / G1 PASS**
4. Local reproducible persistence/backfill — **DONE for initial FX/XAU research universe**
5. S01 frozen backtest + integrity audits + cross-FX disposition — **DONE / GENERAL FX REJECTED**
6. S02 frozen specification + implementation + first baseline — **DONE**
7. S02 post-baseline local sensitivity — **DONE / XAU BROADLY ROBUST**
8. S02 exact predeclared specification neighborhood — **DONE / XAU 20 OF 23 BOTH-OOS POSITIVE**
9. S02 temporal / fixed-rule walk-forward stability — **DONE / RECENT XAU REGIME PERSISTENT**
10. S02 new-market transfer — **NEXT**
11. Live immutable forward test — **PENDING**
12. Customer-value validation / SaaS UI — **PENDING**

## Durable project-state rule

Major decisions, research conclusions, strategy definitions and implementation changes should be written to this repository. Chat is for discussion; the repository is the project source of truth.
