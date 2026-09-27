# Current Next Actions

_Last updated: 2026-09-27_

## Launch status

The complete local launch path is operational.

Verified:

- XAUUSD / USTEC / US30 collectors active
- primary + secondary scanner schedulers healthy
- evidence + immutable forward record UI working
- two completed XAU forward trades externally anchored
- public derived snapshot excludes raw MT5 market data
- invite-access implementation complete
- Telegram alert implementation complete
- cloud snapshot ingestion implementation complete
- Docker deployment complete
- product-publish scheduler operational with LastTaskResult 0
- alert dedupe initialized
- Railway deployment runbook complete

## Next step — public invite-gated hosting

Recommended host: Railway, using the existing GitHub repository and Dockerfile.

The repository is ready for:

1. create a private Railway project/service from `alisufyan-ai7/trading-signal-intelligence`;
2. configure Dockerfile deployment;
3. set healthcheck path `/healthz`;
4. attach persistent storage at `/data`;
5. set cloud secrets:
   - `TRADINGTOP_BETA_USER`
   - `TRADINGTOP_BETA_PASSWORD`
   - `TRADINGTOP_INGEST_TOKEN`
   - `TRADINGTOP_SNAPSHOT_PATH=/data/public_snapshot.json`;
6. generate the public service domain;
7. set the same ingest token + public ingest URL in the Windows collector's local `.env`;
8. push the first snapshot;
9. verify invite gate and current evidence/signals publicly.

See:

`docs/public-beta-deployment-railway.md`

## Important cost/secret rule

Creating a cloud project/service may incur hosting usage.

Do not create hosting resources or generate a public domain until the user explicitly approves the hosting provider/cost.

Do not paste secret values into chat or GitHub.

## Local system

No further local scanner changes are needed for deployment.

Forward collection and F1 evidence accumulation continue unchanged.

XAU F1 progress: `2/20`.
