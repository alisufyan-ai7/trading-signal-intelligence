# EXP-2026-027 — B1/B2 Synthetic-Only SQLite Prototype v0.1

**Status: ISOLATED DRAFT / SYNTHETIC FIXTURES ONLY / NO PRODUCTION AUTHORITY**

Date: 2026-10-11. Repository: alisufyan-ai7/trading-signal-intelligence.

## Authority and unchanged anchors

Owner explicitly authorized **B1/B2 SYNTHETIC-ONLY IMPLEMENTATION**, meaning additive code and offline tests on a new isolated draft branch, **no real SQLite reads, private backups, restore, offsite storage, cloud POST, K5 scan, scheduler change, production update or merge**.

- Base: tested PR #51 exact SHA **620ee672f22b57fde8f512b4493dcd0f6f562e08**; the existing PR #51 branch and PASS evidence are not modified.
- Production main remains expected at **47687d8d0e21523e417899a71dddc886ecf25d73**.
- B1/B2 design contract and acceptance matrix: Issue #47, comment https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/47#issuecomment-6106569668.
- Actual VPS B0 metadata record: https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/47#issuecomment-6106527938. The 22 real SQLite files were **not** used in these tests. Twelve were declared, nine were provenance-mapped historical evidence, one (**data/research.sqlite**) remained unclassified and rights-HOLD.
- Historic AI-v1.2 failed-P2 and earlier AI-v1.0 retired/superseded records remain frozen; AI-v1.2.1 frozen registry mismatch stays historical FAIL.

## Additive prototype files

1. src/trading_signal_intelligence/recovery/b1b2_synthetic_v0_1.py — prototype functions, **not a production tool or CLI**. Requires an explicitly named disposable synthetic fixture root, a fixture-root marker, and a synthetic table marker **inside each source SQLite database**. Only flat named fixture files allowed. No external-network/provider interfaces. Writes mock copies and a manifest only inside its own fixture root.
2. tests/test_b1b2_synthetic_v0_1.py — offline synthetic fixtures, WAL/uncommitted writer, corruption and sequence/hash-chain checks, manifest digest, rights HOLD, path/symlink and duplicate names, quota fail closed, missing synthetic marker, no-overwrite, partial/injected cancellation.
3. This design/evidence note. No frozen runtime, activation, producer, cloud or scheduler files changed.

Fixture markers and path checks are guardrails for **intent**, not a security sandbox. Never call prototype functions against real databases. It is not yet hardened for production with NTFS ACLs, anti-alias/hardlink race checks, custody and duration limits, full SQLite schema/ledger parity, key escrow, or offsite recovery.

## Synthetic capture and verifier contract

- B1 demonstration: per-file SQLite online backup API; no plain file copy and **no claim of atomic consistency across two or more DBs**. Each copied fixture has its own capture start/end UTC. Incomplete/failed synthetic output is preserved, never promoted by a verified manifest.
- B2 demonstration: SQLite read-only connection and query_only on the sealed *captured copy*, full PRAGMA integrity_check, synthetic AI/S02 canonical record-hash chain, record counts/head/optional anchor, UTC validation and SHA-256 before/after copy verification.
- The code deliberately **does not construct** the repository's AILedger or ForwardLedger for verification. Their constructors call schema initialization and can write; verifying a captured copy must not do so.
- A deterministic synthetic manifest SHA-256 is computed over a canonical unsigned body **excluding** the manifest_sha256 field. It identifies only local mock verification. The fields external_backup_verified, independent_restore_verified and hosted_snapshot_durability_verified always remain false; cross_database_atomic is false.
- Source databases and fixtures are all fake, locally generated; no SQLite payload or private ledger is committed to GitHub.

## Acceptance boundary

The synthetic tests run on the current isolated host using existing Python and pytest. Any reported PASS belongs to the exact host, invocation, files and resulting draft SHA. **Native Windows/Python 3.12 exact-commit parity remains pending** until a separately owner-approved guarded fixture-only VPS test. A PASS here cannot be carried back to PR #51, actual B1/B2 backup acceptance, RPO/RTO, B3/B4 offsite, B5 restore, B7 hosted hash read-back or K5/public-crypto cutover.

This prototype is not eligible for merging/deployment and has no automatic runnable scheduled entry point. Production release stays **NO-GO**. Before using real files later, obtain separate owner approval specifying source population and research.sqlite rights, isolated scratch location/ACL/quota, allowed timing, file/sidecar behavior, exact source SHA, rollback, and an explicit validation budget.

## Future release-gate tests not yet proved

- Native Windows WAL/SHM behaviors and read-only-source side effects under actual scanner write cadence.
- Verified ledger-chain parity with all real versions, counts, activation/supersession heads and failure evidence.
- Case-insensitive Windows path aliasing, file replacement races, reparse/hardlink defense and Windows durable flush.
- Per-database lock/timeout/size controls under writers, error/recovery persistence, privacy and licensing checks.
- Complete actual B0 corpus (known + unknown), disk space/retention policy, manifest acceptance semantics.
- Independent off-VPS encrypted copies, recovery key protection, restore verification from each provider.
- Hosted exact-byte snapshot acceptance and K5 writer-side interlock (current/delayed crypto HELD).

## Prospective Windows path-safety correction — 2026-10-11

Frozen observation: Original Windows long-path synthetic SQLite backup FAILED at sqlite3.OperationalError (unable to open database file). The identical frozen code at short TEMP path then passed 15/15 on native Windows Python 3.12.10, exact SHA f5d6344245ff6d1475830bd6f56f71a4040b4ad9. This strongly supports a journal-path-length hypothesis but does not uniquely prove causality. Both observations remain immutable.

Prospective correction: the synthetic-only prototype now checks source and destination prospective SQLite -journal path length, rejecting 240 or more characters on Windows before creating the synthetic destination directory. Two added tests cover the boundary and confirm no output staging on overlong simulated-Windows paths. The new SHA has NOT yet been tested on native Windows (expected: 17 tests). No real database backup, source read, production mutation, cloud call or deployment.

## Repository-only classification of data/research.sqlite

The B0 observed file was 198,176,768 bytes, with contents uninspected. Repository source src/trading_signal_intelligence/storage/sqlite.py defines CandleStore with default data/research.sqlite: a normalized research market-candle SQLite store containing source, source_symbol, symbol, timeframe, UTC timestamp, OHLC, volume and spread. scripts/backfill_mt5.py, scripts/backfill_binance.py and scripts/dataset_summary.py all default to this store. Therefore its *code-intended* role is historical raw market candles, **not an AI/S02 append-only event ledger**.

Actual file schema, row data, provenance/source mix, coverage, corruption status and license terms remain UNVERIFIED; no database read was performed. docs/legal-data-rights.md and docs/data-sources.md record owner-confirmed Exness permission for intended derived-signal commercial use on 2026-09-21 (NOT general raw redistribution); Binance research usage is technically selected while formal paid-production rights are still under review. docs/source-status.md retains an older conflicting Exness BLOCKED entry. Preserve the historical documents; do not assume rights to upload raw candles offsite.

Preservation class: RESEARCH_CANDLE_STORE_EXPECTED / REAL_CONTENT_UNVERIFIED / RIGHTS_HOLD_FOR_OFFSITE. Keep file intact; no deletion, exclusion from governed inventory or cloud transfer.

## First bounded B1/B2 real-database trial — PROSPECTIVE DESIGN ONLY

After a NEW explicit owner authorization for real SQLite access and local scratch writes, propose one small controlled SQLite online-backup experiment against a single S02 ledger (candidate data/forward.sqlite, B0 observed 53,248 bytes), not all 22 files and not the research-candle store. Lock one exact production source SHA, one allowed DB path, one isolated short-path private scratch location, restrictive ACL, max 10 MiB staging allocation, finite deadline and single attempt. Verify only the captured copy with full PRAGMA integrity_check, non-initializing read-only S02 hash-chain adapter, copy SHA-256/size/record counts/head, private local manifest, and clean pre/post Git and filesystem safety checks. Any missing datum, unexplained side effect, invalid chain or corrupted copy fails closed. No offsite service, upload, provider keys, restore, producer/scheduler changes, crypto or publication.

The existing marker-gated synthetic prototype is NOT authorized for real files and must not be reused against real data. A real ledger-copy implementation would require separate review, synthetic proof and a fresh exact bounded owner approval before execution. A one-file success would establish only a LOCAL EXPERIMENTAL COPY, not full corpus protection, backup/restore durability, RPO/RTO or public release.

Status: B0 metadata PASS; earlier synthetic short-path native Windows 15 PASS at frozen SHA; path-guard prospective correction awaiting exact-head 17-test parity; B1/B2 real backup NOT EXECUTED; B3–B9/release NO-GO.
