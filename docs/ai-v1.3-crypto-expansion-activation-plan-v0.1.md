# AI-v1.3 crypto expansion activation plan v0.1

_Status: DESIGN ONLY / NO AUTHORITY TO ACTIVATE — 2026-10-08_

Tracker: Issue #40

Preregistration:

`research/experiments/EXP-2026-017-ai-v1.3-crypto-expansion-preregistration.md`

Compatibility plan:

`docs/ai-v1.3-crypto-expansion-compatibility-v0.1.md`

## 1. Scope

Prospective parallel crypto shadow lineage:

- BTCUSDT
- ETHUSDT
- SOLUSDT

Working runtime/evidence version:

`AI-v1.3`

Decision protocol intent:

`AI-v1.0`

Program ID:

`crypto-expansion-1`

Primary source:

`binance_spot`

Broker execution:

`false`

Initial public actionable signal exposure:

`false`

## 2. Independence from active lineages

AI-v1.1 and AI-v1.2.1 continue unchanged.

No crypto activation step may:

- write an AI-v1.1 ledger;
- write an AI-v1.2/AI-v1.2.1 ledger;
- write an S02 ledger;
- reset another lineage's gate/calendar;
- merge another lineage's evidence into C1/C2/C3;
- alter existing scheduler definitions as a side effect.

The crypto calendar starts only at the future crypto activation timestamp.

## 3. Planned immutable ledgers

Fresh paths only:

- `data/ai_v1_3_btcusdt.sqlite`
- `data/ai_v1_3_ethusdt.sqlite`
- `data/ai_v1_3_solusdt.sqlite`

Entity IDs:

`AI-v1.3:<SOURCE_SYMBOL>:<SOURCE_BAR_CLOSE_UTC>`

Activation entity IDs:

`AI-v1.3:<SOURCE_SYMBOL>:ACTIVATION`

No existing ledger may be copied/renamed into these paths.

## 4. Planned activation anchor

Working filename pattern:

`research/forward/AI-v1.3-crypto-expansion-activation-<UTC>.json`

The future activation anchor must bind at least:

- exact repository commit SHA;
- runtime/evidence version;
- decision protocol version;
- program ID;
- activation timestamp;
- exact market set/order;
- exact primary source;
- exact Binance connector/source artifact hashes;
- exact crypto feature-schema hash;
- exact feature-builder hash;
- exact top-of-book adapter hash;
- exact cost-policy hash;
- exact guardrail hash;
- exact policy hash;
- exact canonical decision-schema hash;
- exact provider response-schema hash;
- exact provider/model ID and parameter fingerprint;
- exact runtime source hash;
- exact ledger source hash;
- exact lifecycle source hash;
- review-gates hash;
- preregistration hash;
- compatibility-plan hash;
- readiness-evidence hash;
- three activation record/head hashes;
- no_backfill=true;
- public_signal_exposure_enabled=false;
- broker_execution_enabled=false.

The anchor itself must be committed and verified upstream before the first
performance-bearing provider call.

## 5. Hard preactivation blockers

Do not prepare an activation payload that reports READY until all are true:

1. ETHUSDT/SOLUSDT Binance canonical mappings are committed;
2. crypto feature semantics are frozen;
3. Binance top-of-book adapter is implemented/tested;
4. numeric fee/slippage/all-in cost policy is frozen;
5. cost guard/lifecycle allocation is implemented/tested;
6. static preactivation verification passes;
7. full regression passes;
8. owner-approved live read-only readiness passes for BTC/ETH/SOL;
9. no planned crypto ledger exists before activation;
10. no crypto activation anchor exists;
11. active AI-v1.1 and AI-v1.2.1 runtime verification passes;
12. existing active ledger bytes remain unchanged during readiness;
13. broker execution is disabled;
14. public crypto signal exposure is disabled.

## 6. Approval sequence

The following boundaries are deliberately separate.

### K0 — design package

Current authorization.

Allowed:

- docs;
- config;
- registry preparation;
- tests;
- issue/PR work.

Not allowed:

- live Binance calls;
- OpenAI calls;
- ledger creation;
- activation;
- scheduler changes.

### K1 — live read-only readiness

Future explicit token:

`AI_V1_3_CRYPTO_READINESS`

May authorize only:

- public Binance H1/H4 reads;
- public Binance top-of-book reads;
- comparison-only diagnostics explicitly included in the readiness command;
- read-only inspection/hash of existing ledgers.

Must produce no crypto ledger, provider inference, scheduler mutation or broker
action.

### K2 — package publication

Future explicit token:

`AI_V1_3_CRYPTO_PACKAGE_PUBLISH`

May publish the exact tested implementation package to production Git/VPS code.

Still must not create ledgers, call OpenAI or install/enable the task.

### K3 — activation-only

Future explicit token:

`ACTIVATE-AI-V1.3-CRYPTO-LEDGERS`

May do exactly:

- create three new append-only crypto databases;
- append exactly one ACTIVATION record to each;
- generate one aggregate activation anchor;
- run activation-only verification;
- commit/publish only the generated activation anchor as separately reviewed.

Must not:

- read Binance for performance;
- call OpenAI;
- create INFERENCE/SIGNAL records;
- install scheduler;
- expose public crypto signals.

### K4 — first performance-bearing cycle

Future explicit token:

`RUN-AI-V1.3-CRYPTO-FIRST-CYCLE`

May execute exactly one live crypto H1 decision batch on all three markets.

Required after-run reconciliation:

- exact provider call count;
- exact market statuses;
- ledger integrity/head for all three;
- provider/model identity;
- usage/cost metadata;
- no write to other ledgers;
- no public crypto signal exposure;
- broker disabled.

Do not retry/backfill a failed/missed first-cycle opportunity unless a separately
registered successor protocol authorizes a future natural opportunity.

### K5 — unattended shadow scheduler

Future explicit token:

`INSTALL-AI-V1.3-CRYPTO-SHADOW-TASK`

May install/enable one dedicated crypto shadow task only after K4 PASS.

Working cadence:

- hourly;
- UTC near minute 04;
- IgnoreNew / no overlapping instances;
- bounded execution timeout;
- broker disabled.

The exact task name/runner/definition must be frozen in the implementation
package and shown to the owner before K5.

### K6 — public research observability

Separate future decision.

May eventually expose only separately approved crypto program health/evidence.

Does not imply actionable signal exposure.

### K7 — actionable public crypto signals

Not pre-authorized by this plan.

Requires a later evidence/product decision after the preregistered review
program.

### K8 — broker execution

Not authorized by this research plan.

Any future broker/exchange execution requires a separate project/governance
decision and must not be inferred from C1/C2/C3.

## 7. Scheduler collision rule

Active schedules currently occupy approximately:

- AI-v1.1: :02;
- AI-v1.2.1: :03;
- product publish: :05.

Working crypto target is :04.

Before K5, readiness must prove that:

- all three crypto snapshots can be frozen within the <=300 second data-age
  boundary;
- the task does not require changing active AI task definitions;
- product publication overlap is safe because initial crypto public exposure is
  disabled;
- multiple instances are blocked.

If these conditions do not hold, revise the preactivation scheduler design
before performance activation rather than after observing results.

## 8. First-cycle fail-closed behavior

The first live batch must fail closed for each affected market on:

- missing/incomplete latest H1/H4;
- stale data;
- missing top-of-book;
- invalid bid/ask ordering;
- missing/unfrozen cost policy;
- schema mismatch;
- provider failure;
- provider refusal;
- invalid structured output;
- ledger integrity failure;
- active-signal concurrency violation.

A failure may create only the predeclared immutable error/missed record appropriate
to the final implementation.

No synthetic successful inference may be inserted later for that missed cycle.

## 9. Post-activation review gates

Use:

`config/ai_v1_3_crypto_review_gates.json`

- C1: >=100 valid inferences and >=20 completed shadow trades; operational only.
- C2: >=500 valid inferences, >=50 completed trades, >=60 calendar days.
- C3: >=1,000 valid inferences, >=100 completed trades, >=120 calendar days.

Per-market and weekday/weekend reporting are mandatory.

## 10. Rollback / recovery principles

Before performance evidence:

- an objectively defective unactivated package may be corrected prospectively.

After activation:

- do not delete/truncate/rewrite ledgers;
- do not reset the activation clock;
- do not backfill missed opportunities;
- preserve failed runtime evidence;
- a decision-affecting defect requires a separately versioned successor lineage;
- scheduler disablement for safety is allowed only under an explicitly reviewed
  operational response, without rewriting evidence.

No automatic destructive database restore is authorized.

## 11. Current state

This document defines future commands/tokens only.

No K1/K2/K3/K4/K5/K6/K7/K8 authority has been granted.

Current owner authorization stops at K0 design/preregistration work.
