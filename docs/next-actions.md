# Current Next Actions

_Last updated: 2026-09-27_

## Immediate objective

Keep the 3–5 day Early Access launch moving while resolving stale USTEC/US30 MT5 bar history.

## Completed

- G1 PASS
- G2 PASS via separate Exness permission confirmed by project owner
- local Early Access FastAPI/UI preview PASS
- XAUUSD immutable forward collector ACTIVE
- multi-market dashboard/API foundation COMPLETE

## Current blocker — USTEC and US30 recent bars

Do **not** activate the two secondary forward ledgers yet.

Observed on 2026-09-27:

- both quotes are current through the latest Friday session (2026-09-25);
- both H1 histories stop at 2026-09-18 11:00 UTC;
- both H4 histories stop at 2026-09-18 08:00 UTC;
- recency probes return `appears_recent: false`.

This is an MT5 terminal/history-synchronization issue, not a strategy decision.

## Step 1 — pull the sync diagnostic + health UI correction

```powershell
git pull
```

The app health card now distinguishes configured markets from activated collectors.

## Step 2 — run targeted MT5 history synchronization probes

```powershell
python scripts\mt5_history_sync_probe.py --symbol USTEC --canonical "NASDAQ 100"

python scripts\mt5_history_sync_probe.py --symbol US30 --canonical "DOW 30"
```

Send both complete JSON outputs.

The probe queries each timeframe through:

- `copy_rates_from_pos`;
- `copy_rates_from`;
- `copy_rates_range`;

and repeats requests to give the terminal a chance to synchronize recent history.

## If final H1/H4 become recent

Re-run:

```powershell
python scripts\mt5_recency_probe.py --symbol USTEC --canonical "NASDAQ 100"
python scripts\mt5_recency_probe.py --symbol US30 --canonical "DOW 30"
```

Only after both markets report `appears_recent: true` for H1 and H4 do we activate their immutable ledgers.

## If they remain stuck on September 18

In the MT5 terminal:

1. open the USTEC chart;
2. switch to H1 and use chart Refresh;
3. switch to H4 and Refresh;
4. repeat for US30;
5. leave the charts open for about a minute;
6. rerun `mt5_history_sync_probe.py`.

If history still does not advance, the next diagnostic will compare server/date-range availability and broker session history rather than activating stale feeds.

## Existing XAU forward test

Leave it untouched.

## Launch work that continues in parallel

While the index history is repaired, continue product work:

- signal/evidence history views;
- authentication;
- one alert channel;
- public deployment setup;
- feedback capture.

USTEC/US30 activation is a market-specific blocker, not a reason to stop the whole product build.
