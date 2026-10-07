# AI-v1.2.1 Expansion Runtime Correction v0.1

_Status: PRE-ACTIVATION VERIFICATION PACKAGE — NOT ACTIVE — 2026-10-07_

## Purpose

Correct the AI-v1.2 first-cycle activation-metadata wiring defect
prospectively without rewriting, deleting or backfilling any AI-v1.2 evidence.

## Frozen predecessor

AI-v1.2 remains immutable.

Activation:

`2026-10-06T20:06:33.495178+00:00`

Activation anchor:

`research/forward/AI-v1.2-expansion-activation-2026-10-06T200633Z.json`

P2 failure evidence:

`research/forward/AI-v1.2-P2-fail-closed-2026-10-06T220043Z.json`

Observed predecessor state after P2:

- EURUSD: ACTIVATION only;
- XAGUSD: ACTIVATION + one `MISSED_INFERENCE/no_current_h1_tick`;
- USOIL: ACTIVATION only;
- valid inferences: 0;
- completed trades: 0;
- AI-v1.2 scheduler: absent.

Do not rerun AI-v1.2.

## Confirmed defect

The activation payload key is:

`expansion_guardrails_sha256`

The failed runtime attempted:

`activation_payload["guardrails_sha256"]`

This happens before the inference loop.

## Successor identity

Runtime/evidence lineage:

`AI-v1.2.1`

Decision protocol:

`AI-v1.0`

Markets:

- EURUSD
- XAGUSD
- USOIL

New prospective ledgers:

- `data/ai_v1_2_1_eurusd.sqlite`
- `data/ai_v1_2_1_xagusd.sqlite`
- `data/ai_v1_2_1_usoil.sqlite`

No predecessor counts/calendar/backfill carry forward.

## Exact intended runtime correction

The successor must read:

`activation_payload["expansion_guardrails_sha256"]`

and pass that exact hash into the existing inference engine parameter:

`guardrails_sha256`

which is recorded in the unchanged generic inference-record field of the same
name.

No model or decision behavior changes.

## Mechanical semantic-diff proof

The correction tests require:

1. AI-v1.2.1 engine source, after normalizing only versioned identifiers, equals
   the AI-v1.2 engine source byte-for-byte.
2. AI-v1.2.1 shadow runtime, after normalizing versioned identifiers and
   normalizing the single allowed guard-hash key correction back to the failed
   predecessor spelling, equals AI-v1.2 shadow runtime byte-for-byte.
3. the AI-v1.2.1 guard profile equals the AI-v1.2 guard profile after
   normalizing status only.
4. X1/X2/X3 thresholds and the three-market set remain identical.
5. a focused end-to-end unit test constructs an activation record containing
   only the correct `expansion_guardrails_sha256` key, reaches one fake
   NO_TRADE inference, and proves the resulting INFERENCE record carries the
   expected guard hash.

## Read-only VPS readiness checkpoint

Before activation-package construction, the owner-run checkpoint must prove:

- exact correction package commit;
- focused/regression tests PASS;
- static preactivation PASS;
- all three live markets READY inside the frozen freshness window;
- active AI-v1.1 ledger bytes unchanged;
- failed AI-v1.2 ledger bytes unchanged and exactly equal to frozen P2 evidence;
- AI-v1.2.1 ledgers absent before/after;
- no provider call;
- no ledger write;
- no scheduler change;
- no public exposure;
- no broker execution.

## Later boundaries

After readiness PASS, a separate activation package will be constructed and
tested.

Later still, separate approvals are required for:

1. package publication to main/VPS;
2. AI-v1.2.1 activation-only ledgers/anchor;
3. first performance-bearing AI-v1.2.1 shadow cycle;
4. scheduler installation only after first-cycle PASS.

No such authority is created by this document.
