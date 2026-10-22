# EXP-038 — Offline synthetic cloud-pilot operator preflight and owner safety gates

**Date:** 2026-10-23. **Status:** GitHub draft preparation. **NO network calls or expenses authorized.**
**Repository:** `alisufyan-ai7/trading-signal-intelligence` only. Based on PR #70 merged GitHub `main=b342aacba48e03a322fb87a7cc94f37478fe8032`; none of the four production scheduled tasks or installed VPS source is changed.

## Owner-confirmed credentials (NO secret values)

On 2026-10-23 owner independently created and privately stored outside VPS all four restricted identities:

| Provider | Writer (already created) | Reader (newly confirmed) | Target |
|---|---|---|---|
| AWS S3 | `vowsig-s3-backup-writer` | `vowsig-s3-restore-reader` | bucket `vowsig-backup-s3-2026`, region `us-east-1` |
| Backblaze B2 | `vowsig-b2-backup-writer` | `vowsig-b2-restore-reader` | bucket `vowsig-backup-b2-2026`, region `us-east-005`, `https://s3.us-east-005.backblazeb2.com` |

Both read-only identities reported restricted to `pilot/` prefix; owner secured all credential values privately, not in chat, repo or on VPS. Credential *existence and intended permissions* are owner-reported; no provider API calls or policy inspection has yet independently verified actual permissions. Never request access-key IDs or secrets in chat.

## Offline-only operator preflight script

`scripts/exp038_offline_synthetic_pilot.py` (pure local):
- Requires the **literal `--offline-only`** CLI flag; rejects `--execute`, `--cloud`, credential and arbitrary parameters. The source contains **no boto3/botocore/socket/HTTP import, no vault or environment secret reader, no provider client builder**.
- Uses only a disposable `vowsig-b1b2-fixture-*` folder in system TEMP. Writes a newly generated synthetic-only marked two-record S02 SQLite ledger, then uses frozen B1's verified `capture_synthetic_set`, frozen B3's AES-256-GCM authenticated portable envelope, frozen B4's restricted AWS/B2 transport contract, and four **memory-only** fake S3 clients (one writer and one reader for each).
- Ephemeral AES key created via `os.urandom(32)` and never printed or persisted. Disposable plaintext, envelopes, memory objects and test key disappear with the invocation; TEMP fixture removed on normal exit. Source intentionally never opens `data/forward.sqlite`, `research.sqlite` or any existing VPS data.
- Calls B4's `run_two_provider_pilot(network_approved=True, approval_phrase=...)` **ONLY with locally constructed in-memory fake clients**. This is a test harness override for fake clients; not an authorization for actual cloud network activity. This script has no supported cloud execution path.
- Simulates exact **five fake S3 operations**: AWS conditional PUT + versioned GET; B2 HEAD + PUT + versioned GET. Performs **two independent authenticated SQLite restores** against recovered fake bytes and checks outcomes.
- Returns sanitized JSON, e.g. `EXP038_OFFLINE_SYNTHETIC_PREFLIGHT_PASS` with `remote_network_requests: 0`, `actual_provider_calls: 0`, `cloud_pilot_authorized: false`. No credentials, secret keys, object payload or private file paths are printed.
- Regression tests `tests/test_exp038_offline_synthetic_pilot.py` check offline execution, CLI denial, in-memory permissions, overwrite exclusion, cleanup and no network/secret modules.

**No acceptance assertion has yet been made from native Windows test output.** Previous PR #70 offline 44 tests passed, but current EXP038 script must be independently run and pinned on Windows and screened through the trusted frozen dependency checker before becoming merge eligible.

## Cost, bucket, and provider-compatibility gates — read-only manual checks ONLY

**These are required prior to ANY separately approved real cloud synthetic pilot, even if offline tests pass. Do not change AWS/B2 settings as part of this step.** Owner's unconditional spending rule is **$0**. A maximum of 5 API operations and 128 KiB ciphertext cap CANNOT prove a $0 invoice. If provider free-tier/credits and current actual usage cannot prove no charge, remain HOLD and use memory-only simulation.

1. **AWS S3** console → Buckets → `vowsig-backup-s3-2026` → Properties → **Bucket Versioning**: record only `Enabled`, `Suspended`, or `Disabled`. The EXP037 adapter *requires* a nonempty version ID in PUT/GetObject; if AWS versioning is disabled/suspended the live pilot is **HOLD**. Owner can approve a separate change only after cost review; do not enable versioning automatically. S3 versioning may increase retained stored objects and cost.
2. AWS bucket → **Permissions → Block Public Access**: confirm **all four block-public-access settings enabled**, bucket not public. Preserve bucket's private policy; no changes.
3. **AWS Billing and Cost Management** → Free Tier / current usage (console, owner-side only): confirm account eligibility, any remaining promotional credits, request/storage allowances and total projected out-of-pocket **exactly $0**. Do not assume Free Tier is available or a budget alarm is a spending cap.
4. **Backblaze B2** console → Buckets → `vowsig-backup-b2-2026`: record bucket visibility **Private**, versioning/file-version history settings as displayed, any lifecycle/retention rules and SSE settings as displayed; **do not change**. B2 is versioned by default, but exact SDK `PutObject.VersionId` and version-targeted `GetObject` still await an authorized network pilot. B2 partial pilot uploads may persist without a delete-capable identity.
5. Backblaze **Billing / usage** console: confirm remaining account free storage + transactions/egress allowances for **the actual billing day**, and projected charge $0. Do not enable billable features or create new buckets/keys.
6. **B2 read-only app key**: preflight confirms scoped bucket `vowsig-backup-b2-2026`, filename prefix `pilot/`, access `Read Only`. Note provider documentation: S3-compatible SDK tools *sometimes* require `listAllBucketNames` for automatic ListBuckets; **our pilot makes no ListBuckets call**, so do not broaden reader permissions based on speculation. If a real SDK requires it, fail closed and review least-privilege alternative, never silently widen.
7. **AWS IAM** reader should have only `s3:GetObject`, `s3:GetObjectVersion` on `arn:aws:s3:::vowsig-backup-s3-2026/pilot/*`, optionally restricted `s3:ListBucket` conditioned on prefix `pilot/` as in original draft PR #68; no write/delete or admin. Writer remains `s3:PutObject` under `pilot/*`. **Do not install any key on production VPS.**
8. **Driver missing:** PR #70 merged B4 accepts injected clients but includes **no SDK client creator or credential loader**. This EXP038 contains only offline fake clients. A separate draft/review of a one-shot, interactive, no-log, secret-safe actual boto3 driver is REQUIRED, with distinct user approval *before* any actual provider API calls.
9. **Real-data hold:** Exness/third-party/raw historical market data, customer data, `data/research.sqlite`, real `forward.sqlite`, and existing AI shadow ledgers are strictly excluded. Actual object storage rights and retention classifications still pending; owner’s consent to synthetic pilot is not permission to upload real data.

## Reproduction and approval checklist

**Operator test after PR creation:** disposable GitHub checkout at exact PR head, **not** live `main`. Reuse prior isolated test environment only if still present (`%TEMP%\vowsig-b3-env-26717b61f7\Scripts\python.exe`). Run:

```powershell
$env:PYTHONPATH = '<DISPOSABLE_PR_CHECKOUT>\src'
& '<ISOLATED_PYTHON>' -B scripts\exp038_offline_synthetic_pilot.py --offline-only
& '<ISOLATED_PYTHON>' -B -m pytest -q -p no:cacheprovider tests\test_exp038_offline_synthetic_pilot.py tests\test_b4_synthetic_s3_pilot_v0_1.py tests\test_b3_synthetic_encrypted_offsite_v0_1.py tests\test_b1b2_synthetic_v0_1.py
```

Expected result is the offline JSON contract (two fake restores and zero external calls) and all tests passing; prior suites include 44 tests plus new test cases, actual count must come from stdout. Rerun trusted frozen-dependency impact checker with pinned existing governance SHA and `main→PR` exact diff; review any non-test runtime dependency or source scope. No merge unless explicit owner GitHub-only approval after evidence. No actual cloud calls until distinct approval and complete $0 spending proof. Never presume "credentials created" means tested or that deleting objects is free/authorized.

## Official external compatibility notes used in design

- AWS conditional overwrite prevention: https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html
- AWS S3 version ID semantics: https://docs.aws.amazon.com/AmazonS3/latest/userguide/versioning-workflows.html
- Backblaze B2 S3-compatible app-key restrictions (noting S3 ListBuckets mapping): https://www.backblaze.com/docs/cloud-storage-s3-compatible-app-keys
- Backblaze B2 S3-compatible API versioning: https://www.backblaze.com/apidocs/introduction-to-the-s3-compatible-api
- B2 app key name/bucket/prefix restrictions: https://www.backblaze.com/docs/cloud-storage-application-keys

**Boundary:** EXP038 establishes isolated *offline simulated readiness* only, not actual offsite backup, connectivity, no-charge guarantee, or cloud recovery. Do not claim real backup is protected.
