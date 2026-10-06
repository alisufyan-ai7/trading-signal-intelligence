# AI-v1.2 market-expansion compatibility plan v0.1

_Status: PRE-ACTIVATION IMPLEMENTATION / LIVE READINESS PROOF PENDING — 2026-10-06_

## Objective

Prepare EURUSD, XAGUSD and USOIL for a separately versioned parallel shadow
lineage while leaving active AI-v1.1 completely unchanged.

Canonical preregistration:

`research/experiments/EXP-2026-015-ai-v1.2-market-expansion-preregistration.md`

## Compatibility finding

The frozen AI-v1.0 feature schema is not directly reusable as a validation
artifact because its `source_symbol` enum contains only:

- XAUUSD
- USTEC
- US30

The frozen guardrail artifact also records those three symbols as its historical
`shadow_markets` metadata.

This is not a performance finding. It was discovered before any AI-v1.2
performance-bearing inference.

## Resolution

Use:

- runtime/evidence version: `AI-v1.2`;
- decision protocol: `AI-v1.0`;
- expansion universe: EURUSD / XAGUSD / USOIL;
- a separate expansion feature-schema profile whose only semantic compatibility
  difference from the frozen base feature schema is the source-symbol allowlist;
- the exact existing AI-v1.0 feature formulas;
- exact existing AI-v1.0 policy;
- exact existing AI-v1.0 BUY / SELL / NO_TRADE decision contract;
- exact existing provider/model parameters;
- exact existing numerical guard semantics;
- exact existing lifecycle and cost semantics;
- exact existing AI-v1.1 rates-synchronization rule.

The expansion schema deliberately retains:

`feature_schema_version = AI-v1.0`

because the feature calculations and payload semantics are unchanged. The
separate AI-v1.2 runtime/evidence identity captures the changed market universe
and validation profile.

## Frozen first expansion mappings

| Source | Canonical | Class | Digits | Point size |
|---|---|---|---:|---:|
| EURUSD | EUR/USD | forex | 5 | 0.00001 |
| XAGUSD | XAG/USD | metal | 3 | 0.001 |
| USOIL | WTI | energy | 3 | 0.001 |

These must match `config/instruments.json`.

## Static preactivation proof

Command:

`python scripts/verify_ai_v1_2_expansion_pre_activation.py`

Required PASS conditions:

- exact expansion config parses and remains `pre_activation`;
- frozen AI-v1.0 decision artifacts still match their upstream activation
  lineage;
- expansion schema is equivalent to the frozen feature schema after normalizing
  only schema ID/title and source-symbol allowlist;
- feature schema version remains AI-v1.0;
- canonical mappings/digits/point sizes match the registry;
- no AI-v1.2 live ledger exists;
- no AI-v1.2 activation anchor exists;
- no provider call, MT5 call, ledger write, scheduler mutation, public exposure
  or broker execution occurs.

## Read-only live MT5 readiness proof

Command:

`python scripts/probe_ai_v1_2_market_readiness.py`

The live probe:

1. requires the static preactivation proof to PASS;
2. captures SHA-256 for all active AI-v1.1 ledgers;
3. refuses to proceed if any AI-v1.2 ledger already exists;
4. initializes MT5 for data reads only;
5. does not call `symbol_select`;
6. refuses/inconclusive if an expansion symbol is not already visible;
7. uses the frozen AI-v1.1 bounded synchronization helper;
8. requires a current-hour tick and synchronized current H1/H4 rows;
9. builds the unchanged AI-v1.0 feature formulas for the latest completed H1
   decision point;
10. verifies freshness and finite instrument-specific cost inputs;
11. makes no OpenAI/provider call;
12. creates no ledger;
13. changes no scheduler;
14. places no broker order;
15. re-hashes active AI-v1.1 ledgers and requires byte identity;
16. reconfirms no AI-v1.2 ledger appeared.

A session break or non-visible symbol is not evidence of model incompatibility.
It leaves readiness incomplete and requires a later read-only observation.

## What this phase does not authorize

No:

- AI-v1.2 activation;
- AI-v1.2 activation anchor;
- AI-v1.2 live ledger;
- scheduled AI-v1.2 task;
- performance-bearing provider inference;
- public expansion signal surface;
- modification of AI-v1.1;
- broker execution.

## Next decision boundary

After:

- focused regression tests PASS;
- static preactivation verification PASS;
- owner-run live MT5 readiness PASS for all three markets;
- active AI-v1.1 ledger byte identity is proven;

prepare the exact AI-v1.2 activation/ledger/task/observability implementation
and a separate owner-review activation package.

Formal AI-v1.2 review thresholds must be frozen before the first
performance-bearing AI-v1.2 inference.
