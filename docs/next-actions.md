# Current Next Actions

_Last updated: 2026-09-27_

## Immediate objective

Launch TradingTop Early Access while the existing XAU forward validation continues automatically.

## Completed

- G1 PASS
- G2 PASS via separate Exness permission confirmed by project owner
- local Early Access FastAPI/UI preview PASS
- XAUUSD immutable forward collector ACTIVE
- multi-market dashboard/API foundation COMPLETE
- USTEC live H1/H4 recency PASS
- US30 live H1/H4 recency PASS

## Immediate step — activate secondary immutable ledgers

The MT5 synchronization probe confirmed current H1/H4 history for both USTEC and US30.

Run exactly once per market:

```powershell
python scripts\activate_s02_forward.py `
  --database data\forward_ustec.sqlite `
  --symbol USTEC `
  --canonical "NASDAQ 100" `
  --entity "S02-v0.1:USTEC:SECONDARY"

python scripts\activate_s02_forward.py `
  --database data\forward_us30.sqlite `
  --symbol US30 `
  --canonical "DOW 30" `
  --entity "S02-v0.1:US30:SECONDARY"

python scripts\verify_forward_ledger.py `
  --database data\forward_ustec.sqlite

python scripts\verify_forward_ledger.py `
  --database data\forward_us30.sqlite
```

Send the complete two activation JSON outputs and the two verification outputs.

Do **not** install the secondary scheduled task yet. The two activation hashes must first be recorded in the durable repository audit trail.

## After hashes are anchored

Then:

1. install `TradingTop S02 Secondary Forward Scan`;
2. verify its first automatic run;
3. confirm the beta health card reports 3/3 live collectors active;
4. continue signal-history/evidence UI;
5. add authentication;
6. add one alert channel;
7. prepare public deployment and first-user feedback capture.

## Existing XAU forward test

Leave it untouched.

## Launch work in parallel

Product work continues even while forward samples accumulate:

- signal/evidence history views;
- authentication;
- alert delivery;
- public deployment;
- feedback/willingness-to-pay capture.

## Claim discipline

Use Early Access / research beta language.

Do not claim guaranteed returns, completed forward validation, personalized advice, or copy trading.
