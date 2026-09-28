# AI Insights UI

_Status: IMPLEMENTED — VPS + cloud verification pending_  
_Date: 2026-09-29_

## Purpose

Expose AI-v1.0 shadow evidence to SignalProof AI users without changing the activated AI-v1 decision system and without publishing private/internal inference material.

This milestone is downstream-only:

AI-v1 immutable ledgers -> verified read-only observability -> sanitized product payload -> public derived snapshot -> Railway API -> AI Insights UI.

The existing S02 benchmark remains a separate evidence stream and must not be relabeled as AI.

## Product boundary

AI Insights may expose:

- AI-v1 shadow runtime health;
- A1 / A2 / A3 validation progress;
- per-market valid-inference, signal, miss and error counts;
- BUY / SELL / NO_TRADE decisions;
- raw confidence explicitly labeled as an uncalibrated model score;
- regime;
- customer-safe rationale summaries emitted by the frozen decision contract;
- supporting factors and risk factors from the frozen structured decision;
- deterministic guard pass/block status;
- shadow entry / stop / TP1 / TP2 levels;
- open/closed shadow lifecycle state;
- recorded shadow net-R outcomes;
- trimmed immutable record hashes.

AI Insights must never expose:

- raw MT5 candles or raw broker market data;
- full feature snapshots;
- provider request IDs;
- raw provider responses;
- provider metadata;
- API credentials;
- full internal ledger payloads;
- hidden chain-of-thought.

## Implementation

Added:

- `src/trading_signal_intelligence/product/ai_insights.py`
- `tests/test_product_ai_insights.py`

Updated:

- `scripts/export_public_snapshot.py`
- `src/trading_signal_intelligence/product/app.py`
- `src/trading_signal_intelligence/product/cloud_app.py`
- `scripts/smoke_beta_product.py`
- `web/index.html`
- `web/app.js`
- `web/styles.css`

## Data path

### VPS

`build_public_ai_insights(...)` consumes only:

- `build_report(...)` from the VPS-verified read-only observability layer;
- `read_records_read_only(...)` using SQLite URI `mode=ro` and `PRAGMA query_only=ON`.

It does not import or invoke:

- the OpenAI provider adapter;
- MT5;
- broker execution;
- the AI-v1 ledger writer.

The builder compares the ledger head observed by the observability report with the ledger head observed during public-payload extraction. If a ledger changes during assembly, the AI snapshot fails closed rather than publishing a mixed-state view.

### Public snapshot

`scripts/export_public_snapshot.py` now adds a sanitized `ai_v1` object to the existing schema-version-1 snapshot.

AI failure does not take down the existing S02 public feed. If AI Insights cannot be built, the snapshot contains a customer-safe `temporarily_unavailable` AI section while the existing S02 snapshot continues.

### Cloud

Railway cloud ingestion validates that the AI block explicitly declares all of the following as false:

- `raw_market_data_included`
- `raw_feature_snapshots_included`
- `provider_request_metadata_included`
- `hidden_reasoning_included`

The public endpoint is:

`GET /api/ai/insights`

Older snapshots without `ai_v1` remain backward compatible and return a safe `snapshot_pending` response until the VPS publishes the first AI-aware snapshot.

## UI

The existing public beta page now includes a separate **AI Shadow Intelligence** section with:

1. shadow runtime health;
2. aggregate evidence counters;
3. A1 / A2 / A3 progress;
4. per-market forward-collection health;
5. recent customer-safe AI decision summaries;
6. AI-v1 shadow signal records and outcomes.

The UI explicitly states:

- AI-v1 is shadow-only;
- broker execution is disabled;
- raw confidence is not a probability of profit;
- hidden chain-of-thought and raw feature snapshots are not published;
- AI-v1 and S02 are separate evidence streams.

## Verification required before milestone closure

On the Windows VPS after pulling the implementation:

1. run the focused AI Insights tests;
2. rerun the existing AI-v1 observability tests;
3. run the beta product smoke;
4. export a public snapshot;
5. verify the exported snapshot contains `ai_v1`;
6. verify all prohibited AI fields are absent from the public snapshot;
7. verify the three AI ledger SHA-256 hashes remain unchanged before vs after export/smoke;
8. run `verify_ai_v1_runtime.py` and require `valid=true`;
9. push the derived snapshot through the existing product publisher;
10. verify Railway `GET /api/ai/insights` returns the sanitized AI block;
11. browser-smoke the public AI section after the new cloud code deployment;
12. keep broker execution disabled.

Only after those checks pass may the AI Insights UI milestone be marked complete.

## Governance

Do not change AI-v1 model, prompt, features, guardrails, universe, lifecycle, cost policy, scheduler decision cadence or existing immutable evidence for this UI milestone.

Any future decision-affecting AI change remains a separately governed version.
