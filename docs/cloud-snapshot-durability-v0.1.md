# Cloud Snapshot Durability v0.1

_Status: NEXT_  
_Date: 2026-09-29_  
_GitHub issue: #6_

## Objective

Make the existing SignalProof AI Railway product retain the latest sanitized public snapshot across container restart/redeploy events.

This milestone is product/cloud reliability only. It must not change AI-v1.0 or S02 decision behavior, evidence semantics, or broker boundaries.

## Observed failure mode

During AI Insights cloud verification:

1. the VPS exported and safely pushed an AI-aware derived snapshot;
2. Railway deployed current `main` successfully;
3. the new container correctly exposed `GET /api/ai/insights`;
4. Railway reported no mounted volumes on the service;
5. the new container started without `/data/public_snapshot.json`;
6. the app correctly returned the safe `snapshot_pending` fallback;
7. republishing the already-VPS-validated snapshot restored:
   - launch_ready=true;
   - all 9 public markets;
   - AI-v1.0 / SHADOW_ONLY;
   - populated AI Insights UI.

Therefore the defect is ephemeral cloud snapshot storage, not collection, sanitization, inference, or ingestion.

## Current architecture

Authoritative producer:

Windows VPS -> `scripts/export_public_snapshot.py` -> sanitized `data/public_snapshot.json`

Cloud ingest:

`scripts/push_public_snapshot.py` -> `POST /api/internal/snapshot`

Current Railway read path:

`TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`

Current service:

- project: `positioning-engine-cron`;
- service: `tradingtop-early-access`;
- production environment;
- GitHub source: `alisufyan-ai7/trading-signal-intelligence`;
- branch: `main`;
- root Dockerfile;
- no persistent Railway volume currently attached.

## Preferred first approach

Investigate attaching a Railway persistent volume to the **existing** service at `/data`.

This is preferred because it preserves:

- the current JSON snapshot contract;
- the current ingest endpoint;
- the current cloud app code path;
- the VPS as authoritative producer;
- the smallest implementation surface.

If the current plan/resource limits do not permit a suitable volume, evaluate the smallest durable alternative for a single sanitized JSON object.

## Hard boundaries

Do not:

- alter AI-v1 model/provider/prompt/features/guardrails/lifecycle/costs/cadence;
- write to AI-v1 immutable ledgers;
- alter S02 logic/ledgers;
- upload raw MT5 candles or raw broker data;
- create a second public Railway app as a workaround;
- weaken snapshot validation or AI safety flags.

## Acceptance criteria

A controlled cloud restart/redeploy must preserve a populated product without manual VPS republish:

- `/api/health`: ok=true, launch_ready=true;
- `/api/ai/insights`: AI-v1.0, SHADOW_ONLY, forward_validation_in_progress;
- broker_execution_disabled=true;
- all public AI safety flags=false;
- market_count=9;
- AI Insights UI populated;
- existing publisher still succeeds;
- no change to live AI/S02 ledgers.

The implementation must include a rollback path before any Railway storage mutation.
