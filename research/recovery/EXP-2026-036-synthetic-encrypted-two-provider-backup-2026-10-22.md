# EXP-036 — synthetic encrypted two-provider backup + independent restore

**Status: DRAFT / synthetic-only; no cloud or real VPS evidence access; not production deployable.**
Date: 2026-10-22. Repo: `alisufyan-ai7/trading-signal-intelligence`.
Base production GitHub `main=d5a139e87a0ee90d5a70f5aa040220fffa7af82a`. Parent readiness: Issue #67; scoped credential handoff draft PR #68.

## Purpose

Prove the mechanics of authenticated encryption, independently held bytes, receipt checks, and isolated SQLite restore **before** connecting any AWS or Backblaze credentials, touching VPS private source ledgers or making billable requests.

Owner confirmed bucket names and regions (registered in PR #68):
- AWS S3: `vowsig-backup-s3-2026`, region `us-east-1`
- Backblaze B2: `vowsig-backup-b2-2026`, region `us-east-005`, endpoint `https://s3.us-east-005.backblazeb2.com`.

**Absolute owner spend policy: $0.** No upload is authorized by this PR. Both writer identities exist, secrets remain *outside* the VPS in owner-controlled secure storage. No credentials in this code or in GitHub.

## Design and execution exclusions

- **Source gate:** only a `vowsig-b1b2-fixture-*` root containing the exact `.vowsig-synthetic-only` marker, with `captured/<set_id>/forward.sqlite` already captured and verified using the repository's existing `b1b2_synthetic_v0_1.py` logic.
- **SQLite:** read-only integrity + canonical record hash-chain verification. Source path must resolve under synthetic `captured/`, non-symlink, S02 only, at most 1 MiB.
- **Encryption:** maintained Python `cryptography` AES-256-GCM, exact 32-byte key supplied only inside synthetic test; unique CSPRNG 96-bit nonce; authenticated canonical metadata includes `SYNTHETIC_ONLY_NEVER_PRODUCTION`, digest, record count, input byte size, immutable ID. Plaintext never put into fake cloud store.
- **Fake providers:** `MemoryBucket("aws-s3-synthetic")` and distinct `MemoryBucket("b2-synthetic")` only; 1.1 MB max object; content-addressed `pilot/synthetic/v1/<id>/<hash>.aesgcm`, no overwrite. There is **no boto3, S3 client, HTTP, subprocess, network URL, cloud endpoint, CLI or credentials** in this module. Both storage maps exist in-process and disappear after test.
- **Readback:** byte-for-byte hash after *each* in-memory provider write; never claim completed two-provider status on one-provider failure; no destructive partial cleanup.
- **Restore:** authenticated decrypt and digest check **before writing any plaintext**; only into `<synthetic root>/restored/<new restore_id>/forward.sqlite` (no overwrite, never production). Reopen SQLite with existing synthetic validator and recheck chain/count/hash. Wrong key, tag mismatch, tamper, wrong scope and duplicate fail closed.
- **Key custody:** No real key generation/rotation or Windows DPAPI credential installation. TEST-ONLY 32-byte constant in tests. Real recovery keys must be stored away from both VPS and provider accounts in a separate owner-controlled secure vault. AES-GCM key secrecy and nonce uniqueness remain essential.
- **No mutation** of any existing production code, backup prototype, scheduler, hosted snapshot, provider API, private K5 dataset, Exness/Binance data, or source rights record.

## Verification

Offline independent authoring-environment smoke run: **10/10 synthetic tests PASS**, Python 3.13.5, cryptography 46.0.4, pytest 9.0.2. **Qualification: the local test harness substituted a minimal copy of the pre-existing B1 fixture helper API** because the private repo was not clonable in the isolated authoring container. This is a meaningful encryption/failure-path smoke test, **NOT** an exact GitHub dependency integration verification and **NOT** a native Windows PASS. Run exact GitHub test dependencies on the Windows VPS in an *isolated disposable checkout* to verify complete integration.

Review/test modules:
- `src/trading_signal_intelligence/recovery/b3_synthetic_encrypted_offsite_v0_1.py`
- `tests/test_b3_synthetic_encrypted_offsite_v0_1.py`
- `ops/backup/exp036-synthetic-test-requirements-v0.1.txt` (isolated dev venv only)

Native Windows manual gate: create disposable checkout/venv not writing into production; checkout exact HEAD; install the two pinned test dependencies **only into that disposable environment** if permitted; run `python -B -m pytest -q -p no:cacheprovider tests/test_b3_synthetic_encrypted_offsite_v0_1.py tests/test_b1b2_synthetic_v0_1.py`; separately run trusted pinned frozen-dependency impact checker base and head. Do not assume synthetic PASS proves server/network/object-lock/cost/rights/real restore behavior.

## Missing distinct approvals and work

1. Owner review and **separate explicit** GitHub merge approval for this new draft PR.
2. Exact unmodified GitHub B1 helper on native Windows test run.
3. Independent live *synthetic-only* S3/B2 adapter under strict size/request budget, provider object identity, prevention of accidental overwrite, scoped readback identities, and user approval to make even test cloud API calls (hard $0 remains).
4. Actual real S02/other 21 ledger **rights-to-store** classification, encrypted off-VPS transfer approval and audited application SQL-copy verification. `research.sqlite` remains RAW_SOURCE_RIGHTS_HOLD.
5. Future scheduling, retention, append-only audit, independent data recovery and failure-domain testing — none deployed now.

**Operator note:** this PR is NOT permission to upload S02 or any real data; no `git pull` on production before owner release gate.
