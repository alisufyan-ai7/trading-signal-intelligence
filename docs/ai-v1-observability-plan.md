# AI-v1 Observability and Parallel Product Work Plan

_Status: OBSERVABILITY V0.1 VERIFIED — forward collection running; AI Insights UI next_  
_Date: 2026-09-28_

## Purpose

AI-v1.0 is now activated and collecting immutable forward shadow evidence on XAUUSD, USTEC and US30.

The activated decision system must remain unchanged while evidence accumulates. Product and observability work may continue in parallel only when it is read-only with respect to AI-v1 decision/evidence semantics.

## Frozen AI-v1 boundary

Do not change AI-v1.0 based on early results:

- model/provider/model parameters;
- prompt/policy;
- feature formulas or schemas;
- guardrails;
- market universe;
- inference cadence/freshness semantics;
- entry/exit lifecycle;
- cost policy;
- scheduler behavior that changes decision opportunities;
- existing immutable ledger records.

Any decision-affecting change requires a separately governed version and activation.

S02 remains unchanged as the deterministic benchmark/control.

## Immediate engineering milestone — AI-v1 Observability v0.1

Build a strictly read-only monitoring/reporting layer.

Primary command:

`scripts/report_ai_v1_progress.py`

Required output:

- scheduler/runtime health;
- last successful scheduled run and task result when available;
- activation anchor identity;
- broker-execution flag;
- ledger hash-chain verification for all three markets;
- valid INFERENCE count;
- NO_TRADE count;
- REJECTED_INFERENCE count;
- MISSED_INFERENCE count;
- ERROR count;
- open shadow signals;
- completed shadow trades;
- TP1 / TP2 / STOP / TIMEOUT outcome counts;
- cumulative net R and drawdown as observational metrics only;
- market-level breakdown for XAUUSD / USTEC / US30;
- provider/runtime error rate;
- A1 / A2 / A3 progress and eligibility state.

The monitor must support machine-readable JSON so the same evidence can feed the web product later.

## Safety requirements for the monitor

Tests must prove that the monitor:

- opens AI-v1 ledgers read-only;
- cannot append, update or delete AI-v1 records;
- cannot mutate S02 databases;
- makes no provider inference call;
- makes no broker call or broker mutation;
- does not modify frozen AI-v1 artifacts;
- fails visibly if ledger verification fails.

## Monitoring cadence

### Every scheduled run

The existing runtime continues its built-in pre/post verification and ledger-chain checks.

A market/provider/system failure must remain visible through a non-zero scheduled-task result or immutable ERROR evidence.

### Daily operational review

Produce a compact read-only health/progress snapshot containing:

- scheduler health;
- ledger integrity;
- inference / missed / error counts;
- open/completed shadow signals;
- A1 progress;
- broker execution still false.

This is operational monitoring, not a performance-tuning loop.

### Governed milestone reviews

Do not make model/prompt/guardrail changes based on interim wins/losses.

Frozen gates:

- A1: >=100 valid inferences AND >=20 completed shadow trades — operational audit only.
- A2: >=500 valid inferences AND >=50 completed shadow trades AND >=60 calendar days — interim review.
- A3: >=1,000 valid inferences AND >=100 completed shadow trades AND >=120 calendar days — first planned publishability decision.

## Parallel product work while AI-v1 collects

After Observability v0.1 is verified:

1. build the AI Insights UI against read-only AI-v1 outputs;
2. expose current shadow signals and immutable AI signal history;
3. show reasoning summaries without hidden chain-of-thought;
4. show issuance/expiry/lifecycle state clearly;
5. show evidence status and A1/A2/A3 progress;
6. continue non-decision product infrastructure such as accounts, plans, notifications and durable presentation/persistence;
7. keep broker-connected automated execution out of scope.

Current public S02 signals must not be relabeled as AI.

## Current evidence checkpoint

The first natural scheduled AI-v1 runs are operating successfully.

At the first recorded live checkpoint:

- XAUUSD: 2 INFERENCE records, 1 SIGNAL, 1 NO_TRADE and 1 MISSED_INFERENCE;
- USTEC: 1 INFERENCE, 1 NO_TRADE and 1 MISSED_INFERENCE;
- US30: 2 MISSED_INFERENCE records;
- one XAUUSD shadow signal remained unresolved;
- all three ledgers verified;
- no provider/system failure was reported;
- broker execution remained disabled.

These counts are descriptive only and must not be used to tune AI-v1.0.

## Expected validation timeline

A1 timing is driven mainly by the natural completed-trade rate. A planning estimate is roughly 1–3 weeks, but no date is guaranteed.

A2 cannot be eligible before 60 calendar days after activation and also requires its inference/trade thresholds.

A3 cannot be eligible before 120 calendar days after activation and also requires its inference/trade thresholds.

Using the 2026-09-28 replacement activation date:

- earliest A2 calendar eligibility: 2026-11-27;
- earliest A3 calendar eligibility: 2027-01-26.

If trade-count thresholds are not met by those dates, the review moves later.

## Active work order

1. Keep AI-v1.0 forward scheduler running untouched.
2. Build and test AI-v1 Observability v0.1.
3. Verify the monitor on the VPS against the live immutable ledgers.
4. Build AI Insights UI from the read-only monitor/export.
5. Continue product work that does not change AI-v1 decision behavior.
6. Perform A1 only when the frozen thresholds are naturally reached.


## Implementation checkpoint — v0.1 committed and VPS verified

Implementation is committed on `main` without changing any activation-bound AI-v1 decision/runtime artifact.

Commits:

- `8876604be49d90ea11982b95f3e7bbc007c7bc1d` — read-only observability core;
- `0723d264121deb0fe483f93398274e598f758f13` — progress-reporting CLI;
- `451169a664e20ba6bee5497493f9ca1a28164f6a` — read-only/tamper/gate tests;
- `9274500e4f345909ab5063785e97a285085996bc` — scheduler-health fail-closed handling and aggregate monitoring totals.

Added:

- `src/trading_signal_intelligence/ai_v1/observability.py`;
- `scripts/report_ai_v1_progress.py`;
- `tests/test_ai_v1_observability.py`.

The core opens AI-v1 SQLite databases using URI `mode=ro` plus `PRAGMA query_only=ON`. It independently verifies the append-only hash chain and activation-anchor match, checks frozen activation artifact hashes, checks the committed upstream anchor, reads Windows Task Scheduler state, and calculates observational-only lifecycle/performance and A1/A2/A3 progress metrics.

No OpenAI/MT5/broker adapter is imported or invoked by the observability module.

Windows VPS verification completed successfully:

1. focused observability tests: `4 passed in 5.34s`;
2. live report: `HEALTHY`, `READ_ONLY`, exit code `0`;
3. all three live AI-v1 database SHA-256 hashes were byte-identical before vs after the report;
4. normal activated runtime verification remained `valid=true`;
5. activation anchor upstream check remained valid;
6. all 25 frozen activation artifact hashes matched;
7. broker execution remained disabled;
8. tracked worktree remained clean.

Observability v0.1 is complete. The next engineering milestone is the AI Insights UI, consuming only the read-only observability/export layer.
