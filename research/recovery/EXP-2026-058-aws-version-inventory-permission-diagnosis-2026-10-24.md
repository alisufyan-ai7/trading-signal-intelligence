# EXP-2026-058 — AWS reader ListBucketVersions permission blocker (read-only fix)

Date: 2026-10-24. Source: owner-provided sanitized Windows VPS output in this same TradingTop Analysis chat. Issue #67 / draft PR #85.

## Read-only diagnostic: exact reported result

```json
{
  "status": "READ_ONLY_VERSION_LIST_DIAGNOSTIC",
  "cloud_deletions_performed": 0,
  "results": [
    {"kind":"DATA", "provider":"AWS_S3", "status":"PERMISSION_DENIED"},
    {"kind":"MANIFEST", "provider":"AWS_S3", "status":"PERMISSION_DENIED"},
    {"kind":"DATA", "provider":"BACKBLAZE_B2", "status":"LIST_SUCCEEDED",
     "versions_on_first_page":2, "truncated":false, "delete_markers":0},
    {"kind":"MANIFEST", "provider":"BACKBLAZE_B2", "status":"LIST_SUCCEEDED",
     "versions_on_first_page":2, "truncated":false, "delete_markers":0}
  ]
}
```

This establishes **AWS S3 IAM reader denied the ListObjectVersions listing operation for BOTH approved data and manifest prefixes**. It does NOT imply the backups are inaccessible for GetObject VersionId: the prior GFS audit had `ALL_SELECTED_RETAINED_COLD_RESTORES_VERIFIED` and `verified_backup_count=2`, confirming successful real restored S02 copies from both AWS and B2. B2 has both expected two data-object versions and two manifest versions and no delete markers. The local GFS policy preview PASS retained both protected IDs with `eligible_ids=[]`; production was unchanged.

## Single least-privileged proposed AWS IAM policy

File: `research/recovery/EXP-2026-058-aws-reader-listbackupversions-least-privilege-policy.json`.

Attach the **identity-based inline policy to the existing AWS reader IAM principal associated with Windows Credential Manager entry `VowSig.S02.AWS.Reader.v1`**, not the AWS writer or B2 keys. Keep its existing GetObject/GetObjectVersion access unchanged. IAM console path: IAM → Users (or relevant credential-owning principal) → Permissions → Add permissions / Create inline policy → JSON. Use policy name `VowSigS02ReaderListVersionsScoped`.

Only allowed action: `s3:ListBucketVersions` on **bucket ARN `arn:aws:s3:::vowsig-backup-s3-2026`**, with `StringEquals` `s3:prefix` restricting requests to the two **exact** prefixes `pilot/vowsig/approved-s02/v1/` and `pilot/vowsig/backup-receipts/v1/`. These precisely match the read-only GFS client call arguments. Do not add `s3:ListBucket` unnecessarily, grant write/delete permissions, alter existing scheduled tasks, rotate/print secrets, or grant whole-bucket list versions rights. If a higher-level explicit deny/SCP or permissions boundary blocks this, the added identity Allow might be insufficient; diagnose separately without broadening permission.

**GitHub does not have AWS IAM account administration access.** The policy is a proposed **owner-executed IAM console change**, not installed by committing it to GitHub. No IAM mutation has occurred in this chat.

## Acceptance after owner applies the AWS reader-only policy

Use a short, exact-source-pinned isolated GFS preview with `--audit-provider-versions --acknowledge-read-cost I_ACCEPT_READ_ONLY_CLOUD_LISTING_COST`, but **do not repeat the retained cold-restores**, since the owner already observed a real two-backup retained cold-restore PASS. Expect `cloud_inventory.status=READ_ONLY_DUAL_PROVIDER_VERSION_INVENTORY_MATCH` with `backup_ids_seen=2` and `aws_object_versions_seen=4`, `b2_object_versions_seen=4`. Still require `provider_deletions_performed=0`, `cloud_deletion_authorized=false`. If AWS still denies, stop; check identity mapping and any explicit deny or conflicting bucket policy before proposing broader rights.

**No physical pruning today:** all backups were created October 24, 2026 and none is older than 30 days. The GFS policy and read-only audit are staged only in PR #85, while the proven 04:15 daily ProgramData task remains ACTIVE, unchanged. A future separate, gated, version-aware cleanup identity and seven-day approval are required for any deletions. The existing baseline manual backup `backup-8bce80179c524ace8f4a52cb702b3716` remains pinned; first scheduled `backup-83688210120f48fa8dd62491720df132` protected as newest.
