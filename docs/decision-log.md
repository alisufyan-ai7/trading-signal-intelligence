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
