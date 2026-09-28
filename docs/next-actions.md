# Current Next Actions

_Last updated: 2026-09-28_

## Public beta launch state

The TradingTop public beta is live and has passed end-to-end browser + publisher smoke.

Public URL:

`https://tradingtop-early-access-production.up.railway.app`

Verified:

- no username/password prompt
- Railway deployment healthy
- 3/3 live collectors active in UI
- XAU/USD, USTEC and US30 live-signal cards visible
- XAU historical evidence visible
- USTEC/US30 transfer-support evidence visible
- two immutable completed XAU forward records visible
- six research/monitoring markets visible with explicit labels
- research-beta disclaimer visible
- snapshot publish returns 200
- product-publish wrapper: `export_exit=0 alert_exit=0 push_exit=0`
- `raw_market_data_included=false`

Telegram remains optional and disabled.

## Immediate product work — AI-v1 implementation

The owner has formally approved the AI-first pivot. Feedback/onboarding work is no longer the primary engineering task.

AI-0 and AI-1 are now complete at the governance/specification level.

Next implementation order:

1. implement the frozen deterministic AI feature snapshot builder;
2. implement the provider-neutral reasoning-model adapter;
3. select and freeze the exact provider/model ID, inference parameters and prompt/policy **before first performance-bearing inference**;
4. implement JSON-schema validation and the frozen deterministic publication guard;
5. implement a separate append-only AI-v1 inference/lifecycle ledger;
6. implement the frozen next-H1-open / TP1 / TP2 / stop / timeout evaluator;
7. add activation fingerprinting and tests proving S02 databases are untouched;
8. activate the shadow scheduler only after the activation checklist passes;
9. build the AI Insights UI against the shadow ledger after the pipeline is operational.

Current public S02 signals remain rule-based and must not be relabeled as AI.

## Forward validation

XAU F1 progress remains `2/20` completed trades.

Do not tune or change S02 based on the first two forward losses.

USTEC and US30 remain secondary forward collectors.

## Persistence caveat

There is still no persistent Railway volume.

A Railway restart/redeploy can temporarily clear the cloud snapshot until the hourly Windows publisher republishes it.

The tested product-publish task now successfully restores/publishes the snapshot.

## TradingTop/Elirox audit checkpoint — 2026-09-27 UTC

See `docs/tradingtop-elirox-public-audit-2026-09-27.md` for source links, observed public flows and product implications. Authenticated TradingTop views and prices remain unverified because Google's OAuth destination returned a 502 connection error in this Work browser session.

Before external invitations:

1. Choose a distinct public product name; the current page uses the same name as the comparison service.
2. Choose a durable, owner-accessible feedback destination and retention policy. The current Railway filesystem is ephemeral; do not acknowledge feedback into it as durable.
3. Implement a small feedback form and verify persistence across a redeploy. Ask about comprehension, missing signal details, alert preference and willingness to pay; do not collect broker credentials.
4. Select the first cohort and prepare the onboarding message; send no invitations until the preceding steps are complete.

This audit did not recheck the hosted beta. The prior launch verification above is the repository's recorded checkpoint.

## Authenticated competitor research — 2026-09-27 UTC

User-authorized email/password sign-in later succeeded. The earlier Google OAuth failure and “authenticated pages unverified” statement above are historical to the first attempt. Signed-in TradingTop screenshots and hashes are archived in `research/competitors/tradingtop/2026-09-27/README.md`. Pricing, signal card, AI log and T1/T2/T3 model pages were observed. T2's displayed three-month gold result is negative; do not use the aggregate AI log headline as a proxy for T2 model performance.

Keep the product priorities above. Add explicit signal issuance/expiry semantics and per-strategy outcome scope to the first-user comprehension check. No trading or broker connection was performed during this research.


## Authenticated TradingTop teardown — product-direction checkpoint 2026-09-28

See `docs/tradingtop-authenticated-teardown-and-product-gap-2026-09-28.md`.

The authenticated research changes the priority order if the intended destination remains a TradingTop-like AI intelligence product.

Approved immediate order:

1. **DONE:** working product name = SignalProof AI;
2. **DONE:** AI-v1 structured signal contract + evaluation protocol frozen;
3. **NEXT:** build AI-v1 as a shadow engine beside S02 on XAUUSD/USTEC/US30;
4. add deterministic publish guards and immutable AI inference logging;
5. add an AI Insights signal/reasoning/log UI;
6. only then prioritize accounts, compute credits, paid plans and user feedback;
7. referrals after paid conversion evidence;
8. broker-connected auto trading last.

Do not modify or stop the active S02 forward ledgers. They become the benchmark/control for AI-v1.


## AI-0 / AI-1 frozen references

- `docs/ai-0-product-naming.md`
- `docs/ai-v1-architecture.md`
- `docs/ai-v1-feature-definitions.md`
- `config/ai_v1_feature_schema.json`
- `config/ai_v1_policy.txt`
- `config/ai_v1_decision_schema.json`
- `config/ai_v1_guardrails.json`
- `docs/ai-v1-ledger-spec.md`
- `config/ai_v1_activation_schema.json`
- `research/experiments/EXP-2026-014-ai-v1-shadow-preregistration.md`

Do not start AI-v1 performance collection until the exact model/provider/prompt fingerprint is committed and an activation record is created.


## Immediate verification — AI-v1 foundation

On the Windows VPS, pull the latest repository and run:

```powershell
git pull

.\.venv\Scripts\python.exe scripts\smoke_ai_v1_foundation.py
```

Expected key output:

```text
"ai_v1_foundation_smoke": "PASS"
"provider_call_made": false
"ledger_verified": true
"s02_database_hashes_unchanged": true
"broker_execution_enabled": false
```

Then, if pytest is available:

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests\test_ai_v1_features.py tests\test_ai_v1_contract_ledger.py tests\test_ai_v1_inference.py tests\test_ai_v1_engine.py tests\test_ai_v1_signals.py
```

Optional read-only live feature probe:

```powershell
.\.venv\Scripts\python.exe scripts\build_ai_v1_feature_snapshot.py --symbol XAUUSD
```

This probe makes no AI call and no trade/broker mutation.

After these pass, the next blocked step is to select and freeze the exact AI provider/model + provider-specific inference parameters, then implement that concrete adapter and create the activation bundle.


## AI-v1 foundation verification — COMPLETE

The Windows VPS foundation smoke passed and the focused AI-v1 test suite reported:

`12 passed in 6.41s`

S02 database hashes remained unchanged and no provider call or broker execution occurred.

The next activation-critical milestone is now:

1. choose the exact AI inference provider/model;
2. freeze provider-specific inference parameters;
3. implement the concrete provider adapter;
4. fingerprint policy/provider/implementation artifacts;
5. build and validate the activation bundle;
6. install the shadow scheduler only after activation checks pass.

Under the project's strict context-isolation rule, provider selection should not silently use outside provider documentation unless the owner explicitly authorizes fresh provider research or names the provider/model to use.
