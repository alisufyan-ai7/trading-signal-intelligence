# Validation Gates

This file is the concise checklist for advancing the project. Detailed evidence belongs in `research/experiments/` and material decisions belong in `docs/decision-log.md`.

## G1 — Research data reliability

**Status:** PASS — RESEARCH DATA

Evidence:

- local Windows MT5 + Python connection works;
- Exness demo exposes 357 symbols across the target asset classes;
- canonical mappings are explicit and source-aware;
- representative H1 history is multi-year for EURUSD, XAUUSD, USTEC and USOIL;
- all representative audit series are strictly increasing with zero duplicate timestamps;
- tick volume is populated across all tested closed bars;
- historical spread fields are available and asset-specific;
- Binance Spot bars normalize to the same internal candle schema;
- Exness/Binance BTCUSDT H1 return correlation over 998 consecutive samples was 0.999451;
- Exness BTCUSDT history is only ~108 days, so Binance direct data is the documented primary crypto-history source.

Operational limitations / hardening still open:

- [ ] identify and classify the single observed 24h Exness BTCUSDT gap;
- [ ] implement session-aware gap classification for non-24/7 instruments;
- [ ] run EXP-2026-003 long-running collector soak test;
- [ ] validate higher-fidelity tick/bid-ask execution-cost sensitivity before live-execution claims.

These remaining items do not block historical strategy research. Detailed evidence: `research/experiments/EXP-2026-002-data-quality-audit.md`.

## G2 — Commercial source rights

**Status:** OPEN / BLOCKED FOR EXNESS PRODUCTION ASSUMPTION

- [ ] obtain written clarification from Exness for commercial server-side derived-signal use without raw-feed redistribution; or
- [ ] identify and approve an alternative production data source with suitable rights;
- [ ] review Binance commercial terms for the intended production usage;
- [ ] document permitted and prohibited data handling per source.

R&D may continue while G2 is unresolved. Commercial launch must not assume rights that have not been confirmed.

## G3 — Strategy robustness

**Status:** STARTING — BACKTEST INFRASTRUCTURE NEXT

- [ ] implement reproducible normalized-data persistence/backfill;
- [ ] complete reproducible backtest pipeline;
- [ ] freeze S01 baseline rules before looking at final test results;
- [ ] include spread/fees/slippage assumptions;
- [ ] run in-sample / out-of-sample split;
- [ ] run walk-forward validation;
- [ ] run parameter-sensitivity tests;
- [ ] test multiple instruments/regimes;
- [ ] begin immutable live forward test only after a candidate survives research validation.

A strategy is not promoted on win rate alone. Expectancy, drawdown, sample size, robustness and cost sensitivity are required.

## G4 — Customer value

**Status:** NOT STARTED

- [ ] define target trader segment;
- [ ] prototype verified signal detail/performance views;
- [ ] interview/test with real traders;
- [ ] measure whether verified history + explanation changes willingness to pay;
- [ ] test pricing only after there is credible forward evidence.

Do not validate G4 by asking whether users like "AI signals" in the abstract. Validate whether they value the specific evidence-driven product behavior.
