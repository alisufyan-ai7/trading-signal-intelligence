# Current Next Actions

_Last updated: 2026-09-27_

## Public Railway beta status

Railway deployment is healthy and the invite/ingestion secret variables are configured.

Public service domain:

`https://tradingtop-early-access-production.up.railway.app`

Verified through Railway:

- deployment SUCCESS;
- Uvicorn running on Railway port;
- `/healthz` returns 200;
- invite username/password variables exist;
- ingestion token variable exists.

The first derived snapshot has not yet been pushed from Windows.

## Immediate Windows action — connect the publisher

Pull the secure ingest helper:

```powershell
git pull

powershell -ExecutionPolicy Bypass -File scripts\configure_cloud_ingest.ps1
```

When prompted, enter the **same** `TRADINGTOP_INGEST_TOKEN` that was configured in Railway.

The prompt is secure and does not display the token.

Then push the current derived snapshot:

```powershell
.\.venv\Scripts\python.exe scripts\export_public_snapshot.py

.\.venv\Scripts\python.exe scripts\push_public_snapshot.py
```

Expected push response:

- `accepted: true`;
- three markets;
- `raw_market_data_included: false`.

Then run the product publish wrapper once:

```powershell
scripts\run_product_publish_task.cmd

Get-Content data\forward-task-logs\product_publish.log -Tail 80
```

Expected final summary:

`export_exit=0 alert_exit=0 push_exit=0`

Telegram can remain disabled.

## Browser verification

Open:

`https://tradingtop-early-access-production.up.railway.app`

Expected:

1. browser requests the Early Access username/password;
2. valid credentials load the beta;
3. health shows 3/3 live collectors active after snapshot push;
4. XAU evidence and the two completed forward trades appear;
5. USTEC/US30 remain scanning with no issued forward trades.

## Persistence note

There is currently no Railway persistent volume.

A Railway restart/redeploy can clear the cloud snapshot until the Windows publisher pushes it again. The hourly product-publish task provides automatic recovery once cloud ingestion is configured.
