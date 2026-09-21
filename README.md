# Trading Signal Intelligence

Research and engineering repository for a broker-neutral, verified trading-signal intelligence SaaS.

## Product thesis

Build a system that **finds the trade, explains the trade, shows the risk, and proves the record**.

The quantitative engine generates candidate setups. AI is used for explanation, context, filtering, research assistance, and user-facing intelligence—not as an unconstrained oracle that invents trades.

## Current architecture decision

- **Initial multi-asset feed:** MetaTrader 5 terminal on Windows, accessed through the official `MetaTrader5` Python package and connected to Exness.
- **Crypto feed:** Binance direct REST/WebSocket market-data APIs.
- **Production principle:** strategies only consume our normalized internal market-data schema and never depend directly on a broker-specific symbol or API.
- **Data-rights principle:** Exness commercial derived-signal use is cleared for the intended launch use case via separate permission confirmed by the project owner; raw-feed redistribution remains out of scope unless separately authorized.

## Four project gates

1. **G1 — Data reliability:** Can MT5 + Exness provide sufficiently reliable research data, and can Binance provide a robust direct crypto feed?
2. **G2 — Commercial data rights:** Do we have explicit permission/licensing for the production use of each source to create commercial derived signals?
3. **G3 — Strategy evidence:** Can at least one strategy survive costs, out-of-sample testing, walk-forward testing, robustness checks, and live forward testing?
4. **G4 — Customer value:** Will traders pay for verified, explainable signal intelligence?

No paid SaaS launch should be treated as validated until all four gates have acceptable answers.

## Repository map

- `PROJECT.md` — source-of-truth project brief and current status
- `docs/architecture.md` — system architecture
- `docs/decision-log.md` — dated architectural/product decisions
- `docs/data-sources.md` — feed capabilities and source status
- `docs/legal-data-rights.md` — commercial-use research and open questions
- `docs/research-plan.md` — staged validation plan
- `strategies/` — versioned strategy hypotheses/specifications
- `src/` — reusable Python package
- `scripts/` — local research/probe scripts
- `config/` — example configuration, never credentials

## Security

Never commit broker passwords, MetaTrader credentials, Binance API keys, tokens, or private account identifiers. Use environment variables or a secrets manager.

## Status

**Phase 1: Early Access product build + continuing forward validation.**

Target launch is 3–5 days. Product development now runs in parallel with immutable strategy validation.
