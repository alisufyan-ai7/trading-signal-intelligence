# Production backup engineering — Stage P1: real S02 offline capture/encryption/restore

2026-10-23 | Issue #67 | **PREPARATION ONLY — NOT CLEARED FOR PRODUCTION RELEASE**

## Objective

Provide a real-data-capable library separate from B1–B6 synthetic experiments. This stage captures exactly one authorized `data/forward.sqlite` through SQLite's online backup API, verifies append-only S02 record hashes, client-side AES-256-GCM seals with canonical authenticated metadata, and independently decrypts, reopens and verifies a recovered SQLite copy from ciphertext and the independently held key.

There is **no CLI, scheduler, SDK import, network client, cloud upload, or executable start-on-production path** in this stage. Owner's request to make the feature ready does not alone establish that current raw/derived evidence can be stored by AWS/B2 or that AWS/B2 storage/API requests guarantee $0. The source-rights requirement remains a BLOCK until scoped evidence exists. Existing prototype B1–B6 remain synthetic-only and unchanged.

### Source gate and boundaries

- Only `data/forward.sqlite`; not `research.sqlite`, not other 20+ ledgers, no repository search or broad globbing.
- Explicit `SourceAuthorization`: approved source/kind, unique two-region pair, nonsecret SHA256 reference to *already reviewed* actual data-rights permission and explicit owner source-access approval. The library verifies only the structure of these attestations; an owner must establish their truth separately.
- Per-object maximum source size 16MiB and 60-second online-capture duration, never-overwrite scratch run IDs, no symlink/reparse/hardlinks, scratch must be outside repository. One SQLite snapshot is transactionally consistent; **no cross-database atomicity**.
- Captured plaintext SQLite resides in operator-chosen private scratch and is NOT secure-erased by deleting a file. Before any real capture, independently validate Windows scratch ACL, disk space, at-rest encryption and handling/retention of failed local copies. No production real-source reads have yet been approved/executed through this code.
- S02 verifier checks SQLite integrity, expected tables/triggers and each ordered canonical previous/current record hash; then checks file identity hasn't changed. It does not establish compliance of all possible third-party data embedded within payloads.
- Sealed envelope includes random 96-bit GCM nonce, 32-byte caller-supplied key, canonical authenticated metadata (schema, classification, source-rights evidence digest, run identity, SHA-256, plaintext length, count). The key MUST remain recoverable outside the VPS and outside both provider accounts. This library never discovers/persists a key, but a future invoking process must have it briefly in RAM.
- Independent recovery takes only ciphertext, separately supplied key and new output scratch, verifies AEAD tag, original SHA, SQLite integrity and complete S02 hash chain. Never restores over an active database. No original source object required.

## Current acceptance

A developer-only offline synthetic-fixture smoke test of an equivalent initial design was run locally (7 tests passed); this is **not** a native Windows test of the exact GitHub commit. Exact version in this PR must run its own suite on the existing Windows VPS in a disposable checkout and pass the frozen dependency impact gate. Only after that may its offline core be reviewed for merge by an explicit exact-head owner decision.

## Next implementation stages (separate narrowly scoped PRs)

P2. Dual-provider injected SDK client transport for a **single** approved sealed S02 artifact: exact endpoint/bucket/region, no SDK implicit credentials/retries, per-request signed wire fence, AWS atomic conditional PUT, B2 HEAD404 unique key, versioned GET readback from each provider, independent authenticated decrypt/SQLite chain validation after each, 5-request maximum, no ambiguous retries. No provider networking until a separate narrowly scoped owner action.

P3. Identity and rights/security: explicitly reviewed IAM roles, AWS and B2 private/versioned buckets and retention, provider/region storage rights, verified $0 billing arrangement or owner-revised budget; key custody off VPS, test restore on another machine, sanitised evidence, deploy/rollback and alert/runbook. **No real cloud call (even HEAD), credential injection, real DB upload or scheduler install** until these controls pass and user separately approves the exact scope.

P4. Expand permissions/restore verifiers per ledger (AI v1.1, v1.2.1, v1.3 and failed/superseded archives) individually; raw market-data `research.sqlite` remains excluded pending source rights and size/cost analysis. Test isolated Windows recovery, failure replay, offsite retention/version protection and alert delivery; only then operate real scheduled backups.

## Important semantics

`Production-ready code` requires tested integration, security gates, data rights, deploy and restore readiness. **This P1 PR by itself is neither production-ready deployment nor approval to store data with providers.** Do not merge P1/P2/P3/P4 automatically. Existing scheduled tasks, production worktree, current Python environments, and PRs #75/#76 must not be changed.
