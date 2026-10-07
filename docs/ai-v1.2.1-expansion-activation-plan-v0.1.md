# AI-v1.2.1 Expansion Activation Plan v0.1

_Status: PRE-ACTIVATION / NO AUTHORITY TO ACTIVATE — 2026-10-07_

## 1. Scope

This plan governs the prospective AI-v1.2.1 successor to the immutable
AI-v1.2 P2 fail-closed runtime.

Runtime version:

`AI-v1.2.1`

Decision protocol:

`AI-v1.0`

Markets:

- EURUSD
- XAGUSD
- USOIL

Parallel active runtime:

`AI-v1.1`

Broker execution remains disabled.

Public expansion exposure remains disabled.

## 2. Immutable predecessor

AI-v1.2 remains historical evidence and must not be retried, rewritten,
truncated or backfilled.

Predecessor activation anchor:

`research/forward/AI-v1.2-expansion-activation-2026-10-06T200633Z.json`

Predecessor P2 failure evidence:

`research/forward/AI-v1.2-P2-fail-closed-2026-10-06T220043Z.json`

The AI-v1.2.1 activation payload and aggregate anchor must bind both predecessor
files by SHA-256.

No AI-v1.2 evidence count or calendar time carries forward.

## 3. Frozen correction

The only decision-path plumbing correction is:

failed predecessor lookup:

`activation_payload["guardrails_sha256"]`

successor lookup:

`activation_payload["expansion_guardrails_sha256"]`

The resulting frozen hash continues to be written into the existing generic
inference-record field:

`guardrails_sha256`

No model, provider parameters, policy, feature formula, decision schema,
numerical guardrail, lifecycle rule, cost rule, synchronization rule, cadence
or market-set semantic changes.

## 4. Preactivation prerequisites

Before package publication:

1. exact successor source/config package is committed on a branch;
2. full AI-v1 regression family passes;
3. focused successor correction tests pass;
4. static AI-v1.2.1 preactivation verification passes;
5. read-only live readiness passes for all three markets;
6. failed AI-v1.2 ledger hashes remain equal to frozen P2 evidence;
7. AI-v1.1 remains healthy;
8. AI-v1.2.1 ledgers/anchor/task remain absent;
9. package activation preview is side-effect free;
10. activation executor contains no provider/MT5/scheduler path;
11. future activation anchors are protected with Git `-text` on Windows.

## 5. Approval boundaries

### P0 — package publication

Explicit token:

`AI_V1_2_1_PACKAGE_PUBLISH`

Authorizes only publication of the exact tested package commit to production
main/VPS.

It does not authorize activation or inference.

### P1 — activation-only

Explicit token:

`ACTIVATE-AI-V1.2.1-LEDGERS`

Authorizes exactly:

- one new ACTIVATION record in each fresh AI-v1.2.1 ledger;
- one aggregate AI-v1.2.1 activation anchor;
- publication of only that generated anchor;
- activation-only verification.

It does not authorize MT5 reads, provider inference, scheduler installation,
public exposure or broker execution.

### P2 — first performance-bearing cycle

Explicit token:

`AI_V1_2_1_SHADOW_START`

May be requested only after P1 is fully PASS and the activation anchor matches
upstream raw bytes.

Authorizes one controlled fresh-H1 manual shadow cycle only.

No automatic retry is permitted after the cycle starts.

### P3 — scheduler installation

Explicit token:

`AI_V1_2_1_SCHEDULER_INSTALL`

May be requested only after P2 PASS.

Authorizes installation/enabling of the hourly AI-v1.2.1 shadow task only.

It does not authorize public exposure or broker execution.

## 6. Activation-only transaction

Activation must fail closed if any AI-v1.2.1 ledger, activation anchor or
scheduler already exists.

The activation executor must:

1. verify exact committed production package;
2. verify successor preactivation PASS;
3. verify parallel AI-v1.1 healthy;
4. create three temporary one-record activation ledgers;
5. verify each temporary ledger;
6. construct and validate one aggregate anchor;
7. atomically move the three ledgers and anchor into final locations;
8. make no provider call;
9. make no MT5 call;
10. install no scheduler;
11. perform no backfill.

New ledgers:

- `data/ai_v1_2_1_eurusd.sqlite`
- `data/ai_v1_2_1_xagusd.sqlite`
- `data/ai_v1_2_1_usoil.sqlite`

Entity IDs:

`AI-v1.2.1:<MARKET>:ACTIVATION`

## 7. Anchor publication and raw-byte verification

After activation, only the generated activation anchor may be staged and
published.

The anchor filename pattern is:

`research/forward/AI-v1.2.1-expansion-activation-*.json`

The repository must enforce:

`research/forward/AI-v1.2.1-expansion-activation-*.json -text`

Activation-only verification must compare local raw anchor bytes to upstream
Git blob bytes and require equality before P1 can close.

## 8. Evidence clock

AI-v1.2.1 X1/X2/X3 counts and calendar start at the new AI-v1.2.1 activation
timestamp.

Thresholds remain:

- X1: >=100 valid inferences and >=20 completed shadow trades;
- X2: >=500 valid inferences, >=50 completed shadow trades and >=60 calendar
  days;
- X3: >=1,000 valid inferences, >=100 completed shadow trades and >=120
  calendar days.

Per-market decomposition remains mandatory.

## 9. Forbidden actions

This plan never authorizes:

- rerunning AI-v1.2;
- rewriting predecessor evidence;
- pooling predecessor counts/calendar;
- backfill;
- dropping a weak market after activation;
- public expansion exposure;
- broker execution;
- live-money trading.
