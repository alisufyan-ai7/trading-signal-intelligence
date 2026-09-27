# Current Next Actions

_Last updated: 2026-09-27_

## Railway status

Railway deployment is successful.

Service:

`tradingtop-early-access`

Verified:

- Docker image built successfully;
- Uvicorn started;
- `/healthz` returned 200;
- deployment status is SUCCESS;
- no public domain exists yet.

## Immediate step — configure secrets before public exposure

Generate strong values locally and keep them out of chat/Git.

Required Railway service variables:

- `TRADINGTOP_BETA_USER`
- `TRADINGTOP_BETA_PASSWORD`
- `TRADINGTOP_INGEST_TOKEN`

Already configured:

- `TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`

The same `TRADINGTOP_INGEST_TOKEN` must later be stored in the Windows collector's local `.env`.

Do not generate the Railway public domain until these three variables are set.

## After secrets are configured

Return to ChatGPT and say:

`Railway secrets configured`

Then:

1. verify Railway variable names;
2. redeploy if needed;
3. generate the Railway service domain;
4. provide the public ingest URL;
5. configure the Windows collector's local ingest URL/token;
6. push the first derived snapshot;
7. verify invite gate + 3/3 health + current evidence/signals;
8. mark public-beta deployment complete.

## Persistence

No Railway volume is currently attached.

This is acceptable for the first beta because the Windows product-publish task republishes the derived snapshot hourly. A Railway restart may temporarily show an empty snapshot until the next push.

## Forward evidence

Forward collection continues unchanged.

XAU F1 progress: `2/20`.
