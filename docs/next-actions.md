# Current Next Actions

_Last updated: 2026-09-27_

## Immediate objective

Launch TradingTop Early Access while all three launch-market forward collectors run independently and immutably.

## Completed

- G1 PASS
- G2 PASS via separate Exness permission confirmed by project owner
- local Early Access FastAPI/UI preview PASS
- XAUUSD immutable forward collector ACTIVE
- USTEC recency PASS
- US30 recency PASS
- USTEC immutable forward ledger ACTIVATED + HASH ANCHORED
- US30 immutable forward ledger ACTIVATED + HASH ANCHORED
- multi-market dashboard/API foundation COMPLETE

## Immediate step — install the secondary hourly scheduler

Pull the activation-anchor updates and install the USTEC/US30 task:

```powershell
git pull

powershell -ExecutionPolicy Bypass -File scripts\install_s02_secondary_forward_task.ps1
```

Then inspect the task:

```powershell
Get-ScheduledTask -TaskName "TradingTop S02 Secondary Forward Scan"
Get-ScheduledTaskInfo -TaskName "TradingTop S02 Secondary Forward Scan"
```

The task should be `Ready`, with its next run near minute 03 of the hour.

## Verify the three product collectors

Restart or refresh the local beta app after `git pull`.

Expected health state:

- XAUUSD: scanning / active;
- USTEC: scanning / active;
- US30: scanning / active;
- health card: **3/3 live collectors active**.

If the app is not already running:

```powershell
python scripts\run_beta_app.py
```

Open:

`http://127.0.0.1:8000`

## After the first scheduled secondary run

Run:

```powershell
Get-ScheduledTaskInfo -TaskName "TradingTop S02 Secondary Forward Scan"

Get-Content data\forward-task-logs\s02_secondary_forward.log -Tail 150

python scripts\verify_forward_ledger.py --database data\forward_ustec.sqlite
python scripts\verify_forward_ledger.py --database data\forward_us30.sqlite
```

Send those outputs if any SIGNAL / EXIT / MISSED_SIGNAL / SKIPPED_SIGNAL appears or if the task/ledger reports an error.

## Product build — continue immediately

While forward collectors run:

1. signal-history/evidence API + UI;
2. current active-signal detail view;
3. authentication;
4. one alert channel;
5. production deployment;
6. feedback/willingness-to-pay capture;
7. founding paid tier after initial user validation.

## Existing XAU forward test

Leave it untouched.

## Claim discipline

Use Early Access / research beta language.

Do not claim guaranteed returns, completed forward validation, personalized advice, or copy trading.
