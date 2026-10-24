# EXP-2026-059 — GFS exact cloud-version inventory: first real AWS + B2 PASS

Date: 2026-10-24 | Owner-supplied read-only PowerShell console | Issue #67 / existing DRAFT PR #85.

## Immutable evidence and result

**GFS_READ_ONLY_DUAL_PROVIDER_VERSION_INVENTORY = PASS.** After narrowly scoping `s3:ListBucketVersions` to the *AWS reader* IAM principal, the user reran the already-verified source at exact candidate `07b7f5daa9b3fd6250b55b27c91bbed6c0e44a6d` (reused clean disposable VPS checkout, **not production**). Output:

```text
GFS_DUAL_CLOUD_VERSION_INVENTORY=PASS
PROTECTED_BACKUPS=2
AWS_OBJECT_VERSIONS=4
B2_OBJECT_VERSIONS=4
CLOUD_DELETIONS_PERFORMED=0
```

The SHA-pinned CLI's PASS condition explicitly required:
- `cloud_inventory.status == READ_ONLY_DUAL_PROVIDER_VERSION_INVENTORY_MATCH` (exact matching manifest/data backup-ID topology in AWS and B2);
- `backup_ids_seen == 2`, `aws_object_versions_seen == 4`, `b2_object_versions_seen == 4`;
- `cloud_deletion_authorized == false`;
- `provider_deletions_performed == 0`.

This is stronger than the prior four raw listing calls: it establishes correct per-backup data/receipt pairing and verified listing topology across BOTH providers under current inventory implementation. It does **NOT** authorize deletion, prove 30-day aging behavior against real aged objects or establish an immutable post-approval deletion plan.

Earlier distinct owner's test already reported `ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED`, `verified_backup_count=2` using the same candidate; it independently rehydrated both protected recovery IDs from both providers. That cold-restore test was **NOT rerun** in this latest four-line command (do not invent additional restores).

## Protected recovery points and state

- First real manual AWS+B2 AES-encrypted S02 backup ID `backup-8bce80179c524ace8f4a52cb702b3716`, special pinned.
- First real scheduled AWS+B2 AES-encrypted S02 backup ID `backup-83688210120f48fa8dd62491720df132`, current newest protected.
- First scheduled backup and dual restore success in EXP055, immutable.
- Existing production `main` Windows VPS checkout and `VowSig S02 Encrypted Dual Cloud Backup` (daily 04:15 UTC observed) remain unchanged; no source merge or task retarget authorized.
- At Oct 24, there are two known successful backups and no scheduled backup older than 30 days: local policy preview `history_verified=1`, `daily=1`, `eligible_ids=[]`, `protected_ids` includes both. No historic candidate should be purged now.

## Remaining gap: future actual expiration

The GFS selection policy (30 daily, up to 8 earlier weekly, 12 monthly plus protected milestones), listing inventory and read-only independent cold-restore gate are **STAGED in draft PR #85**. Native Windows offline targeted GFS tests have not yet been supplied; this successful real data-path inventory and restore is separate evidence.

**NO automatic pruning or DeleteObject is installed or active.** Physical version-aware deletion, if approved in a future prospective release, requires independently scoped delete authority (not existing daily backup reader/writer keys), exact versions for AWS and B2 encrypted data+recovery receipts, a pinned candidate hash, retained-point restore before and after, explicit owner approval and >=7-day grace, fail-closed outage/incident handling and immutable audit records. Avoid granting an app backup task the power to erase both cloud histories. No cloud lifecycle purges or IAM delete permissions have been changed.

## Milestone closure

- AWS reader permission blockage: FIXED, verified real four-prefix calls.
- Exact 2-provider version inventory: **CLOSED PASS**.
- Read-only retained restoration: **CLOSED PASS from prior owner output**.
- Real automatic GFS expiration/deletion: **PENDING, DISABLED**.
- All cloud data versions/receipts unchanged and preserved.

Credentials, exact opaque VersionIds, decrypted data keys and passphrases are **not** saved in this file or shared in chat.
