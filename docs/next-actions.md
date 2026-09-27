# Current Next Actions

_Last updated: 2026-09-27_

## Launch status

TradingTop Early Access has passed the local Day-2 product smoke and the first immutable XAU forward lifecycles are anchored.

Current forward evidence:

- XAU completed trades: 2
- XAU cumulative net R: approximately -2.0147R
- XAU skipped overlapping setup: 1
- USTEC forward events: 0
- US30 forward events: 0
- XAU ledger valid: yes
- USTEC ledger valid: yes
- US30 ledger valid: yes

The two XAU losses do not alter strategy status. F1 remains an execution/lifecycle audit at 20 completed trades.

## Launch layer implemented

The repository now includes:

- optional invite-gated web access using environment credentials;
- Telegram SIGNAL/EXIT notifier;
- cloud beta app that accepts derived snapshots only;
- authenticated snapshot-ingestion endpoint;
- Docker deployment;
- Windows-side snapshot push client;
- hourly product publish wrapper/scheduler;
- launch-layer smoke test.

The cloud path does not require raw MT5 bars or the immutable SQLite ledgers to leave the Windows collector.

## Immediate local smoke

Pull the launch-layer changes and refresh the app environment:

```powershell
git pull

powershell -ExecutionPolicy Bypass -File scripts\setup_beta_app.ps1

.\.venv\Scripts\python.exe scripts\export_public_snapshot.py

.\.venv\Scripts\python.exe scripts\smoke_launch_layer.py
```

Expected:

- `launch layer smoke: PASS`
- `local_collectors=3/3`
- `cloud_snapshot_collectors=3/3`
- `snapshot_forward_signals=2`

## Initialize alerts without replaying old trades

Before adding a Telegram token, mark the already-observed SIGNAL/EXIT records as seen:

```powershell
.\.venv\Scripts\python.exe scripts\notify_forward_events.py --initialize
```

Expected: four records marked seen (2 SIGNAL + 2 EXIT). This prevents first-time alert configuration from replaying already-closed trades.

## Product publish scheduler

The publish task runs after the scanners and is safe even before Telegram/cloud credentials are configured:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_product_publish_task.ps1

Get-ScheduledTaskInfo -TaskName "TradingTop Product Publish"
```

It runs hourly near minute 05 and:

1. exports the public derived-data snapshot;
2. sends new Telegram alerts if configured;
3. pushes the snapshot to the cloud beta if configured.

Without Telegram/cloud credentials those two steps report disabled and still exit successfully.

## Secrets — keep local only

Use a local `.env` based on `.env.example`.

Configure later without posting secrets into chat or GitHub:

- `TRADINGTOP_BETA_USER`
- `TRADINGTOP_BETA_PASSWORD`
- `TRADINGTOP_TELEGRAM_BOT_TOKEN`
- `TRADINGTOP_TELEGRAM_CHAT_ID`
- `TRADINGTOP_INGEST_URL`
- `TRADINGTOP_INGEST_TOKEN`

## Next after smoke passes

The next launch step is public hosting.

Recommended sequence:

1. deploy the Dockerized cloud app;
2. attach persistent storage for `public_snapshot.json`;
3. set invite and ingestion secrets;
4. configure the Windows collector's ingest URL/token;
5. push the first derived snapshot;
6. verify the public beta behind the invite gate;
7. then enable Telegram for new SIGNAL/EXIT lifecycle alerts.

No scanner/strategy/ledger implementation needs to change for deployment.
