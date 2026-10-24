# Trading Signal Intelligence

## Current verified VowSig operations (2026-10-24)

The private repository's latest backup/recovery handoff is **[VowSig operational status — 2026-10-24](docs/vowsig-operational-status-2026-10-24.md)**. The Windows VPS has an **active daily 04:15 local-time encrypted S02-only backup** to AWS S3 and Backblaze B2. The first manual and first scheduled backups both passed independent real two-cloud restore; **two backup IDs** and **four encrypted data/receipt versions per provider** passed the subsequent read-only GFS version inventory. Source evidence: [Issue #67](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/67), [draft PR #85](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/85), EXP053–EXP059.

The requested **30-day daily / 8-week weekly / 12-month monthly** historical retention policy is **coded and read-only verified**; **automatic cloud deletion is not enabled**. The installed scope covers `data/forward.sqlite` only. The first natural next-day task result, delivered failure alerts, broader-IP backups and owner-gated version-aware cleanup remain pending. Read the linked status before interpreting the legacy launch-stage description below. Broker execution remains disabled.

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

## Historical initial-build status (retained as dated launch context)

**Earlier phase description:** Phase 1: Early Access product build + continuing forward validation.

An early project plan stated a 3–5 day launch target. **That estimate is historical, not a current October 24, 2026 deadline or validated product readiness statement.** Current operating milestones and pending work are in [the October 24 operational handoff](docs/vowsig-operational-status-2026-10-24.md).
