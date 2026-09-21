# Current Next Actions

_Last updated: 2026-09-21_

## Immediate objective

Launch **TradingTop Early Access in 3–5 days** while the existing forward validation continues automatically.

## Gate status

- G1 research data: PASS
- G2 commercial source rights: **PASS — separate Exness permission confirmed by project owner**
- G3 strategy evidence: IN PROGRESS
- G4 customer value: starts with the Early Access cohort

Paid replacement market-data subscriptions are deferred until application revenue exists.

## Launch universe

### Live-signal launch markets

1. XAU/USD — primary historical lead, forward test already active
2. NASDAQ 100 / USTEC — secondary historical transfer support
3. DOW 30 / US30 — secondary historical transfer support

### Research/monitoring markets visible in product

- EUR/USD
- GBP/USD
- USD/JPY
- XAG/USD
- S&P 500
- WTI

The UI must show evidence status per market rather than implying equal validation.

## Step 1 — pull and preview the beta app

```powershell
git pull
pip install -e ".[app]"
python scripts\run_beta_app.py
```

Then open:

`http://127.0.0.1:8000`

Expected:

- TradingTop Early Access page;
- XAU/USD, NASDAQ 100 and DOW 30 in the live-signal section;
- remaining researched markets in the research section;
- XAU forward state visible;
- USTEC/US30 initially show forward collector not activated.

Leave the app running only for preview; this is not the final internet deployment yet.

## Step 2 — verify USTEC and US30 live recency

In a second PowerShell window:

```powershell
python scripts\mt5_recency_probe.py --symbol USTEC --canonical "NASDAQ 100"
python scripts\mt5_recency_probe.py --symbol US30 --canonical "DOW 30"
```

Both H1 and H4 should report `appears_recent: true`.

## Step 3 — activate separate immutable secondary ledgers

Only if recency is clean:

```powershell
python scripts\activate_s02_forward.py --database data\forward_ustec.sqlite --symbol USTEC --canonical "NASDAQ 100" --entity "S02-v0.1:USTEC:SECONDARY"

python scripts\activate_s02_forward.py --database data\forward_us30.sqlite --symbol US30 --canonical "DOW 30" --entity "S02-v0.1:US30:SECONDARY"

python scripts\verify_forward_ledger.py --database data\forward_ustec.sqlite
python scripts\verify_forward_ledger.py --database data\forward_us30.sqlite
```

Send the two recency outputs plus both activation and verification JSON outputs.

Do **not** install the secondary scheduled task until those two activation hashes are durably anchored in the repo.

## Step 4 — after secondary activation

Once the hashes are anchored:

1. install the USTEC/US30 hourly scheduler;
2. connect all three ledgers to the web product status API;
3. add product signal-history/evidence views;
4. add authentication;
5. add one alert channel;
6. deploy the beta publicly;
7. start collecting user feedback and willingness-to-pay data.

## Existing XAU forward test

Leave it untouched.

Normal health check:

```powershell
python scripts\summarize_s02_forward_ops.py
python scripts\verify_forward_ledger.py
Get-ScheduledTaskInfo -TaskName "TradingTop S02 XAU Forward Scan"
```

Report immediately on SIGNAL / EXIT / MISSED_SIGNAL / SKIPPED_SIGNAL or any task/ledger error.

## Launch claim discipline

Launch language:

**TradingTop Early Access — verified rule-based market setups with transparent historical and forward performance.**

Do not claim guaranteed returns, completed forward validation, personalized advice, or copy trading.
