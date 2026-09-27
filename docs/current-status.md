# Current Status

**Phase:** 1 — Strategy evidence research  
**Date:** 2026-09-27

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
