# EXP-039 — offline-restricted S3 call-boundary and one-time cloud-pilot readiness

**Date 2026-10-23; PREPARATION ONLY.** PR draft, base GitHub `main=32e3b9fbf9305bbe1f897908bac6a3e3bc0fd54a` (EXP038 PR71 merged and 59 Windows offline tests PASS). Project context limited to this current TradingTop Analysis chat and private repo `alisufyan-ai7/trading-signal-intelligence`. No other repositories, chats, or account memory.

## Owner console confirmations (status evidence, not API verification)

Owner explicitly reported that they manually reviewed AWS and Backblaze cloud console settings **without any API call or changes**:

| Provider | Parameter | Owner-reported status |
|---|---|---|
| AWS S3 bucket `vowsig-backup-s3-2026`, `us-east-1` | Versioning | `Enabled` |
| AWS S3 bucket | Block Public Access | **all four settings enabled** |
| Backblaze B2 bucket `vowsig-backup-b2-2026`, `us-east-005` | Visibility | **Private** |
| AWS | Free-tier eligibility / zero-spend | **zero cost evidenced** per owner's console review |
| B2 | Free-tier eligibility / zero-spend | **zero cost evidenced** per owner's console review |

No billing dashboard data, screenshots, free-tier balances, account credit details or actual provider API replies were given to the assistant. **These statements are owner attestations only, not independently verified provider balances or a $0 guarantee.** A five-operation/request ceiling, 128KiB object cap, Free Tier, budget alert or credit estimate cannot guarantee that an account will never incur charges. If actual out-of-pocket cost cannot be assured, the next real provider step remains on HOLD rather than relaxing the hard $0 policy.

All four independently scoped credentials are also owner-confirmed and privately held OFF the VPS:
- AWS upload identity `vowsig-s3-backup-writer`; reader `vowsig-s3-restore-reader`.
- Backblaze upload identity `vowsig-b2-backup-writer`; reader `vowsig-b2-restore-reader`.
- Reader scope: target bucket, `pilot/` prefix, READ ONLY. Writers: restricted pilot upload; no delete/list/admin. These are **owner-reported permissions**, not API-verified.

## Provider compatibility: public documentation only, not tested against these buckets

1. AWS [S3 adding versioned objects](https://docs.aws.amazon.com/AmazonS3/latest/userguide/AddingObjectstoVersioningEnabledBuckets.html) documents that a PUT into a versioning-enabled bucket receives an object version ID, consistent with B4's required version-specific independent GET.
2. AWS [conditional writes](https://docs.aws.amazon.com/AmazonS3/latest/userguide/conditional-writes.html) documents `If-None-Match: *` atomic no-current-object overwrite protection (not immutable history; existing delete markers can permit writes).
3. Backblaze [S3 PUT](https://www.backblaze.com/apidocs/s3-put-object) illustrates `x-amz-version-id` in the response. [S3 GET](https://www.backblaze.com/apidocs/s3-get-object) documents the `versionId` query and response header; [S3 HEAD](https://www.backblaze.com/apidocs/s3-head-object) is supported. B2 buckets are intrinsically versioned. No conclusion is drawn about this owner's actual keys, prefix rights or endpoints, which still require owner-approved API testing.
4. B2 `IfNoneMatch` support was NOT established, so B4 retains separate read-only HEAD preflight and a unique nonce-bound content-hash key. **B2 HEAD+PUT is non-atomic** and does not prove zero overwrite races.

## EXP039 B5 call boundary: additional defense before any future live driver

Proposed NEW `src/trading_signal_intelligence/recovery/b5_synthetic_s3_call_boundary_v0_1.py` is a pure-Python **credential-free**, **SDK-free**, import-safe, inert wrapper for externally supplied clients. It has NO boto3/botocore/HTTP/session/credential initialization or runnable CLI, and adds no scheduled job or production import.

A future separately approved driver MAY wrap four narrowly scoped boto3-style clients with `guard_pair`, then hand the wrappers to existing B4. The boundary:
- Pins exact provider bucket, key and full encrypted envelope digest, enforces no more than 131072 encrypted bytes, and checks exact allowed kwargs.
- Shares a tiny state machine per writer/reader pair, enforcing AWS **PUT `IfNoneMatch=*` then versioned GET**, Backblaze **HEAD 404 then PUT then versioned GET**. No extra ACL, DELETE, LIST, bucket management, public ACL or malformed file payload may pass.
- Wrong role, prior in-flight or ambiguous upload, missing version receipt, wrong object, second upload, extra retrieval, SDK failure → FAIL CLOSED. Errors are normalized to fixed messages, not credential-bearing provider exceptions. `_Gate.calls` count is logical Python method attempts ONLY.
- Exact existing B4 endpoint, region, SigV4 and no-SDK-retry client configuration check before any allowed method.
- Reader and writer wrapped independently. No automatic retry/cleanup; partial synthetic provider objects may remain after an interrupted future pilot.

**Important limitations:** A Python wrapper is NOT a sandbox. A caller holding the unwrapped SDK client can bypass it, and **one SDK method call does not guarantee one physical HTTP request** (credential retrieval, redirects, SDK retries, signing/transport internals and network behavior may add calls). **A separate real-network driver security review must prove** explicit direct credential injection (no chain/environment/IMDS/account-role fallback), pinned HTTPS endpoint + TLS hostname verification + region, disabled retries/redirects, path/addressing compatibility and actual request-level trace/count against real SDK version. Under no conditions may it install keys onto the production VPS, print them, write `.env`, create a scheduled task, or run without separate explicit owner approval and spending safeguards. No such driver exists in this PR. Nothing in this draft may be interpreted as approval to make a HEAD/PUT/GET against an actual bucket.

## Offline testing and closure protocol

Proposed NEW `tests/test_b5_synthetic_s3_call_boundary_v0_1.py` (11 test functions) uses only EXP038's **locally instantiated** fake AWS/B2 clients and B1/B3 disposable synthetic fixtures. Cases include exact two-provider B4+guard authenticated restore, five fake methods, wrong-role denied, AWS no-HEAD, object prefix/JSON kwargs enforced, no extra ACL/DELETE/LIST, replay/ambiguous receipt poison, B2 HEAD 403 fail-close, 404 then ordered PUT/GET and single-read, invalid client endpoint or envelope refused before fake calls.

**As authored:** no native Windows test result exists yet; DO NOT cite inherited 59/59 EXP038 PASS as B5 PASS. Requirements before merge consideration:
1. Owner runs exact SHA pinned disposable GitHub review of B5 + all EXP038/B4/B3/B1 synthetic test modules in EXISTING ISOLATED Python venv, **never** production `.venv`. CLI offline EXP038 also rechecked and all errors preserved.
2. SHA-pinned trusted frozen-dependency guard compares current GitHub main to exact PR head. Only the 3 new B5 module/test/doc files may appear.
3. Postflight confirms installed production source remains at prior SHA, clean and no real database content, cloud credentials, or tasks were accessed.
4. GitHub-only merge requires separate exact-head owner approval even if all tests pass.

## Next blocked steps after reviewed merge

- A distinct owner-approved, security-reviewed ephemeral operator driver *outside production VPS* would be needed for actual S3 cloud requests. It must accept *four* independently held restricted credentials through a private vault/UI without writing keys in any logs/CLI/history; run only on a trusted transient environment; verify actual SDK's signing, TLS, HTTP call counts and no hidden retries. Confirm `pilot/synthetic/v1/` prefix restriction, provider-specific `VersionId` behavior, B2 HEAD 404 using restricted reader, no mutations outside future approved PUTs, and independent restored SQLite hash.
- Real provider billing eligibility must still be reviewed immediately before actual calls. If a legally and technically enforceable $0 cap is absent, user may choose to remain permanently offline; never incur charge based only on estimates.
- After safe pilot, real data backups **remain separately blocked by data-source licensing/storage rights, privacy, recovery-key custody, retention and human approval**. Existing Exness/market data and `research.sqlite` are NEVER permitted merely because synthetic upload/restore passed.

**Non-negotiable boundary:** this PR creates NO cloud clients, accesses NO credentials, performs NO AWS or Backblaze API requests, incurs no cloud spend, touches no VPS production source, and modifies no scheduled tasks or real databases. EXP036/037/038 historical failed and passing evidence remains immutable.
