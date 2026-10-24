# EXP-2026-057 — GFS retention implementation: safe local planner and protected milestones

Date: 2026-10-24 | Existing draft PR #85 | Issue #67 | Scope restricted to `alisufyan-ai7/trading-signal-intelligence`.

## Request

Implement the owner-selected recovery-point retention: **30 daily, 8 weekly, 12 monthly**, with protected milestones, for the existing real daily encrypted S02 backup pair (AWS S3 + Backblaze B2). This is a *retention decision engine*; the existing real backup Task Scheduler installation remains untouched.

## Delivered code and exact current boundaries

- `src/trading_signal_intelligence/recovery/s02_gfs_retention_policy_v0_1.py`: pure, deterministic UTC policy selection. Source: bounded sanitized successful scheduled `history.jsonl`. Keeps every successful backup in previous 30 days; for the older 8-week window, latest verified per ISO UTC week (up to 8 weeks); for the preceding 12 calendar months, latest verified per month; adds explicit pinned first-manual backup and the latest two successfully restored scheduled backups. Reports kept IDs and expired candidate IDs, SHA-256 of canonical plan, hold reasons, counts and explicit `cloud_deletion_authorized=false`. It **never** imports boto3 or invokes cloud deletion, encryption, passwords or Windows Task Scheduler. History gaps are reported implicitly by bucket counts; monthly tiers may not yet exist in newly activated systems.
- `scripts/vowsig_s02_gfs_retention_preview_v0_1.py`: read-only operator entrypoint accepting only the sanitized scheduled `history.jsonl` under the exact `VowSig-S02-AutoBackup\state` tree. Rejects symlinks, absent/bad/unbounded history, invalid timestamps, duplicate IDs, unauthenticated SUCCESS claims, and malformed rows. Detects `operator-review-required.json`. Prints proposed GFS plan and `provider_deletions_performed=0`, without credentials/network/file writes.
- `tests/test_s02_gfs_retention_policy_v0_1.py`: offline tests of daily/weekly/monthly selection, ISO calendar boundaries, pin protection, duplicates, invalid records, incident latch, stale history, deterministic plan hash and absent cloud mutation; native Windows acceptance still needs execution in isolated checkout. No claim of actual passed Windows tests until console output is supplied.
- Existing live Task Scheduler: `VowSig S02 Encrypted Dual Cloud Backup`, daily at 04:15 UTC as observed at activation, under Windows `fxut9592472\trader`. Its stable ProgramData runtime is an isolated snapshot installed from `b262b66c055659db06b8573392c63615ea92030e`; **GitHub commits alone DO NOT update it**. Existing daily AWS+B2 backups and independent cold restores are active and must continue unchanged.

## Protected recovery points

- First manual verified backup ID **`backup-8bce80179c524ace8f4a52cb702b3716`** is hard-pinned and MUST never become an automatic candidate.
- The two most recent successful scheduled dual-cloud independent-restored backups remain protected, even if outside the policy window. First real task-backed automatic backup ID was **`backup-83688210120f48fa8dd62491720df132`**.
- Future owner-pinned IDs can be passed to the pure `choose_gfs` policy API, but cannot be supplied as unverified process arguments to the preview CLI. A proper protected inventory is needed before destructive cleanup is possible.
- The plan makes proposed deletions by **backup ID only**. A backup ID alone is NEVER sufficient to delete a cloud object version.

## Crucial capability boundary: safely deleting real old cloud versions is not active

**NOT YET IMPLEMENTED/ACTIVATED:** any destructive S3/B2 `DeleteObject(VersionId)`, standalone pruning task, IAM delete principals, bucket lifecycle policy, or deleting local encrypted receipts. Nothing previously uploaded is removed by this code. The request is fulfilled as a deterministic selection and no-delete preview **phase**, not yet as a fully operating auto-pruner. Do NOT describe cloud pruning as active.

Why that boundary is essential:

1. Each recovery point consists of four separate *versioned* cloud objects (AWS encrypted data+encrypted manifest, B2 encrypted data+encrypted manifest), and optionally the Windows local encrypted receipt. The actual sealed manifest contains data VersionIds, **but the scheduled audit log does not contain encrypted manifest VersionIds**. A correct deletion service must inventory all exact versions using provider-specific read-only listing, validate all six aliases/receipts, reject orphan/unrecorded versions, and restore retained points from both clouds before and after pruning.
2. The four currently enrolled AWS/B2 credentials are writer/reader only by intended role. Granting deletion rights to a daily backup agent or running broad lifecycle policies would substantially weaken ransomware/rollback resilience.
3. There is not yet a month of successful history: first real automatic run was October 24, 2026. **No normal daily backup is beyond 30 days yet**; therefore no ordinary daily object should be purged today even if deletion were supported. Keep the original manual baseline protected indefinitely absent separate owner release.
4. Purging a single manifest but keeping ciphertext, or vice versa, destroys that restore point; cloud versions and B2 S3 API semantics must be independently checked before any DeleteObject is permitted.

## Required next, narrowly scoped acceptance

1. Run offline planner tests in an exact SHA-pinned isolated checkout using the existing stable Python environment (no changes to live task/runtime). Produce the current read-only plan from `C:\ProgramData\VowSig-S02-AutoBackup\state\history.jsonl`. Expected initially: zero expired candidates, hard-pinned baseline, newly scheduled backup(s) kept, no network/deletions.
2. Collect read-only cloud version inventories and original manual pinned backup ID outside the scheduled history. Verify both encrypted data and encrypted manifest copies and intact cold recovery in each provider.
3. Implement a **separate** version-aware, least-privileged cleanup executor requiring an owner-approved SHA-bound plan after >=7 days grace. Dry-run before granting scoped delete capability, never using the daily writer or reader identity for mass deletion. Fail closed on an outage, missed backup, recent incident latch or absent retained month/week proof. Only this explicit later release can delete expired cloud versions.
4. If owner later authorizes automatic pruning, schedule that separate executor in a safe cadence without modifying/interrupting the existing 04:15 daily task. Create alerts for any blocked cleanup. No speculative costs, provider permissions or live install PASS claims.

## Older backups today

**All preserved in AWS and Backblaze.** Each daily backup continues creating a uniquely encrypted new backup plus manifests. GFS selection only proposes which historical backup IDs may eventually be consolidated. Storage and request costs continue until a separately audited deletion release, but the existing S02 dataset is small. No deletion has occurred in this work.

## Evidence and governance

First real manual dual-cloud PASS: EXP-2026-053; first real task-backed scheduler PASS: EXP-2026-055; owner-selected GFS design: EXP-2026-056. These records are immutable. This EXP-057 documents the policy implementation and explicitly *does not* overwrite their results. Draft PR #85 is unmerged; live production checkout and existing tasks are intentionally untouched.


## 2026-10-24 additional code: optional live read-only AWS+B2 exact-version inventory

- `src/trading_signal_intelligence/recovery/s02_gfs_cloud_inventory_v0_1.py`: read-only `list_object_versions` for exact permitted encrypted S02 data/manifest prefixes in the two pinned private buckets, only when caller explicitly provides reader SDK clients. Bounded pagination (100 pages/50K listing entries), strict S02 key parser, version IDs kept in Python memory only, missing/extra backups/partial provider mismatches/nonlatest versions/delete markers/permission denied all HOLD. Output is limited to counts and SHA-256 of publicly safe backup-ID sets, `cloud_deletion_authorized=false`, `provider_deletions_performed=0`. This does not by itself prove cryptographic recovery.
- `tests/test_s02_gfs_cloud_inventory_v0_1.py`: fake-provider read-only inventory tests of complete pair, incomplete/unknown sets, denied listing, duplicate/version invalidity, no uploads/deletes.
- `scripts/vowsig_s02_gfs_retention_preview_v0_1.py` now supports optional `--audit-provider-versions --acknowledge-read-cost I_ACCEPT_READ_ONLY_CLOUD_LISTING_COST`. This explicitly opted-in mode loads the existing **reader** credentials from Windows Credential Manager and may perform billable provider read-only list calls, but it has **no DeleteObject path**, and refuses to authorize cloud deletion even on an inventory match. Default local preview performs **zero cloud API requests**.
- The initial historical backup ID is always explicitly included in the expected cloud inventory alongside scheduled history. Any unrecorded provider object or imperfect B2/AWS version list causes a HOLD instead of omitting it from retention decisions.
- Current Windows Credential Manager **reader** principals may not have ListBucketVersions permissions. A read-only version-audit HOLD is expected until least-privileged list permissions are independently verified. No expansion of IAM granted by this commit.
- Next acceptance is offline targeted native Windows tests and a default local-only preview. Real-version cloud auditing is optional and explicitly consented. Actual deletion/pruning still not live; it requires a separate approved delete identity, verified retained cloud restores, version-aware signed immutable candidate list, >=7-day grace, and owner approval.
