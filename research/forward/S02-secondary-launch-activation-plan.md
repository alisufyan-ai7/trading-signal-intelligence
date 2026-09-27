# Secondary S02 Forward Activation — USTEC + US30

**Created:** 2026-09-21  
**Status:** ACTIVATED / HASHES ANCHORED — SCHEDULER NEXT

## Purpose

Broaden the Early Access live-signal universe without modifying the already anchored XAUUSD forward protocol.

Secondary markets:

- USTEC / NASDAQ 100;
- US30 / DOW 30.

Both met the frozen historical transfer-support rule, but their final-test margins were small. They must therefore be labelled secondary evidence, not equivalent to the XAU historical lead.

## Isolation rule

Use separate append-only databases:

- `data/forward_ustec.sqlite`;
- `data/forward_us30.sqlite`.

Do not put these secondary signals into `data/forward.sqlite`, because that database is the primary XAU activation chain.

## Pre-activation check

Confirm fresh live bars:

```powershell
python scripts\mt5_recency_probe.py --symbol USTEC --canonical "NASDAQ 100"
python scripts\mt5_recency_probe.py --symbol US30 --canonical "DOW 30"
```

Both H1 and H4 should report `appears_recent: true`.

## Activation commands

Run exactly once per market:

```powershell
python scripts\activate_s02_forward.py --database data\forward_ustec.sqlite --symbol USTEC --canonical "NASDAQ 100" --entity "S02-v0.1:USTEC:SECONDARY"

python scripts\activate_s02_forward.py --database data\forward_us30.sqlite --symbol US30 --canonical "DOW 30" --entity "S02-v0.1:US30:SECONDARY"
```

Preserve both activation outputs before starting scheduled scans.

## Verification

```powershell
python scripts\verify_forward_ledger.py --database data\forward_ustec.sqlite
python scripts\verify_forward_ledger.py --database data\forward_us30.sqlite
```

Each fresh database should show one valid ACTIVATION record.

## Scheduler

Only after both activation hashes are durably recorded:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\install_s02_secondary_forward_task.ps1
```

The secondary task runs at approximately minute 03, after the primary XAU task near minute 02.

## Research discipline

- same S02 v0.1 rules;
- no parameter changes;
- no claim that USTEC/US30 are as strongly validated as XAU;
- any missed signal remains explicit;
- separate activation hashes and ledgers remain independently verifiable.


## Recency gate result — 2026-09-27

The targeted synchronization probe passed for both markets.

USTEC and US30 each reported:

- H1 latest bar `2026-09-25T20:00:00Z`;
- H4 latest bar `2026-09-25T20:00:00Z`;
- quote timestamp `2026-09-25T20:54:59Z`;
- approximately 0.916h lag to quote;
- all three MT5 retrieval methods agreeing;
- H1/H4 `appears_recent = true`.

The prior Sep 18 stale-history state was a terminal synchronization condition and is resolved.

Activation may proceed. Scheduler installation remains blocked until both activation hashes are durably anchored.


## Activations completed and anchored — 2026-09-27

### USTEC / NASDAQ 100

- activated at UTC: `2026-09-27T12:42:13.014356Z`;
- record ID: `7d6305cdaca54bcfa2611fe4edc5499b`;
- activation/head SHA-256: `b0bcb4c952c64c3043512905b803697b491841b99b08b256feb9de82f2cd2780`;
- verification: valid, one ACTIVATION record, no unresolved signals;
- durable anchor: `research/forward/S02-USTEC-v0.1-activation-2026-09-27.md`.

### US30 / DOW 30

- activated at UTC: `2026-09-27T12:42:13.701885Z`;
- record ID: `ad5d6ac943344a0fbfef37d962a09bb9`;
- activation/head SHA-256: `3bc5a922843fea806b8aa4ab3c53a98a2d371982c7479164548b1a1e8fbea581`;
- verification: valid, one ACTIVATION record, no unresolved signals;
- durable anchor: `research/forward/S02-US30-v0.1-activation-2026-09-27.md`.

Both activations use repository HEAD `08cf2282776a4f5f7863f6c16d96b1704dc56bca` and the same frozen S02 v0.1 protocol bundle as the primary XAU collector.

The secondary hourly scheduler may now be installed.
