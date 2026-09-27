# Current Next Actions

_Last updated: 2026-09-27_

## Launch status

TradingTop Early Access Day-2 smoke passed:

- 3/3 collectors ready;
- launch_ready=True;
- public derived-data snapshot exported;
- no raw MT5 market data included.

The smoke also detected **2 immutable forward SIGNAL records**. Inspecting and externally anchoring their current ledger heads is now the highest-priority evidence task.

## Immediate step — inspect the first forward signals

Pull the event inspector and cache-busted frontend:

```powershell
git pull

.\.venv\Scripts\python.exe scripts\inspect_forward_events.py
```

Paste the complete JSON output.

The command is read-only. It reports, per market:

- SIGNAL / EXIT / MISSED_SIGNAL / SKIPPED_SIGNAL counts;
- exact signal direction, timestamps, entry/stop/target;
- current unresolved signals;
- current ledger head hash;
- ledger verification.

Do not recreate, edit or resolve any signal manually.

## Refresh the beta frontend

Restart the local app after the pull:

```powershell
.\.venv\Scripts\python.exe scripts\run_beta_app.py
```

Then refresh `http://127.0.0.1:8000`.

The HTML now version-tags the CSS/JS assets, so the browser should load the current bundle without relying on the old cached static files.

Expected:

- `3/3 live collectors active`;
- historical evidence cards visible;
- the Immutable Forward Record section renders the actual two signals rather than `Loading forward records...`.

If the browser still shows the old bundle, use `Ctrl+F5` once.

## After event inspection

Once the two signal records and new ledger heads are anchored in GitHub:

1. continue authentication / invite-only access;
2. add one alert channel;
3. add cloud snapshot ingestion;
4. deploy the public beta;
5. add feedback + willingness-to-pay capture.

Forward collection continues unchanged throughout.
