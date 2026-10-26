# S02 backup and disaster-recovery evidence index

## GitHub lineage migration — 2026-10-26

Historical P1–P8 stage PRs #77–84 and 87-direct-commit integration #85 were **closed superseded but not erased**. Their complete frozen commit ancestry is retained by branch `archive/pr85-original-stacked-backup-history-20261024` at `0c16270e4fca9f1f0124acf776ee4d2a0604de83`. The complete **39-file exact source/test blob-equivalent** successor is now [DRAFT PR #87](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/87) based directly on `main`; it is not yet regression-tested/released. All EXP043–059 research notes stay on `main` via preservation merges #86 and #88. For closed-stage restoration and owner authorization boundaries see [PR audit](../../docs/pr-queue-review-2026-10-24.md). These administrative changes do not imply any new cloud backup execution, protected-version deletion or physical automatic GFS pruning.

**Current state (2026-10-24):** [VowSig operational status](../../docs/vowsig-operational-status-2026-10-24.md) — first actual encrypted AWS S3 + Backblaze B2 S02-only backup PASS; daily Interactive Task Scheduler installed and first real task-run independently verified recovery PASS; 30-daily / 8-weekly / 12-monthly GFS **selection** and verified two-provider version inventory PASS; **no cloud deletion/cleanup scheduler installed**.

## Earlier P1–P8 preparatory evidence preserved from original stacked PRs

The original **EXP-2026-043 through EXP-2026-050** research records are now included byte-identically here on `main` through the docs-only preservation change. They document the successive offline S02 capture core, dual-provider signed transport, signed release-evidence gate, pinned boto3 fake transport, encrypted exact-version recovery manifest, private receipt handoff, in-memory escrow and synthetic cold-disaster recovery. **Historic offline tests and intermediate FAIL/HOLDs remain factual, not upgraded retroactively to production PASS.** Their executable implementations and tests are separately staged in the focused code-only review successor; no installed VPS software changes from preserving these notes.

## Read in verification order

| Evidence | What it establishes | Boundary |
|---|---|---|
| [EXP053 first manual real backup](EXP-2026-053-first-real-s02-dual-cloud-backup-pass-2026-10-24.md) | Real one-shot encrypted S02 upload to AWS/B2 and independent dual-provider cold restore PASS, 30 records | One `data/forward.sqlite`; not all research data |
| [EXP054 daily backup protocol](EXP-2026-054-daily-s02-auto-backup-and-retention-2026-10-24.md) | Same-user credential custody, 04:15 local Interactive task, failure latch and no-prune design | Preparation plan; later live acceptance in EXP055 |
| [EXP055 scheduler activation](EXP-2026-055-first-daily-s02-scheduler-activation-pass-2026-10-24.md) | Actual Task Scheduler install and first real task-launched dual-cloud recovery PASS | **Next natural day not yet proven** |
| [EXP056 GFS policy proposal](EXP-2026-056-proposed-gfs-s02-retention-policy-2026-10-24.md) | 30 daily / 8 weekly / 12 monthly, initial baseline and recent recovery pinning, seven-day deletion grace | Design; no delete authority |
| [EXP057 GFS policy implementation](EXP-2026-057-implemented-gfs-retention-planner-2026-10-24.md) | Read-only selector, inventory and opt-in retained cloud restores committed in draft PR #85 | No installed cleanup task |
| [EXP058 AWS version listing permissions](EXP-2026-058-aws-version-inventory-permission-diagnosis-2026-10-24.md) | Original AWS `ListObjectVersions` DENIED and subsequent owner remediation; B2 listings PASS | Existing AWS reader got scoped LIST only; no delete |
| [EXP059 full paired two-provider inventory PASS](EXP-2026-059-gfs-two-cloud-read-only-version-inventory-pass-2026-10-24.md) | Two protected backup IDs, four exact data+manifest object versions in each cloud; zero deletes | Strong read-only audit, not authorization to prune |

Historic EXP029/030, EXP036–052, synthetic/offline gate outputs and earlier STOP/HOLD attempts remain **unchanged immutable evidence**. Do not reclassify them as PASS merely because later versions worked.

### Original protected backup IDs

- First real manual: `backup-8bce80179c524ace8f4a52cb702b3716` — special GFS pin.
- First real scheduled: `backup-83688210120f48fa8dd62491720df132` — currently among newest scheduled protections.

Both recovered from **both** providers; do not copy private object VersionIds, decrypted manifests, access keys or recovery passphrases into Git.

### Where code and operations live

- **Installed recurring runtime:** `C:\ProgramData\VowSig-S02-AutoBackup\current` on Windows VPS, with private history and review latch under its `state` folder. Owner-observed installed source at `b262b66c055659db06b8573392c63615ea92030e`.
- **Pure GFS and read-only audit source (draft only):** `src/trading_signal_intelligence/recovery/s02_gfs_retention_policy_v0_1.py`, `s02_gfs_cloud_inventory_v0_1.py`, `s02_gfs_retained_restore_audit_v0_1.py`, CLI `scripts/vowsig_s02_gfs_retention_preview_v0_1.py`. Owner-observed verified pinned GFS source `07b7f5daa9b3fd6250b55b27c91bbed6c0e44a6d`.
- **Project governance:** [Issue #67](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/67), [draft PR #85](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/85). GitHub `main` was `bc00e87cfaafe03127fde3d1ddda5154801e3d92` and clean live VPS `main` at `d5a139e87a0ee90d5a70f5aa040220fffa7af82a` on owner verification. Reconfirm after this dated note.

### Next not-yet-closed milestones

Second natural daily recurrence; offline/native Windows GFS tests (do not invent PASS); separately approved limited-scope version-aware deletion tool; exact paired manifest/data pruning with seven-day owner-reviewed plan; delivered task failure alerts; billing/retention costs; off-VPS recovery-passphrase custody; extension to other SQLite/research/IP assets. Broker execution remains disabled, and no unrelated scheduled task/production changes are part of these experiments.
