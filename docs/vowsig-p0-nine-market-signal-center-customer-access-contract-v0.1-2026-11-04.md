# VowSig P0 — nine-market Signal Center and customer-facing access contract v0.1

**Date:** 2026-11-04. **Status:** DRAFT P0 / OWNER REVIEW; NOT an authorization to implement, deploy, merge, release signals, enable alerts or trade. **Source boundary:** this conversation and the private GitHub repository `alisufyan-ai7/trading-signal-intelligence` ONLY. **Canonical parent:** [PR #93 architecture](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93), exact reviewed planning HEAD `b81e6909dcf58957fb311f8cc50f74bbeef63318`; [P0 source review](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93#issuecomment-6605762017). This document is a *bounded customer-facing P0 clarification*, not a competing system architecture. No production code or trading protocol changes.

## 1. Answer to the owner's nine-market and naming questions

**Recommended product direction:** The Signal Center's **All Markets** directory and optional member watchlist can display **all NINE existing research markets**. Its **Signals** feed must display detailed BUY/SELL/NO_TRADE and active shadow setup lifecycles **only for currently permitted Core AI-v1.1 markets**. A market being in the directory is NOT a license, evidence of an active signal, commercial eligibility, or a promise that per-signal data will become available. Do not backfill missing signals with fabricated cards, stale setups or restricted internal events.

Customers should not be forced to understand `AI-v1.1`, `AI-v1.2.1`, `AI-v1.3` to use VowSig. Navigation is organized by **Signals, Markets, History, Learn, Watchlist**. Technical version/program identity remains mandatory in **expandable Methodology / Record provenance**, as well as in member-history filtering when valuable, and is fully visible as a first-class analysis dimension in **private admin**. Customer-friendly status labels are derived from true program permissions + freshness + lifecycle; version labels are not substituted with marketing confidence claims.

A useful flow is **find market -> see whether a research signal is available -> inspect entry/risk/lifecycle (only if permitted) -> examine verified record/results -> learn -> save/watch and return**. No broker execution and no customer trade alerts in Free v0.1.

## 2. Exact nine-market catalog (planned)

| Market | Customer display | Internal source program (admin) | Market-directory visibility | Detailed current/recent research signals in customer Signal Center |
| --- | --- | --- | --- | --- |
| XAUUSD | Gold (XAU/USD) | Core AI-v1.1 | Yes | YES, only permitted sanitized **SHADOW_ONLY** core signal details, when eligible and fresh |
| USTEC | NASDAQ 100 (USTEC) | Core AI-v1.1 | Yes | YES, only permitted sanitized **SHADOW_ONLY** core signal details, when eligible and fresh |
| US30 | Dow 30 (US30) | Core AI-v1.1 | Yes | YES, only permitted sanitized **SHADOW_ONLY** core signal details, when eligible and fresh |
| EURUSD | EUR/USD | Expansion AI-v1.2.1 | Yes, aggregate research status | **NO**; validation progress/availability only, no BUY/SELL detail or levels |
| XAGUSD | Silver (XAG/USD) | Expansion AI-v1.2.1 | Yes, aggregate research status | **NO**; validation progress/availability only, no BUY/SELL detail or levels |
| USOIL | WTI Oil (USOIL) | Expansion AI-v1.2.1 | Yes, aggregate research status | **NO**; validation progress/availability only, no BUY/SELL detail or levels |
| BTCUSDT | Bitcoin (BTC/USDT) | Crypto AI-v1.3 | Yes, aggregate research status | **NO**; validation progress/availability only, no BUY/SELL detail or levels |
| ETHUSDT | Ethereum (ETH/USDT) | Crypto AI-v1.3 | Yes, aggregate research status | **NO**; validation progress/availability only, no BUY/SELL detail or levels |
| SOLUSDT | Solana (SOL/USDT) | Crypto AI-v1.3 | Yes, aggregate research status | **NO**; validation progress/availability only, no BUY/SELL detail or levels |

Every listed market must distinguish `cataloged`, `program_observable`, `signal_detail_permitted`, `research_snapshot_fresh`, `current_signal_present`, `commercial_customer_eligible` as independent backend fields; the last defaults **FALSE** for all current offerings. The current snapshot actually supplies a separate nine-market catalog/validation-program surface; do not infer all programs publish permitted signal events. Do not call restricted expansion/crypto research "active signals". When a market has no new permitted signal, display **No current research signal** or **Validation in progress**, not a fake WAIT or BUY/SELL.

**S02 exception:** The deterministic S02 forward benchmark is *not* a tenth AI market/program and never powers the Signals feed. Existing `/api/signals` already publicly exposes its benchmark lifecycle rows, including some entry/stop/target data. Retain its separate Evidence/Benchmark treatment and legacy public contract unless a separately approved compatibility/privacy change is made; S02 is not interchangeable with the expansion/crypto no-per-signal policy.

## 3. Customer information hierarchy (recommendation)

**Public top navigation:** Signals (a clear research-only public preview), Markets, How It Works, Learn, Evidence, Sign in / Create free account. Preserve existing SEO/market/Learn/Evidence routes until an explicitly reviewed rewrite/migration; do not create thin pages claiming nine commercially available signal products.

**Signed-in Free navigation:** **Signal Center** (default landing), Markets (all nine), Verified History (permitted core only), Learn, Watchlist; profile holds preferences/security/account. A compact dashboard overview is optional, not a competing first landing destination. Put learning links directly beside signal concepts such as stop, target, NO_TRADE, risk and outcome. No `AI-v1.x` selection needed for normal use.

**Signal Center tabs (proposed):**
1. **Research Signals:** Fresh permitted core shadow setups, clear research badge, issue/source time and age, lifecycle, direction/NO_TRADE, entry/SL/TP1/TP2 only when permitted. State and absence are explicit; no "buy now" buttons.
2. **All Markets (9):** Search/filter by Gold & Indices, FX/Metals/Energy, Crypto; progress and data recency for each. Restricted six markets show **Research validation — detailed signals unavailable** with allowed aggregate metrics and learning only. No signal-result lists with private fields.
3. **Verified History:** Only user-permitted sanitized core decision/signal/lifecycle history; include losses, breakevens, NO_TRADE, blocked/rejected counts (according to tier permissions), costs, sample periods, and unresolved items separated.

**Signal detail card** is customer-readable: market, observation timestamp (UTC and chosen local zone), `SHADOW_ONLY RESEARCH`, latest lifecycle status, direction or NO_TRADE, entry/stop/targets when allowed, rationale, risk/invalidation, estimated vs measured cost and end result when completed, link to hash-backed record. The expandable **Record & Methodology** section holds exact model/program/protocol/source identity, confidence calibration disclaimer, record provenance, historical/forward classification and metric computation definition. Never present raw model confidence as probability of profit.

**Admin-only** retains explicit AI-v1.0 legacy vs v1.1 core vs v1.2.1 expansion vs v1.3 crypto vs independent S02, diagnostic guard failures, raw internal counts (but never secrets, raw feed or hidden reasoning via dashboard), exact release states and reconciled performance for authorized data.

## 4. Launch permissions: role, source, lifecycle and rights jointly constrain the payload

| Feature / field | Anonymous Public | Verified Free | Private owner/admin |
| --- | --- | --- | --- |
| Nine cataloged markets and permitted aggregate program-health status | Yes, sanitized | Yes, sanitized + watchlist | Yes, diagnostics subject to rights |
| Core three permitted shadow signal summaries | Preserve current v1 public core contract; optionally preview in new v2 | Full allowed sanitized research history and detail after separate evidence export | Source-reconciled read-only detail, operator flags |
| Detailed expansion/crypto events, active BUY/SELL, entry/stop/targets | **Never under current rules** | **Never under current rules** | Owner-authorized private evidence analysis only; not customer exposure |
| S02 benchmark | Preserve existing separate S02 Evidence and v1 APIs | Same separate benchmark, never AI customer signal | Independent control analysis |
| Source lineage/model version | Summary methodology and record provenance | Expandable Record & Methodology, not navigation primary | First-class filters/diagnostics |
| Signal eligibility | SHADOW_ONLY only; no commercial alerts | SHADOW_ONLY only; no commercial alerts | Eligibility investigation, **no release override** |
| Watchlist/saved filters | None | Own nine-market watchlist; restricted markets display progress only | Aggregated usage only, not cross-user impersonation |
| Paid subscription/broker execution/real-money recommendations | None | None | Disabled |

**Fail-closed policy:** `role_allowed AND record_program_allowed AND source_data_permitted AND rights_permitted AND publication_gate_allowed AND freshness_state_safe` before returning any signal-level member detail; distinguish archival/history access from current-signal recency. `commercial_customer_eligible` additionally requires separate qualified per-signal release, never implied by registration. Never hide private data solely in JS/CSS. Prevent leaks through v1 APIs, v2 aliases, enumerated IDs, search filters, errors, static exports, caches, logs, snapshots and client bundles; keep v1 public compatibility policy explicit.

**Legacy API caution:** Current anonymous `GET /api/ai/insights` already includes detailed sanitized core entries/stops/TP1/TP2, reason and net R; `GET /api/signals` publishes separate S02 benchmark details. Free value **cannot** be defined as obscuring those existing public fields without approved backend/API changes. Public adverse-outcome totals and methodology must remain honest.

## 5. Visible status contract (never infer availability from 'nine markets')

**Orthogonal server fields:** `market_catalog_status`, `data_snapshot_freshness`, `source_program_status`, `signal_publication_permission`, `signal_lifecycle`, `record_validity`, `customer_eligibility`. Proposed customer-language mapping:
- `NO_CURRENT_DATA` / `PROVIDER_ERROR` -> "Data unavailable / research paused" + verified as-of UTC; no current direction.
- `STALE` / `PAUSED` -> "Updates delayed" and last valid timestamp; **do not replay old active directions** as current.
- `NO_TRADE` -> "No trade identified" / "No research setup" with permitted explanation; not an unsuccessful trade.
- `REJECTED` / `GUARD_BLOCKED` -> "Setup not published" when permitted, otherwise aggregate excluded count; not an active signal.
- `SHADOW_SIGNAL_ACTIVE` -> "Open research setup — SHADOW_ONLY" **only for permitted core**, with freshness and age.
- `PARTIAL` -> "Partially progressed (research)" with one parent signal and single net-R accounting.
- `CLOSED` / `EXPIRED` / `INVALIDATED` -> final historical research status; never recirculate as current.
- Restricted six market programs -> "Research validation — no detailed signals available", irrespective of internal inference activity.
- Future `CUSTOMER_ELIGIBLE`, alerts, billing and broker execution are explicitly **not enabled** by this document.

## 6. Versioned P0 metrics contract (maintain PR #93 direction)

For any displayed result use the tuple `metric_version,source_program_id,market,model_version,protocol_version,source_window_start_utc,source_window_end_utc,as_of_utc,source_head_hash/source_snapshot_sha,projection_version,cost_model_version,unit,population,valid_completed_n,invalid_or_unknown_n,open_n,validation_status`. Keep forward versus backtest and legacy versus active AI independent. S02 is never pooled as AI.

- A completed trade is exactly one unique, verified `EXIT` per permitted signal identity, with **finite, valid, combined, already-accounted-for net R**. TP1 partial contribution is included once, never added to combined final net R again. `NO_TRADE`, guard rejection, error, open signal and stale data are not completed outcomes.
- `win_rate = completed net_R > 0 / valid_completed_n`; show losses (`<0`) and breakevens (`=0`) separately. `expectancy_R = sum(completed net_R)/valid_completed_n`. `profit_factor = sum(positive net_R)/abs(sum(negative net_R))`, **N/A** if no negative-denominator outcomes. Drawdown uses exit-effective-UTC ordered cumulative completed normalized net R, tie-breaking deterministically on source ID; not simulated account dollars or customer execution P&L.
- Never treat absent/invalid `total_combined_signal_net_r` as zero. Source report currently uses a legacy fallback in `ai_v1/observability.py::_performance`; new v2 metrics require explicit invalid/unknown handling.
- Maintain costs (spread/slippage/fees) and cost-version definitions, denominators, sample size, time window, source hash and reproducibility; calculated values withheld or N/A for insufficient provenance. Different programs need matched cohorts before comparisons.

## 7. P0 implementation-boundary audit and acceptance tests

Current source files reviewed (exact parent repo branch): `web/index.html`, `web/app.js`, `src/trading_signal_intelligence/product/cloud_app.py`, `product/ai_insights.py`, `ai_v1/observability.py`; historical competitor research: `docs/tradingtop-authenticated-teardown-and-product-gap-2026-09-28.md`, `docs/tradebise-authenticated-product-business-seo-audit-2026-10-04.md`, and synthesis `docs/competitor-synthesis-waqarzaka-tradebise-tradingtop-vowsig-2026-10-04.md`. Existing `ai_insights.py` defaults to **12 recent decisions / 20 shadow signal rows**: a separate independently authorized sanitized full-history/source-event export and idempotent, source-hash-reconciled read model are mandatory for true member history and owner Performance Lab. The Windows immutable ledgers are not a web database.

Contract tests to specify before implementation:
1. **Nine-catalog invariant:** exactly the reviewed 9 canonical market IDs present, grouped into 3 permitted core plus 6 aggregate-only validation markets (while program status may change over time).
2. **No restricted leak:** neither anonymous nor Free role can request per-signal event IDs, BUY/SELL detail, entry/stop/target, hashes or alert payload from EURUSD/XAGUSD/USOIL/BTCUSDT/ETHUSDT/SOLUSDT, including via filter/ID guesses/alternate endpoint/cached snapshot; admin rights don't grant commercial publishing.
3. **Customer wording contract:** no version numbers in primary menu; user-readable status is accurate with separate optional exact version provenance.
4. **Nine-market watchlist:** user A/B isolation, optional opt-in research interest for all 9 but notification trading alerts remain disabled; restricted watchlist does not trigger signal-level exposure.
5. **Data-loss/freshness invariants:** no fabricated active setups under stale, missing, provider error, no-trade, rejected, expired or public snapshot not recent; previously closed/losing history preserved.
6. **Evidence metrics:** synthetic complete partial/exit cost cases, duplicate/missing/nonfinite, chronology, mismatched source hashes, unknown market, cross-version/lineage and empty cohorts fail closed or show N/A, never inflated claims.
7. **Existing contract parity:** old `/api/ai/insights` and `/api/signals` remain unchanged until separately approved API/SEO compatibility migration; existing S02 separate; public adverse outcomes preserved.

No tests executed and no source code modified by this document.

## 8. Decision status and minimal next slices

**Owner product preference captured in new conversation (not an API release approval):** customers should find signals first, learning second; all nine researched markets should be discoverable; AI-v1.x codes should not dominate customer UI. **Recommended P0 interpretation for owner sign-off:** nine-market Markets directory and watchlist, but only three existing Core research signal-detail programs; six aggregate-only market-status programs; no new exposure rights.

**Still requiring explicit sign-off before an implementation PR:** approve above 9-vs-3 access matrix and customer navigation, decide whether nine-market watchlist can be saved in Free from day one (recommended YES with progress-only for six), approve v1 public compatibility, full-history export permissions and minimal P0 KPI data/cost contract. Managed PostgreSQL/email vendor/privacy/budget choices are subsequent P1 provisioning decisions. G4 customer-value evidence remains an input to wider launch; do not assume adoption.

**Proposed bounded sequence:**
- P0A (this **docs-only** review) → approve product/tier/market/status/metric contracts.
- P1A approved implementation PR: secure identity, verified sessions and `/app` shell; feature-flagged nine-market watchlist and public aggregate-status tiles. No Windows/VPS changes.
- P2A approved separate PR: authorized immutable-source sanitized history export/read-model and owner Performance Lab with exact reconcilable metrics. No broad scheduler modifications.
- P3A approved separate PR: the Signal Center signals/history/detail UI and research-only member API for the three permitted core markets, plus all-nine directory.
- P4 consent-aware customer comprehension and retention evidence. **No paid plans, broker execution, new active market permission or customer trading-alert delivery.**

**Governance:** Keep PR #93 open/draft/unmerged; this P0 addendum is likewise a proposed draft. Do not deploy, touch the production Windows source, alter AI/guard/publisher/GFS tasks, bypass eligibility, enable billing or assume nine actual active signal sources. Keep this document and GitHub PR metadata as the handoff for future chats.
