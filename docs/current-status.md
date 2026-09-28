# Current Status

**Phase:** AI-v1 forward shadow collection active; observability verified; AI Insights UI next  
**Date:** 2026-09-28

## Infrastructure

- Repository initialized: YES
- MT5 historical research connector: WORKING
- Binance historical research connector: WORKING
- Normalized candle model: WORKING
- Local SQLite research store/backfill: WORKING
- Historical backtest framework: WORKING
- Candle-level strategy audit tooling: WORKING
- H1↔H4 consistency audit tooling: WORKING
- S02 post-baseline local-sensitivity runner: COMPLETE
- S02 exact predeclared-neighborhood runner: COMPLETE
- S02 temporal-stability runner: COMPLETE
- S02 new-market transfer runner: COMPLETE
- Immutable hash-chained forward ledger: ACTIVATED / HASH ANCHORED
- S02 live forward scanner: ACTIVE / 72 CONSECUTIVE HOURLY RUNS VERIFIED THROUGH 2026-09-21 15:02 UTC
- SaaS UI: EARLY ACCESS DAY-2 BUILD / 3 FORWARD COLLECTORS ACTIVE
- AI-v1 replacement activation: VERIFIED / RUNTIME-BOUND
- AI-v1 shadow scheduler: ACTIVE / HOURLY / SHADOW-ONLY
- AI-v1 broker execution: DISABLED
- AI-v1 observability v0.1: COMPLETE / VPS VERIFIED / READ-ONLY
- AI-v1 next engineering milestone: AI INSIGHTS UI

## AI-v1 active forward-collection plan

AI-v1.0 is now collecting immutable forward evidence under the frozen preregistration and activated runtime.

Immediate work is **not** model tuning. The active sequence is:

1. keep the hourly AI-v1 scheduler running untouched;
2. **DONE:** build/test a strictly read-only progress and health monitor;
3. **DONE:** verify that monitor against the live VPS ledgers;
4. **NEXT:** build the AI Insights UI from read-only exported evidence;
5. continue product work that does not alter AI-v1 decision behavior;
6. review A1/A2/A3 only at their frozen eligibility thresholds.

Canonical plan: `docs/ai-v1-observability-plan.md`.

## Validation gates

- G1 research data: **PASS**
- G2 commercial source rights: **PASS — EXNESS COMMERCIAL DERIVED-SIGNAL PERMISSION CONFIRMED BY PROJECT OWNER**
- G3 strategy evidence: **IN PROGRESS — S02 XAU HISTORICAL ROBUSTNESS PASSED; TRANSFER PARTIAL; IMMUTABLE FORWARD EVIDENCE NEXT; NOT CANDIDATE**
- G4 customer value: **NOT STARTED**

## Data state

Research data is sufficient for historical testing. EURUSD, GBPUSD, USDJPY and XAUUSD have current H1 research datasets through 2026-09-17, with H4 regime data available.

The earlier GBPUSD/USDJPY August H1 cutoff was a transient MT5 history-synchronization state and has been repaired in the local research store.

EURUSD and XAUUSD broker H4 OHLC matched exact four-H1 reconstruction over every complete overlapping group tested.

## S01 Trend Pullback v0.1

**Disposition:** REJECTED AS A GENERAL FX HYPOTHESIS.

S01 remains a regression benchmark. Its already-observed XAU behavior is retained only as a separate research lead.

Evidence:

- `research/experiments/EXP-2026-003-s01-baseline.md`
- `research/experiments/EXP-2026-008-s01-cross-fx-disposition.md`

## S02 Structure Breakout v0.1

**Status:** RESEARCH — XAU FORWARD TEST ACTIVATED; LIVE EVIDENCE ACCUMULATION NEXT; NOT CANDIDATE.

The frozen four-market baseline is complete and the EURUSD/XAUUSD candle-level sample audits both passed 10/10 sampled trades.

OOS net expectancy:

- EUR/USD: validation +0.0459R/trade; final test -0.0127R/trade
- GBP/USD: validation -0.1858R/trade; final test +0.0444R/trade
- USD/JPY: validation +0.1764R/trade; final test -0.1631R/trade
- XAU/USD: validation +0.0986R/trade; final test +0.2323R/trade

XAU/USD is the only market positive in both OOS splits and is positive in each observed OOS calendar year 2023–2026. It also remains positive when the existing ledger is repriced at 2x and 3x the baseline spread-cost proxy.

Post-baseline local sensitivity (17 configurations per market) is now complete. XAU/USD remained positive in both OOS splits for 15/17 variants and positive in the final test for 17/17. The only validation-negative XAU neighbors were the tighter 1.50 ATR stop (-0.0393R/trade) and lower 2.0R target (-0.0192R/trade). Final-test expectancy across all XAU local variants stayed between +0.1450R and +0.2544R/trade. OOS trade counts remained substantial and the worst validation drawdown was -31.25R.

Exact pre-first-result specification sensitivity is now complete (23 configurations per market):

- EURUSD: 6/23 positive in both OOS splits;
- GBPUSD: 0/23;
- USDJPY: 0/23;
- XAUUSD: 20/23.

For XAUUSD, validation expectancy ranges from approximately -0.0393R to +0.1346R/trade and final-test expectancy from +0.1450R to +0.2765R/trade. The three validation-negative variants are structure window 30, stop 1.50 ATR, and target 2.0R. ATR 10/20, H4 EMA 30/80, wider breakout/filter settings and cost multiplier 2.0x all remain positive in both OOS splits.

Temporal analysis with the unchanged baseline is now complete. XAU has 10/15 positive complete half-years overall, but the recent sequence is more informative: six consecutive positive half-years from 2023-H2 through 2026-H1. Its rolling 12-month windows are positive for every start from 2022-01 through 2025-07 (15 consecutive windows). The six most recent fixed-rule prior-12m -> next-6m pairs are all positive-to-positive.

New-market transfer is complete. USTEC and US30 satisfy the pre-frozen descriptive transfer-support flag, with validation/final net expectancy of approximately +0.124/+0.012R and +0.094/+0.012R per trade respectively. XAGUSD, US500 and USOIL do not satisfy the rule.

Important caveats:

- the USTEC/US30 final-test margins are small and should not be promoted from this result;
- XAGUSD, the closest same-asset-class transfer market to XAU, is validation-negative after costs despite positive 2025–2026 results;
- US500 turns negative in the final test and USOIL is negative in both OOS splits;
- all 23 XAU exact-spec variants remain negative in development, so the XAU edge is not stationary over the full history;
- genuinely new forward evidence is still required.

Detailed evidence:

- `research/experiments/EXP-2026-009-s02-structure-breakout-baseline.md`
- `research/experiments/EXP-2026-010-s02-robustness-reconciliation.md`

## Experiment ID hygiene

Canonical experiment IDs are now unique. The executed data-quality audit is EXP-2026-006, the merged collector soak plan is EXP-2026-007, the S01 cross-FX disposition is EXP-2026-008, and the S02 baseline is EXP-2026-009.

## Immediate next external input

No intervention is required while the task remains healthy. Continue accumulating forward observations. Use `scripts/summarize_s02_forward_ops.py` plus `scripts/verify_forward_ledger.py` for concise health checks, and report immediately when SIGNAL/MISSED_SIGNAL/SKIPPED_SIGNAL/EXIT counts change or the task/ledger reports an error.

## Early Access launch scope — 2026-09-21

Target: launch within 3–5 days.

Initial live-signal markets:

- XAU/USD — primary;
- NASDAQ 100 / USTEC — secondary;
- DOW 30 / US30 — secondary.

Additional researched markets appear in the app with explicit evidence/status labels rather than being silently omitted.

Paid market-data subscriptions are deferred until product revenue exists; the confirmed Exness permission is the launch data path.


## Early Access Day-1 checkpoint — 2026-09-27

Local FastAPI/UI preview passed:

- application installed and started successfully;
- root page, static assets, `/api/health` and `/api/markets` returned successfully;
- multi-market launch UI rendered XAUUSD, USTEC and US30 plus the research-monitoring universe.

Secondary live-data recency did **not** pass:

- USTEC quote timestamp: 2026-09-25T20:54:59Z;
- USTEC H1 latest bar: 2026-09-18T11:00:00Z;
- USTEC H4 latest bar: 2026-09-18T08:00:00Z;
- US30 quote timestamp: 2026-09-25T20:54:59Z;
- US30 H1 latest bar: 2026-09-18T11:00:00Z;
- US30 H4 latest bar: 2026-09-18T08:00:00Z.

Both secondary markets therefore failed the pre-activation recency gate. Their forward ledgers must not be activated until recent H1/H4 history is synchronized.

A targeted `scripts/mt5_history_sync_probe.py` has been added. It requests recent history through MT5 position-, from-date-, and date-range APIs to diagnose/encourage terminal history synchronization without changing the frozen strategy or XAU forward protocol.


## Secondary recency recovery — 2026-09-27

The targeted MT5 history synchronization probe resolved the USTEC/US30 stale-history condition.

For both USTEC and US30:

- quote timestamp: `2026-09-25T20:54:59Z`;
- H1 latest bar: `2026-09-25T20:00:00Z`;
- H4 latest bar: `2026-09-25T20:00:00Z`;
- lag versus quote: approximately 0.916 hours;
- `copy_rates_from_pos`, `copy_rates_from`, and `copy_rates_range` all agreed;
- final H1 `appears_recent = true`;
- final H4 `appears_recent = true`.

The pre-activation recency gate is therefore passed for both secondary launch markets.

USTEC and US30 immutable ledgers are now activated, verified and durably anchored. Next: install the secondary hourly scheduler and confirm the first automatic run.


## Secondary forward activations — 2026-09-27

USTEC activation/head hash:

`b0bcb4c952c64c3043512905b803697b491841b99b08b256feb9de82f2cd2780`

US30 activation/head hash:

`3bc5a922843fea806b8aa4ab3c53a98a2d371982c7479164548b1a1e8fbea581`

Both ledgers verified with one ACTIVATION record and no unresolved signals. Separate durable anchor files are stored under `research/forward/`.


## Secondary scheduler first run — 2026-09-27

The first automatic USTEC/US30 run completed successfully:

- Windows task result: `0`;
- missed runs: `0`;
- USTEC scan/verify completed with no actions and a valid activation-only ledger;
- US30 scan/verify completed with no actions and a valid activation-only ledger;
- anchored head hashes remained unchanged.

The repository `.venv` also successfully runs the beta app with Uvicorn.

## Early Access Day-2 product layer

Implemented:

- frozen historical-evidence summaries for XAUUSD, USTEC and US30;
- public evidence API;
- per-market immutable signal-history API;
- aggregated live-signal-history API;
- forward operational-event counts;
- evidence cards in the beta UI;
- immutable forward-record UI section;
- read-only public snapshot exporter containing derived signal/evidence data only;
- fast beta product smoke script.

No frozen S02 strategy/scanner/ledger code was changed.


## Day-2 local smoke checkpoint — 2026-09-27 13:18 UTC

Local product smoke passed:

- `beta smoke: PASS`;
- collectors ready: `3/3`;
- launch ready: `True`;
- public snapshot exported successfully;
- `raw_market_data_included = false`.

The smoke output also reported `forward_signals = 2`. These are the first detected immutable forward SIGNAL records in the three-market launch system and must be inspected/anchored before treating them as ordinary UI data.

A read-only `scripts/inspect_forward_events.py` was added to print the exact SIGNAL/EXIT/MISSED_SIGNAL/SKIPPED_SIGNAL lifecycle records, current ledger heads and verification state across all three launch markets.

The browser screenshots still showed an older cached frontend bundle (old health-card wording and a persistent `Loading forward records...` state). Static asset URLs are now versioned to force the current evidence/signal UI to load.


## First completed XAU forward lifecycles — anchored 2026-09-27

The XAU forward ledger now contains two completed forward trades and one skipped overlapping setup.

- trade 1: short, net `-1.0071426171R`;
- trade 2: short, net `-1.0075745151R`;
- cumulative completed forward net R: approximately `-2.0147171322R`;
- skipped setup: one short signal while trade 2 was already open, correctly logged as `SKIPPED_SIGNAL`;
- unresolved signals: none;
- ledger verification: valid;
- current XAU ledger head: `e7b3e4d69292a81865ae62201e5cebb469e1b77d6826e0a9f434c4a677dcd904`.

F1 execution-audit progress is now `2/20` completed trades. This sample is too small for any strategy-performance decision.

Durable checkpoint: `research/forward/S02-XAUUSD-forward-checkpoint-2026-09-27.md`.


## Launch plumbing — 2026-09-27

Launch-critical product infrastructure has advanced without modifying any activated strategy/scanner/ledger implementation.

Added:

- optional HTTP Basic invite gate driven by environment secrets;
- Telegram SIGNAL/EXIT notifier with persistent deduplication state;
- cloud-facing FastAPI app that consumes only the derived public snapshot;
- bearer-authenticated snapshot ingestion;
- Docker container definition;
- Windows snapshot push client;
- hourly product publish task (snapshot -> optional alert -> optional cloud push);
- launch-layer smoke test.

The public/cloud design intentionally keeps raw MT5 candles and immutable forward SQLite databases on the Windows collector.

The first two completed XAU forward trades and current ledger head have been externally anchored in the repository.


## Launch-layer smoke + product-publish scheduler — 2026-09-27 13:39 UTC

The launch layer passed its local integration smoke:

- `launch layer smoke: PASS`;
- local collectors: `3/3`;
- cloud snapshot collectors: `3/3`;
- snapshot forward signals: `2`;
- exported snapshot explicitly reports `raw_market_data_included = false`.

Alert deduplication was initialized before any Telegram credentials were configured:

- existing lifecycle records marked seen: `4` (2 SIGNAL + 2 EXIT);
- state: `data/telegram_alert_state.json`.

This prevents already-closed historical-forward events from being replayed when Telegram is enabled later.

The `TradingTop Product Publish` Windows task is installed and Ready:

- next run at installation checkpoint: `2026-09-27 14:05:05` machine-local time;
- missed runs: `0`;
- pre-first-run result `267011 / 0x41303` means the task has not executed yet.

Only the first product-publish execution remains to be verified locally before public hosting.


## Product-publish automation verified — 2026-09-27

The first scheduled product-publish execution completed successfully:

- Windows Task Scheduler `LastTaskResult = 0`;
- missed runs: `0`;
- derived public snapshot exported successfully;
- `raw_market_data_included = false`;
- Telegram integration correctly reported disabled because credentials are not yet configured;
- cloud snapshot push correctly reported disabled because ingest URL/token are not yet configured.

A manual wrapper run also completed the same three stages successfully.

One logging-only defect was observed: the summary line rendered `push_exit=` blank even though the push step completed and the task returned success. The wrapper now uses delayed CMD expansion so future logs report all three exit codes explicitly.

Public-host deployment readiness has been hardened with:

- public `/healthz` endpoint for platform health checks;
- invite gate still applied to the actual beta surface;
- Railway deployment runbook at `docs/public-beta-deployment-railway.md`.

The local product layer is now considered READY FOR PUBLIC INVITE-GATED DEPLOYMENT.


## Railway deployment attempt — BLOCKED 2026-09-27

The user explicitly approved Railway deployment.

Attempted to create a new private Railway project named `tradingtop-early-access` in the user's personal Railway workspace.

Railway rejected the resource creation before any project/service was provisioned with:

`Free plan resource provision limit exceeded. Please upgrade to provision more resources!`

No Railway TradingTop project, service, domain, secret, or volume was created.

Project isolation remains intact: the application was **not** placed into either pre-existing unrelated Railway project.

Resolution options:

1. upgrade the Railway plan/capacity; or
2. free an unused Railway resource/project/service from the account.

After Railway capacity exists, resume with a new isolated `tradingtop-early-access` project and follow `docs/public-beta-deployment-railway.md`.


## Railway capacity recheck — 2026-09-27

After the user reported Railway capacity ready, a second isolated project-creation attempt was made.

Railway still returned:

`Free plan resource provision limit exceeded. Please upgrade to provision more resources!`

The connected Railway identity is `alisufyan-ai7` in workspace `alisufyan-ai7's Projects`, which currently contains two projects:

- `positioning-engine-cron` — currently zero services;
- `quantlyra-production` — active, multiple services.

Because the project-count/resource limit still blocks creating a third isolated project, deployment cannot proceed without either:

1. explicit approval to repurpose/remove the empty `positioning-engine-cron` Railway project; or
2. a Railway plan/capacity change that allows a third project.

No unrelated Railway project has been modified.


## Railway repurpose + service configuration — 2026-09-27

The user explicitly approved repurposing the empty Railway project `positioning-engine-cron` for TradingTop.

Railway now contains:

- project: `positioning-engine-cron` (repurposed);
- environment: `production`;
- service: `tradingtop-early-access`;
- source repo: `alisufyan-ai7/trading-signal-intelligence`;
- branch: `main`;
- builder: Dockerfile;
- Dockerfile path: `Dockerfile`;
- healthcheck: `/healthz`;
- healthcheck timeout: 120s;
- restart policy: on failure, max 5 retries;
- `TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`.

No public domain has been generated and no invite/ingestion secrets have been exposed.

Railway's connector successfully attached/configured the service but did not create its first deployment record. The connector's `redeploy` operation cannot act until one deployment already exists, and a second service is blocked by the free-plan resource limit.

**Required one-time UI action:** in Railway, open `positioning-engine-cron` → `tradingtop-early-access` and trigger the first deployment / deploy latest commit for `main`.

After that first deployment exists, automation can resume through the Railway connector for status, logs, redeploys and domain configuration.


## Railway first deployment — SUCCESS 2026-09-27

The first deployment of Railway service `tradingtop-early-access` completed successfully.

Deployment:

- deployment ID: `d8f2f1ee-dc9c-473e-bc37-325cd19b2ef6`;
- source commit: `d136a31f48997f17940d0e9931bb6f66da1656b1`;
- Dockerfile build: success;
- runtime: Uvicorn started successfully;
- Railway healthcheck: `GET /healthz -> 200 OK`;
- deployment status: `SUCCESS`;
- region: `asia-southeast1-eqsg3a`.

Current Railway variables contain only the non-secret snapshot path:

`TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`

No public Railway domain exists yet.

The invite credentials and ingestion token are intentionally still unset, so the service remains unexposed.

Persistent volume is still absent. This does not block the beta; the Windows publisher can repush the snapshot after a Railway restart/redeploy.


## Railway invite-gated domain — 2026-09-27

The three required Railway secret variable names are present:

- `TRADINGTOP_BETA_USER`
- `TRADINGTOP_BETA_PASSWORD`
- `TRADINGTOP_INGEST_TOKEN`

Their values remain redacted through the connector.

Saving the secret variables triggered a successful Railway deployment. The new deployment passed `GET /healthz -> 200 OK`.

A Railway public service domain has now been created:

`https://tradingtop-early-access-production.up.railway.app`

The invite middleware is active because both beta-user/password variables are configured. Snapshot ingestion remains separately protected by the bearer ingestion token.

The cloud currently has not yet received its first derived snapshot.

Added `scripts/configure_cloud_ingest.ps1` so the Windows collector can securely store the Railway ingest URL/token in local `.env` without echoing the token.


## Public app auth removed / VPS env simplified — 2026-09-27

Per project-owner request, HTTP Basic username/password authentication has been removed from the TradingTop app.

Changes:

- local app no longer mounts the Basic-auth middleware;
- cloud app no longer mounts the Basic-auth middleware;
- Railway `TRADINGTOP_BETA_USER` and `TRADINGTOP_BETA_PASSWORD` were blanked;
- snapshot ingestion remains protected by `TRADINGTOP_INGEST_TOKEN`;
- `.env.example` now documents only ingest + optional Telegram settings.

The Windows VPS collector successfully ran `scripts/configure_cloud_ingest.ps1`, which stored:

- `TRADINGTOP_INGEST_URL=https://tradingtop-early-access-production.up.railway.app/api/internal/snapshot`;
- `TRADINGTOP_INGEST_TOKEN=<secret>`

in the repository-root local `.env`.

The token value remains local/private and is ignored by Git.


## Cloud ingest URL incident — 2026-09-27

The first Windows-to-Railway snapshot POST failed with HTTP 404.

Railway HTTP logs showed the local `.env` ingest URL was malformed: the ingestion-token assignment had been concatenated into the request path. Because that malformed request path caused the ingestion token to appear in Railway request logs, the affected token must be treated as compromised and rotated before further pushes.

Mitigations committed:

- `scripts/configure_cloud_ingest.py` now writes URL/token with `python-dotenv set_key` and verifies both values after writing;
- ingest URLs are validated as HTTPS and rejected if they contain environment-variable text or suspicious `=` path content;
- `scripts/push_public_snapshot.py` now refuses malformed URLs before sending and reports HTTP failures without a Python traceback.

Next: rotate `TRADINGTOP_INGEST_TOKEN` in Railway and the VPS `.env`, then retry the snapshot push.


## First successful Windows -> Railway snapshot push — 2026-09-27

The Windows VPS successfully exported and pushed the current derived public snapshot to Railway.

Push response:

- `accepted = true`;
- `generated_at_utc = 2026-09-27T17:10:07.772574+00:00`;
- snapshot market rows: `9`;
- launch live-signal markets: `3`;
- `raw_market_data_included = false`.

The 9 snapshot rows are expected: 3 live-signal markets plus 6 research/monitoring markets.

Railway request logs confirm:

- `POST /api/internal/snapshot -> 200 OK`;
- public `GET /` -> 200;
- `GET /api/health` -> 200;
- `GET /api/markets` -> 200;
- `GET /api/signals` -> 200.

Railway also automatically deployed the latest hardened code commit and passed `/healthz`.

The public beta data path is now end-to-end operational:

Windows collectors -> immutable ledgers -> derived public snapshot -> bearer-authenticated Railway ingestion -> public UI/API.


## Public browser smoke + scheduled publish — PASS 2026-09-27

The project owner completed a browser smoke of the Railway-hosted public beta.

Observed in the live UI:

- no username/password prompt;
- systems operational;
- 3/3 live collectors active;
- XAU/USD, NASDAQ 100 and DOW 30 live-signal cards visible;
- frozen evidence cards visible for XAUUSD, USTEC and US30;
- two closed immutable XAU forward signals visible with entry/stop/target/result/hash;
- six research/monitoring markets visible with explicit evidence-status labels;
- research-beta disclaimer visible;
- historical and forward evidence are visibly separated.

The Windows product-publish wrapper was also run manually after cloud ingestion was fixed.

Final wrapper status:

`export_exit=0 alert_exit=0 push_exit=0`

Telegram remained intentionally disabled.

Railway logs independently confirm the wrapper's cloud push:

`POST /api/internal/snapshot -> 200 OK` at approximately 2026-09-27T17:14Z.

Day-4 deployment smoke is therefore complete.


## AI-0 / AI-1 governance checkpoint — 2026-09-28

The project owner formally approved the AI-first product direction.

### AI-0 — naming

Working product name selected:

**SignalProof AI**

Working promise:

> AI finds the setup. Risk rules verify it. Every signal stays on the record.

The customer-facing beta metadata/UI has been renamed away from the competitor brand. Engineering identifiers and the existing Railway hostname may remain temporarily until a separate public-hostname transition is performed.

No broad trademark/domain clearance has been performed under the strict context-isolation rule; the name remains a working product name until that separate check.

### AI-1 — frozen architecture

The AI-v1 protocol is now frozen **before first AI-v1 performance-bearing inference**.

Frozen artifacts:

- `docs/ai-v1-architecture.md`
- `docs/ai-v1-feature-definitions.md`
- `config/ai_v1_feature_schema.json`
- `config/ai_v1_policy.txt`
- `config/ai_v1_decision_schema.json`
- `config/ai_v1_guardrails.json`
- `docs/ai-v1-ledger-spec.md`
- `config/ai_v1_activation_schema.json`
- `research/experiments/EXP-2026-014-ai-v1-shadow-preregistration.md`

AI-v1 initial universe:

- XAUUSD
- USTEC
- US30

AI-v1 initial mode:

- shadow only;
- completed-H1 feature snapshots;
- BUY / SELL / NO_TRADE;
- provider-neutral reasoning-model adapter;
- deterministic publication/risk guard;
- separate immutable AI ledger;
- no broker execution;
- no S02 inputs;
- no news/sentiment in v1.0;
- exact provider/model/prompt still must be frozen before activation.

The existing S02 forward ledgers remain unchanged and continue as the benchmark/control.

### AI-v1 review gates

- A1: >=100 valid inferences and >=20 completed shadow trades — operational audit only.
- A2: >=500 valid inferences, >=50 completed trades and >=60 days — interim review.
- A3: >=1,000 valid inferences, >=100 completed trades and >=120 days — first publishability decision.

No AI-v1 result has been observed yet.

### Immediate implementation status

Authorized next work:

1. deterministic feature builder;
2. provider-neutral inference adapter;
3. exact model/provider selection and prompt freeze;
4. schema validator + deterministic guard;
5. separate append-only AI ledger;
6. shadow lifecycle evaluator;
7. activation fingerprints / tests;
8. shadow scheduler.

Activation remains blocked until all frozen preconditions pass.


## AI-v1 foundation implementation — committed 2026-09-28

The next engineering milestone is now implemented in code, but **not activated**.

Implemented:

- deterministic AI-v1 H1/H4 feature snapshot builder;
- canonical feature JSON + SHA-256;
- provider-neutral reasoning-model adapter contract;
- strict BUY/SELL/NO_TRADE decision validation;
- deterministic publication guard;
- isolated append-only AI-v1 hash-chained ledger;
- inference-cycle orchestration for INFERENCE / NO_TRADE / REJECTED_INFERENCE / MISSED_INFERENCE;
- deterministic next-H1-open signal construction;
- TP1/TP2/STOP/TIMEOUT shadow lifecycle evaluator;
- conservative same-bar stop-first handling;
- 50/50 TP1/TP2 cost/R accounting;
- read-only live MT5 feature-snapshot probe;
- synthetic foundation smoke script that also verifies the three S02 database hashes remain unchanged.

New implementation package:

`src/trading_signal_intelligence/ai_v1/`

New scripts:

- `scripts/smoke_ai_v1_foundation.py`
- `scripts/build_ai_v1_feature_snapshot.py`

New tests:

- `tests/test_ai_v1_features.py`
- `tests/test_ai_v1_contract_ledger.py`
- `tests/test_ai_v1_inference.py`
- `tests/test_ai_v1_engine.py`
- `tests/test_ai_v1_signals.py`

No external AI provider call has been made.
No AI-v1 database has been activated.
No broker execution has been enabled.
The exact provider/model ID is still intentionally unselected and remains an activation blocker.

**Required verification before continuing:** run the AI-v1 foundation smoke/tests on the Windows VPS after pulling the latest repository state.


## AI-v1 foundation VPS verification — PASS 2026-09-28

The Windows VPS pulled the Windows-SQLite cleanup fix and reran the complete foundation verification successfully.

Observed smoke result:

- `ai_v1_foundation_smoke = PASS`;
- `inference_adapter_exercised = true`;
- `provider_call_made = false`;
- `metadata_filter_passed = true`;
- `guard_publishable = true`;
- `estimated_cost_r ≈ 0.04885929772637945`;
- `ledger_verified = true`;
- `s02_database_hashes_unchanged = true`;
- `broker_execution_enabled = false`.

Observed AI-v1 unit-test result:

`12 passed in 6.41s`

The foundation implementation is therefore verified on the target Windows VPS.

The exact provider/model ID, provider-specific inference parameters, activation bundle and shadow scheduler remain unactivated/open. No external AI inference has been made yet.


## AI-v1 provider selection + concrete adapter — committed 2026-09-28

Fresh public provider research is now explicitly allowed under the project isolation rule; private context remains restricted to this chat and this exact repository.

AI-v1 provider/model is now frozen **before first performance-bearing inference**:

- provider: OpenAI;
- API: Responses;
- model snapshot: `gpt-5.4-2026-03-05`;
- reasoning effort: `medium`;
- service tier: `default`;
- `store=false`;
- truncation disabled;
- max output tokens: `8192`;
- no tools / no prior-response state;
- temperature/top_p omitted.

Provider-selection evidence:
`docs/ai-v1-provider-selection.md`

Frozen provider config:
`config/ai_v1_provider.json`

OpenAI-compatible strict-output schema:
`config/ai_v1_openai_response_schema.json`

The provider-compatible schema exists because OpenAI Structured Outputs does not support the conditional composition constructs in the canonical schema. The canonical local decision validator remains authoritative.

Implemented:

- concrete dependency-free OpenAI Responses HTTPS adapter;
- completed/incomplete/refusal/error parsing;
- request/usage metadata capture without storing API credentials;
- immutable AI `ERROR` event on provider failure;
- provider/activation contract tests;
- dependency-free local `.env` loader;
- secure local API-key configuration helper;
- synthetic non-performance provider smoke script;
- activation preview/fingerprint builder;
- guarded three-ledger activation script that performs no provider call and installs no scheduler.

No live provider call has been made yet.
No AI-v1 activation ledger exists yet.
No shadow scheduler is installed yet.
S02 remains unchanged.


## AI-v1 provider adapter VPS verification + activation preview — PASS 2026-09-28

The Windows VPS pulled the frozen OpenAI provider implementation and completed the expanded offline verification.

Observed focused test result:

`20 passed in 4.46s`

Activation preview result:

- `mode = PREVIEW_ONLY`;
- `provider_call_made = false`;
- `ai_ledgers_created = false`;
- `broker_execution_enabled = false`;
- repository commit at preview: `5cf4c47971c1d9e8a5c079f68e89ccf587d1e253`;
- provider: `openai`;
- model: `gpt-5.4-2026-03-05`;
- model-parameter fingerprint: `ed5069535190cb33771ff8efe1c4389e09abaddea933143c0c839c6dc87d3e9b`;
- cost-policy fingerprint: `b420e2a1f5b1acfdbdd46c3355c520b6a3e2d9697adc0c1ff0e7c5ca48b4671e`.

Preview activation bundle hashes:

- XAUUSD: `31ef91c9bc3e9711f78426f3a88dc2c8856e14f2f43b7aa198dd96337315c578`;
- USTEC: `d189151b45892b0333b7a5a7a50b97431a3fbe650ab005ad4f018533b6ffece2`;
- US30: `bfd6e4b61169740a7936a0aa04f19dabe0d6c4736368556f070f782d71f2d7b4`.

These are preview fingerprints only; no ACTIVATION record was created and they must not be treated as final ledger-head anchors.

The next required checkpoint is exactly one synthetic non-performance OpenAI provider smoke after configuring `OPENAI_API_KEY` locally. The real AI-v1 ledgers remain unactivated.


## AI-v1 synthetic provider smoke — ACCESS BLOCKED 2026-09-28

The first synthetic non-performance OpenAI provider smoke reached the live Responses API but failed before any model inference with:

`HTTP 403 / model_not_found: project does not have access to gpt-5.4-2026-03-05`.

Consequences:

- no AI-v1 trading/performance decision was produced;
- no AI-v1 performance ledger was written;
- no activation ledger exists;
- no shadow scheduler is installed;
- S02 remains unchanged;
- the API key itself is functioning well enough to authenticate the request, but this OpenAI project cannot currently use the frozen model snapshot.

Official OpenAI documentation still lists `gpt-5.4-2026-03-05` as a valid GPT-5.4 snapshot. OpenAI project documentation also states that project owners can configure **Model Usage** permissions and rate limits per project, and GPT-5.4's documented API rate-limit table starts at Tier 1 rather than Free.

Therefore this is treated as a **project/model access blocker**, not as an AI-v1 performance result and not yet as evidence that the frozen model must be replaced.

Added `scripts/probe_openai_model_access.py` to query the project's model metadata only (GET /v1/models and GET /v1/models/{model}); it makes no inference request and no ledger write. It probes the configured GPT-5.4 snapshot plus dated GPT-5.5, GPT-5.4 Mini and GPT-5.2 candidates for diagnostic purposes.

Do not activate or change the frozen model until that access diagnostic is reviewed.


## Wrong OpenAI project-key precedence identified and fixed — 2026-09-28

Root cause of the earlier GPT-5.4 403 is now identified: the VPS inherited `OPENAI_API_KEY` belonged to another OpenAI project, while the correct SignalProof key was present in this repository's local `.env`.

The previous loader did not override an already-present process/system variable, so the unrelated Windows credential won.

Fix committed:

- project-local `.env` now explicitly overrides inherited environment values for AI-v1 provider operations;
- `smoke_ai_v1_openai_provider.py`, `probe_openai_model_access.py`, and `activate_ai_v1.py` use project-local precedence;
- regression test added;
- `.env` remains excluded from Git.

The previous 403 should therefore be treated as a credential-source/configuration error from the wrong OpenAI project, not evidence about this project's GPT-5.4 access.


## Correct-project OpenAI verification + synthetic provider smoke — PASS 2026-09-28

After fixing project-local credential precedence, the Windows VPS confirmed the correct SignalProof OpenAI project is being used.

Focused regression tests:

`8 passed in 2.41s`

Metadata-only model probe:

- models list HTTP status: `200`;
- accessible models returned: `134`;
- frozen model `gpt-5.4-2026-03-05`: accessible, HTTP `200`, present in model list;
- dated GPT-5.5, GPT-5.4 Mini and GPT-5.2 diagnostic candidates were also accessible;
- no inference call and no performance-ledger write occurred during the probe.

The frozen-model synthetic provider smoke then passed:

- `provider_smoke = PASS`;
- provider: `openai`;
- served model: `gpt-5.4-2026-03-05`;
- service tier: `default`;
- model-parameter fingerprint: `ed5069535190cb33771ff8efe1c4389e09abaddea933143c0c839c6dc87d3e9b`;
- decision contract valid;
- synthetic result: `NO_TRADE`, raw confidence 18, regime RANGE;
- performance-ledger write: false.

Observed synthetic request usage:

- input tokens: 954;
- output tokens: 264;
- reasoning tokens within output: 86;
- total tokens: 1,218.

At the current documented GPT-5.4 standard price ($2.50/M input, $15/M output), this specific smoke call cost approximately **$0.00635** before any account-specific discounts/credits.

D033 remains unchanged. The earlier 403 is fully explained by the wrong inherited VPS project key.

AI-v1 is now ready for the **ledger-only activation step**. No performance-bearing AI-v1 inference has occurred yet.


## AI-v1 first activation verified; replacement runtime-bound activation required — 2026-09-28

The first ledger-only AI-v1 activation succeeded and its anchor is durably committed at:

`a3c986fb9527d351c0998f072ebfe159b7a8b0ac`

Verified activation heads:

- XAUUSD: `2e9e547276a054416d60ef4a6b6d0bc042fee43c7c0fdd3eec86a2548bbe34b1`
- USTEC: `571fad6647ca024b5c53e567b3d6e8643e5dc3e938b39e451f5830d6de0ab268`
- US30: `f508a6b65c9ad5b6775180498ae80f06ffc6d53cc6220fbe275ffd5fcf5e867a`

Git comparison confirmed the anchor commit adds only the activation JSON above the activated repository commit.

No performance-bearing AI-v1 inference has occurred.

During the required pre-scheduler review, one governance completeness issue was identified: the unattended live H1 runtime/scheduler did not yet exist in the repository tree bound by the first activation. The scheduler was therefore **not installed or run**.

A final live runtime is now implemented and frozen before first performance evidence:

- `docs/ai-v1-shadow-runtime.md`
- `src/trading_signal_intelligence/ai_v1/shadow_runtime.py`
- `scripts/run_ai_v1_shadow.py`
- `scripts/verify_ai_v1_runtime.py`
- `scripts/run_ai_v1_shadow_task.cmd`
- `scripts/install_ai_v1_shadow_task.ps1`
- `scripts/supersede_ai_v1_activation.py`
- `tests/test_ai_v1_shadow_runtime.py`

The activation bundle builder now fingerprints the runtime specification/source/task files. Inference-record provenance was also completed before live collection.

The first activation must now be preserved as a **superseded pre-performance activation**, its activation-only databases archived without deletion, and a replacement AI-v1.0 activation created from the final runtime commit.

This correction is not performance-driven: all three current AI ledgers still contain activation only.
