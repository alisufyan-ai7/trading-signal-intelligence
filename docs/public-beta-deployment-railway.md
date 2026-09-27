# Public Beta Deployment — Railway

**Status:** READY TO DEPLOY  
**Updated:** 2026-09-27

## Why this shape

The Windows machine remains the private collector and research source of truth.

It keeps:

- MT5 terminal access;
- raw candles;
- immutable forward SQLite ledgers;
- scanner schedules.

The cloud service receives only `data/public_snapshot.json`, which contains derived signal/evidence data and explicitly sets `raw_market_data_included = false`.

## Railway service

Deploy this repository from GitHub using the root `Dockerfile`.

Recommended service settings:

- Dockerfile: `Dockerfile`;
- healthcheck path: `/healthz`;
- restart policy: on failure;
- persistent volume mounted at `/data`;
- snapshot path: `/data/public_snapshot.json`.

Do not expose a public domain until invite credentials and the ingestion token are configured.

## Required cloud secrets

Set in the Railway service secret/environment manager:

- `TRADINGTOP_BETA_USER`
- `TRADINGTOP_BETA_PASSWORD`
- `TRADINGTOP_INGEST_TOKEN`
- `TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`

Use strong unique values. Do not commit them to Git or paste them into project documentation.

## Windows collector secrets

After the cloud service receives a public HTTPS domain, set locally in `.env`:

- `TRADINGTOP_INGEST_URL=https://<service-domain>/api/internal/snapshot`
- `TRADINGTOP_INGEST_TOKEN=<same secret as cloud>`

Then test:

```powershell
.\.venv\Scripts\python.exe scripts\export_public_snapshot.py
.\.venv\Scripts\python.exe scripts\push_public_snapshot.py
```

Expected cloud response:

- `accepted: true`;
- three markets;
- `raw_market_data_included: false`.

## Invite-gate verification

After the first snapshot push:

1. unauthenticated browser request should prompt for Early Access credentials;
2. valid invited credentials should load the beta;
3. health card should show 3/3 collectors active;
4. XAU evidence + two existing closed forward trades should render;
5. USTEC/US30 should show scanning with no forward signals until they issue one.

The hosting healthcheck endpoint `/healthz` remains public so the platform can monitor the container without bypassing the invite gate for product pages/APIs.

## Telegram

Telegram is optional for the first public deploy.

Alert state has already been initialized so the two historical-forward XAU SIGNALs and EXITs will not replay.

When ready, set only on the Windows collector:

- `TRADINGTOP_TELEGRAM_BOT_TOKEN`
- `TRADINGTOP_TELEGRAM_CHAT_ID`

The hourly product-publish task will then send only new SIGNAL/EXIT records.

## Rollback

Cloud deployment does not change the activated scanners or forward ledgers.

If the cloud service fails, disable snapshot push or remove the public domain. The local forward evidence system continues independently.


## Deployment attempt — 2026-09-27

An automated deployment attempt was made after explicit user approval.

Railway rejected creation of the isolated `tradingtop-early-access` project with:

`Free plan resource provision limit exceeded. Please upgrade to provision more resources!`

The failure occurred before Railway provisioned a project/service, so there is nothing to roll back.

Do not use an unrelated existing Railway project as a workaround. Preserve TradingTop isolation.

Retry this runbook after Railway account capacity is increased or an unused Railway resource is safely removed.


## Railway service attached — 2026-09-27

The formerly empty Railway project `positioning-engine-cron` was explicitly approved for repurposing to TradingTop.

A GitHub-backed Railway service now exists:

- service: `tradingtop-early-access`;
- source: `alisufyan-ai7/trading-signal-intelligence`;
- branch: `main`;
- Dockerfile: `Dockerfile`;
- healthcheck: `/healthz`;
- snapshot path variable: `/data/public_snapshot.json`.

Railway did not create an initial deployment record during service creation, and the free plan blocks creating an additional service. This commit intentionally provides a fresh `main` push so Railway's GitHub source can trigger the first build on the existing service.
