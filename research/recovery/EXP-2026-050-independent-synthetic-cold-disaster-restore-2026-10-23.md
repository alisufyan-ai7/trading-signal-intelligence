# EXP050 / P8 — Independent encrypted receipt cold restore, partial-provider failure and incident state

2026-10-23 | Issue #67 | **DRAFT OFFLINE/SYNTHETIC ONLY. NOT REAL PROVIDER I/O. NOT PRODUCTION-READY.**

## Exact baseline and why this stage matters

- Immutable P7/PR #83 exact owner-tested Windows HEAD `443e69e259b512043f80b7151be3b010f8935d8e`: **111 consolidated P1–P7 tests PASS in 47.69s**, seven SDK pins PASS, trusted frozen dependency coverage 113 protected / 20 changed paths PASS, production unchanged, no cloud/real database/credential/package/task/merge. [Issue #67 P7 PASS](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/67#issuecomment-6367170275). Earlier failed attempts and P6 95-pass run remain immutable.
- P5 encrypts exact AWS/B2 `VersionId` references. P6 passes those IDs to one AES-GCM receipt sink with an independent manifest key, but reports `LOCAL_RECEIPT_ONLY`. P7 adds an owner-injected no-overwrite encrypted receipt commit/readback seam and a cold read-only opener. P7 **does not** retrieve and verify original data from the providers. P8 fills the *offline testing* gap by using the opened receipt to restore an independent SQLite copy from each **synthetic** exact-version provider, while handling provider partial failure.

## P8 source and protections

`src/trading_signal_intelligence/recovery/offline_synthetic_cold_disaster_drill_v0_1.py` implements a single complete offline synthetic drill. Scope is deliberately **hard-locked** to the three-record fixture, run ID `release-test-0001`. External/future network-capable reader injection is blocked by requiring **exact types** `SyntheticMemoryEscrowReader` and two independent `SyntheticMemoryVersionReader` objects for AWS/B2. Neither class imports a cloud SDK, accesses credentials, opens sockets or implements network; all ciphertext is explicitly provided in memory from the prior synthetic fixture.

Drill steps:

1. Start with **only** a separate encrypted receipt snapshot, its content hash and run ID, separately supplied manifest/data keys, and two independent fake provider ciphertext readers. No original S02 database, source repo, P6 receipt writer or P7 write identity is supplied.
2. Open P7/P5 authenticated receipt with manifest key, validate exact schema/object SHA/version references and synthetic run record count **BEFORE** any provider fake read.
3. Perform **exactly one synthetic versioned ciphertext read from AWS and one from B2**, each against the authenticated private reference; bounded SHA check, decrypt AES with independently supplied data key, restore to separate no-overwrite scratch directories, run real SQLite `integrity_check` and S02 canonical append-only record-chain verification. No actual AWS/B2 account traffic.
4. Return only safe nonprivate fields: two verified -> `SYNTHETIC_DUAL_PROVIDER_RESTORED`; one verified -> `SYNTHETIC_ONE_PROVIDER_RESTORED_DEGRADED` + `HOLD_AND_INVESTIGATE` (never healthy); both unavailable/invalid -> fixed redacted `OfflineColdDrillRejected` and no retry. Never echo private exact versions, keys, bucket paths, plaintext, provider exceptions. Scratch database files are **synthetic**.
5. Every successful fake drill reports `real_offhost_restore_proven=False`, `live_provider_requests_authorized=False`, `production_resume_authorized=False`. Neither two healthy simulations nor recovery from one fake provider demonstrates real offsite resilience.
6. Negative regression covers both separate restores, AWS/B2 offline/corrupt/missing, both unavailable, wrong independent keys, tampered escrow, wrong encrypted receipt SHA, wrong provider VersionId, reader swap, prohibited callable injection, one-shot no retry and safe public redaction. No merged production/frozen file is modified.

## Incident and release operator planning

The future **real** dual-provider backup operator (not implemented/activated by P8) must be **OFF by default**. A one-provider incident must be recorded as DEGRADED/HOLD even when independent restore succeeds from the other source. Preserve exact provider versions and ciphertext receipts without automatic second PUT, replace, delete, re-upload, or assuming success. Raise a sanitized actionable alert to the human owner; require independent evidence and exact scoped owner reauthorization before proceeding. Both providers fail -> hard STOP; avoid resuming scheduled uploads or normalizing partial backup into dual success. Prevent production overwrite and preserve historical failed evidence.

Hard **$0 spent** guarantee remains; no real AWS/B2 API including HEAD or new resource creation until account-specific billing hard gates. Real S02 to approved regions `us-east-1` and `us-east-005` remains RIGHTS_HOLD pending actual source/processor agreement. Four scoped provider identities held outside VPS; both data and manifest AES keys have separate owner-controlled off-VPS custody; no keys or raw versions in GitHub/chat. B2 HEAD→PUT cannot be counted as atomic exclusive-create without an independently verified backend. An authentic private receipt and locally restored synthetic SQLite database do not establish offhost version retention, bucket privacy, legal rights, data lifecycle, or recoverability after VPS loss.

## Acceptance for draft

One **SHA-pinned Windows VPS disposable checkout** at exact P8 new HEAD, verify three new added files vs exact P7 parent and their Git blobs, all P1–P8 regression tests with existing pinned real boto3/botocore fake in-memory HTTP tests, trusted `e1fb7073100746848bce8ee1ee0b823f5528d14b` frozen checker blob `502d180a91ed5e9c76d967289c30f2637d58fffa` unchanged, production worktree HEAD `d5a139e87a0ee90d5a70f5aa040220fffa7af82a` clean before/after. Do not install packages, access actual providers/credentials or private SQLite rows, create/modify scheduled tasks, change `main`, or merge PRs.

**Next genuine release task after P8 offline proof:** independently audited encrypted receipt *off-VPS persistent backend*, exact AWS/B2 account/rights/billing/identity/retention evidence, controlled VPS-only manual operator with dedicated ACL scratch and ephemeral scoped secrets, and real provider exact-version independent off-host restore with partial-provider incident handling. A dry-run simulation cannot certify those conditions.
