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
