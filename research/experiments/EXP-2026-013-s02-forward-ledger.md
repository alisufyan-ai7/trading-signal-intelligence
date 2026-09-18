# EXP-2026-013 — S02 Immutable Forward-Test Ledger

**Status:** ACTIVATED — HASH ANCHORED; LIVE SCANNING NEXT  
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
- SHA-256 of the live scanner source;
- SHA-256 of the ledger implementation;
- a protocol-bundle SHA-256 over those fingerprints, config hash and freshness limit;
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


## Activation completed — 2026-09-18

The primary XAUUSD forward test was activated after the Windows research host passed all 7 tests.

- activated at UTC: `2026-09-18T13:58:54.786419+00:00`
- repository HEAD at activation: `b309cff26974728ef1f359d443d5927ee16010db`
- activation record hash: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`
- initial ledger head hash: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`
- config SHA-256: `6d347330084e34f31a129892b9a43ba96b88c96ac07c93625a601ffc1ad1bd91`
- strategy SHA-256: `9f5e28817c49e9d206f28961d421d8370ba815b9b5f2d74ae991f68b088e618b`
- scanner SHA-256: `2f29c7104a0fdd03f7072a677fa2d1656dd549c9f57fbe164696407d75f1da19`
- ledger SHA-256: `18eb7f052800f37289248c2381fe5af840469140aea68368dbda882bb3d826f8`
- protocol bundle SHA-256: `484b3de25c6ff6c24de30c5a700f211b98be8534c7b0354fcb2d6219587232cf`
- immediate verification: valid, 1 record, ACTIVATION only.

Durable anchor: `research/forward/S02-XAUUSD-v0.1-activation-2026-09-18.md`.

Live scanning may begin only with the exact frozen fingerprints above.

## First manual live scan — 2026-09-18

- scanned at UTC: `2026-09-18T14:09:12.789641+00:00`;
- actions: none;
- record counts: `ACTIVATION = 1`;
- verification: `valid = true`;
- records: `1`;
- ledger head unchanged: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`;
- unresolved signals: none.

Interpretation: no qualifying S02/XAUUSD signal occurred between activation and the first manual scan. The frozen scanner and fingerprint checks ran successfully without mutating the ledger.

Next operational step: install the hourly Windows scheduled task near minute 02 after each H1 close. The task wrapper also runs ledger verification and writes logs under `data/forward-task-logs/`.


## Windows hourly scheduler installed — 2026-09-18

Task Scheduler registration completed successfully:

- task name: `TradingTop S02 XAU Forward Scan`;
- state: `Ready`;
- next run shown by Windows: `2026-09-18 15:02:02` (machine-local time);
- missed runs: `0`;
- runner: `scripts/run_s02_forward_task.cmd`;
- working directory: repository root;
- last-run sentinel: `1999-11-30`;
- last task result: `267011` (`0x41303`), the Windows Task Scheduler status meaning the task has not yet run.

Interpretation: installation is successful; no scheduled execution has occurred yet. Keep the interactive Windows user logged in and MT5 available for the first scheduled run.

## First scheduled live scan — 2026-09-18

- Windows task last run: `2026-09-18 15:02:02` machine-local;
- Windows task result: `0` (success);
- missed runs: `0`;
- scanner UTC: `2026-09-18T15:02:12.926407+00:00`;
- actions: none;
- ledger verification: valid;
- records: 1 (ACTIVATION only);
- ledger head unchanged: `c901167c0aa2f8d0aff8feb4411664063488b6e67da894279c63bd4fca284115`;
- unresolved signals: none.

The initial task wrapper produced the filename `s02_xau_forward_+.log` because its timestamp-format command was parsed incorrectly by Windows CMD. This was an operational logging-name defect only: the scanner and verifier both exited successfully, and the ledger was unchanged.

The wrapper was corrected after this run to append to `data/forward-task-logs/s02_xau_forward.log`. No frozen strategy, scanner, ledger, config, activation fingerprint or forward record was changed.
