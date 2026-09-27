# Current Next Actions

_Last updated: 2026-09-27_

## Launch status

TradingTop Early Access is ready for the final local automation check before public deployment.

Completed:

- G1 research data PASS
- G2 Exness commercial derived-use permission PASS
- XAUUSD / USTEC / US30 forward collectors active
- primary + secondary scanner schedulers operational
- local beta UI/API operational
- evidence + immutable forward record UI operational
- 2 completed XAU forward trades externally anchored
- derived public snapshot path validated
- raw market data excluded from public snapshot
- invite-access implementation complete
- Telegram SIGNAL/EXIT implementation complete
- cloud snapshot-ingestion implementation complete
- Docker deployment definition complete
- launch-layer smoke PASS
- alert dedupe initialized with 4 existing SIGNAL/EXIT records
- product-publish scheduler installed

## Immediate checkpoint — first product-publish execution

The product-publish task was installed with its first scheduled execution at approximately minute 05.

After the next scheduled run, execute:

```powershell
Get-ScheduledTaskInfo -TaskName "TradingTop Product Publish"

Get-Content data\forward-task-logs\product_publish.log -Tail 120
```

Expected:

- `LastTaskResult : 0`
- a real `LastRunTime`
- snapshot export succeeds
- Telegram step reports disabled if credentials are not configured
- cloud push reports disabled if ingestion URL/token are not configured
- final line:
  `export_exit=0 alert_exit=0 push_exit=0`

No credentials are required for this verification.

### Faster option

The same safe wrapper can be tested immediately instead of waiting for the scheduled minute:

```powershell
scripts\run_product_publish_task.cmd

Get-Content data\forward-task-logs\product_publish.log -Tail 120
```

It is safe before cloud/Telegram configuration because those integrations are optional until secrets are present.

## After product-publish PASS

The next step is **public invite-gated deployment**.

Deployment requirements:

1. Dockerized `trading_signal_intelligence.product.cloud_app:app`;
2. persistent storage for `public_snapshot.json`;
3. environment secrets:
   - `TRADINGTOP_BETA_USER`
   - `TRADINGTOP_BETA_PASSWORD`
   - `TRADINGTOP_INGEST_TOKEN`
   - `TRADINGTOP_SNAPSHOT_PATH`
4. after deployment, set locally:
   - `TRADINGTOP_INGEST_URL`
   - matching `TRADINGTOP_INGEST_TOKEN`
5. push the first snapshot from Windows;
6. verify the public invite gate, evidence view and two existing forward trades;
7. then optionally configure Telegram credentials for future SIGNAL/EXIT alerts.

## Secrets

Do not paste secrets into chat or commit them to GitHub.

Keep them only in local `.env` and the hosting provider's secret/environment-variable manager.

## Forward research

All three forward collectors continue unchanged during deployment.

S02 remains NOT CANDIDATE.

XAU F1 progress remains `2/20` completed forward trades.
