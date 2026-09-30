# Project Brief

_Last updated: 2026-10-01_

## Goal

Create a low-cost AI market-intelligence SaaS that continuously scans markets, generates structured AI BUY/SELL/NO_TRADE decisions from causally available derived market features, applies deterministic risk/publication guardrails, and keeps an immutable verified performance record.

## Core positioning

The product direction was formally changed on 2026-09-28 to **AI-first intelligence with deterministic guardrails and verifiable evidence**.

Public product name: **VowSig**. Historical SignalProof AI references remain in provenance-bearing artifacts.

> AI finds the setup. Risk rules verify it. Every signal stays on the record.

The existing S02 rule engine remains active as an unchanged benchmark/control. It is not relabeled as AI.

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
- AI-v1 shadow inference on XAUUSD, USTEC and US30 using causally available engineered features
- Structured BUY/SELL/NO_TRADE model outputs with deterministic publication/risk guardrails
- Separate immutable AI inference / signal lifecycle ledger
- AI reasoning summaries that do not expose hidden chain-of-thought
- Web dashboard, alerts and subscriptions developed in parallel with validation

### Out of scope for v1

- Holding customer funds
- Fully automated copy trading / broker-connected AI execution before a separately approved execution phase
- Portfolio management
- Native mobile apps
- Rebuilding a full charting terminal
- Redistributing raw broker market data without explicit rights
- Marketing unsupported accuracy/win-rate claims

## Four validation gates

| Gate | Question | Status |
|---|---|---|
| G1 | Can MT5/Exness and Binance reliably provide the research data we need? | **PASS — RESEARCH DATA** |
| G2 | Can each intended production source legally support commercial derived signals? | **PASS — Exness commercial derived-signal permission confirmed by project owner** |
| G3 | Can at least one strategy demonstrate robust positive expectancy after costs? | **IN PROGRESS — S02 XAU historical robustness passed; transfer is partial; immutable forward evidence next; not candidate** |
| G4 | Will traders pay for verified and explainable signals? | **READY TO START — FEEDBACK MECHANISM VERIFIED; NO REAL-USER EVIDENCE YET** |

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
- new-market transfer is complete and partial: USTEC and US30 meet the frozen descriptive support rule, while XAGUSD, US500 and USOIL do not;
- the USTEC/US30 final-test edges are small (~+0.012R/trade each), so they are supporting observations rather than strong independent candidates;
- genuinely new immutable forward evidence remains required before candidate status.

See:

- `strategies/S02-structure-breakout/v0.1.md`
- `research/experiments/EXP-2026-009-s02-structure-breakout-baseline.md`

## Initial strategy families

- S01 Trend Pullback — **v0.1 rejected for general FX; XAU lead retained**
- S02 Structure Breakout — **XAU forward test active; USTEC + US30 selected as secondary launch signal markets; not candidate**
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
- EXP-2026-012 — S02 new-market transfer protocol + result
- EXP-2026-013 — S02 immutable forward-test ledger protocol
- EXP-2026-014 — AI-v1 shadow inference preregistration

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
10. S02 new-market transfer — **DONE / PARTIAL TRANSFER (USTEC + US30)**
11. Live immutable forward-test infrastructure — **DONE / XAUUSD + USTEC + US30 ACTIVE**
12. Early Access SaaS MVP — **LIVE / RAILWAY PUBLIC BETA**
13. AI-0 product naming — **SUPERSEDED / HISTORICAL NAME: SIGNALPROOF AI; CURRENT PUBLIC BRAND: VOWSIG**
14. AI-1 architecture + preregistration — **DONE / FROZEN PRE-ACTIVATION**
15. AI-v1 shadow implementation + activation — **DONE / LIVE FORWARD COLLECTION ACTIVE**
16. AI-v1 read-only observability — **DONE / VPS VERIFIED**
17. AI Insights UI — **DONE / VPS + CLOUD VERIFIED**
18. Cloud snapshot durability v0.1 — **DONE / CONTROLLED REDEPLOY VERIFIED**
19. Early Access feedback & customer discovery v0.1 — **DONE / LIVE + CONTROLLED REDEPLOY VERIFIED**
20. AI-v1 index missed-inference diagnostic v0.1 — **DONE / ISSUE #10**
21. AI-v1 index H1 boundary probe v0.1 — **DONE / ISSUE #11**
22. AI-v1 scheduled-run forensic diagnostic v0.1 — **DONE / ISSUE #12**
23. AI-v1 historical tick boundary diagnostic v0.1 — **DONE / ISSUE #13**
24. AI-v1 MT5 rates-cache access correlation v0.1 — **DONE / ISSUE #14**
25. AI-v1.1 MT5 rates synchronization correction v0.1 — **DONE / CUTOVER + CLOUD VERIFIED / ISSUE #15 CLOSED**
26. VowSig public rebrand v0.1 — **DONE / PRODUCTION + NATURAL CONTINUITY VERIFIED / ISSUE #16 CLOSED**
27. First cohort G4 customer-value evidence v0.1 — **NEXT PRODUCT MILESTONE / ISSUE #9**
28. Organic acquisition & SEO v0.1 — **DEFERRED / AFTER INITIAL REAL-USER EVIDENCE**

## Durable project-state rule

Major decisions, research conclusions, strategy definitions and implementation changes should be written to this repository. Chat is for discussion; the repository is the project source of truth. The canonical cross-chat continuation and operating contract is `docs/CURRENT-HANDOFF.md`; future chats must reconcile it against current `main` before acting.


## Immediate launch objective — 2026-09-21

The application should not wait for 100 forward trades before users can see and test it.

Target: **Early Access Beta in 3–5 days**, following `docs/launch-plan-5-day-beta.md`.

Forward validation continues unchanged and constrains performance claims. Product development, usability testing and customer discovery now run in parallel.


## Launch universe decision — 2026-09-21

The first Early Access release is intentionally broader than XAU/USD.

**Live-signal launch markets:**

- XAU/USD (`XAUUSD`) — primary historical lead and active immutable forward test;
- NASDAQ 100 (`USTEC`) — secondary market; met the frozen transfer-support rule;
- DOW 30 (`US30`) — secondary market; met the frozen transfer-support rule.

**Research/monitoring markets shown in-product, but not promoted as equally validated live-signal markets:**

- EUR/USD;
- GBP/USD;
- USD/JPY;
- XAG/USD;
- S&P 500;
- WTI.

The product will expose evidence status per market instead of implying equal strategy validation.

## G2 update — 2026-09-21

The project owner confirms that separate Exness permission covering the intended commercial derived-signal use has already been obtained.

**G2 is therefore marked PASS for the intended Exness-based launch use case.**

This pass is based on the separate permission held by the project owner, not on the default retail Client Agreement. The permission artifact itself should be retained securely outside the public repository if confidential.

Paid replacement data providers are deferred until application revenue justifies the expense.


## AI-first product pivot — 2026-09-28

The owner formally approved the new product direction after authenticated TradingTop research.

AI-v1 is intentionally introduced **alongside** S02 rather than replacing it.

Frozen AI-v1 references:

- `docs/ai-0-product-naming.md`
- `docs/ai-v1-architecture.md`
- `docs/ai-v1-provider-selection.md`
- `docs/ai-v1-feature-definitions.md`
- `config/ai_v1_feature_schema.json`
- `config/ai_v1_policy.txt`
- `config/ai_v1_provider.json`
- `config/ai_v1_openai_response_schema.json`
- `config/ai_v1_decision_schema.json`
- `config/ai_v1_guardrails.json`
- `docs/ai-v1-ledger-spec.md`
- `config/ai_v1_activation_schema.json`
- `research/experiments/EXP-2026-014-ai-v1-shadow-preregistration.md`

AI-v1.1 is now the active hourly shadow runtime on XAUUSD, USTEC and US30, with frozen decision protocol AI-v1.0. AI-v1.0 runtime is retired and its scheduler remains Disabled; its evidence is preserved separately. The exact provider/model and inference parameters remain frozen to OpenAI `gpt-5.4-2026-03-05`. Broker execution remains disabled. VowSig is the public product brand at `https://vowsig.com`. The governed public-surface correction is upstream-valid, and the first natural post-cutover cycle cryptographically extended every AI-v1.1 pre-cutover ledger head without reset, fork, or backfill. The next product milestone is owner-controlled first-cohort G4 customer-value evidence collection under GitHub Issue #9 while AI-v1.1 forward collection continues unchanged.

The active S02 forward protocols and their ledgers must remain unchanged.
