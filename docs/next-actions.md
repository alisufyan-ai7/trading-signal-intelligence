# Current Next Actions

_Last updated: 2026-09-18_

## G3 status

S02 Structure Breakout v0.1 remains:

`RESEARCH — PRIMARY XAU FORWARD TEST ACTIVATED; LIVE EVIDENCE ACCUMULATION NEXT; NOT CANDIDATE`

## Activation anchor

The primary forward hypothesis is frozen and activated:

- test entity: `S02-v0.1:XAUUSD:PRIMARY`
- activation UTC: `2026-09-18T13:58:54.786419+00:00`
- activation record hash: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`
- initial ledger head: same hash
- protocol bundle SHA-256: `484b3de25c6ff6c24de30c5a700f211b98be8534c7b0354fcb2d6219587232cf`
- verification immediately after activation: valid, one ACTIVATION record

Durable anchor:

`research/forward/S02-XAUUSD-v0.1-activation-2026-09-18.md`

The code/config/scanner/ledger fingerprints committed at activation must remain unchanged for this forward test.

## First manual live scan — COMPLETE

First scan completed at `2026-09-18T14:09:12.789641Z` with no actions. Ledger verification stayed valid with one ACTIVATION record and the original anchored head hash.

## Immediate action — install hourly Windows scheduler

Pull the scheduling helpers and install the task:

```powershell
git pull
powershell -ExecutionPolicy Bypass -File scripts\install_s02_forward_task.ps1
```

The task runs hourly near minute 02 and writes scanner + verifier logs to `data\forward-task-logs\`.

Then check:

```powershell
Get-ScheduledTask -TaskName "TradingTop S02 XAU Forward Scan"
Get-ScheduledTaskInfo -TaskName "TradingTop S02 XAU Forward Scan"
```

Keep this Windows user logged in and MT5 available. After the first scheduled run, inspect the newest log and verify the ledger again.

