# Decision Log

This file records material product, data and architecture decisions. New entries should be appended rather than silently rewriting history.

## 2026-09-16 — D001: Repo is the source of truth

**Decision:** Major strategy definitions, research conclusions, architecture decisions and implementation status live in this repository rather than only in chat.

**Reason:** The project needs durable, reviewable state and reproducible research.

## 2026-09-16 — D002: MT5 + Python replaces MetaApi as the initial broker connector

**Decision:** Use the official MetaTrader5 Python package with a local Windows MetaTrader 5 terminal for initial multi-asset R&D.

**Initial broker:** Exness demo.

**Reason:** It avoids an additional middleware subscription and gives direct access to the instruments/data exposed to the logged-in MT5 terminal.

**Constraint:** This is an R&D decision, not a conclusion that Exness data is licensed for commercial SaaS-derived signals.

## 2026-09-16 — D003: Binance direct for crypto

**Decision:** Use Binance's direct REST/WebSocket market-data interfaces as the primary crypto source; use broker crypto CFDs only for comparison or broker-specific strategy research.

**Reason:** Direct exchange data avoids unnecessary broker-CFD basis differences and gives a cleaner crypto research source.

## 2026-09-16 — D004: No raw-feed redistribution in v1

**Decision:** The SaaS is designed around derived signals, scores, explanations and performance records—not streaming raw broker prices or cloning broker charts.

**Reason:** Product focus and reduced data-licensing exposure. This does not eliminate the need to confirm commercial rights for using source data to create derived products.

## 2026-09-16 — D005: Exness production-data status is blocked pending clarification

**Decision:** Exness demo/MT5 may be used for prototyping and R&D, but Exness is not assumed to be an approved production commercial signal-data source.

**Reason:** The current Exness (VG) Client Agreement (version 24 July 2026) states in its prohibited-actions section that accessing/collecting/storing/using market data, price feeds, quotes or platform data for purposes other than the client's own genuine trading—including an external platform/system/product/service—is prohibited. The current API Terms also grant API use for managing the client's account and executing transactions in good faith.

**Next action:** Obtain written clarification/permission for server-side calculation of proprietary commercial derived signals without redistributing raw market data, or select an alternative licensed production source.

Sources:
- https://www.exness.com/legal-documents/
- https://www.exness.com/cdn/media/exnessvg/exness_vg_client_agreement.pdf
- https://www.exness.com/cdn/media/docs/exness-api-terms-of-use.pdf

## 2026-09-16 — D006: Quantitative engine first, AI second

**Decision:** Strategy rules/risk logic generate candidate signals; AI explains/contextualizes them downstream.

**Reason:** Better reproducibility, lower model cost, easier validation and clearer performance attribution.

## 2026-09-16 — D007: Verified forward record is a core product feature

**Decision:** Once live testing starts, the system stores original signal parameters immutably and automatically evaluates outcomes.

**Reason:** The long-term product moat should be evidence and transparency rather than unverifiable "AI confidence" marketing.

## 2026-09-17 — D008: G1 adapter concept passed initial live probe

**Decision:** Continue with the local MT5/Exness research adapter and direct Binance adapter because the first live probe successfully returned a 357-symbol MT5 universe, live EURUSD bid/ask, normalized H1 MT5 bars, and normalized Binance BTCUSDT H1 bars on a common UTC schema.

**Status:** This is a prototype pass only. History depth, gaps, spread distributions, session behavior, long-running reliability and representative multi-asset coverage remain to be validated before G1 is fully passed.

## 2026-09-17 — D009: Canonical symbol mapping must be explicit and source-aware

**Decision:** Do not infer canonical instruments solely from broker `currency_base` / `currency_profit` metadata. Maintain an explicit mapping registry using source symbol, path/category, description, and verified canonical identity.

**Reason:** The Exness MT5 probe showed inconsistent crypto metadata for several token/USD instruments even though source names and descriptions were clear. Silent inference could contaminate strategy research and cross-source comparisons.

**Implication:** Strategy code consumes canonical symbols only after source-specific normalization; broker metadata remains auxiliary evidence rather than the canonical identity authority.

## 2026-09-17 — D010: G1 research-data gate passed

**Decision:** Historical strategy research may proceed using the normalized MT5/Exness and Binance adapters.

**Evidence:** Representative audits returned ~7–8.5 years of H1 data for EURUSD, XAUUSD, USTEC and USOIL, with strictly increasing timestamps, zero duplicates, fully populated tick volume and historical spread fields. Binance BTCUSDT normalizes to the same schema.

**Limitations:** Session-aware gap classification and long-running collector reliability remain operational hardening tasks. G1 passing does not imply production/commercial data rights; G2 remains open.

## 2026-09-17 — D011: Binance is the primary long-horizon crypto research source

**Decision:** Use Binance direct data for historical crypto strategy research; do not use the current Exness BTCUSDT history as the primary long-horizon crypto dataset.

**Reason:** The Exness demo server returned only 2,575 H1 BTCUSDT bars (~108 days), while the design requires multi-year samples. Over 999 overlapping closed H1 candles, Exness/Binance BTCUSDT had 0.999451 return correlation and modest basis, supporting Exness as a broker-specific reference/sanity feed without treating the two instruments as interchangeable.

## 2026-09-17 — D012: Cost modeling is instrument-specific and conservative

**Decision:** Preserve and use MT5 historical bar spread as a baseline cost proxy, converted through each symbol's point size, with configurable additional slippage. Do not use one universal spread assumption and do not treat bar spread as perfect executable bid/ask history.

**Observed median spread fields:** EURUSD 6 points (~0.6 pip), XAUUSD 125 points (~$0.125), USTEC 249 points (~2.49 index points), USOIL 18 points (~$0.018), Exness BTCUSDT 700 points (~$7.00).

**Reason:** Transaction costs differ materially by asset class and time. Robust strategy evidence must survive realistic and stressed cost assumptions rather than only gross-price backtests.

## 2026-09-17 — D013: Treat BTCUSD and BTCUSDT as separate Exness instruments

**Decision:** Keep Exness `BTCUSD` and `BTCUSDT` as distinct canonical instruments in research and never merge them into one generic Bitcoin price series.

**Evidence:** A live Exness Market Watch screenshot showed both symbols simultaneously as separate instruments, with different quoted prices at the same moment. Both showed an approximately $7 bid/ask spread, but BTCUSDT was about $5 above BTCUSD in the captured snapshot.

**Implication:** Cross-source comparison to Binance Spot should use Exness `BTCUSDT` versus Binance `BTCUSDT`. Exness `BTCUSD` may be studied separately and, if needed, compared to a true USD spot venue rather than to a USDT market. This avoids contaminating basis/strategy analysis with an avoidable USD-versus-USDT mismatch.

## 2026-09-17 — D014: Reject S01 v0.1 as a general FX strategy

**Decision:** S01 Trend Pullback v0.1 is rejected as a general FX strategy hypothesis and is retained only as a regression benchmark. XAU/USD behavior remains a separate market/regime research lead, not an accepted strategy.

**Evidence:** The frozen v0.1 rules were tested unchanged across EUR/USD, GBP/USD, USD/JPY and XAU/USD. EUR/USD, refreshed GBP/USD and refreshed USD/JPY all produced negative validation and final-test expectancy after costs. XAU/USD was near-flat through validation and strong only in the already-observed 2025–2026 period. Ledger, sampled candle-level and H1↔H4 integrity checks did not identify an implementation defect explaining the FX failures.

**Implication:** Do not optimize S01 v0.1 in place. Any XAU-specific follow-up becomes a separately versioned hypothesis with new evidence requirements.

## 2026-09-17 — D015: Freeze S02 Structure Breakout v0.1 before first result

**Decision:** S02 v0.1 is frozen before any S02 backtest result is viewed, with a predeclared first universe of EUR/USD, GBP/USD, USD/JPY and XAU/USD.

**Frozen baseline:** H1 20-bar prior structure, 0.10 ATR breakout margin, gap-open exclusion, 1.25× prior-median true-range expansion, 1.10× prior-median tick-volume expansion, H4 EMA50 regime with 3-bar slope agreement, next-H1-open entry, 1.75 ATR stop, 2.5R target, 72-H1-bar timeout and the existing conservative signal-bar spread cost convention.

**Reason:** The project should test an independently specified breakout-continuation hypothesis rather than tune S01 after failure. Predeclaring rules and markets preserves the value of negative as well as positive results.

**Implication:** Implementation bugs may be corrected without changing alpha semantics. Any alpha-rule/parameter change after the first S02 result requires a new strategy version.

## 2026-09-18 — D016: Treat the first S02 robustness run as post-baseline local sensitivity and reconcile it with the original frozen neighborhood

**Decision:** Preserve the completed 17-configuration `run_s02_robustness.py` output as valid post-baseline local sensitivity evidence, but do not describe it as the exact pre-first-result neighborhood from the S02 v0.1 specification. Before temporal/walk-forward analysis, run the exact one-at-a-time neighborhood recorded in `strategies/S02-structure-breakout/v0.1.md`.

**Evidence:** In the completed local sensitivity test, XAU/USD remained positive in both validation and final-test periods for 15/17 configurations and positive in the final test for 17/17. GBPUSD and USDJPY had zero configurations positive in both OOS splits; EURUSD had 6/17. All 17 XAU configurations remained negative in development.

**Protocol finding:** The local runner was frozen after the first S02 baseline and before its sensitivity results, but its values differ from the broader neighborhood written in the strategy specification before first result. The original specification includes ATR-period and H4-EMA perturbations and broader values for structure, breakout margin, expansion filters and H4 slope.

**Implication:** The local XAU plateau is encouraging but not sufficient for candidate status. The exact original specification neighborhood is the next required robustness test. No parameter is selected from either sensitivity run.


## 2026-09-18 — D017: S02 XAU passes the exact pre-first-result parameter-neighborhood robustness test

**Decision:** Treat XAU/USD S02 v0.1 as a robust historical research lead across the originally frozen one-at-a-time parameter neighborhood, but do not promote it to candidate or forward-test status yet.

**Evidence:** Across 23 exact-spec configurations, XAU/USD is positive in validation for 20/23 variants, positive in the final test for 23/23, and positive in both OOS splits for 20/23. Final-test expectancy ranges from approximately +0.1450R to +0.2765R/trade. The newly included ATR-period and H4-EMA perturbations remain positive in both OOS splits.

**Failures:** The three validation-negative XAU variants are structure window 30, stop 1.50 ATR, and target 2.0R.

**Critical limitation:** Development expectancy is negative for all 23 XAU configurations. The evidence therefore supports parameter robustness in a later market regime, not a stationary full-history edge.

**Implication:** Freeze a temporal stability protocol using the unchanged v0.1 baseline only. Do not select a better robustness variant, do not retrofit long-only behavior, and do not claim candidate status from historical robustness alone.


## 2026-09-18 — D018: S02 XAU shows sustained recent temporal persistence but remains a historical lead

**Decision:** Treat XAU/USD S02 v0.1 as having passed the planned historical parameter-robustness and fixed-rule temporal-stability stages for a recent regime. Do not treat this as proof of a stationary or future edge.

**Evidence:** XAU has six consecutive positive complete half-years from 2023-H2 through 2026-H1. Rolling 12-month windows are positive for all 15 starts from 2022-01 through 2025-07. The six most recent fixed-rule prior-12m -> next-6m pairs are positive-to-positive.

**Counterevidence / caution:** All 23 parameter-neighborhood variants remain negative in development, and 2023-H1 is negative. USDJPY also shows strong historical persistence but fails sharply from 2025 onward, demonstrating that persistence can break.

**Implication:** Freeze new-market transfer testing on XAGUSD, USTEC, US500, US30 and USOIL using unchanged v0.1. In parallel, prepare immutable forward-test infrastructure. Candidate status remains blocked pending genuinely new forward evidence.
