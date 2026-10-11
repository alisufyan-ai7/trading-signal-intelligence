# EXP-2026-029 — VowSig protected-copy retention and second-failure-domain plan

**Status: DESIGN / REPO EVIDENCE ONLY; NO CLOUD OR VPS ACTION AUTHORIZED**
Date: 2026-10-11. Approved task: proceed with the next milestone after the single-S02 local backup and independent local recovery PASS. Build quickly, test proportionately and protect production.

## 1. Verified starting point

- First privately held real SQLite online-copy trial used only `data/forward.sqlite` (S02). Owner-reported verification: **17 S02 records**, **53,248 bytes**, SHA-256 `1e3a07d7f9b8729b96aee9534a1295e876c06dceca496eb3880b61e5872e502c`; private logical manifest SHA-256 `b19d64c626dd40abe1009eb084012d5aab08d506e35c0cadc18d79c2b4423cf1`.
- Subsequent **independent local** recovery: original copied to a separate ACL-restricted TEMP directory, SHA-256 matched, SQLite integrity and S02 canonical chain **PASS**, 17 records, original backup and manifest unchanged. Full owner-supplied record: PR #53 comment `6107657967` and Issue #47 comment `6107659794`.
- These are two locations **on the same VPS**. Neither copy is protected against host loss, compromised host administrators, VPS deletion or unapproved TEMP cleanup. They are **not durable offsite backups**. Retain existing copies unchanged; no automatic deletion, movement or rotation is authorized.
- Frozen source: PR #53 `2da5ea34d5277776757de9cc3cbffeb5c1f43a4d` (14/14 native Windows synthetic PASS); PR #52 `52b0c9556f4f223060e66f4620e02b27717221ec` (17/17 native Windows synthetic PASS); both DRAFT/UNMERGED. Production `main=47687d8d0e21523e417899a71dddc886ecf25d73` at checkpoint. No PR is authorized to merge.

## 2. Preserve the whole observed population, without inventing completeness

Companion matrix: `research/recovery/vowsig-sqlite-protection-inventory-2026-10-11.csv`.

Owner's B0 **metadata-only** inventory identified **22 SQLite files under the repository `data/` tree**, total **205,860,864 bytes** at observation (196.324 MiB). Exact provenance: Issue #47 comment `6106527938`. B0 did **not** inspect rows, schemas or hashes, measure all-VPS evidence outside `data/`, or establish writer quiescence. These paths are a **known candidate set**, not a final signed comprehensive backup corpus.

| Class | Files | Protection decision |
| --- | ---: | --- |
| Current S02 | 3 | Required, including validated `forward.sqlite` |
| Current AI-v1.1 | 3 | Required; preserve core chain |
| Current AI-v1.2.1 | 3 | Required; historical frozen mismatch never erased |
| Private AI-v1.3 crypto | 3 | Required; K5 private shadow only, public crypto remains HELD |
| Failed AI-v1.2 P2 | 3 | Required; preserve FAIL_CLOSED and its evidence |
| Retired AI-v1.0 | 3 | Required; preserve performance-bearing history |
| Superseded first activation | 3 | Required; preserve supersession history |
| `data/research.sqlite` | 1 | Preserve; raw market-candle store **intended by code**, actual content and offsite rights HOLD |

The 21 known governed ledgers sum to **7,684,096 bytes** by subtraction from B0 metadata (~7.33 MiB). The research store alone is **198,176,768 bytes** (~189 MiB). These are **B0 observations**, not verified SQLite-copy sizes or cloud quota forecasts; database growth and staging needs remain unknown. Exactly **one of the 21 governed ledgers** has a proven local copy + reopened recovery; the others do not. Historical files and failed campaigns must never be silently omitted. A future population freeze must handle any discovered files beyond `data/` separately.

## 3. Destination architecture: existing repo design, staged rollout

Source of architecture: `docs/vowsig-durable-ip-backup-and-recovery-plan-v0.1.md` (already a documentation-only design; no implementation authority). Use a **3-2-1-style strategy**: live VPS data; encrypted/versioned immutable **AWS S3 primary vault in a separate security boundary**; independent **Backblaze B2 secondary account/provider**. Private GitHub preserves code and permitted sanitized hashes/manifests, **never raw SQLite or secrets**. The public Railway sanitized snapshot is not a replacement for the source evidence.

### First incremental protection unit

After separate provider/rights/storage authorization, promote **only the existing, already verified S02 backup artifact** (the 53,248-byte local copy), **not another read of the live ledger**. Steps are conditional design, not a command:

1. Determine applicable Exness/Binance and other source terms for storing encrypted ledger evidence in third-party accounts/regions, plus confidentiality, jurisdiction, and whether records embed raw broker/market data. Owner-confirmed Exness commercial **derived-signal use** (per `docs/legal-data-rights.md`) does **not** automatically prove offsite raw-data/ledger storage rights. Binance commercial terms remain under review. No external transfer while permissions are unclear.
2. Owner selects accounts, geographic region, data retention horizon and acceptable cost; private administrative MFA, independently recoverable credentials and decryption key custody must be established **outside the VPS**. Storage provisioning, credential generation/purchase and transfers need separate owner permission.
3. Package a versioned **non-overwriting** artifact ID and canonical digest-only manifest. Encrypt before transmission if required by the approved data classification; cloud-at-rest encryption is still required. Avoid putting passwords, provider tokens, personal information or raw records in the manifest. Key identification may be logged; key material must not be logged or committed.
4. Upload ciphertext into a private primary bucket with versioning, verified immutable retention / Object Lock where configured and a least-privilege write-only publisher identity. Confirm the provider-returned object version and **download/read back** into a separate isolated scratch to compare the full ciphertext hash; successful HTTP upload alone is not durability proof.
5. Independently replicate the *verified immutable artifact* to a second-provider account; verify its version/size/hash and decrypt/reopen an isolated S02 copy with the same original plaintext SHA, 17 records and chain. Never install into production.
6. After both providers are verified, store a **sanitized identity-only checkpoint** in the repository/PR, excluding real database bytes, private manifests, cloud credentials and object-access URLs. Keep historic local evidence until an explicit retention decision; **do not delete TEMP artifacts just because cloud upload succeeded**.

### Separation, permissions, controls

- Routine VPS identity: upload new immutable versions only; cannot overwrite/delete historic objects or disable retention. Restore/admin identity and MFA separately controlled; independent AWS/B2 keys and recovery channels.
- No public buckets, public links, broad ACLs, or secrets in Git/console logs. Buckets must not be shared with the product's public snapshot service; backup verification must not trigger publish/scheduler/trading.
- Immutable retention policy needs owner and cost/legal review first. Cloud Object Lock does **not** repair a previously bad SQLite copy; verify **before and after** transfer.
- AWS S3 and Backblaze B2 are architectural preferences from the existing repository plan, **not current provisioned or verified services**. No claim about current provider pricing, quotas, Object Lock availability or actual account configuration is made here.

## 4. Retention policy proposal (not activated)

| Tier | Proposed cadence | Proposed minimum retention | Activation dependency |
| --- | --- | --- | --- |
| Short local verified copy | Every 3 hours | 7 days | Whole-corpus B1/B2 + safe storage + explicit scheduler approval |
| Primary S3 versioned backup | Every 3 hours | Per approved version/lock policy | Account, rights, writer and immutable upload test |
| Daily immutable checkpoint | Once daily UTC | 1 year | Costs and retention/legal sign-off |
| Weekly checkpoint | Once weekly | 3 years | Costs and retention/legal sign-off |
| Monthly or governance event | Monthly / every material event | Long-term; event policy defined | Explicit retention policy and lifecycle review |
| Independent B2 | At least daily | Matches approved daily/governance policy | Cross-account transfer, rights, key custody, readback |

Targets inherited from the existing design are **RPO <=3h and RTO <=4h**, only *targets*, not observed performance. No task, encryption service, cloud retention rule, automatic cleanup or alert was created. Governance FAIL/retired/superseded anchors are protected independently of normal pruning rules. Routine Git commits for every snapshot are neither required nor wanted.

## 5. Minimal manifest contract and acceptance (future)

For each approved source: `archive_id`, UTC capture start/end, class/right-to-store decision, exact relative file path, immutable ledger lineage and production commit/tree, schema/verification version, SQLite online-copy method, byte count, `PRAGMA integrity_check`, non-initializing canonical ledger-chain verification, record count/head, plaintext SHA-256, optional ciphertext SHA-256, verified encryption/key-reference identifier (never secret material), per-provider returned immutable object identity/version and readback digest, restore test UTC, and provenance of the owner approval. Use canonical self-excluding manifest SHA-256. Represent pending data as `NOT_TESTED`, `RIGHTS_HOLD`, or `NO_OFFSITE_COPY`; never mark PASS from an expected value or a mock fixture. Cross-ledger atomicity is **FALSE** unless independently proven.

**Acceptance of one externally protected S02** requires: permission to store the content, distinct account failure domain, immutable/encrypted object, full post-upload readback, independent re-opened/decrypted ledger integrity and chain, exact original SHA and manifest match, credential/key recovery outside the VPS, and no source/production mutation. That remains a one-ledger milestone. **Full 21-ledger protection** additionally requires all governed file identities present, independently verified copies and bounded consistency, including failed and superseded evidence. The 22nd research store remains explicit HOLD, not invisible exclusion. Restore-to-production, VPS loss simulation, and whole-system RPO/RTO have separate gates.

## 6. Current hold line and single next decision

**Completed:** B0 metadata inventory, synthetic PR #52/53 tests, one real S02 local SQLite backup, and one independent local copy/reopen verification. **Not completed:** off-VPS storage, account setup, external encrypted backup, independently durable readback, other 20 governed ledger copies, actual raw-candle rights validation, all-VPS inventory completeness, and full disaster recovery.

**Next smallest owner decision:** approve a **provider and rights readiness review ONLY** (which destination account/region, retention price ceiling, encryption/key custody and applicable source rights), with no cloud provisioning, billing, credentials, reads or uploads. Then request a distinct, narrowly scoped authorization for the already verified S02 artifact to be encrypted and uploaded/tested—never infer it from this planning instruction.

All operations in this record are **documentation-only**. Preserve existing TEMP originals, Git branches and immutable failures. No actual backup, new VPS read, cloud setup, transfer, deletion, publication, K5 scan, Task Scheduler action, trading or merge has occurred.
