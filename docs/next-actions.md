# Current Next Actions

_Last updated: 2026-09-27_

## Public beta status

The TradingTop app is now intended to be publicly readable without a username/password prompt.

Snapshot ingestion remains private and bearer-token protected.

Public URL:

`https://tradingtop-early-access-production.up.railway.app`

## VPS environment file

On the Windows VPS, the environment file is:

`C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence\.env`

Required entries:

```text
TRADINGTOP_INGEST_URL=https://tradingtop-early-access-production.up.railway.app/api/internal/snapshot
TRADINGTOP_INGEST_TOKEN=<same secret configured in Railway>
```

Optional Telegram entries:

```text
TRADINGTOP_TELEGRAM_BOT_TOKEN=
TRADINGTOP_TELEGRAM_CHAT_ID=
```

Do not add beta username/password variables. The app auth gate has been removed.

## Immediate verification

The secure helper has already written the ingest URL/token on the VPS.

Run:

```powershell
.\.venv\Scripts\python.exe scripts\export_public_snapshot.py
.\.venv\Scripts\python.exe scripts\push_public_snapshot.py
```

Expected:

- `accepted: true`
- `markets: 3`
- `raw_market_data_included: false`

Then:

```powershell
scripts\run_product_publish_task.cmd
Get-Content data\forward-task-logs\product_publish.log -Tail 80
```

Expected summary:

`export_exit=0 alert_exit=0 push_exit=0`

Telegram may remain disabled.

## Railway code refresh

The current Railway runtime has the username/password variables blank, so Basic auth is already effectively disabled.

To deploy the code version that removes the auth middleware entirely, use Railway dashboard → `tradingtop-early-access` → **Deploy Latest Commit** after the latest GitHub commits are visible.

After that, confirm the public URL opens directly without a credentials prompt.

## Security boundary

Public read access is intentional.

The write endpoint `/api/internal/snapshot` remains protected by `TRADINGTOP_INGEST_TOKEN`.

Never expose or commit the ingestion token.


## Immediate security action — rotate ingestion token

The previous token appeared in a malformed Railway request path and must not be reused.

1. generate a new random 32-byte token locally;
2. replace Railway `TRADINGTOP_INGEST_TOKEN`;
3. pull the hardened helpers;
4. rerun `scripts/configure_cloud_ingest.ps1` with the new token;
5. retry export + push.

The hardened push client will now reject the malformed URL condition locally before any request is sent.
