# AI-v1.0 -> AI-v1.1 Activation & Supersession Plan v0.1

_Status: OWNER REVIEW REQUIRED — NOT APPROVED FOR ACTIVATION_  
_Date: 2026-09-30_  
_Parent issue: #15_

## Purpose

Define the exact prospective transition from the currently active AI-v1.0 shadow collector to AI-v1.1, whose only intended decision-affecting change is deterministic MT5 H1/H4 rates-read synchronization.

This document is a cutover plan only. It does not authorize activation, ledger creation, scheduler mutation, provider calls, backfill, or broker execution.

## Current verified state

The owner-run pre-activation checkpoint at repository commit:

`20ceb15e925dd3532117210e8ccba7eee82f7b4b`

passed:

- 26 focused/regression tests;
- v1.1 preactivation check = PASS;
- frozen decision artifacts match the active v1.0 anchor;
- live v1.1 execution remains blocked;
- v1.1 ledger count = 0;
- v1.1 activation-anchor count = 0;
- provider call made = false;
- MT5 call made = false;
- activation performed = false;
- scheduler changed = false.

The active upstream v1.0 anchor remains:

`research/forward/AI-v1-activation-2026-09-28T155616Z.json`

## Non-negotiable evidence rule

AI-v1.0 has performance-bearing forward records.

Therefore the existing:

`scripts/supersede_ai_v1_activation.py`

must **not** be used for this transition. That script is intentionally restricted to an activation-only/pre-performance supersession and refuses ledgers with performance-bearing records.

AI-v1.0 ledgers must remain immutable and preserved in their existing paths unless a separately reviewed archival copy procedure is introduced later.

No v1.0 record is deleted, rewritten, moved as part of activation, or backfilled into v1.1.

## Version identities

### AI-v1.0 legacy evidence

- runtime/evidence lineage: `AI-v1.0`;
- existing ledgers:
  - `data/ai_v1_xauusd.sqlite`
  - `data/ai_v1_ustec.sqlite`
  - `data/ai_v1_us30.sqlite`
- existing activation anchor remains immutable;
- final ledger heads/counts at cutover must be captured in a retirement/supersession metadata record.

### AI-v1.1 active replacement

- runtime/evidence lineage: `AI-v1.1`;
- frozen decision protocol: `AI-v1.0`;
- new ledgers:
  - `data/ai_v1_1_xauusd.sqlite`
  - `data/ai_v1_1_ustec.sqlite`
  - `data/ai_v1_1_us30.sqlite`
- A1/A2/A3 valid-inference/trade/calendar evidence restarts from the v1.1 activation time;
- no v1.0 gate counts carry forward;
- no prior missed v1.0 opportunity is backfilled.

## Cutover blocker discovered during review

The current read-only/public stack is hard-wired to v1.0:

- `src/trading_signal_intelligence/ai_v1/observability.py` reads `data/ai_v1_*.sqlite`;
- it probes task name `SignalProof AI-v1 Shadow Scan`;
- `src/trading_signal_intelligence/product/ai_insights.py` is built on that observability report;
- `scripts/export_public_snapshot.py` exports that result under `ai_v1`.

If the scheduler were switched to v1.1 before this layer becomes version-aware, the website could present frozen v1.0 evidence while a v1.1 collector is actually active.

Therefore activation is blocked until version-aware observability/public export is implemented and tested.

## Required implementation before owner activation review

### 1. Complete the v1.1 live runtime path

Add new files only; do not modify the activated v1.0 runtime files.

Required:

- v1.1 live runner using:
  - `MT5Connector`;
  - `read_synchronized_market_bars`;
  - frozen OpenAI adapter/config;
  - `run_market_cycle_v1_1`;
  - only v1.1 ledgers;
- synchronization timeout/no-current-tick outcomes recorded explicitly without provider calls;
- v1.1 runtime verifier;
- v1.1 task wrapper;
- v1.1 task installer/switch procedure.

Before activation, the live runner must remain fail-closed.

### 2. Implement version-aware observability

A new observability path must support AI-v1.1 without changing v1.0 evidence.

Required public/report fields include:

- `runtime_version`;
- `decision_protocol_version`;
- activation time;
- active ledger paths;
- active scheduler identity;
- v1.1-only A1/A2/A3 progress;
- synchronization operational counts;
- broker execution disabled.

The legacy v1.0 report must remain available as historical evidence, but must not be mixed into v1.1 gate progress.

### 3. Implement public snapshot transition

The public AI Insights payload must explicitly identify the active runtime.

Recommended compatibility shape:

- keep top-level snapshot key `ai_v1` for API/UI compatibility;
- inside it expose:
  - `runtime_version: AI-v1.1`;
  - `decision_protocol_version: AI-v1.0`;
  - v1.1 current forward evidence only;
  - notice that prior AI-v1.0 forward evidence is a separate legacy lineage;
- optionally add a sanitized legacy-lineage summary, but never merge v1.0 trade/inference counts into v1.1 gates.

Cloud validation/tests must reject an ambiguous active runtime.

### 4. Add performance-bearing v1.0 retirement metadata

Do not mutate or move v1.0 ledgers.

At cutover, create a committed metadata file such as:

`research/forward/AI-v1.0-retired-<UTC>.json`

It must bind:

- active v1.0 activation anchor;
- retirement timestamp;
- reason: prospective MT5 rates synchronization correction;
- final SHA-256 and head hash for each v1.0 ledger;
- final record counts/types;
- final valid inference / missed inference / completed trade counts;
- unresolved signal count;
- final scheduler state before disable;
- performance-bearing records observed = true;
- ledgers preserved = true;
- backfilled into v1.1 = false;
- provider call during retirement = false;
- broker execution = false.

This is metadata only. It does not rewrite v1.0.

## Critical cutover precondition: no unresolved v1.0 signals

The clean transition condition is:

`v1.0 unresolved shadow signals = 0`

Reason:

Stopping the v1.0 scheduler while it has an unresolved signal would strand that signal's frozen lifecycle and could prevent a valid TP/stop/timeout outcome from being appended.

We must not patch v1.0 into a special drain mode after activation.

Therefore:

- continue v1.0 unchanged until unresolved signals naturally reach zero;
- only then perform the scheduler cutover.

If unresolved signals are not zero, activation waits.

## Exact activation sequence

The final approved cutover should be performed between H1 cycles and in this order.

### Phase A — final pre-cutover verification

1. pull exact approved activation commit;
2. require clean tracked worktree;
3. run full v1.1 + v1.0 regression suite;
4. run v1.1 preactivation verifier;
5. verify no v1.1 ledgers/anchors exist;
6. verify v1.0 ledgers/anchor are valid;
7. verify v1.0 unresolved signals = 0;
8. capture current v1.0 ledger hashes/heads/counts;
9. capture current Windows task definition/state;
10. verify product/public snapshot still reports v1.0 as active.

Any failure => stop; no mutation.

### Phase B — disable v1.0 issuance

1. disable the existing Windows scheduled task; do not delete it yet;
2. verify task state = Disabled;
3. verify no task instance is Running;
4. do not modify v1.0 ledgers.

If disabling fails or an instance remains active => stop before v1.1 activation.

### Phase C — create v1.0 retirement metadata

1. create retirement metadata from the already-captured immutable v1.0 state;
2. do not move/delete/rename any v1.0 database;
3. commit/push the retirement metadata before v1.1 first inference.

If the metadata cannot be durably committed => keep v1.0 task disabled and do not activate v1.1 until reviewed.

### Phase D — create v1.1 activation ledgers + anchor

Only after explicit owner confirmation:

1. create exactly three new v1.1 ledgers;
2. each starts with exactly one `ACTIVATION` record;
3. use one shared activation timestamp;
4. entity IDs use `AI-v1.1:<market>:ACTIVATION`;
5. activation payload binds:
   - exact repository commit;
   - active v1.0 upstream anchor;
   - unchanged model/policy/schema/feature/guard/lifecycle hashes;
   - v1.1 sync/runtime/runner/verifier/task hashes;
   - 30s/1s synchronization constants;
   - gate carry-forward = false;
   - backfill = false;
   - broker execution = false;
6. verify all three ledgers;
7. write one v1.1 activation anchor;
8. commit/push the anchor before any performance-bearing v1.1 run.

If any market ledger/anchor operation fails, no v1.1 scheduler is installed.

### Phase E — verify product/observability on activation-only v1.1

Before first model call:

1. run v1.1 runtime verifier in activation-only mode;
2. run version-aware observability;
3. export a public snapshot locally;
4. confirm:
   - active runtime = AI-v1.1;
   - decision protocol = AI-v1.0;
   - v1.1 gate counts = zero;
   - legacy v1.0 counts are not merged;
   - broker execution false;
   - safety fields false;
5. do not publish a misleading cloud snapshot if these checks fail.

### Phase F — install/switch the scheduler

1. register or replace the scheduled task only after activation-only verification passes;
2. task description must explicitly say AI-v1.1;
3. use the same near-:02 H1 cadence;
4. StartWhenAvailable and IgnoreNew remain unchanged;
5. execution time limit remains 10 minutes;
6. runner must be the versioned v1.1 task wrapper;
7. verify NextRunTime and task action path;
8. retain the v1.0 task definition evidence in retirement metadata.

### Phase G — first v1.1 collection run

At the first natural scheduled run:

1. synchronization check happens before feature construction/provider call;
2. no backfill of v1.0 missed cycles;
3. only post-v1.1-activation opportunities are eligible;
4. if rates are unsynchronized:
   - no provider call;
   - explicit fail-closed operational record;
5. if synchronized:
   - unchanged AI-v1.0 decision protocol executes;
6. run v1.1 verifier immediately afterward;
7. inspect all three markets.

### Phase H — first public publish

After the first verified v1.1 runtime cycle:

1. export sanitized version-aware snapshot;
2. verify locally;
3. publish using the existing cloud ingest mechanism;
4. verify cloud:
   - runtime AI-v1.1;
   - protocol AI-v1.0;
   - broker execution disabled;
   - all safety declarations false;
   - no v1.0/v1.1 gate-count mixing;
5. preserve the previous cloud snapshot until a verified v1.1 snapshot is ready.

## Rollback / fail-closed rule

Once v1.1 has produced any performance-bearing inference, do **not** silently switch back to v1.0 and continue a mixed evidence lineage.

If v1.1 fails after activation:

- disable v1.1 scheduler;
- preserve v1.1 ledgers and anchor unchanged;
- do not backfill;
- do not resume v1.0 automatically;
- diagnose under a new governed version/correction;
- public AI Insights may show temporarily unavailable rather than misrepresenting runtime state.

Before the first performance-bearing v1.1 inference, a failed installation/cutover may be aborted while preserving activation-only v1.1 evidence; any replacement activation must be explicitly governed.

## A1/A2/A3 reset

For AI-v1.1:

- A1 starts from zero:
  - >=100 valid v1.1 inferences;
  - >=20 completed v1.1 shadow trades.
- A2 starts from the v1.1 activation time:
  - >=500 valid v1.1 inferences;
  - >=50 completed v1.1 trades;
  - >=60 calendar days.
- A3 starts from the v1.1 activation time:
  - >=1000 valid v1.1 inferences;
  - >=100 completed v1.1 trades;
  - >=120 calendar days.

AI-v1.0 remains historical operational/performance evidence but does not satisfy v1.1 gate thresholds.

## Owner approval boundary

This plan does not authorize activation.

Before any Phase B mutation, the owner must be shown:

- exact final repository commit;
- full regression/preflight PASS;
- v1.0 unresolved signal count = 0;
- exact retirement metadata preview;
- exact v1.1 activation payload preview;
- exact scheduled-task diff;
- exact public-snapshot versioning diff.

Only then should an explicit activation confirmation be requested.
