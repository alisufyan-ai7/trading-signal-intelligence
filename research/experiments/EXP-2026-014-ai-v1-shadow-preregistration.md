# EXP-2026-014 — AI-v1 shadow inference preregistration

_Status: PREREGISTERED / PRE-ACTIVATION — 2026-09-28_

## Research question

Can a structured AI reasoning model, operating only on causally available engineered market-state features, generate economically useful BUY/SELL/NO_TRADE decisions after realistic costs, while outperforming or complementing the unchanged deterministic S02 control on the same forward calendar?

## Pre-registration timing

This document, `docs/ai-v1-architecture.md`, `config/ai_v1_decision_schema.json` and `config/ai_v1_guardrails.json` are committed **before the first AI-v1 performance-bearing shadow inference is activated**.

No AI-v1 result has been observed at the time of this preregistration.

## Frozen universe

- XAUUSD
- USTEC
- US30

## Frozen cadence

Evaluate each newly completed H1 bar that has a valid fresh feature snapshot.

## Frozen data boundary

Use only completed candles and derived market features available at inference time.

No news, sentiment, S02 signal state, user position data, future bars or incomplete bars enter AI-v1.0.

## Frozen decision space

The AI may output:

- BUY
- SELL
- NO_TRADE

The exact schema is `config/ai_v1_decision_schema.json`.

## Frozen execution evaluation

Published shadow proposals use:

- next eligible H1 open entry;
- AI-selected stop ATR multiple within 1.00–3.00;
- AI-selected TP1 within 0.75–2.00R;
- AI-selected TP2 within 1.50–4.00R with TP2 > TP1;
- 50% evaluated at TP1;
- 50% evaluated at TP2;
- no stop move after TP1;
- 24-H1-bar maximum hold;
- existing instrument-specific cost framework;
- deterministic conservative handling for ambiguous intrabar exit order.

## Frozen publication boundary

The deterministic guard in `config/ai_v1_guardrails.json` may reject an AI proposal but may not reverse its direction or optimize its parameters.

## Control

S02-v0.1 remains unchanged and continues in its existing forward ledgers.

AI-v1 does not read S02 outputs.

Comparisons are performed only after AI-v1 data exists, on overlapping forward calendar windows where possible.

## Primary evaluation

Primary economic metric:

- net expectancy in R per completed AI shadow trade after costs.

Supporting:

- profit factor;
- maximum drawdown R;
- TP1/TP2/stop/timeout rates;
- trade count;
- average hold;
- performance by symbol;
- raw-confidence bucket diagnostics;
- operational reliability/cost.

Inference accuracy alone is not the primary success metric.

## Review gates

- A1: >=100 valid inferences and >=20 completed shadow trades — operational audit only.
- A2: >=500 valid inferences, >=50 completed shadow trades and >=60 calendar days — interim review.
- A3: >=1,000 valid inferences, >=100 completed shadow trades and >=120 calendar days — first planned publishability decision.

## Anti-overfitting / governance rules

Before activation, the exact provider/model ID, parameters and prompt/policy must be committed.

After activation:

- do not tune the prompt/model/guardrails in place based on results;
- do not delete losing signals;
- do not pool changed model versions;
- do not alter S02 to make the comparison easier;
- do not promote AI-v1 based on a short winning streak;
- any decision-affecting change becomes a new version and a new activation.

## Status

Implementation is authorized.

Activation is **not** authorized until the checklist in `docs/ai-v1-architecture.md` is satisfied and the exact model/prompt fingerprint is frozen.
