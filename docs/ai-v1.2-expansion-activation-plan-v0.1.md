# AI-v1.2 parallel expansion activation plan v0.1

_Status: PRE-ACTIVATION PACKAGE / NOT AUTHORIZED TO ACTIVATE — 2026-10-06_

## Objective

Activate a separately versioned shadow-only expansion lineage for:

- EURUSD
- XAGUSD
- USOIL

while active AI-v1.1 continues unchanged on:

- XAUUSD
- USTEC
- US30.

The two lineages must remain evidence-isolated.

## Frozen identities

Expansion runtime/evidence version:

`AI-v1.2`

Decision protocol:

`AI-v1.0`

Parallel active runtime:

`AI-v1.1`

AI-v1.2 does not supersede AI-v1.1.

## Frozen review gates

AI-v1.2 uses its own names:

- X1: >=100 valid inferences and >=20 completed shadow trades; operational
  audit only.
- X2: >=500 valid inferences, >=50 completed shadow trades and >=60 calendar
  days from AI-v1.2 activation; interim economic review.
- X3: >=1,000 valid inferences, >=100 completed shadow trades and >=120
  calendar days from AI-v1.2 activation; first expansion
  publishability/graduation decision.

All gate reports must show EURUSD, XAGUSD and USOIL separately. Gate results do
not authorize broker execution.

## Model / policy / feature boundary

Reused exactly:

- provider/model configuration;
- AI-v1.0 policy;
- AI-v1.0 structured output contract;
- feature formulas;
- feature builder;
- provider-neutral inference adapter;
- lifecycle evaluator;
- numerical guard thresholds;
- cost-policy semantics;
- rates synchronization logic.

Version-isolated profiles:

- expansion source-symbol feature-schema allowlist;
- expansion guardrail market metadata;
- X1/X2/X3 review-gate configuration.

No active AI-v1.1 or frozen AI-v1.0 artifact is edited for the expansion.

## Evidence isolation

AI-v1.2 paths:

- `data/ai_v1_2_eurusd.sqlite`
- `data/ai_v1_2_xagusd.sqlite`
- `data/ai_v1_2_usoil.sqlite`

Entity IDs begin with `AI-v1.2:`.

No AI-v1.1 counts or records carry forward.
No historical AI-v1.2 inference is backfilled.

## Public boundary

AI-v1.2 is private shadow research at activation.

`public_exposure_enabled = false`

The public VowSig surface remains an independent later governance decision.

## Broker boundary

`broker_execution_enabled = false`

No order path is added.

## Scheduler design

Existing AI-v1.1 task remains unchanged:

`SignalProof AI-v1.1 Shadow Scan`

AI-v1.2 uses a separate task:

`VowSig AI-v1.2 Expansion Shadow Scan`

Frozen target start minute:

`:03` each hour.

The one-minute offset from the existing near-:02 AI-v1.1 task reduces exact
simultaneous starts while remaining inside the frozen <=300-second freshness
boundary. The rates synchronizer still fails closed if current H1/H4 state is
not available.

The two scheduled tasks remain independently observable and independently
disableable.

## Activation sequence

### Gate P0 — package verification

Before any activation:

1. exact package commit is reconciled;
2. focused tests pass;
3. static compatibility/preactivation checks pass;
4. live MT5 readiness PASS for all three expansion markets remains the admitted
   readiness evidence;
5. AI-v1.1 runtime verifies healthy;
6. activation preview is generated;
7. exact package commit and artifact hashes are presented for owner review.

No live expansion state exists at P0.

### Approval A — activation-only ledgers

Requires separate explicit owner approval.

Authorized command token:

`ACTIVATE-AI-V1.2-LEDGERS`

The activation script may then create exactly:

- three one-record ACTIVATION ledgers;
- one aggregate AI-v1.2 expansion activation anchor.

It may not:

- call MT5;
- call OpenAI;
- create performance-bearing records;
- install a scheduler;
- expose public signals;
- backfill;
- enable broker execution.

### Gate P1 — commit activation anchor

After activation-only creation:

1. verify the three ledgers contain exactly one ACTIVATION each;
2. commit/push **only** the generated activation anchor;
3. do not commit SQLite ledgers;
4. verify the committed anchor upstream;
5. verify AI-v1.2 activation-only runtime;
6. verify AI-v1.1 remains healthy.

### Approval B — performance-bearing shadow start

A second explicit owner approval is required before:

- the first AI-v1.2 OpenAI inference;
- manual AI-v1.2 live scan;
- installation/enabling of the AI-v1.2 hourly task.

This keeps ledger activation separate from performance-bearing provider calls.

### Gate P2 — first live shadow cycle

After Approval B:

1. run one controlled fresh-H1 AI-v1.2 cycle;
2. verify only AI-v1.2 ledgers changed;
3. verify AI-v1.1 ledgers were not changed by the AI-v1.2 process;
4. verify no broker execution/public exposure;
5. verify runtime and ledger integrity.

Only after P2 PASS may the separate hourly AI-v1.2 scheduler be installed.

## Rollback / stop behavior

Before any performance-bearing AI-v1.2 inference:

- an activation-only AI-v1.2 campaign may be abandoned by leaving its evidence
  preserved and not installing the scheduler;
- do not rewrite/delete activation evidence to pretend activation did not occur.

After performance-bearing inference starts:

- do not delete/rewrite expansion ledgers;
- do not drop a weak market;
- stop/disable the AI-v1.2 task if a decision-affecting defect is found;
- preserve all prior evidence;
- any decision-affecting correction becomes a new version/activation.

AI-v1.1 continues independently unless a separate AI-v1.1 governance decision
says otherwise.

## Current authority

Current authority covers package implementation, tests and read-only
verification only.

It does **not** authorize Approval A or Approval B.
