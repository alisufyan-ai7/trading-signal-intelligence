# AI-v1 live shadow runtime specification

_Status: FROZEN BEFORE FIRST PERFORMANCE-BEARING INFERENCE — 2026-09-28_

This document freezes the operational runtime that turns the already-activated AI-v1 research protocol into unattended H1 shadow collection.

It does not change the AI-v1 decision space, feature formulas, model, risk rules, lifecycle, market universe or broker-execution boundary.

## Runtime universe

Exactly:

- XAUUSD
- USTEC
- US30

Source:

`exness_mt5_demo`

AI-v1 remains shadow-only. Broker execution is disabled.

## Data retrieval window

Each scheduled run requests:

- latest 500 H1 bars;
- latest 200 H4 bars;

through the existing MT5 connector with the current bar marked incomplete.

These values match the already-committed pre-activation live feature-probe defaults.

Only completed bars enter feature calculations.

## Cadence

Windows Task Scheduler runs once per hour near minute 02.

The task uses:

- `StartWhenAvailable`;
- `MultipleInstances IgnoreNew`;
- 10-minute execution limit;
- interactive/highest Windows principal so the existing MT5 terminal session is available.

The protocol freshness boundary remains unchanged:

`0 <= data_age_seconds <= 300`

The scheduler timing is only an operational way to reach that frozen boundary.

## Cycle identity

Each completed H1 opportunity is identified as:

`AI-v1.0:<SOURCE_SYMBOL>:<SOURCE_BAR_CLOSE_UTC>`

No completed bar after activation may receive more than one live-equivalent inference cycle.

## Backlog rule

The runtime never backfills a stale bar with a retrospective AI decision.

For an unprocessed completed H1 bar after activation:

- if data age exceeds the frozen 300-second limit, append `MISSED_INFERENCE`;
- do not call the provider for that stale bar.

If the scheduler was unavailable for multiple H1 closes, the stale opportunities are recorded as missed rather than retrospectively inferred.

## Fresh-cycle rule

For a fresh unprocessed completed H1 bar:

1. verify the committed activation anchor and frozen artifact hashes;
2. verify the local AI ledger hash chain;
3. require the next H1 bar to exist so the frozen next-H1-open entry can be observed;
4. build the deterministic feature snapshot;
5. require the snapshot source-bar close to equal the scheduled cycle close;
6. call the exact frozen OpenAI model;
7. validate and guard the structured output;
8. append immutable inference/lifecycle records;
9. for an approved BUY/SELL, create the shadow signal from the observed current-H1 open;
10. verify the ledger again.

No broker order or broker mutation occurs.

## Existing open signal

Before a new inference cycle, the runtime evaluates any existing unresolved AI shadow signal against newly completed H1 bars.

The frozen lifecycle rules remain:

- stop-first for ambiguous same-bar ordering;
- 50% TP1;
- 50% TP2;
- no stop move after TP1;
- 24-H1-bar timeout;
- frozen cost treatment.

After deterministic lifecycle evaluation, at most one unresolved AI-v1 signal may remain per market.

## Provider/data failures

Provider failures are recorded as immutable `ERROR` records for the affected fresh cycle.

Feature-snapshot failures are also recorded as immutable `ERROR` records.

A stale or unavailable next-H1-open cycle is not retried as if it were live later.

## Activation verification

The runtime refuses to run unless:

- a local activation record matches a committed activation anchor;
- the activation anchor's exact bytes are present in the configured Git upstream branch;
- all artifact hashes contained in that anchor still match the local frozen files;
- every market ledger verifies as a valid append-only hash chain;
- broker execution is false.

Before the first scheduled run, each active ledger must contain only its single replacement ACTIVATION record.

## Logging

The scheduled wrapper writes operational output to:

`data/forward-task-logs/ai_v1_shadow.log`

The wrapper runs the shadow cycle and then the runtime verifier.

A market/provider/system failure produces a non-zero task result rather than silently reporting success.

## Versioning boundary

After the replacement activation that binds this runtime, a decision-affecting change to any of the following requires a separately governed version/activation:

- market universe;
- H1/H4 retained retrieval window if it changes computed features;
- inference cadence/freshness semantics;
- provider/model/parameters;
- feature formulas;
- prompt/policy;
- guardrails;
- entry/exit lifecycle;
- cost policy.

Pure logging/display changes that do not affect decisions or evidence semantics may be handled separately, but frozen artifact hashes must continue to verify.
