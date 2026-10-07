# VowSig Scalable Multi-Lineage Public Observability v0.1

_Status: ISOLATED ENGINEERING MILESTONE / NOT PUBLISHED — 2026-10-07_

## Objective

Expose customer-safe validation progress for multiple independently governed AI shadow lineages without turning research-only markets into public signal markets.

Initial programs:

- Core AI Shadow Validation — active AI-v1.1 on XAUUSD / USTEC / US30.
- Expansion Shadow Validation — AI-v1.2.1 on EURUSD / XAGUSD / USOIL.

The public surface must be able to add a future separately governed program, including a possible crypto lineage, without hard-coding new gate names into browser code.

## Separation of concerns

This milestone separates public research observability from public signal exposure.

For AI-v1.2.1:

- public_research_observability = true;
- public_signal_exposure = false;
- signal_details_included = false;
- broker execution remains disabled.

No entry, stop, target, rationale, confidence, signal record, or alert payload is included in the generic validation-program contract.

## Generic validation-program contract

The public snapshot gains validation_programs_schema_version = 1 and validation_programs = [...].

Each program contains a stable program_id, title, runtime/protocol versions, SHADOW_ONLY mode, research/signal visibility flags, normalized health, sanitized aggregate counts, generic gate requirements, per-market collection status, and explicit false raw/private-data flags.

Gate names are data, not frontend code. Each gate is rendered from a requirements list. v0.1 supports count and calendar-age requirements, so future lineages can use different gate IDs without changing the browser renderer.

## Current program identities

### core-ai-shadow

Current runtime AI-v1.1, markets XAUUSD / USTEC / US30, gates A1 / A2 / A3. The existing richer AI Insights decision/signal feed remains separate and backward compatible.

### market-expansion-1

Runtime AI-v1.2.1, markets EURUSD / XAGUSD / USOIL, gates X1 / X2 / X3. This program is research-progress-only and deliberately omits actionable signal details.

## Website behavior

The homepage keeps the existing AI Insights feed for the currently public core shadow lineage and adds a separate generic validation-program section. It renders runtime/mode, visibility boundary, aggregate counts, gate progress, and per-market collection health from API data. The browser contains no hard-coded A1/A2/A3 or X1/X2/X3 arrays.

## Cloud and publisher safety

The cloud snapshot validator and VPS push guard fail closed if a validation program is not SHADOW_ONLY, lacks public research-observability authorization, includes signal details, has broker execution enabled, contains raw/private data, or duplicates a program ID.

For research-only programs, top-level recent_decisions, shadow_signals, signal_records, and alerts collections are forbidden.

## Public-surface governance v0.3

The existing v0.2 correction schema remains historical evidence and keeps its original six-artifact allowlist. v0.3 is additive and expands the correctable public-product allowlist only by:

- ai_insights_source;
- public_snapshot_export_script;
- public_snapshot_push_script.

A v0.3 correction may supersede the current v0.2 tip. Schema regression from v0.3 back to v0.2 is rejected. The v0.3 builder remains confirmation-gated and records a caller-supplied change scope, with decision-artifact, ledger, backfill, provider, MT5, broker, and scheduler mutation flags all false.

## Non-goals

This milestone does not authorize or change model/provider, prompt/policy, feature definitions, decision schema, guardrails, lifecycle, costs, cadence, ledgers, activation anchors, schedulers, broker execution, backfill, expansion signal exposure, or expansion alerts.

## Publication sequence

Before production publication:

1. Complete isolated branch tests.
2. Verify a clean fast-forward candidate from production.
3. Run owner/VPS read-only validation against live AI-v1.1 and AI-v1.2.1 state.
4. Generate one v0.3 correction with change scope VowSig scalable multi-lineage public observability v0.1.
5. Inspect the correction and rerun public/runtime regression tests.
6. Request separate publication-only approval.
7. Publish the exact tested commit/correction and reconcile VPS.
8. Generate/push the public snapshot and verify A1/A2/A3 plus X1/X2/X3.

No production deployment is authorized by this design document itself.
