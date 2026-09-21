# Current Next Actions

_Last updated: 2026-09-21_

## Priority shift

Target an **Early Access Beta in 3–5 days**.

The active S02/XAUUSD forward test keeps running automatically in parallel. We do not wait for F2/F3 to begin product/customer work.

## Today — launch foundation

1. Confirm the production data path:
   - if separate written Exness commercial permission exists, archive it and mark G2 accordingly;
   - otherwise use a commercial production data provider and keep Exness R&D-only.

2. Start the cloud MVP:
   - landing page;
   - authentication;
   - production database;
   - signal/current-state API;
   - signal history;
   - health/ledger status.

3. Keep the existing XAU forward task untouched.

## 3–5 day build

Follow:

`docs/launch-plan-5-day-beta.md`

Scope is intentionally narrow:

- XAU/USD only;
- active/no-active setup card;
- entry/stop/target/R:R;
- immutable signal history/results;
- historical vs forward evidence clearly separated;
- one alert channel;
- mobile-responsive web;
- risk disclosure;
- no execution/copy trading.

## Launch mode

Use **Early Access / Research Beta** language.

Do not claim:

- proven future profitability;
- guaranteed win rate;
- personalized investment advice;
- completed forward validation.

A free or invite-gated first cohort is preferred so product learning can begin immediately.

## Forward evidence still runs

- F1: 20 completed trades — execution audit;
- F2: 50 trades + 90 days — interim strategy review;
- F3: 100 trades + 180 days — first candidate-status decision.

These gates control strategy claims, not beta-launch timing.

## Operations

Normal forward health check:

```powershell
python scripts\summarize_s02_forward_ops.py
python scripts\verify_forward_ledger.py
Get-ScheduledTaskInfo -TaskName "TradingTop S02 XAU Forward Scan"
```

Report immediately on SIGNAL / EXIT / MISSED_SIGNAL / SKIPPED_SIGNAL or any task/ledger error.
