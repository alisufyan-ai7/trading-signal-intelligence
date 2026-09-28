# Cloud Snapshot Durability v0.1

_Status: VOLUME ATTACHED — SEED + CONTROLLED REDEPLOY VERIFICATION PENDING_  
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


## Approved implementation design

Use one Railway persistent volume attached to the existing `tradingtop-early-access` service and mount it at:

`/data`

Keep the application variable unchanged:

`TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`

No application-code change is required for the storage path.

### Why this is the preferred design

The current service already writes the sanitized public snapshot to `/data/public_snapshot.json`. A Railway volume mounted at `/data` therefore preserves the current producer, ingest endpoint, cloud reader, JSON schema and public API without introducing another database or storage service.

Railway's current volume reference states:

- Free/Trial default volume size: 0.5 GB;
- Free: max 1 volume per project;
- Trial: max 3 volumes per project;
- one volume per service;
- replicas cannot be used with a volume;
- services with a volume incur a small amount of downtime during redeploy because Railway prevents two deployments from mounting the same volume simultaneously;
- deleted volumes remain restorable for up to 48 hours before permanent deletion.

This service currently runs one replica and has no volume, so those constraints are compatible.

### First-attach behavior

Railway volumes are runtime mounts and are not overlays. When the new volume is mounted at `/data`, the previous container-ephemeral `/data` contents are not copied into the new volume automatically.

Therefore the first deployment after attachment is expected to start with no snapshot and safely show `snapshot_pending`.

Immediately after the service is healthy, republish the already-sanitized snapshot from the VPS using the existing publisher. That first post-attach push seeds the persistent volume.

### Migration procedure

1. Confirm current public app is healthy and current snapshot is populated.
2. In the existing Railway project `positioning-engine-cron`, select the existing service `tradingtop-early-access`.
3. Create one volume attached to this service.
4. Set mount path exactly to `/data`.
5. Do not change `TRADINGTOP_SNAPSHOT_PATH`.
6. Allow Railway to redeploy/restart the service.
7. Confirm `/healthz` returns HTTP 200.
8. If `/api/health` reports `snapshot_pending=true`, republish the existing sanitized snapshot from the VPS.
9. Verify the full public safety/health contract.
10. Trigger one controlled redeploy of the same service without republishing.
11. Verify the snapshot remains populated after redeploy.
12. Only then mark durability v0.1 complete.

### Rollback

If the service fails after the volume is attached:

1. do not modify AI-v1 or S02;
2. detach/remove the volume from the existing cloud service;
3. restore the previous service configuration with ephemeral storage;
4. redeploy the service;
5. republish the sanitized snapshot from the VPS;
6. confirm the public beta returns to the previously verified behavior.

If the volume is deleted, Railway documents a restoration window of up to 48 hours before permanent deletion.

### Expected operational tradeoff

A mounted Railway volume improves snapshot durability but changes deploy behavior: future redeploys may have brief downtime because Railway cannot mount the same volume to old and new deployments simultaneously.

For this single-replica research beta, that tradeoff is acceptable for v0.1 and is preferable to temporarily losing the entire snapshot on every redeploy.

## Verification command

After the volume is seeded, use:

`scripts/verify_cloud_snapshot_durability.py`

The script is read-only. It verifies the public cloud contract and prints a compact snapshot identity that can be compared before and after a controlled Railway redeploy.
