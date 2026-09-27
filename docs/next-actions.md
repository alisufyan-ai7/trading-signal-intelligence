# Current Next Actions

_Last updated: 2026-09-27_

## Public beta status

The TradingTop public beta data path is now operational end-to-end.

Public URL:

`https://tradingtop-early-access-production.up.railway.app`

Verified:

- Railway deployment SUCCESS
- `/healthz` 200
- public app root 200
- `/api/health` 200
- `/api/markets` 200
- `/api/signals` 200
- Windows snapshot push 200
- derived snapshot accepted
- raw market data excluded

Snapshot composition:

- 3 live-signal markets
- 6 research/monitoring markets
- 9 total market rows

## Immediate operational check

Run the local publish wrapper once:

```powershell
scripts\run_product_publish_task.cmd
Get-Content data\forward-task-logs\product_publish.log -Tail 80
```

Expected:

`export_exit=0 alert_exit=0 push_exit=0`

Telegram may remain disabled.

## Browser smoke

Open:

`https://tradingtop-early-access-production.up.railway.app`

Confirm:

1. no username/password prompt;
2. 3/3 live collectors active;
3. XAU evidence and two completed forward trades visible;
4. USTEC and US30 scanning with no forward signals;
5. research/monitoring markets visible with explicit evidence labels;
6. research-beta disclosure visible.

## Next launch work

After browser smoke passes:

1. add user feedback / willingness-to-pay capture;
2. decide first invite/public-user cohort;
3. optionally enable Telegram alerts for future SIGNAL/EXIT records;
4. monitor public snapshot freshness and Railway restarts;
5. continue XAU F1 forward accumulation unchanged.

## Persistence

No Railway volume is attached yet.

If Railway restarts before the next scheduled Windows push, the snapshot can temporarily disappear. The hourly product-publish task should restore it automatically.
