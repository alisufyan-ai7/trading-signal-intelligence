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


## 2026-09-18 — D019: S02 new-market transfer is partial, not broad

**Decision:** Treat the frozen S02 v0.1 transfer test as partial supporting evidence only. USTEC and US30 meet the predeclared descriptive support rule; XAGUSD, US500 and USOIL do not.

**Evidence:** USTEC validation/final expectancy is approximately +0.1243/+0.0122R per trade and US30 +0.0936/+0.0123R. XAGUSD is -0.0839/+0.1432, US500 +0.0283/-0.0331, and USOIL -0.1466/-0.1493. All splits exceed the predeclared 50-trade minimum.

**Interpretation:** The two supportive markets are correlated U.S. equity indices and their final-test margins are small. XAGUSD does not provide full-OOS same-metal confirmation. This is not broad cross-asset validation.

**Implication:** Stop extending historical parameter searches. The primary next evidence for the robust XAU historical lead must be immutable forward observations generated after a frozen activation timestamp.

## 2026-09-18 — D020: Primary forward test uses unchanged S02 v0.1 on XAUUSD with an append-only hash chain

**Decision:** Begin the forward-evidence phase with XAUUSD as the primary hypothesis, using the unchanged S02 v0.1 baseline and an event-sourced append-only SQLite ledger.

**Integrity rules:** Ledger records are SHA-256 hash-chained and SQLite triggers reject UPDATE/DELETE. Activation commits to the strategy config hash and strategy-source hash. Signals older than the frozen freshness threshold are recorded as missed rather than backfilled as live.

**Limitations:** A local hash chain is tamper-evident within the retained database but is not independently timestamped proof by itself. External ledger-head anchoring is a separate follow-up.

**G2:** Exness remains R&D-only; this forward test does not establish commercial data rights.


## 2026-09-18 — D021: Anchor the S02/XAUUSD forward activation before live scanning

**Decision:** Accept the primary XAUUSD S02 v0.1 forward activation after all 7 local tests passed and the fresh ledger verified with exactly one ACTIVATION record.

**Activation UTC:** `2026-09-18T13:58:54.786419+00:00`.

**Activation / initial ledger-head SHA-256:** `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`.

**Protocol bundle SHA-256:** `484b3de25c6ff6c24de30c5a700f211b98be8534c7b0354fcb2d6219587232cf`.

**Repository HEAD pulled before activation:** `b309cff26974728ef1f359d443d5927ee16010db`.

**Durable anchor:** `research/forward/S02-XAUUSD-v0.1-activation-2026-09-18.md`.

**Implication:** Live scanning may begin with the exact frozen fingerprints. Strategy/scanner/ledger/config changes invalidate this activation for the changed implementation and require a separately versioned protocol. Historical signals may not be retroactively inserted as live signals.


## 2026-09-21 — D022: Predeclare S02 forward-test review gates before the first live trade

**Decision:** Keep the activated S02/XAUUSD v0.1 forward test running continuously and evaluate it at predeclared trade-count/time gates rather than after arbitrary winning or losing streaks.

**F1:** first 20 completed trades — execution/lifecycle audit only; no alpha decision.

**F2:** at least 50 completed trades **and** at least 90 calendar days after activation — interim strategy review; favorable results are insufficient for candidate promotion.

**F3:** at least 100 completed trades **and** at least 180 calendar days after activation — first planned candidate-status decision.

**Scheduling estimate:** Historical S02/XAUUSD frequency is roughly 10–11 trades/month, implying F2 around Jan–Feb 2027 and F3 around Jun–Jul 2027 if live frequency is similar. Actual dates remain trade-count driven.

**Parallel work:** Continue G2 commercial-source-rights work immediately, add external verification/backup hardening, allow lightweight G4 customer discovery, and permit separately frozen S03/S04/S05 research without changing the active S02 protocol.


## 2026-09-21 — D023: Launch Early Access in days while forward validation continues

**Decision:** Product launch and strategy validation are separate tracks. Target a 3–5 day Early Access Beta instead of waiting for the S02 F2/F3 forward-evidence gates.

**Launch scope:** XAU-focused signal dashboard, transparent historical/forward evidence, immutable signal history, alerts, authentication, risk disclosure and a small user cohort. No auto-execution, personalized suitability or unsupported performance claims.

**G3:** Remains in progress. F1/F2/F3 govern how strongly S02 may be described, not whether the application can be launched as a research beta.

**G2:** Do not mark Exness commercial-data rights as passed under the ordinary retail Client Agreement. G2 may pass via separate written source permission or a production market-data provider/subscription that explicitly permits the intended commercial derived-signal use.

**Implication:** Build and launch the product now in parallel with forward validation. Keep Exness as R&D-only unless separate written permission is documented.


## 2026-09-21 — D024: Mark G2 passed and launch with a three-market live-signal universe

**Decision:** G2 is passed for the initial Exness-based launch because the project owner confirms separate Exness permission covering the intended commercial derived-signal use.

**Launch data policy:** Use Exness for the first revenue-generating release. Do not purchase a replacement paid market-data feed before product revenue exists.

**Initial live-signal markets:** XAUUSD, USTEC and US30.

**Evidence labels:** XAUUSD remains the primary historical/forward lead. USTEC and US30 are secondary because they passed the frozen historical transfer-support rule but have much smaller final-test margins.

**Additional product coverage:** EURUSD, GBPUSD, USDJPY, XAGUSD, US500 and USOIL remain visible as research/monitoring markets with explicit evidence labels.

**Integrity rule:** USTEC and US30 get separate append-only forward databases and activation hashes. The existing XAU activation/database remains untouched.

**Product implication:** The 3–5 day Early Access build proceeds now; paid data replacement is a later revenue-funded infrastructure choice rather than a launch prerequisite.


## 2026-09-27 — D025: Activate and anchor USTEC and US30 as secondary Early Access forward markets

**Decision:** Activate separate immutable S02 v0.1 forward ledgers for USTEC and US30 after both markets passed the live H1/H4 recency gate.

**USTEC activation:** `2026-09-27T12:42:13.014356Z`; activation/head SHA-256 `b0bcb4c952c64c3043512905b803697b491841b99b08b256feb9de82f2cd2780`.

**US30 activation:** `2026-09-27T12:42:13.701885Z`; activation/head SHA-256 `3bc5a922843fea806b8aa4ab3c53a98a2d371982c7479164548b1a1e8fbea581`.

**Repository HEAD at both activations:** `08cf2282776a4f5f7863f6c16d96b1704dc56bca`.

**Protocol:** Both use the unchanged S02 v0.1 config and the same frozen protocol bundle hash `484b3de25c6ff6c24de30c5a700f211b98be8534c7b0354fcb2d6219587232cf`.

**Evidence tier:** USTEC and US30 remain secondary launch markets because their frozen historical final-test margins were small. They are not promoted to the XAU evidence tier merely by activation.

**Implication:** Install the separate secondary hourly task and preserve each ledger independently.


## 2026-09-27 — D026: Strict context isolation for TradingTop research and Work mode

**Decision:** For this TradingTop Analysis project, do not use account-level memory, saved/personal memory, other chats, other projects, other repositories, or unrelated connected-app context.

**Allowed context only:**

- the current open chat;
- the private GitHub repository `alisufyan-ai7/trading-signal-intelligence`;
- authenticated TradingTop pages explicitly opened during this project’s Work-mode research;
- fresh public web research specifically about TradingTop/Elirox when the user asks for external verification or comparison.

**Not allowed:**

- Personal Context / account memory;
- prior chats outside this project;
- any other GitHub repository;
- unrelated Gmail/Drive/app content;
- inferences based on user history outside the allowed sources.

**Work-mode implication:** Even if the product setting is changed to Default Memory so Work mode becomes available, this project remains logically isolated by instruction. Work should be told to use only the allowed sources above.

**Reason:** Preserve research provenance and prevent contamination from unrelated projects or account-level context.


## 2026-09-28 — D027: Pivot product architecture to AI-first intelligence with deterministic guardrails

**Decision:** The project owner formally approves the product-direction pivot from the original "quantitative engine first, AI explanation second" architecture to an **AI-first market-intelligence product with deterministic publication/risk guardrails and immutable evidence**.

This supersedes D006 for the product's forward architecture while preserving D006 as the historical decision that produced the existing S01/S02 research foundation.

**New architecture principle:**

> AI proposes the market decision; deterministic code validates publishability/risk; every inference and signal remains attributable in an immutable record.

**Preserved controls:**

- S02-v0.1 remains unchanged;
- existing XAUUSD, USTEC and US30 S02 forward ledgers remain active and untouched;
- S02 becomes the deterministic benchmark/control for AI-v1;
- no broker execution or auto trading is authorized by this decision;
- AI-v1 begins in shadow mode.

**Reason:** Authenticated TradingTop research showed that the intended comparison product is AI-first at the user-experience layer: structured inference, confidence, reasoning, AI logs and model-specific trading history. The current beta has strong data/evidence infrastructure but its signal brain remains rule-based.

## 2026-09-28 — D028: Adopt "SignalProof AI" as the working product name

**Decision:** Use **SignalProof AI** as the working customer-facing product name for AI-0.

**Working positioning:** AI market intelligence with a verifiable record.

**Working promise:** "AI finds the setup. Risk rules verify it. Every signal stays on the record."

**Boundary:** This is a working project name, not a claim of trademark/domain clearance. Under the project's strict isolation rule, broad external brand clearance was not performed here. Perform a separate clearance check before a paid public launch.

**Implication:** Stop using the competitor's brand as this application's visible identity. Engineering identifiers such as the repository/package name may remain unchanged.

## 2026-09-28 — D029: Freeze AI-v1 shadow architecture and EXP-2026-014 before first AI result

**Decision:** Freeze the first AI signal protocol before any AI-v1 performance-bearing inference is observed.

**Frozen initial universe:** XAUUSD, USTEC, US30.

**Frozen cadence:** each eligible completed H1 bar.

**Frozen AI role:** provider-neutral reasoning model operating only on causally available engineered market-state features. AI-v1.0 excludes news, social sentiment, S02 outputs, user positions and incomplete/future candles.

**Frozen decisions:** BUY / SELL / NO_TRADE.

**Frozen publication model:** AI direction/risk proposal -> schema validation -> deterministic freshness/cost/concurrency/risk guard -> shadow signal or rejection.

**Frozen entry/lifecycle:** next eligible H1 open; model-proposed stop 1.00–3.00 ATR; TP1 0.75–2.00R; TP2 1.50–4.00R and greater than TP1; 50/50 target evaluation; no stop move after TP1; 24 H1-bar timeout; instrument-specific costs.

**Evidence separation:** AI-v1 receives its own append-only ledger. It must never write into S02 databases.

**Review gates:**

- A1: >=100 valid inferences and >=20 completed AI shadow trades — operational audit only.
- A2: >=500 valid inferences, >=50 completed trades and >=60 calendar days — interim evidence review.
- A3: >=1,000 valid inferences, >=100 completed trades and >=120 calendar days — first planned publishability decision.

**Activation blocker:** Before first performance-bearing inference, commit the exact inference provider/model ID, inference parameters, prompt/policy, implementation fingerprints and activation record.

**Frozen artifacts:**

- `docs/ai-v1-architecture.md`
- `config/ai_v1_decision_schema.json`
- `config/ai_v1_guardrails.json`
- `research/experiments/EXP-2026-014-ai-v1-shadow-preregistration.md`


## 2026-09-28 — D030: Freeze AI-v1 feature formulas and provider-neutral reasoning policy

**Decision:** Remove remaining implementation ambiguity from AI-v1 before provider/model selection by freezing both the causal feature definitions and the provider-neutral reasoning policy.

**Frozen feature definition artifact:**

- `docs/ai-v1-feature-definitions.md`
- `config/ai_v1_feature_schema.json`

The feature protocol fixes return horizons, Wilder ATR/RSI semantics, EMA semantics, prior-20 structure, previous-day structure, true-range expansion, tick-volume z-score, realized-volatility buckets, deterministic trend regime, fixed UTC session buckets, spread normalization, data-age calculation and canonical snapshot hashing.

**Frozen reasoning policy artifact:**

- `config/ai_v1_policy.txt`

The policy requires the model to:

- use only the supplied feature snapshot;
- output BUY / SELL / NO_TRADE in the frozen schema;
- prefer NO_TRADE when evidence is weak/mixed;
- keep stop/target proposals within frozen bounds;
- avoid outputting executable price arithmetic;
- return concise rationale/factor tags only;
- never rely on outside market knowledge, news, S02 state or hidden chain-of-thought.

**Remaining activation variable:** The exact provider/model identifier and provider-specific inference parameters remain intentionally unset until implementation. They must be committed before first performance-bearing inference. Selecting that model does not reopen the frozen feature/policy/guard contract unless the protocol version is changed.


## 2026-09-28 — D031: Freeze AI-v1 ledger isolation and activation record contract

**Decision:** AI-v1 uses three new market-specific append-only databases and a separately frozen activation-record schema.

**AI-v1 database paths:**

- `data/ai_v1_xauusd.sqlite`
- `data/ai_v1_ustec.sqlite`
- `data/ai_v1_us30.sqlite`

These databases are independent of all active S02 forward databases.

**Frozen ledger artifact:** `docs/ai-v1-ledger-spec.md`.

**Frozen activation artifact:** `config/ai_v1_activation_schema.json`.

The AI ledger reuses the project's proven append-only SHA-256 hash-chain integrity pattern but defines AI-specific lifecycle records for activation, inference, abstention, rejected inference, signal, partial exit, exit, missed inference and error.

Before activation, each market's activation record must bind the exact repository commit, provider/model, inference-parameter fingerprint, policy/feature/schema/guard hashes, implementation source hashes and cost-policy fingerprint.

**Reason:** AI-generated outputs must remain attributable to the exact model/input/policy/implementation that created them, and they must not contaminate the already-activated S02 evidence.


## 2026-09-28 — D032: Fresh public research is allowed; private-context isolation remains strict

**Decision:** Clarify D026. Fresh public web/search/open-source research is allowed whenever it materially supports this project, including provider/model/API documentation, libraries, standards and competitor verification.

**Still prohibited as project context:**

- account-level memory / Personal Context;
- chats outside this project;
- other private projects;
- any GitHub repository other than `alisufyan-ai7/trading-signal-intelligence`;
- unrelated private connected-app data.

**Allowed context remains:**

- this current open chat;
- this exact private repository;
- authenticated TradingTop pages explicitly opened for this project;
- fresh public internet/open-source research.

**Reason:** The isolation requirement is intended to prevent contamination from unrelated private/user history, not to block current public technical research.

## 2026-09-28 — D033: Freeze OpenAI GPT-5.4 dated snapshot as AI-v1 provider/model

**Decision:** Use the OpenAI Responses API with exact model snapshot `gpt-5.4-2026-03-05` for AI-v1.

**Selection basis:** Public provider research was completed before any AI-v1 performance-bearing inference. The dated GPT-5.4 snapshot provides an explicit model-version lock for the multi-month preregistered experiment, supports Structured Outputs and reasoning, and costs materially less than the dated GPT-5.5 snapshot. Newer moving aliases were not selected because a moving model would weaken causal/reproducibility claims across A1/A2/A3.

**Frozen request semantics:**

- endpoint: `POST https://api.openai.com/v1/responses`;
- reasoning effort: `medium`;
- service tier: `default`;
- `store=false`;
- truncation: disabled;
- max output tokens: 8192;
- no tools;
- no conversation/previous-response state;
- temperature/top_p omitted;
- exact frozen policy text;
- canonical feature JSON as the only market-state input.

**Privacy:** `OPENAI_API_KEY` remains local to the VPS and is never committed or ledgered. OpenAI's public data-control documentation states that Responses API data is not used for training; AI-v1 additionally disables response storage.

**Frozen artifacts:**

- `docs/ai-v1-provider-selection.md`
- `config/ai_v1_provider.json`

## 2026-09-28 — D034: Freeze a provider-compatible OpenAI schema while retaining canonical local validation

**Decision:** Keep `config/ai_v1_decision_schema.json` as the canonical semantic contract, but send `config/ai_v1_openai_response_schema.json` to OpenAI Structured Outputs.

**Reason:** OpenAI's current Structured Outputs subset does not support composition keywords used by the canonical schema, including `allOf`, `if`, `then` and `else`.

The provider schema removes those unsupported composition constructs only. It does not authorize a broader decision contract. After every provider response, local `validate_decision()` still enforces all frozen semantics, including NO_TRADE null fields, directional numeric bounds and TP2 > TP1.

Both the provider schema and canonical schema are fingerprinted in the activation bundle.


## 2026-09-28 — D035: Treat GPT-5.4 403 as a pre-activation access blocker, not a model result

**Observed:** The first synthetic non-performance request to the frozen OpenAI model `gpt-5.4-2026-03-05` returned HTTP 403 / `model_not_found` stating that the API project does not have access to that model.

**Decision:** Do not interpret this as a trading/model-performance result and do not silently switch models.

Before changing D033:

1. inspect the exact API project's model access using metadata-only API requests;
2. check whether GPT-5.4 access can be enabled through OpenAI project Model Usage / billing tier;
3. if the exact frozen snapshot becomes accessible, retain D033 unchanged;
4. if it cannot be made accessible, choose only an accessible **dated snapshot** and record a superseding provider/model decision before the first performance-bearing inference.

The diagnostic candidate list is operational, not a ranking and not authorization to use a fallback.

No AI-v1 activation/performance evidence exists yet, so a provider substitution at this stage remains methodologically admissible if fully recorded before activation.


## 2026-09-28 — D036: Project-local `.env` overrides inherited machine credentials for AI-v1

**Observed:** The Windows VPS already had an `OPENAI_API_KEY` environment variable belonging to another OpenAI project. AI-v1's earlier local-env loader used non-overriding semantics, so the inherited Windows value took precedence over this repository's `.env`, causing the provider request to authenticate against the wrong OpenAI project.

**Decision:** For SignalProof AI-v1 runtime/provider scripts, project-scoped credentials loaded from this repository's ignored local `.env` must override inherited process/user/system environment variables with the same name.

**Implementation:**

- added `load_project_env(...)` with explicit override semantics;
- provider smoke, model-access probe and guarded activation scripts now use it;
- `.env` remains ignored by Git;
- added a regression test proving a project-local `OPENAI_API_KEY` replaces an inherited different-project value.

**Reason:** This repository is intentionally isolated. Credentials for unrelated projects must never silently influence its provider identity.


## 2026-09-28 — D037: First AI-v1 activation anchor verified; no performance records existed

**Observed:** The ledger-only activation completed at `2026-09-28T11:42:13.314465+00:00` and was anchored in Git commit `a3c986fb9527d351c0998f072ebfe159b7a8b0ac`.

Verified initial ledger heads:

- XAUUSD: `2e9e547276a054416d60ef4a6b6d0bc042fee43c7c0fdd3eec86a2548bbe34b1`
- USTEC: `571fad6647ca024b5c53e567b3d6e8643e5dc3e938b39e451f5830d6de0ab268`
- US30: `f508a6b65c9ad5b6775180498ae80f06ffc6d53cc6220fbe275ffd5fcf5e867a`

The activation used OpenAI `gpt-5.4-2026-03-05` with model-parameter fingerprint `ed5069535190cb33771ff8efe1c4389e09abaddea933143c0c839c6dc87d3e9b` and broker execution disabled.

Git comparison confirmed that the anchor commit is exactly one commit after the activated repository commit `2750aa1a45a3cae6de47165e933f1ca7a99b6669` and adds only the activation-anchor JSON.

No AI-v1 performance-bearing inference existed at this checkpoint.

## 2026-09-28 — D038: Supersede the first ledger-only activation before first performance inference so the live runtime is also bound

**Finding:** The first activation correctly bound the frozen model, policy, feature/guard/lifecycle implementation and ledger code, but the unattended live H1 runtime/scheduler had not yet been implemented and therefore could not be part of that activation repository tree.

**Decision:** Do not start the scheduler against the first activation.

Because there are still zero performance-bearing AI-v1 records, preserve the first activation as a superseded pre-performance artifact, archive its three activation-only databases without deletion, then create a replacement AI-v1.0 activation after the final live runtime is committed and tested.

This is a protocol-completeness correction made **before first performance evidence**, not a response to model performance.

The replacement activation bundle additionally binds:

- `docs/ai-v1-shadow-runtime.md`;
- `src/trading_signal_intelligence/ai_v1/shadow_runtime.py`;
- `scripts/run_ai_v1_shadow.py`;
- `scripts/run_ai_v1_shadow_task.cmd`;
- `scripts/install_ai_v1_shadow_task.ps1`.

The live runtime freezes the already-preregistered three-market H1 cadence, uses the pre-activation live-probe retrieval windows (500 H1 / 200 H4), records stale backlog cycles as `MISSED_INFERENCE` rather than backfilling, verifies the committed upstream activation anchor before any run, and keeps broker execution disabled.

The inference ledger payload is also completed before replacement activation with explicit policy/guardrail hashes, raw confidence, provider request ID, usage metadata and normalized NO_TRADE decision provenance.

After the replacement activation is committed and anchored, any decision-affecting runtime change requires separate governance/versioning.


## 2026-10-02 — D039: Start SEO foundation before first-cohort G4 evidence, while keeping evidence-informed expansion gated

**Decision:** Restructure Organic Acquisition & SEO v0.1 (Issue #8) into two governed phases.

- **Phase 8A — SEO foundation / discoverability:** active immediately and may proceed before Issue #9 real-user evidence.
- **Phase 8B — evidence-informed content / conversion expansion:** remains gated on the initial aggregate evidence from Issue #9.

**Reason:** The original all-or-nothing SEO deferral protected the project from inventing customer language before user research. That remains appropriate for customer-language-dependent content, CTA/conversion messaging, market prioritization and pricing-related SEO. However, VowSig now has a stable brand/domain, production deployment, public evidence surfaces and measurement boundary, so technical discoverability and information architecture can be developed without pretending to know customer preferences.

**Phase 8A includes:** current production SEO/indexability baseline, search-intent map, URL/information architecture, index/noindex and canonical policy, initial factual market/education priorities, internal-link foundation, technical SEO implementation plan and privacy-respecting measurement.

**Issue #9 remains required for:** real user terminology, comprehension problems, market/alert preferences, trust/value findings, willingness-to-pay evidence, and the Phase 8B content/conversion expansion.

**Safety boundary:** This roadmap change does not modify AI-v1.1, the AI-v1.0 decision protocol, S02, immutable ledgers, validation thresholds, broker execution, or trading behavior. No website mutation is authorized until the Phase 8A baseline and implementation plan are reviewed.


## 2026-10-08 — D040: Adopt a multi-provider durable IP backup architecture

**Decision:** Adopt the documented target architecture in `docs/vowsig-durable-ip-backup-and-recovery-plan-v0.1.md` for future implementation.

The intended durable hierarchy is:

1. Windows VPS as the live operational database host;
2. AWS S3 with versioning, encryption and Object Lock as the primary immutable backup vault;
3. Backblaze B2 as an independent second-provider disaster-recovery copy;
4. private GitHub for source, methodology, governance, activation/checkpoint hashes and selected manifests rather than bulk SQLite storage;
5. future S3/B2 storage for immutable training-dataset versions and proprietary model checkpoints.

**Reason:** VowSig's growing append-only evidence ledgers contain the market-state/AI-decision/outcome history that may become a core proprietary training asset. GitHub currently preserves code and cryptographic anchors, while live SQLite data is intentionally ignored by Git. A ledger hash proves identity but cannot reconstruct a destroyed database.

**Backup integrity rule:** Live SQLite databases must be copied through the SQLite online backup mechanism, then pass `PRAGMA integrity_check`, application ledger-chain verification and SHA-256/manifest generation before being treated as valid backups.

**Security rule:** Routine VPS backup credentials must be least privilege and unable to erase immutable history. Backup/restore credentials, provider accounts and secrets must remain separated.

**Recovery rule:** No automatic destructive restore into production. Restore first into an isolated location, verify hashes/database integrity/ledger chain, and require explicit owner authorization before replacing any live evidence database.

**Status:** Architecture/documentation decision only. No AWS/B2 resources, credentials, scheduled backup jobs, database mutations, restores, purchases or production changes are authorized or implemented by this decision.

## 2026-10-08 — D041: Preregister an isolated BTC/ETH/SOL crypto AI expansion before any live crypto inference

**Decision:** Create a separately versioned prospective crypto AI lineage for BTCUSDT, ETHUSDT and SOLUSDT under Issue #40.

Working runtime/evidence identity:

`AI-v1.3`

Working validation-program identity:

`crypto-expansion-1`

Decision protocol intent remains `AI-v1.0`, with the exact dated OpenAI model/provider profile reused unless a preactivation incompatibility is proven.

**Why separate:** The existing AI-v1.2 preregistration explicitly excluded crypto because its source/session/volume/cost semantics differ. Binance Spot is 24/7, its kline volume is base-asset volume rather than MT5 tick volume, and the current Binance kline adapter has no spread field while AI-v1 requires finite spread/cost context.

**Frozen initial universe:**

- BTCUSDT -> BTC/USDT
- ETHUSDT -> ETH/USDT
- SOLUSDT -> SOL/USDT

No post-activation market substitution is allowed because of weak performance or low activity.

**Primary source intent:** Binance Spot H1/H4 completed klines. Exness crypto CFDs are comparison-only where instrument identity is explicitly compatible; they may not replace the primary Binance source or enter crypto gate counts.

**Feature/cost boundary:** Price/ATR/EMA/RSI/structure/volatility formulas are intended to remain unchanged, but crypto receives a separately versioned feature profile because:

- `volume_z_20` uses Binance base-asset volume;
- spread must come from a prospective Binance top-of-book observation;
- zero-spread or unrelated MT5-spread substitution is forbidden;
- exact fee/slippage/all-in round-trip cost arithmetic must be numerically frozen before activation.

The numeric crypto cost policy is intentionally still a hard preactivation blocker.

**Planned evidence isolation:**

- `data/ai_v1_3_btcusdt.sqlite`
- `data/ai_v1_3_ethusdt.sqlite`
- `data/ai_v1_3_solusdt.sqlite`

No backfill. No count/calendar pooling with AI-v1.1, AI-v1.2.1 or S02.

**Frozen review gates:**

- C1: >=100 valid inferences and >=20 completed shadow trades; operational audit only.
- C2: >=500 valid inferences, >=50 completed trades and >=60 calendar days.
- C3: >=1,000 valid inferences, >=100 completed trades and >=120 calendar days.

Per-market and weekday/weekend reporting are mandatory. Gate results do not authorize public actionable signals or broker execution.

**Working scheduler design:** hourly near UTC minute 04, with all three causally available crypto snapshots frozen as one batch before provider calls. The existing <=300-second data-age intent remains; if readiness cannot satisfy it, scheduling/batching must be corrected before activation rather than relaxing freshness after performance evidence.

**API cost planning checkpoint:** Owner-VPS read-only usage analysis on 2026-10-08 measured approximately USD 0.011578 per successful inference across 456 usage-bearing AI calls. At 720 H1 opportunities per 24/7 crypto market per 30 days, the three-market crypto cohort is estimated at about USD 25.01/month incremental, taking the current six-market + three-crypto model estimate to about USD 61.69/month. USD 75/month is the planning budget with headroom. Cost is not a research gate.

**Approval boundary:** Current authorization is design/preregistration only. No Binance live/readiness call, OpenAI call, crypto ledger, activation anchor, scheduler change, public crypto signal or broker action is authorized by D041.

## 2026-10-08 — D042: Freeze the AI-v1.3 crypto research transaction-cost proxy before any performance-bearing inference

**Evidence:** Owner-authorized K1 live read-only Binance readiness passed for BTCUSDT, ETHUSDT and SOLUSDT. Official Binance Spot fee material was then researched before activation.

**Official fee baseline:** Binance's current Spot fee table lists the Regular User standard maker/taker rate as 0.100% / 0.100%. Binance separately offers account-dependent BNB/VIP discounts and may run temporary promotions.

**Decision:** AI-v1.3 will not rely on favorable account status or temporary promotions. Freeze a conservative research fee assumption of:

- Regular User;
- taker entry;
- taker exit;
- 0.100% per side;
- no BNB discount;
- no VIP discount;
- no pair-promotion discount.

Canonical policy:

`config/ai_v1_3_crypto_cost_policy.json`

Canonical research record:

`research/experiments/EXP-2026-018-ai-v1.3-crypto-cost-policy.md`

**Frozen static round-trip research cost:**

`0.002 * reference_midpoint + 2.0 * reference_spread`

where:

- one observed spread is the round-trip bid/ask crossing proxy;
- one additional observed spread is a preregistered conservative slippage buffer;
- the extra spread is a protocol-owned research assumption, not a Binance factual claim.

**Cost guard:** Carry forward `max_round_trip_cost_r = 0.15` from AI-v1 without tuning it against crypto outcomes. Directional proposals above that cost threshold are rejected with `cost_too_high`.

**SELL semantics:** A SELL shadow result does not imply that Binance Spot naked short execution is authorized or available. Borrow interest and futures funding are not modeled. Any executable short venue requires separate execution governance.

**Status:** The numeric cost-policy-definition blocker is closed prospectively. Runtime integration, deterministic guard/lifecycle tests, K2 package publication, K3 activation, K4 first performance-bearing cycle, K5 scheduling, public crypto exposure and broker/exchange execution remain unapproved.

## 2026-10-08 — D043: Integrate the frozen AI-v1.3 crypto cost policy through an isolated guard/signal/lifecycle path

**Authorization:** Owner explicitly approved `APPROVE AI-v1.3 OFFLINE COST INTEGRATION`.

**Decision:** Implement the frozen EXP-2026-018 cost policy through AI-v1.3-specific modules rather than changing the active AI-v1.1 / AI-v1.2.1 cost semantics.

Implemented isolated components:

- `crypto_cost_v1_3.py` — validates the frozen policy and computes fee + spread + slippage cost;
- `crypto_guardrails_v1_3.py` — applies the frozen 0.15R cost guard;
- `crypto_engine_v1_3.py` — validates execution context before provider use and freezes cost provenance into the crypto inference record;
- `crypto_signals_v1_3.py` — carries the exact frozen cost breakdown into the crypto SIGNAL;
- existing deterministic `evaluate_signal()` — reused unchanged to allocate the already-frozen total cost pro rata across partial/final exits.

**Isolation rule:** No active AI-v1.1, AI-v1.2.1 or S02 runtime/cost function was changed to adopt the crypto formula.

**Fail-closed rule:** Invalid/stale Binance execution context is rejected before a provider call in the AI-v1.3 engine path.

**Evidence:** Exact cost-integration candidate `b5a81bb076c7e1b189a23082ba4c9ffdb2cd98b7` passed 20 focused crypto tests, 271 full regression tests and Ruff on all changed Python surfaces in disposable Windows verification run `37853582251`.

**Safety:** The verification made no live Binance call, no OpenAI call, no crypto ledger, no scheduler mutation and no broker action.

**Status:** The cost-policy runtime-integration blocker is closed. This does not authorize K2 package publication, K3 activation, K4 first performance-bearing cycle, K5 unattended scheduling, public actionable crypto signals or broker/exchange execution.

