# Current Next Actions

_Last updated: 2026-09-27_

## Railway deployment state

The empty Railway project `positioning-engine-cron` has been explicitly repurposed for TradingTop.

Configured service:

`tradingtop-early-access`

Source:

`alisufyan-ai7/trading-signal-intelligence` → `main`

Configured:

- Dockerfile deployment
- `/healthz` healthcheck
- restart-on-failure
- `TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`

No public domain or secrets are exposed yet.

## One-time Railway dashboard action required

The Railway connector attached and configured the service but did not create the service's first deployment record.

In the Railway dashboard:

1. open project `positioning-engine-cron`;
2. open service `tradingtop-early-access`;
3. trigger **Deploy / Deploy Latest Commit** for branch `main`;
4. wait until Railway shows a deployment attempt (success or failure).

Do not create another service.

Do not generate a public domain yet.

Do not paste invite or ingestion secrets into chat.

## After the first deployment attempt

Return to ChatGPT and say:

`Railway first deploy triggered`

Then the next automated steps are:

1. inspect build/runtime logs;
2. fix any deployment failure;
3. confirm `/healthz`;
4. configure invite + ingestion secrets via Railway's secret manager;
5. generate the Railway service domain only after the invite gate is active;
6. configure the Windows ingest URL/token locally;
7. push the first derived snapshot;
8. verify the public invite-gated beta.

## Persistence note

Persistent Railway volume creation is currently unavailable through the connector because the Railway AI sub-agent has reached its usage limit.

This does not block beta launch. Without a volume, the snapshot may need to be repushed after a cloud redeploy/restart. The hourly Windows publisher already supports repushing it.
