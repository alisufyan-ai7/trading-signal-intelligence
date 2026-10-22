# EXP-035 — AWS S3 + Backblaze B2 $0 backup credential handoff (PREPARATION ONLY)

**Owner-confirmed 2026-10-22 in current isolated chat:** AWS S3 `vowsig-backup-s3-2026` (`us-east-1`); Backblaze B2 `vowsig-backup-b2-2026` (`us-east-005`, endpoint `https://s3.us-east-005.backblazeb2.com`). Both buckets reported created. **Absolute spending requirement $0**; no credential or backup material may be pasted into chat or GitHub. Use only this repo and current project chat as VowSig context.

## Freeze current production

Production Github source `main=d5a139e87a0ee90d5a70f5aa040220fffa7af82a` is the prior PR #66 successfully installed publisher version. This draft modifies ONLY new nonsecret `ops/backup/` review files on a separate branch; no merge, VPS source update, scheduled task alteration, broker, K5 read, cloud upload, bucket policy change or new cloud account operation was done by preparing these files. The owner must configure provider IAM/app keys in their own web consoles.

## Destination and prefix

| Location | Bucket | Region | API endpoint | Initial prefix |
| --- | --- | --- | --- | --- |
| AWS S3 | `vowsig-backup-s3-2026` | `us-east-1` | SDK default AWS S3 | `pilot/` |
| B2 S3-compatible | `vowsig-backup-b2-2026` | `us-east-005` | `https://s3.us-east-005.backblazeb2.com` | `pilot/` |

Configuration is declarative: `ops/backup/vowsig-offsite-targets-v0.1.json` is **NOT read by installed code** and does **not** itself impose security or spend controls until separately implemented and tested. Both network writers remain DISABLED.

## Owner action 1 — AWS restricted pilot uploader (UI only)

1. Open AWS IAM > Policies > Create policy > JSON. Paste the exact contents of `ops/backup/aws-s3-pilot-write-only-policy-v0.1.json`, name policy `vowsig-s3-pilot-put-only-v1`. This allows `s3:PutObject` **only** on `arn:aws:s3:::vowsig-backup-s3-2026/pilot/*`; it intentionally omits Get, List, Delete, ListAllMyBuckets, PutBucketPolicy, KMS, replication and administrative actions.
2. IAM > Users > Create user **`vowsig-s3-backup-writer`**, with **no AWS Management Console access**, and attach **only** that policy. Do not add users to an Administrator group or attach additional broad policies.
3. Under Security credentials > Create access key (purpose: external workload; follow AWS warnings), generate one programmatic key only if needed. **Save the access key ID and secret access key immediately in a reputable MFA-protected password manager outside the VPS.** Do not screenshot, paste, email or commit either value. Avoid using the AWS root identity.
4. The separate restore/verification read-only role/user will use `ops/backup/aws-s3-pilot-restore-readonly-policy-v0.1.json` after the uploader is tested. Keep restore credentials off the VPS. Do not create AWS KMS keys as part of this pilot; bucket default SSE-S3 plus separate client-side authenticated encryption is the plan. Verify bucket private, Block Public Access, and versioning in the console without changing charged settings.

**Important:** `s3:PutObject` permissions alone do not enforce no overwrite of the same object name, a hard request byte cap or an unconditional billing stop. Immutable, no-overwrite object names and upload byte limits must be enforced by reviewed code, plus versioning/retention where separately configured. A $0 billing preference is not a cloud-provider billing guarantee.

## Owner action 2 — Backblaze bucket-scoped pilot uploader (UI only)

1. B2 Cloud Storage > Application Keys > **Add a New Application Key**. Name: **`vowsig-b2-backup-writer`**.
2. Allow Access to Bucket(s): **`vowsig-backup-b2-2026`** only, **not All**. Type of Access: **Write Only**. Restrict File Name Prefix to **`pilot/`** if available. Keep "Allow List All Bucket Names" off unless the exact chosen client requires S3 List Buckets compatibility; don't give delete or bucket management/admin permissions.
3. Save app key ID and secret **locally in the MFA-protected password manager, outside VPS**. B2 application key ID maps to S3 access key ID, and B2 secret app key maps to S3 secret access key. **Never use the Backblaze master key** in an S3 client; it is not supported for S3-compatible API.
4. A **separate Read Only** B2 app key will be used later for independent restore/readback; never expose that key to routine scheduled writer. Confirm bucket is private and default encryption is enabled, without destructive retention changes.

Official technical docs used to verify B2 capability/prefix/endpoint: https://www.backblaze.com/docs/cloud-storage-application-keys ; https://www.backblaze.com/docs/cloud-storage-map-iam-policies-and-s3-acls-to-backblaze-b2-access-controls ; https://www.backblaze.com/docs/cloud-storage-call-the-s3-compatible-api

## Owner report: nonsecret status ONLY

User replies `AWS IAM policy + writer created: YES/NO`; `B2 Write Only app key scoped to bucket/pilot: YES/NO`; `Both secrets saved privately: YES/NO`; `bucket public access blocked: YES/NO`; `AWS versioning: ON/OFF`; `B2 bucket versioning/retention state: as displayed`. **Do not ask for or include access key IDs, secrets, recovery keys, bucket account IDs, confidential file locations, bank/credit details, or screenshots of credential creation results.**

## Before any real data copy: follow separate gates

1. Inspect source license / PII class and get rights-to-store decision for exact historical S02 artifact. Owner's product backup approval does not override third-party market-data terms. `data/research.sqlite` remains RAW_RIGHTS_HOLD, and 21 governed ledgers are not automatically eligible for third-party transfer. Existing local Oct11 verified S02 object: 53,248 bytes; 17 records; SHA256 `1e3a07d7f9b8729b96aee9534a1295e876c06dceca496eb3880b61e5872e502c`. Do not read source SQLite or alter private K5.
2. Prepare independently reviewed, Python-3.12 compatible, **synthetic-only** client-side authenticated encryption + S3/B2 transport adapters using scoped keys and a unique `pilot/` object path; explicit hard-coded aggregate bytes/request ceilings and no automatic retries on ambiguous writes. No upload is authorized just because the IAM credentials exist.
3. Create a **non-secret** key reference and separately custody authenticated encryption recovery key **off VPS AND independent of both storage accounts**. A DPAPI-at-rest Windows service-user credential store can be prepared later after review; current VPS secrets never appear in GitHub files. Do not use shared/global environment variables, plaintext `.env`, logs, PowerShell transcripts, screenshots or CLI history to pass keys.
4. Owner separately approves synthetic cloud PUT/GET pilot with full pre/post verification (checksum, ciphertext and independent readback) and then separately rights-cleared existing S02 artifact; verify encrypted archive decrypt + SQLite integrity/chain + 17 records. No unapproved full-corpus capture, new scheduler, retention deletion or source change.
5. Hard $0 budget: storage should stay below provider-free buffers. **There is no unconditional guarantee of zero billed usage from IAM policies or upload caps alone**. On absence of provable zero-cost conditions, STOP without transfer. No automation is enabled, no paid resources, no cost-incurring AWS KMS/replication/service was provisioned.

## Reviewer and activation gates

- Files: only new nonsecret `ops/backup/` docs/policies/config; no code files changed.
- Confirm valid JSON, exact two bucket names, correct independent regions/HTTPS endpoint, `s3:PutObject` only for uploader, no global IAM actions, no secret material, no runtime references to pilot config.
- Until owner manual review and explicit merge, PR remains DRAFT. Even merging later does NOT grant VPS deployment or cloud PUT/GET.
