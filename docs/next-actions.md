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

## Immediate product work — Early Access feedback & customer discovery v0.1

AI-v1.0 is now activated and the hourly shadow scheduler is collecting immutable forward evidence on XAUUSD, USTEC and US30.

The activated decision system is frozen. Do not tune or change the model, prompt, features, guardrails, market universe, lifecycle, cost policy or decision cadence based on early results.

The active plan is documented in:

`docs/ai-v1-observability-plan.md`

Current work order:

1. **RUNNING:** leave AI-v1.0 shadow collection untouched;
2. **DONE / VPS VERIFIED:** read-only `scripts/report_ai_v1_progress.py` observability layer;
3. **DONE / VPS VERIFIED:** mutation-safety/tamper/gate tests and byte-identical live-ledger proof;
4. **DONE / CLOUD VERIFIED:** AI Insights UI backed by the sanitized read-only AI-v1 export; canonical record: `docs/ai-insights-ui.md`;
5. **DONE / REDEPLOY VERIFIED:** Cloud Snapshot Durability v0.1 — persistent `/data` volume proven across controlled redeploy; canonical record: `docs/cloud-snapshot-durability-v0.1.md`, GitHub Issue #6;
6. **IN PROGRESS:** Early Access Feedback & Customer Discovery v0.1 — storage/API/UI + tests committed; **NEXT:** VPS tests, dedicated Railway owner secret, synthetic submission and controlled-redeploy persistence proof; GitHub Issue #7;
7. perform A1 only when the frozen >=100 valid-inference AND >=20 completed-trade thresholds are naturally reached.

A2 remains subject to >=500 valid inferences, >=50 completed trades and >=60 calendar days. A3 remains subject to >=1,000 valid inferences, >=100 completed trades and >=120 calendar days.

### Deferred growth backlog — Organic acquisition & SEO v0.1

**DEFERRED / AFTER ISSUE #7.** This does not change the current implementation priority.

Canonical plan: `docs/future-organic-acquisition-seo-v0.1.md`  
GitHub Issue: #8

Preserved future ideas include evidence-first per-market landing pages, educational search content, search -> education -> product funnels, intentional internal linking, privacy-respecting acquisition measurement, and free-value-first conversion. The first implementation batch must be revised using actual customer-language/comprehension findings from Issue #7 before SEO work starts.

Current public S02 signals remain rule-based and must not be relabeled as AI.

## Forward validation

XAU F1 progress remains `2/20` completed trades.

Do not tune or change S02 based on the first two forward losses.

USTEC and US30 remain secondary forward collectors.

## Persistence caveat

Railway now has a persistent 500 MB volume mounted at `/data` on the existing production service. A controlled redeploy completed without republishing, and the exact sanitized snapshot identity remained available afterward. Durability v0.1 is complete.

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


## Immediate next checkpoint — provider adapter verification

The exact provider/model is now frozen to OpenAI `gpt-5.4-2026-03-05`.

On the Windows VPS:

1. pull latest code;
2. run the expanded offline AI-v1 tests;
3. run activation preview (no provider call);
4. configure `OPENAI_API_KEY` locally;
5. run exactly one **synthetic, non-performance** provider smoke;
6. do not activate the three AI ledgers until the provider smoke result is reviewed and the activation preview is clean.

Commands:

```powershell
git pull
.\.venv\Scripts\python.exe -m pytest -q tests\test_ai_v1_features.py tests\test_ai_v1_contract_ledger.py tests\test_ai_v1_inference.py tests\test_ai_v1_engine.py tests\test_ai_v1_signals.py tests\test_ai_v1_openai_responses.py tests\test_ai_v1_activation.py
.\.venv\Scripts\python.exe scripts\prepare_ai_v1_activation.py
```

The preview must report:

- `mode=PREVIEW_ONLY`;
- `provider_call_made=false`;
- `ai_ledgers_created=false`;
- `broker_execution_enabled=false`.

Configure the API key without pasting it into chat:

```powershell
.\.venv\Scripts\python.exe scripts\configure_openai_api_key.py
```

Then run the one synthetic provider smoke:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_ai_v1_openai_provider.py
```

That call uses an explicitly synthetic flat market-state fixture, does not write a performance ledger, and must not be used to tune the frozen protocol.

Do **not** run `scripts\activate_ai_v1.py` yet. Activation will occur only after review of these outputs, followed by GitHub anchoring before the shadow scheduler is installed.


## Provider adapter verification + activation preview — COMPLETE

The VPS expanded offline suite passed:

`20 passed in 4.46s`

The activation preview also passed with no provider call, no AI-ledger creation and broker execution disabled.

Next:

```powershell
.\.venv\Scripts\python.exe scripts\configure_openai_api_key.py
.\.venv\Scripts\python.exe scripts\smoke_ai_v1_openai_provider.py
```

Do not paste the API key into chat or commit it.

Do not run `scripts\activate_ai_v1.py` until the synthetic provider-smoke output has been reviewed.


## OpenAI project model-access diagnostic — REQUIRED

The synthetic provider smoke failed before inference because the API project does not have access to the frozen `gpt-5.4-2026-03-05` snapshot.

Pull the diagnostic commit and run:

```powershell
git pull
.\.venv\Scripts\python.exe scripts\probe_openai_model_access.py
```

This command:

- makes only OpenAI model-metadata GET requests;
- makes no Responses/inference call;
- writes no AI ledger;
- does not modify the frozen provider configuration;
- does not touch broker execution.

Send the JSON output for review.

Do not rerun the provider smoke and do not run `scripts\activate_ai_v1.py` until model access is resolved.

If the frozen GPT-5.4 snapshot is accessible after changing OpenAI project Model Usage/billing permissions, keep the current preregistration unchanged. If it remains unavailable but another dated snapshot is accessible, a new **pre-activation superseding provider decision** must be committed before any inference with that fallback.


## Retry provider verification after credential-precedence fix

The wrong-project Windows environment key no longer takes precedence over the repository `.env`.

Run:

```powershell
git pull

.\.venv\Scripts\python.exe -m pytest -q tests\test_ai_v1_local_env.py tests\test_ai_v1_openai_responses.py tests\test_ai_v1_activation.py

.\.venv\Scripts\python.exe scripts\probe_openai_model_access.py
```

If the probe shows `gpt-5.4-2026-03-05` accessible under the correct project, rerun exactly one synthetic provider smoke:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_ai_v1_openai_provider.py
```

Do not run `scripts\activate_ai_v1.py` until the corrected-project provider smoke has been reviewed.


## Next checkpoint — activate and anchor AI-v1 shadow ledgers

Correct-project model access and the synthetic provider smoke are now verified.

The next allowed action is **ledger-only activation**. This creates exactly three new AI-v1 append-only SQLite ledgers and one local activation-anchor JSON. It makes **no OpenAI inference call**, enables no broker execution, and installs no scheduler.

Run on the VPS:

```powershell
git pull

.\.venv\Scripts\python.exe scripts\activate_ai_v1.py --confirm ACTIVATE-SHADOW-LEDGERS
```

Expected summary must include:

- `activation = PASS`;
- `provider_call_made = false`;
- `broker_execution_enabled = false`;
- `scheduler_installed = false`;
- one generated `research/forward/AI-v1-activation-*.json`;
- three AI ledger head hashes.

After the script passes, **do not run any AI shadow scheduler yet**.

Commit only the generated activation anchor:

```powershell
git status --short
git add research/forward/AI-v1-activation-*.json
git commit -m "Anchor AI-v1 shadow activation"
git push
```

Then provide the activation output / commit SHA for review. The scheduler is authorized only after the committed anchor is verified against the three local ledger heads.


## Immediate checkpoint — preserve/supersede first activation before runtime-bound replacement

The first activation/anchor is valid as a ledger-only pre-performance artifact, but the final unattended shadow runtime was not part of its activated repository tree.

**Do not install or run the AI shadow scheduler against that first activation.**

Pull the final runtime implementation and run the expanded offline suite:

```powershell
git pull

.\.venv\Scripts\python.exe -m pytest -q tests\test_ai_v1_features.py tests\test_ai_v1_contract_ledger.py tests\test_ai_v1_inference.py tests\test_ai_v1_engine.py tests\test_ai_v1_signals.py tests\test_ai_v1_openai_responses.py tests\test_ai_v1_activation.py tests\test_ai_v1_local_env.py tests\test_ai_v1_shadow_runtime.py
```

If the tests pass, supersede/archive the current activation-only ledgers:

```powershell
.\.venv\Scripts\python.exe scripts\supersede_ai_v1_activation.py --confirm SUPERSEDE-PREPERFORMANCE-ACTIVATION
```

This command is required to fail closed if any AI ledger contains anything beyond its single ACTIVATION record. It does not call OpenAI and does not delete the old ledgers; it moves them under `data\ai-v1-superseded\...` and writes a GitHub-trackable supersession anchor.

Then commit/push only the supersession anchor:

```powershell
git status --short

git add research/forward/*SUPERSEDED.json
git commit -m "Preserve superseded pre-performance AI-v1 activation"
git push
```

Stop there and provide:

- pytest result;
- supersession output;
- resulting Git commit SHA.

After that checkpoint is verified, create the replacement activation from the final runtime-bound repository commit. Do not install the scheduler until the replacement activation anchor is also committed and verified upstream.
