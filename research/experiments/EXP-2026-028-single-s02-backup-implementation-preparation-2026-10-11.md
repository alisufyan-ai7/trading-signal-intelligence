# EXP-2026-028 — One-ledger S02 recovery implementation preparation

**Status: DRAFT / CODE PREPARATION ONLY / NO REAL DATA TOUCHED**
Date: 2026-10-11. Owner approval: `APPROVE B1/B2 REAL-LEDGER BACKUP IMPLEMENTATION PREPARATION ONLY`.

## Scope and tested ancestry

- Separate isolated branch, stacked on PR #52 exact previously tested `52b0c9556f4f223060e66f4620e02b27717221ec`. PR #52's native Windows 17/17 PASS is scoped to that frozen commit and does not transfer to EXP-028.
- Production main was `47687d8d0e21523e417899a71dddc886ecf25d73`; PR #51 was `620ee672f22b57fde8f512b4493dcd0f6f562e08`. Neither branch nor scheduler or VPS was changed by this work.
- Only two new Python files and this preparation note. No CLI, scheduled task, runtime integration, workflow or publisher modification.

## Prototype

`src/trading_signal_intelligence/recovery/b1b2_single_s02_local_trial_v0_1.py` has a callable future one-file online-backup primitive and a pure sealed-copy verifier. There is deliberately **no executable production entry point**. By default the capture function rejects access unless a separate call explicitly asserts permission; the Python boolean is **not an authorization mechanism** and does not grant permission to use any real private file. No function was invoked against production during this preparation.

Boundaries for a separately approved future first trial:

- Exactly `repo_root/data/forward.sqlite` (S02). Never discover directories or batch the 22 files. No `research.sqlite`, AI market expansion or raw candle database.
- Require source to be a regular non-symlink/non-hardlink SQLite file, 10 MiB maximum; reject WAL header or existing `-wal`, `-shm`, `-journal` source sidecars before SQLite open. Conservatively excludes active/WAL-mode sources; no attempt to checkpoint or change journal mode.
- Create a new immutable trial directory in a separately named, non-repository local scratch parent; no overwrites. Enforce Windows journal-path <240 chars, copy cap 10 MiB, backup callback deadline 30 seconds. Stop and preserve incomplete output on any error; never label a failed attempt verified.
- SQLite online backup API, not file copying. Source opened `mode=ro` and `PRAGMA query_only=ON`; destination opened separately and closed. No source schema initialization.
- Seal copied SQLite before checking `PRAGMA integrity_check`, `forward_records` required columns and append-only trigger names, record chronology fields, canonical hash-chain, record counts/head and full copy SHA-256. No `ForwardLedger.__init__` in the real verifier.
- Write a private, non-self-referential SHA-256 manifest only after success. `PRIVATE_LOCAL_EXPERIMENTAL_COPY_ONLY`; no claims of cross-DB atomicity, offsite storage, restoration, real writer quietness or publisher cutover. SHA of Git source revision is supplied by future guarded caller; its identity must be externally checked, as this library does not query Git.
- Source-file sidecar absence is a point-in-time check, not a proof a producer will stay stopped. Any actual execution plan must first independently confirm safe source access, writer/session state, ACL, privacy and rights; do not assume SQLite `mode=ro` alone is sufficient for a busy WAL database.

## Offline-only tests

`tests/test_b1b2_single_s02_local_trial_v0_1.py` contains 14 tests using `ForwardLedger` **only to generate fake SQLite files inside temporary mock repositories**. Covers explicit default denial, sealed-copy chain/integrity and manifest, no-overwrite, non-initializing copy verifier, tampering, missing triggers, WAL/sidecar hold, research-store rejection, in-repository destination rejection, size budget, malformed SHA/ID, empty ledger and synthetic source drift during copy verification. **No private VPS DB or offsite source used.** Tests are authored but not yet run on the native Windows VPS at this new exact commit. Do not claim PASS based solely on prior PR #52 tests.

## Repository-only research-store classification

Existing `data/research.sqlite` is the expected `CandleStore` raw market-bars store (MT5/Binance backfill defaults) according to current repository code. Its **actual 198,176,768-byte VPS contents and source mix remain uninspected**; raw data transfer rights and Binance production rights remain under review. This trial deliberately excludes it.

## Release and operational gates

**No authorization yet** for opening/hashing/querying a real SQLite file, touching source sidecars, creating a backup on VPS, recovering/restoring, offsite storage, network/cloud, Task Scheduler, K5 crypto scan, publisher cutover or merging this PR. Historical failures stay historical. PRs require owner's explicit per-merge decision and mandatory manual dependency verification.

Next: review the exact additive draft and perform one isolated synthetic-fixture test at the new SHA, then propose an owner-scoped one-file real-data execution command **only after separate explicit permission**. Keep work proportionate; don't run repeated safety-script campaigns. Even a successful one-ledger trial will not close B3–B9/full recovery.

An additional fail-closed requirement rejects a source whose size/mtime changes or whose SQLite sidecars appear between preflight and manifest promotion. This is not a substitute for validating that the real source writer is quiescent before an authorized trial.
