# Validation Gates

This file is the concise checklist for advancing the project. Detailed evidence belongs in `research/experiments/` and material decisions belong in `docs/decision-log.md`.

## G1 — Research data reliability

**Status:** PROTOTYPE PASS — robustness validation in progress

Evidence already obtained:

- local Windows MT5 + Python connection works;
- Exness demo exposes 357 symbols;
- live EURUSD bid/ask works;
- normalized MT5 H1 bars work with UTC timestamps, tick volume, spread and open/closed state;
- Binance Spot H1 bars normalize to the same schema.

Remaining:

- [ ] complete symbol/category inventory;
- [ ] verify canonical mappings for the initial universe;
- [ ] audit H1 history depth on FX, metal, index, energy and crypto;
- [ ] verify duplicates/gaps;
- [ ] characterize spread distributions;
- [ ] verify tick-volume coverage;
- [ ] compare Exness BTCUSDT versus Binance BTCUSDT;
- [ ] test long-running collection reliability;
- [ ] document source/session limitations.

Target next evidence: `research/experiments/EXP-2026-002-data-quality-audit.md`.

## G2 — Commercial source rights

**Status:** OPEN / BLOCKED FOR EXNESS PRODUCTION ASSUMPTION

- [ ] obtain written clarification from Exness for commercial server-side derived-signal use without raw-feed redistribution; or
- [ ] identify and approve an alternative production data source with suitable rights;
- [ ] review Binance commercial terms for the intended production usage;
- [ ] document permitted and prohibited data handling per source.

R&D may continue while G2 is unresolved. Commercial launch must not assume rights that have not been confirmed.

## G3 — Strategy robustness

**Status:** NOT STARTED

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
