# Current Next Actions

_Last updated: 2026-09-21_

## G3 status

S02 Structure Breakout v0.1 remains:

`FORWARD TEST ACTIVE — XAUUSD PRIMARY; NOT CANDIDATE`

The anchored forward test is operational. Through `2026-09-21T15:02:06Z`, the current task log contains 72 consecutive hourly scans with no scheduling gaps, no verification failures, no signal lifecycle actions, and an unchanged activation-only ledger.

## Normal operation

No manual hourly scanner command is required.

Keep:

- the Windows user session logged in;
- MT5 running and connected to the research demo;
- the hourly Task Scheduler job enabled;
- `data/forward.sqlite` and both task-log files intact.

24/7 scheduling is intentional. Weekend/closed-market runs are harmless and avoid embedding unverified broker-session assumptions into the scheduling layer.

## Concise health check

Pull the read-only summary helper once:

```powershell
git pull
```

Then future checks can use:

```powershell
python scripts\summarize_s02_forward_ops.py
python scripts\verify_forward_ledger.py
Get-ScheduledTaskInfo -TaskName "TradingTop S02 XAU Forward Scan"
```

The summary script does not modify the forward ledger or frozen protocol.

## When to report immediately

Send the output as soon as any of these occurs:

- `SIGNAL` appears;
- `EXIT` appears;
- `MISSED_SIGNAL` appears;
- `SKIPPED_SIGNAL` appears;
- Task Scheduler `LastTaskResult` is non-zero;
- `NumberOfMissedRuns` increases;
- ledger verification returns `valid: false`;
- protocol-fingerprint mismatch stops the scanner.

Otherwise, a periodic concise health check is enough; there is no research value in reviewing every empty hourly scan individually.

## Evidence discipline

Do not:

- rerun activation;
- delete/rebuild `data/forward.sqlite`;
- edit forward records;
- change S02 v0.1, the live scanner, ledger implementation, or activated config;
- switch to long-only;
- select a robustness variant.

The next substantive G3 evidence begins with the first genuinely new signal lifecycle record. Periodic external anchoring of changed ledger heads remains required before public verification claims.

G2 commercial rights remains independently open; Exness remains R&D-only.
