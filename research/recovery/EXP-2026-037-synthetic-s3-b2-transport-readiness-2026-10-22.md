# EXP-037 — guarded, bounded, synthetic-only AWS S3 and Backblaze B2 pilot transport

**2026-10-22. Scope: preparatory draft only. No real cloud or VPS calls.**
Parent: GitHub Issue #67, merged synthetic portable-AES-GCM PR #69, separate unmerged credential-readiness PR #68.
This project is strictly isolated to the current TradingTop Analysis chat and private repository `alisufyan-ai7/trading-signal-intelligence`.

## Owner and provider facts (confirmed in this chat)

- AWS S3 existing private backup bucket: `vowsig-backup-s3-2026`, `us-east-1`; SDK client MUST pin `https://s3.us-east-1.amazonaws.com`.
- Backblaze B2 existing private backup bucket: `vowsig-backup-b2-2026`, `us-east-005`; SDK endpoint MUST pin `https://s3.us-east-005.backblazeb2.com`.
- Owner has created scoped write-only AWS IAM and B2 app key, with secrets retained privately outside VPS. Keys were not given to the assistant. $0 **hard owner spending requirement**, not an AWS/B2 provider billing guarantee.
- **No separate read-only credentials are yet confirmed.** Need one separately held AWS `vowsig-s3-restore-reader` IAM user and one B2 `vowsig-b2-restore-reader` app key, both least-privilege and bucket/prefix-scoped. Do not share credentials in GitHub, chat, CLI flags, PowerShell transcript or screenshots.
- Do NOT grant write/delete/ACL/KMS/bucket management to readers. AWS reader policy already drafted at `ops/backup/aws-s3-pilot-restore-readonly-policy-v0.1.json` on PR #68 (still DRAFT; don't merge without separate approval): `s3:GetObject`, `s3:GetObjectVersion` on `arn:aws:s3:::vowsig-backup-s3-2026/pilot/*` plus conditional prefix-only ListBucket. B2 reader app key: **Read Only**, named bucket only, prefix `pilot/`, never master key. AWS writer policy PR #68: `s3:PutObject` to named bucket/prefix only.
- No provider account settings or billing limits were accessed from this implementation. **No cloud operation is authorized yet**. Synthetic-only cloud test still requires distinct owner approval and manual capacity/cost safety assertion prior to any network call. Application source rights / offsite storage HOLD for actual S02/market-data ledgers and `research.sqlite`.

## Implementation

`src/trading_signal_intelligence/recovery/b4_synthetic_s3_pilot_v0_1.py` uses the existing merged B3 AES-256-GCM **portable envelope**. No CLI, no boto3 import, no network client or credential loader, no scheduler reference and no production runtime import path. It accepts **injected, separately scoped** S3-compatible writer/reader clients from a FUTURE approved operator driver.

**Fail-closed before network:**
1. Explicit `network_approved=True` AND exact `OWNER_APPROVED_EXP037_SYNTHETIC_TWO_PROVIDER_PILOT` phrase. Neither value is provided by any installed code. The phrase is an anti-accident interlock, not a substitute for separate owner authorization.
2. Strict disposable B1 synthetic fixture marker/root and `captured/<set_id>/forward.sqlite` only; verify existing B1 SQLite synthetic marker, integrity and chain; authenticate downloaded-envelope-equivalent plaintext locally using provided ephemeral test key and compare **exact** synthetic captured source hash/count **before any client call**.
3. Exactly owner-supplied bucket/region/HTTPS endpoint, AWS SigV4 signature, zero SDK retries (`total_max_attempts=1`) and <=5s connect/<=10s read timeout; reject writer/reader being same client; never use AWS root or Backblaze master key.
4. Encrypted envelope <=**131,072 bytes**; under `pilot/synthetic/v1/<id>/<sha256>.aesgcm` only; the key includes randomized 96-bit AES-GCM nonce through a content hash. No plaintext upload and no public/ACL/bucket mutation.
5. Exactly **at most five S3 API operation attempts**: AWS `PutObject` with atomic `IfNoneMatch='*'`, then version-specific `GetObject` using separate reader. B2 preflight `HeadObject` via separate reader, `PutObject` without unverified B2 IfNoneMatch support, and version-specific `GetObject` via reader. B2 collision protection is **not atomic**: unpredictable content-addressed key+HEAD reduce but do not eliminate overwrite race; do not overclaim immutability. No LIST/DELETE, no multipart, no retries after ambiguous PUT, no automatic cleanup of remote objects. Actual GET response is bounded and digest-checked.
6. Both objects require nonempty version IDs in upload/readback replies; two isolated B3 AES-GCM decrypt + read-only SQLite integrity/record-chain restores into `<synthetic root>/restored/{awsrestore,b2restore}/`. No completed result on provider or restore uncertainty; previous partial cloud objects may remain.
7. Receipts are **nonsecret**: provider, bucket, region, object key/hash, version ID, count. An accepted result is labelled `SYNTHETIC_ONLY_TWO_REMOTE_PROVIDER_RESTORES`, NOT a VowSig real-data backup.

**Financial boundary:** five operations and 128 KiB **constrain exposure but cannot guarantee a $0 invoice** (pricing/credit/subscription and uncapped provider operations remain external). No client construction or call is performed in this PR; no cloud charges from this work. Refuse further action if owner's zero-charge constraint cannot be satisfied. Test claims rely on independent provider receipts only after future approved network pilot; no such receipts exist now.

**Key custody:** for SYNTHETIC ONLY a disposable random 32-byte AES key is permitted; owner-secured real recovery key must be independently recoverable OFF VPS and outside both provider account domains, tested before any real-data backup. Never write key in receipts, logs, environment files or GitHub. No confidential databases or raw Exness/Binance payloads in current scope.

## Offline tests

`tests/test_b4_synthetic_s3_pilot_v0_1.py` includes **15 proposed tests** using in-process fake boto3-style clients with separate AWS/B2 storage and writer/reader roles. Scenarios include default/phrase deny with zero calls, full two-provider independent restore with source hash equality, strict role separation, prohibited real DB path, forged source SHA, wrong crypto key, endpoint/retry policy, shared client, B2 key exists, B2 HEAD 403, ambiguous PUT zero retry, missing version, B2 corrupted GET no all-clear, oversized envelope, and strict five-operation budget.

**Authoring status: implementation prepared, exact integrated Python tests have NOT YET been executed.** No pass is claimed. The historical EXP036 29/29 native Windows PASS and frozen gate at `main` do not substitute for EXP037 testing.

Native Windows owner test (future instruction separately prepared):
- Disposable GitHub checkout at exact EXP037 PR head based on new production **GitHub** `main=3719c79697d05a57a3bf32ce6ab42d9a1b9614eb`.
- Reuse `%TEMP%\vowsig-b3-env-26717b61f7\Scripts\python.exe` **only if present**; it has isolated `cryptography==46.0.4` and pytest 9.1.1, not production `.venv`.
- Set `PYTHONPATH` to disposable `src`; no production package install; `python -B -m pytest -q -p no:cacheprovider tests/test_b4_synthetic_s3_pilot_v0_1.py tests/test_b3_synthetic_encrypted_offsite_v0_1.py tests/test_b1b2_synthetic_v0_1.py`. The new 15 tests + existing 12 B3 + 17 B1 produce **expected 44 tests**, not a claimed result.
- Trusted frozen-dependency impact must run with pinned existing `governance/frozen-dependency-change-impact-gate-20261010` source and exact base/head, expected changed paths only new B4 module, tests, this doc. Do not merge or deploy without independent PASS and separate explicit user approval.

## Future stage after owner approval

- Build/review separately approved local-only operator driver **outside production Python** with boto3 SigV4 fixed endpoint, no retry, `max_pool_connections=1`, `connect_timeout=5`, `read_timeout=10`; key IDs/secrets from **local no-echo input or owner vault**, never passed in CLI argv, logs, environment files, source tree or chat. Keep four identities separate (AWS/B2 writers and readers), and never grant routine writer read/delete.
- Confirm private buckets, applicable versioning, actual provider no-charge eligibility, read-only key capability and *zero-charge* guard with owner before API activity. Provider free quotas are not absolute billing stops.
- Run a **single** explicitly owner-approved synthetic encrypted object to AWS and B2, exactly five API attempts maximum, independent recovered SQLite proof, sanitize evidence to Issue #67. Never repeat uncertain PUT or auto-delete, so held objects count against free-tier quota until owner later manages retention.
- Real S02/21 governed ledgers/research SQLite remain unauthorized for offsite transfer until separate file-class rights and retention/restore approval. Do not add VPS tasks/deploy.
