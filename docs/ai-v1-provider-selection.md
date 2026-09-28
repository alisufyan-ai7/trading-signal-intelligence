# AI-v1 provider/model selection — 2026-09-28

_Status: FROZEN PRE-ACTIVATION_

## Selection objective

Choose one exact, reproducible reasoning-model endpoint for the preregistered AI-v1 shadow experiment.

The selection is made **before any AI-v1 performance-bearing inference** and is based on operational criteria rather than observed trading results.

## Selection criteria

In priority order:

1. **Reproducibility across the A1/A2/A3 evidence window** — prefer an immutable/date-pinned model snapshot over a moving alias.
2. **Structured-output reliability** — the provider must support strict schema-constrained JSON suitable for the frozen BUY/SELL/NO_TRADE contract.
3. **Reasoning capability** — the model must be suitable for judgement over a compact engineered market-state snapshot.
4. **Stateless request control** — no conversation history, outside tools, web search or hidden external market context.
5. **Data/privacy controls** — derived market-state inputs only; no credentials or user/account data.
6. **Cost/throughput** — the first protocol runs each eligible H1 bar on three markets, so the model should be economically sustainable.
7. **Simple failure semantics** — refusals, incomplete output and provider errors must be recordable without silently fabricating a decision.

## Public provider research

Research date: 2026-09-28.

### OpenAI

Official GPT-5.4 model documentation states:

- Responses API supported;
- Structured Outputs supported;
- reasoning efforts include none/low/medium/high/xhigh;
- price displayed as $2.50 / 1M input tokens and $15 / 1M output tokens;
- the exact snapshot `gpt-5.4-2026-03-05` is available;
- OpenAI explicitly describes snapshots as locking a model version so behavior/performance remain consistent.

Official GPT-5.5 documentation also exposes an exact dated snapshot, `gpt-5.5-2026-04-23`, with Structured Outputs, but at approximately double GPT-5.4 token pricing ($5 input / $30 output per 1M).

Current GPT-6 models are newer and cheaper in some tiers, but the public material reviewed for this decision did not establish a date-pinned GPT-6 Sol snapshot suitable for a 120-day frozen research protocol.

OpenAI Structured Outputs documentation supports strict JSON-schema output but does not support JSON-Schema composition keywords including `allOf`, `if`, `then` and `else`. Therefore the canonical AI-v1 schema cannot be sent byte-for-byte to OpenAI; a separately frozen provider-compatible schema is required while local runtime validation remains authoritative.

Official OpenAI data-control documentation states that `/v1/responses` data is not used for training and documents endpoint retention controls. The AI-v1 request additionally freezes `store=false`.

Sources:

- https://developers.openai.com/api/docs/models/gpt-5.4
- https://developers.openai.com/api/docs/models/gpt-5.5
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://developers.openai.com/api/docs/guides/reasoning
- https://developers.openai.com/api/docs/guides/your-data
- https://developers.openai.com/api/reference/cli/resources/responses/methods/create

### Anthropic

Current Anthropic documentation lists Claude Sonnet 5 as active and describes it as a strong speed/intelligence balance. The current model lifecycle documentation reviewed here did not provide a date-pinned Sonnet 5 identifier analogous to OpenAI's dated GPT-5.4 snapshot.

That makes it less attractive for this particular preregistered experiment even though it is a viable product model in general.

Sources:

- https://docs.anthropic.com/en/docs/about-claude/model-deprecations
- https://docs.anthropic.com/en/docs/build-with-claude/prompt-engineering/prompt-templates-and-variables

### Google Gemini

Current Google documentation supports structured JSON output and offers lower-cost/high-throughput Gemini models. The reviewed current model catalog encourages newer Flash-family models for new projects. The public material reviewed for this decision did not establish a date-pinned immutable model identifier with the same explicit snapshot guarantee as GPT-5.4.

Sources:

- https://ai.google.dev/gemini-api/docs/models
- https://ai.google.dev/gemini-api/docs/pricing
- https://ai.google.dev/gemini-api/docs/generate-content/structured-output

## Frozen selection

**Provider:** OpenAI  
**API:** Responses API, `POST /v1/responses`  
**Model snapshot:** `gpt-5.4-2026-03-05`

The reason is methodological rather than brand preference: the exact dated snapshot gives the strongest currently verified reproducibility property for the multi-month AI-v1 experiment while retaining full-size reasoning capability and strict structured output at lower cost than the dated GPT-5.5 snapshot.

## Frozen request semantics

- model: `gpt-5.4-2026-03-05`
- reasoning effort: `medium`
- service tier: `default`
- store: `false`
- truncation: `disabled`
- max output tokens: `8192`
- tools: none
- conversation / previous response: none
- temperature: omitted
- top_p: omitted
- web/file/code/computer tools: none
- system/instructions: exact bytes of `config/ai_v1_policy.txt`
- user input: canonical compact JSON of the frozen feature snapshot
- output: strict provider-compatible JSON schema
- local `validate_decision()`: authoritative semantic validator after provider schema validation

The request is deliberately stateless. A new inference receives no previous AI-v1 inference, PnL, conversation state or outside market information.

## Provider-compatible schema rule

The canonical contract remains:

`config/ai_v1_decision_schema.json`

OpenAI receives:

`config/ai_v1_openai_response_schema.json`

The provider schema removes only JSON-Schema composition constructs that OpenAI Structured Outputs does not support. It does **not** widen the permitted AI-v1 semantic decision contract. Local runtime validation still enforces the canonical conditional rules, including:

- NO_TRADE => stop/TP values must be null;
- BUY/SELL => stop/TP values must be numeric and in frozen bounds;
- TP2 > TP1.

Both schema hashes are included in activation fingerprints.

## Secret boundary

The only provider secret is `OPENAI_API_KEY`.

It must live only in the Windows VPS local `.env` / process environment and must never be:

- committed to GitHub;
- pasted into chat;
- included in the AI ledger;
- sent to the cloud product snapshot.

The concrete adapter reads the key at request time.

## Activation boundary

This model selection does **not** activate AI-v1.

Before the first real model call that could enter performance evidence:

1. concrete adapter and tests must pass;
2. activation bundle must bind the exact provider/model/request semantics and code hashes;
3. three AI-v1 ledgers must receive their ACTIVATION records;
4. activation heads must be anchored in GitHub;
5. scheduler must be installed only after those anchors exist.
