# EXP-2026-013 — S02 Immutable Forward-Test Ledger

**Status:** INFRASTRUCTURE READY — ACTIVATION HASH NEXT  
**Created:** 2026-09-18

## Objective

Create genuinely new S02 evidence after a frozen activation timestamp, without silently reconstructing historical signals as if they had been observed live.

Primary forward hypothesis:

- strategy: S02 Structure Breakout v0.1 unchanged;
- market: XAU/USD / XAUUSD;
- source: Exness MT5 demo for R&D only;
- direction rules: unchanged long + short baseline;
- no selected robustness variant;
- no long-only retrofit.

## Ledger model

The local forward database is event-sourced and append-only.

Each record contains:

- monotonic sequence;
- unique record ID;
- record type;
- entity ID;
- recorded-at UTC;
- effective-at UTC;
- canonical JSON payload;
- previous record SHA-256;
- current record SHA-256.

SQLite triggers reject UPDATE and DELETE on forward records.

## Activation commitment

The ACTIVATION record commits to:

- activation UTC;
- strategy/config identity;
- SHA-256 of canonical S02 v0.1 config JSON;
- SHA-256 of the S02 strategy source file;
- source/canonical symbol;
- freshness limit for live signal recording.

The scanner refuses to run if the current config/source hashes differ from activation.

## Anti-backfill rule

A historical setup discovered after activation is never inserted as a live SIGNAL if it is older than the frozen freshness threshold. It is logged as MISSED_SIGNAL.

Default freshness threshold: **5 minutes after signal close**.

This makes operational gaps visible rather than silently repairing the record after outcomes are partly known.

## Lifecycle

Initial implementation supports:

- ACTIVATION;
- SIGNAL;
- MISSED_SIGNAL;
- SKIPPED_SIGNAL (e.g. an existing open position);
- EXIT.

SIGNAL records include the next-H1 bar open observed from MT5, stop, target, ATR/risk inputs, structure level, expansion ratios, spread proxy, cost proxy, and frozen hashes.

EXIT records use the same conservative stop/target/gap/time-stop semantics as the backtest, evaluated only from bars that are closed by scan time.

## External anchoring limitation

The local SHA-256 chain is tamper-evident if the retained database is preserved, but the database owner could theoretically discard and recreate the whole file.

Therefore:

1. activation record hash must be copied into the durable research audit trail before hourly scans begin;
2. periodic external ledger-head anchoring is a required follow-up before public verification claims.

## Activation sequence

1. pull repository;
2. run pytest;
3. run `python scripts/activate_s02_forward.py` exactly once;
4. report activation/config/code/ledger hashes;
5. record activation hash durably;
6. only then begin hourly scans.

No historical signal may be added to the forward ledger before activation.
