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

## Immediate action — first live scan

Pull the documentation anchor. The frozen scanner/strategy/ledger source files have not changed since activation.

```powershell
git pull
python scripts\scan_s02_forward.py
python scripts\verify_forward_ledger.py
```

Paste both JSON outputs.

### Expected behavior

A scan can validly produce any of these:

- no action: no S02 signal closed since activation;
- `SIGNAL`: a qualifying setup was discovered within the frozen 5-minute freshness window and its next-H1 open was current;
- `MISSED_SIGNAL`: a qualifying setup existed after activation but was discovered too late to count as live;
- `SKIPPED_SIGNAL`: a fresh setup occurred while a forward position was already open;
- `EXIT`: a previously recorded live signal has reached a frozen exit condition.

A `MISSED_SIGNAL` is an operational observation, not a strategy loss, and must never be rewritten into a SIGNAL later.

## Scanner cadence after the first successful run

The scanner needs to run just after each H1 close so a new signal can be captured within the frozen 5-minute limit.

Target Windows schedule:

- every hour;
- approximately minute 01–02 after the hour;
- MT5 terminal running and logged into the research demo;
- network available.

Do not schedule more frequently than necessary. The strategy is H1 closed-candle based.

We will set up the Windows Task Scheduler job only after one manual scanner run is confirmed clean.

## Verification discipline

After operational changes or suspected outages:

```powershell
python scripts\verify_forward_ledger.py
```

The chain must remain `valid: true`.

Do not delete `data/forward.sqlite`, recreate the activation, or manually edit forward records.

## Forward evidence policy

- Primary forward market remains XAUUSD only.
- Rules remain full v0.1 long + short.
- No long-only retrofit.
- No robustness variant selection.
- No historical signal backfill.
- USTEC and US30 remain secondary historical transfer observations, not active forward hypotheses.
- Exness remains R&D-only while G2 is unresolved.
- Historical strength plus a small number of forward trades will not automatically pass G3.

Periodic external ledger-head anchoring remains a follow-up before any public verification claim.
