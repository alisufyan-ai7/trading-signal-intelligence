# Current Next Actions

_Last updated: 2026-09-27_

## Launch status

TradingTop Early Access is now in Day 2 build.

Completed:

- G1 PASS
- G2 PASS
- XAUUSD forward collector active
- USTEC forward collector active
- US30 forward collector active
- primary + secondary scheduled tasks operational
- local FastAPI beta preview passed
- evidence API/UI implemented
- immutable forward signal-history API/UI implemented
- public derived-data snapshot exporter implemented

## Immediate local verification

Pull and run the fast product smoke check:

```powershell
git pull

.\.venv\Scripts\python.exe scripts\smoke_beta_product.py

.\.venv\Scripts\python.exe scripts\export_public_snapshot.py
```

Expected smoke output:

- `beta smoke: PASS`
- `collectors_ready=3/3`
- `launch_ready=True`

The snapshot exporter should report `raw_market_data_included: false`.

Then restart the beta app:

```powershell
.\.venv\Scripts\python.exe scripts\run_beta_app.py
```

Refresh `http://127.0.0.1:8000`.

Expected new sections:

- 3/3 systems operational;
- historical evidence cards for XAUUSD, USTEC, US30;
- immutable forward record;
- empty-state message until the first live SIGNAL occurs.

## Next engineering step

After the smoke check passes:

1. add authentication / invite-only access;
2. add one alert channel;
3. add cloud snapshot ingestion so the public app can receive derived data from the Windows collector without raw MT5 candles;
4. deploy the public beta;
5. add feedback + willingness-to-pay capture.

## Operations

Forward collectors continue automatically.

Report immediately if any SIGNAL / EXIT / MISSED_SIGNAL / SKIPPED_SIGNAL appears or if a scheduler/ledger reports an error.

Do not modify or recreate any of the three activated forward ledgers.
