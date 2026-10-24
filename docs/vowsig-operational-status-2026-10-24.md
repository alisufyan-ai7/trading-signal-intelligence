# VowSig — current operating status and verified handoff (2026-10-24)

> **Current operational overlay / read this first.** This document reconciles the owner's exact Windows VPS output and [Issue #67](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/67) against the private repository on 2026-10-24. It **supersedes older statements about the S02 backup implementation** in the 2026-10-08 design and the early-October status files. Earlier gate, product, trading and crypto research records are historical or belong to separate workstreams; nothing here silently authorizes changes to them.

## Trusted scope and sources

- Project: **TradingTop Analysis / VowSig**, private GitHub `alisufyan-ai7/trading-signal-intelligence` ONLY, plus the **current open chat**. Do not borrow external chats, other repositories or personal memory to reconstruct state.
- Current VowSig product website: `https://vowsig.com` (do not infer contemporary hosted health without fresh verification). Product strategy is AI-assisted research/signals with verifiable evidence; broker execution remains disabled under repository governance.
- **Observed on 2026-10-24:** remote GitHub `main` at `bc00e87cfaafe03127fde3d1ddda5154801e3d92`; live Windows VPS production checkout stayed on clean `main` at `d5a139e87a0ee90d5a70f5aa040220fffa7af82a` after owner operations. These are **different refs**, and neither should be silently reset or fast-forwarded. They must be freshly reconciled before later mutations.
- Issue **#67** is the active S02 backup / recovery / GFS workstream; **draft, open, unmerged PR #85** on `implementation/backup-integrated-release-candidate-20261023` holds current code, tests, documentation and prospective GFS review. Never treat the PR branch as installed code by default. Source used for successful first recurring-task installation: `b262b66c055659db06b8573392c63615ea92030e`. Source used in verified real GFS read-only checks: `07b7f5daa9b3fd6250b55b27c91bbed6c0e44a6d`. PR-head advances for documentation do **not** retarget VPS tasks.
- Owner-provided console evidence supports the specific statuses below; no direct Windows/host/provider administration or cloud billing verification occurred from this documentation operation.

## Verification matrix: precise statuses

| Workstream | Last evidence on 2026-10-24 | Current status |
|---|---|---|
| Real *manual* S02 backup | AES-encrypted `data/forward.sqlite`, 30 records, real AWS S3 + B2 upload with independent exact-version SQLite recovery from **each** provider | **PASS**; ID `backup-8bce80179c524ace8f4a52cb702b3716` |
| Daily *automatic* S02 backup | New isolated Task Scheduler entry installed, fifth owner-held vault credential ready, stable Python runtime under ProgramData, task-run first two-cloud backup and independent restore successful | **ACTIVE / initial scheduler invocation PASS**; ID `backup-83688210120f48fa8dd62491720df132` |
| Daily recurrence | Name `VowSig S02 Encrypted Dual Cloud Backup`, Windows `fxut9592472\trader`, 04:15 **VPS local time (UTC+00 on observed result)**, next scheduled run reported `2026-10-25T04:15:15.0000000+00:00` | **Installed**; **second natural daily run not yet verified** |
| Restore resiliency | Both protected IDs independently recovered from both providers via real owner-run retention audit | **PASS**, `verified_backup_count=2` |
| Exact cloud-version listing | AWS reader `s3:ListBucketVersions` IAM permission corrected; all four prefix lists now succeed, two data and two receipt versions/provider, no delete markers | **PASS** |
| Full GFS read-only version inventory | Pinned GFS CLI returned `GFS_DUAL_CLOUD_VERSION_INVENTORY=PASS`; 2 protected IDs; 4 AWS and 4 B2 data+manifest versions paired correctly | **PASS** |
| GFS 30 daily / 8 weekly / 12 monthly | Deterministic, read-only selector and retention preview + opt-in cloud inventory/restore code in **draft PR #85**; baseline special pin + newest two backups | **CODE COMMITTED / local real preview PASS**; physical cleanup **NOT INSTALLED** |
| Actual deletion of expired cloud objects | No deletion IAM principal, no S3/B2 lifecycle purge, no `DeleteObject` executor or pruning schedule | **DISABLED / zero deletions performed** |
| Backup notification, billing alert, object lock, wider research DB coverage | Not established as active by these owner outputs | **PENDING / DO NOT CLAIM LIVE** |
| Production code and established research workflows | All provided backup/GFS console output passed `PRODUCTION_UNCHANGED=PASS`; no GitHub merge or broker/trading action authorized | **UNTOUCHED IN THESE CHECKPOINTS** |

## Backup scope, custody and failure behavior

- Exactly **one** application evidence database is covered by the installed daily backup: `data/forward.sqlite` (**S02 XAU**, online SQLite copy). Do **not** misstate this as backup coverage of all S02 markets, other AI ledgers, Git history, model artifacts, raw MT5/Binance history or a full VPS disaster-recovery image. The broader [durable IP design](vowsig-durable-ip-backup-and-recovery-plan-v0.1.md) remains substantially **not deployed**.
- Cloud destinations are private AWS S3 bucket `vowsig-backup-s3-2026` (us-east-1) and private Backblaze B2 bucket `vowsig-backup-b2-2026` (us-east-005). Data and its separately AES-encrypted recovery manifest are stored in both. Each successful run creates a **fresh backup ID/version**; there is also a private **local encrypted** receipt. These are not public/site data.
- Five fixed Windows Credential Manager Generic targets: the existing four AWS/B2 scoped writer/reader entries and the additional `VowSig.S02.Recovery.Passphrase.v1` / `VowSigS02`. **Never** commit, echo, request, or log actual keys, raw cloud opaque VersionIds, decrypted manifests or recovery passphrases. Owner must keep the recovery phrase independently **off the VPS**. A different passphrase for a future backup would not decrypt earlier ones.
- The scheduled task follows the existing *Interactive* convention: **RDP disconnect is fine as long as the user stays signed in**; full Windows sign-out, or reboot before interactive sign-in, blocks the task. Source runtime: `C:\ProgramData\VowSig-S02-AutoBackup\current`; append-only sanitized history: `C:\ProgramData\VowSig-S02-AutoBackup\state\history.jsonl`.
- On ambiguous upload/recovery failure, `state\operator-review-required.json` latches the next runs before cloud calls. **No blind retry** or automatic deletion. A failed task produces a local status/history; **owner-delivered failure notifications are NOT implemented**.
- Cloud requests, storage and full restores **may incur small charges**. No promise of zero provider costs or provider-billing coverage.

## Retention decision and current boundary

**Selected GFS design:** retain successful independently restored snapshots **daily for the last 30 UTC days**, then up to **one per ISO week for 8 older weeks**, then **one per calendar month for 12 older months**, plus the first real manual success and other explicit owner pins; always preserve the latest two independently verified successful scheduled recoveries.

For the actual October 24 audit: **one successful scheduled entry** in `history.jsonl`, two protected IDs total (manual + scheduled), `eligible_ids=[]`; neither cloud has an expired object eligible for deletion. Both AWS/B2 encrypted data and recovery manifests remain intact. **No version purging is authorized today.**

*Staged in draft PR #85 only*: `src/trading_signal_intelligence/recovery/s02_gfs_retention_policy_v0_1.py` (pure selector); `scripts/vowsig_s02_gfs_retention_preview_v0_1.py` (default local-only preview); `s02_gfs_cloud_inventory_v0_1.py` (opt-in read-only exact-version audit); `s02_gfs_retained_restore_audit_v0_1.py` (opt-in provider cold-restore verifier), plus offline tests. **Native Windows GFS synthetic tests were not separately observed as PASS**; actual two-cloud inventory/restore **were** owner-verified. Keep these distinctions.

*Not staged as a live/delete-capable subsystem*: cloud pruning execution, separate least-privilege delete principal, complete protected manifest+data version deletion procedure, retained cold restores before/after pruning, seven-day plan approval and hold/reconciliation/rollback semantics. Never give the daily backup reader or writer broad deletion powers merely to enable cleanup. No automatic cleanup task currently exists.

## Last immutable evidence and recovery navigation

Read in order:

1. [EXP053 — first real manual two-cloud encrypted backup + independent restore](../research/recovery/EXP-2026-053-first-real-s02-dual-cloud-backup-pass-2026-10-24.md).
2. [EXP054 — daily Task Scheduler implementation, credentials, retention behavior](../research/recovery/EXP-2026-054-daily-s02-auto-backup-and-retention-2026-10-24.md).
3. [EXP055 — first real scheduler-invoked dual-cloud backup + restore PASS](../research/recovery/EXP-2026-055-first-daily-s02-scheduler-activation-pass-2026-10-24.md).
4. [EXP056 — GFS design and deletion safety gates](../research/recovery/EXP-2026-056-proposed-gfs-s02-retention-policy-2026-10-24.md).
5. [EXP057 — implemented selector/inventory/restoration preview and uncompleted delete stage](../research/recovery/EXP-2026-057-implemented-gfs-retention-planner-2026-10-24.md).
6. [EXP058 — AWS reader list-version IAM permission correction](../research/recovery/EXP-2026-058-aws-version-inventory-permission-diagnosis-2026-10-24.md).
7. [EXP059 — real end-to-end two-provider exact version inventory PASS](../research/recovery/EXP-2026-059-gfs-two-cloud-read-only-version-inventory-pass-2026-10-24.md).

Historic synthetic cloud preparations and earlier failed GUI/PowerShell attempts remain preserved; do **not** retrospectively turn FAIL/HOLD into PASS. GitHub Issue #67 and draft PR #85 discussion also contain the full sequence.

## Next actions (requiring new verification or specific owner authorization)

1. **Observe the second natural daily scheduled run** on/after 2026-10-25 04:15 UTC. Inspect `Get-ScheduledTaskInfo`, latest `history.jsonl` entry, no incident latch, and a *new* independently restored backup ID. Do not treat today's initial activation as proof of tomorrow's natural recurrence.
2. Run **targeted offline/native Windows** GFS tests in a SHA-verified *disposable* checkout. Do not rerun the old 153-test backup suite just to check unchanged source; do not touch active ProgramData task.
3. To **activate retention deletion later**, design separate signed/approved exact-version plan after >=7-day grace and an independently protected, narrowly scoped delete actor. Never auto-prune on a first plan or when any version, receipt, period or provider is ambiguous. No normal recovery point reaches the 30-day horizon before late November 2026.
4. Add opt-in **delivered** failure alerts, cloud billing oversight, review of backup scope gaps (other SQLite and repository archive), and possible immutable protected storage with separate account security.
5. Treat unrelated product/AI/crypto issues as separate workstreams. Older October 12 PR #63/EXP034 overlays in this repository require fresh SHA/runtime reconciliation before continuing. Do not infer their current status from this backup-specific handoff.

## Mutation and handoff rules

This is **documentation only**, not consent to modify production, run a cloud backup, merge PR #85, change installed tasks, add IAM deletion rights, prune cloud versions or execute trades. Continue only from the current open chat and this repo. For a fresh session: reconcile remote GitHub `main`, draft PR #85 HEAD, latest Issue #67 evidence, live VPS checkout and last scheduled run **before** suggesting mutations. Never claim future scheduled runs or cleanup were completed without operator output.
