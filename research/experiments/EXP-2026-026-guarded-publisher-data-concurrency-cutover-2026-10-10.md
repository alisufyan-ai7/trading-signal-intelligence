# EXP-2026-026 — Guarded Publisher Data Preservation, K5 Concurrency and Cutover Safety v0.3

**Status: PREPARATION ONLY / DRAFT UNMERGED / VPS TESTS PENDING / NO RELEASE AUTHORITY.**
Date: 2026-10-10. Repository: `alisufyan-ai7/trading-signal-intelligence`. No other repo/project context used.

## 1. Authority and exact lineage

Owner's instruction: **"proceed with Recommended next priority"** after choosing mandatory **manual pre-merge verification**, leaving current private GitHub plan unchanged. Work is limited to additional design, isolated draft source, mock/offline tests and documentation, **no** VPS execution, scheduler changes, private ledger writes, manual K5 scan, data backfill, cloud POST, rollout, merge or public crypto actionable exposure. Full output of every test must be supplied before claiming PASS.

Review branch `research/guarded-publisher-safety-v0-3-20261010` starts at exact reviewed PR #49 head `c3e2ae4276f58bb338b2d97a36908a2ae2b01689`. PR #49 is stacked on PR #48 `3cc0384ee21e66ce0e93bcc4d6a6e855ec21d34d` and PR #46 `13f10339df1410bbbe075371b52b34901ebd121b`. Production `main` was previously reconciled to `47687d8d0e21523e417899a71dddc886ecf25d73`, **not** altered.

Previously accepted evidence: PR #48 84 native Windows tests PASS at its own exact SHA, PR #49 117 native Windows tests PASS at `c3e2ae4...`, read-only actual-VPS registry compatibility PASS (preserves original 34-artifact verification FAIL on one historic instrument registry hash; 33 other artifacts valid; only ETHUSDT/SOLUSDT prospective additions accepted). Separate PR #50 governance guard 21 native offline PASS at `e1fb707...`, **not merged or GitHub-enforced**. Owner requires manual SHA-pinned checks and explicit per-PR merge approval.

## 2. Two release-blocking findings confirmed in code

### K5 final check -> HTTP POST time-of-check/time-of-use (TOCTOU)

`scripts/guarded_product_publish_v0_1.py` before v0.3 checked K5 `Ready`, task result `0`, age, cryptographic ledger-row head fingerprints before/after full snapshot generation, and K5 state after export. The HTTP POST occurs *after* these checks and lasts up to 60 seconds. **There is no writer-side mutex in the frozen AI-v1.3 scanner** which the publisher also holds through the entire POST. A new K5 writer could begin after the final check. A Task Scheduler `Ready`/last result `0` observation is not a hard concurrency barrier. Calling the current crypto snapshot current under that race is not justified.

**Preparation-only safety containment:** v0.3 review branch sets `CRYPTO_WRITER_INTERLOCK_READY = False` and `require_crypto_writer_interlock` intentionally ALWAYS raises until a *separate, prospective, verified writer-side shared lock protocol* is installed and approved. The publisher's prepared code will therefore generate only the independent fresh core+expansion public programs. It neither probes K5 nor reads its BTC/ETH/SOL ledgers nor imports prior crypto as delayed under default mode. This prevents silence or false freshness without blocking legitimate base lineage reporting. The existing future-only 3-program path remains review/test-only; toggling the flag to `True` **does not permit crypto publication**. Do not call this a production cutover or a permanently solved crypto concurrency problem.

For crypto research aggregates later: preregister a K5-writer and publisher shared inter-process lock, with lock identity, acquisition ordering, bounded timeout, crash release, and coverage beginning BEFORE ledger writes and ending AFTER publish commit/host acceptance. Need avoid holding writer lock across blocking cloud request if it can cause missed cycles; alternative immutable per-cycle view with writer-generated sealed manifest/version and exact cloud acceptance semantics can be designed and proved. Both require explicit prospective frozen-source governance and native Windows fault injection. Never change K5 frozen source casually.

### Local history is NOT durable backup

Current guarded publisher writes a uniquely SHA-256-addressed candidate archive using exclusive create + file fsync before POST; appends a separate `.accepted` receipt after the HTTP push client reports success; atomically replaces `data/public_snapshot.json` afterward. The archive is **on the same VPS disk**, susceptible to host loss; file fsync alone is not a cross-device durable transaction, and Windows directory metadata/rename persistence remains unproved. A client POST success is not an independent read-back proof of hosted persistence; receipt failure after cloud acceptance creates divergent states; a timeout may occur after cloud accepted but before client receives confirmation. An unaccepted candidate cannot be reused as accepted. No automated recovery/retention/quota/replication is established.

**Preparation-only audit:** `scripts/audit_guarded_snapshot_history_v0_3.py` reads only local sanitized derived snapshot archives and receipts, checks SHA names vs raw bytes, timestamp consistency, receipt integrity, reject corrupt/orphan/symlink/unexpected entries, reports accepted vs pending and free disk bytes. It **always reports** `external_backup_verified=False` and `hosted_snapshot_durability_verified=False`; it never uses the contents or existence of `public_snapshot.json` to infer a cloud POST happened. It performs no write, deletion, restore or network operation. There is no retention auto-pruning. A local archive PASS is NOT a release-pass backup.

Consult existing `docs/vowsig-durable-ip-backup-and-recovery-plan-v0.1.md` (status: documentation design only): private live SQLite ledgers are outside Git; recommended independent encrypted offsite AWS S3 Object Lock + Backblaze B2 copies plus independently verified restores. This task **does not purchase, provision, connect, credentialize, restore or simulate production backup**. Existing source evidence, historical failed/superseded ledgers, crypto and S02 databases must remain in scope. No raw private data in GitHub, website snapshot or public issue.

## 3. Recovery contract / architecture, before future cutover

Explicit classes requiring independent policy:
1. **Private SQLite source of truth:** current and retired S02, AI-v1.1, AI-v1.2.1, AI-v1.3 (BTCUSDT/ETHUSDT/SOLUSDT) and prior failed/superseded evidence; consistent SQLite online backup snapshot semantics, no copying of live SQLite pages with unsafe file-copy assumptions; encrypted offsite replication and integrity + test restore. Owner approval required before touching databases, backup services, credentials, or offsite destinations.
2. **Publication artifacts:** `data/public_snapshot.json`, all guarded history candidates and accepted receipts, cloud hosted `/data/public_snapshot.json`, and privacy-safe metadata/hashes. Each requires explicit copy/manifest, remote provider receipt and read-back hash validation. Host loss can affect cloud and VPS separately.
3. **Code and governance:** `main` and all preregistration/activation/failure anchors, source blobs and repository history; independent Git bundle/offsite archive as already planned, never overwrite frozen anchors.
4. **Local disk capacity:** preflight disk-free budget with reserve for next export + append-only archive growth + SQLite growth. Exact forecast and retention plan to be approved; arbitrary archive deletion is forbidden. Fail closed on low disk rather than purging accepted history.
5. **Disagreement states:** (a) staged candidate only: unaccepted, never reuse; (b) POST succeeded but receipt missing: indeterminate local acceptance, check hosted exact digest independently, never fabricate receipt; (c) accepted receipt but local snapshot replace failed: verified acceptance only if independent hosted read-back matches, recover via independently authorized steps; (d) corrupted receipt/archive: quarantine logically, preserve bytes, do not edit or discard; (e) hosted rollback/redeploy: last known good must be identified cryptographically and restored only with explicit owner approval.

No RPO/RTO, retention days, storage quota, backup prices, S3/B2 setup, or cloud credentials have yet been approved. **No false zero-loss guarantee.**

## 4. Cutover order (PLAN ONLY; NO ACTION COMMANDS)

**HOLD prerequisites**:
- All stacked PRs #46/#48/#49 and this successor code independently exact-SHA verified and authorized through owner-prescribed manual frozen-dependency checker, with explicit owner per-PR, per-SHA merge authority. PR #50 remains separate draft; no implicit bypass.
- Selected native Windows tests + adversarial fault cases PASS. Review both full base and crypto current/delayed JSON against strict schema v1. Current/delayed crypto must stay excluded until writer interlock and compatible schema is separately approved. All public signal/broker flags remain safe.
- Read-only actual VPS proof of current core/expansion reports and scheduler state; frozen AI-v1.2.1 mismatch preserved while separately attested prospective operational health passes.
- Offsite encrypted copies for every required SQLite ledger class, accepted receipts and source history, verified backup manifests plus **independent restore rehearsal**; tested point-in-time consistency and dedup/retention/quota; owner authorizes external services and storage before any operation. Prevent leakage of provider credentials or private data into public repo.
- Save last known good website snapshot SHA/timestamp, application health, 9 market-status contract, core + expansion counters and all local + cloud source digests, Task Scheduler task XML/actions for **each** scheduled task, runner file hashes, source commit, Windows task credentials/access class, old cloud ingest config (redacted), rollback procedure and fail-closed time window. No secret dump into GitHub.
- Verify old `TradingTop Product Publish` at :05 and proposed successor are NOT concurrent: an owner-authorized scheduled handoff or an atomic single task replacement with pre-captured original XML. Do not create a second hourly publisher beside the old. Preserve independent core/expansion :02/:03 and K5 :04 scanner definitions.
- Do not mistake a successful publisher task exit code 0 for all-lineage health; explicitly assert core and expansion health + historical mismatch, K5 absence/pending where appropriate, cloud remote durability and no actionable crypto exposure.

**ONLY AFTER future owner approvals**:
1. Observe a quiet window and save exact immutable prestate checks; reject mismatch/dirty worktree.
2. Take independently verified backups and reversible snapshots of task definitions and previous sanitized website state.
3. Stop/replace exactly the old publisher under owner authorization; ensure no concurrent old invocation remains and no unverified new runner is active.
4. With crypto held, evaluate one bounded candidate in an isolated directory, check exact new SHA and base programs, match counters or explain natural new ledger growth; staged artifact must be signed off before upload.
5. Owner separately authorizes **one** sanitized cloud publication, verify cloud acceptance AND independent remote digest/last-generated-at read-back on existing durable Railway volume, no raw/provider content. Local acceptance receipt/replace must reconcile to remote exact bytes, including power-loss recovery states.
6. After observed full cycle (including Task Scheduler next-run; no duplicate publish), verify historical snapshots retained and independent backup health, and explicitly accept/abort. Rerun no failed step without new decision.
7. Rollback if any mismatch: halt only new publication task, restore original publisher task XML/action without touching AI scanners, keep all candidate/accepted/failed artifacts, verify old public snapshot and hosted exact SHA independently, leave crypto hidden; do not delete archive/failed evidence or run K5 manually. Distinct owner authorization required for real rollback mutation.

**NO live actions are authorized by this document.** Do not issue a runnable command for task disable/replace/restart, cloud POST, provider call or backup service enrollment until owner explicitly approves the separate action.

## 5. Prospective offline and read-only gates

New tests:
- Core/expansion base exporter STILL runs under crypto writer-interlock absence (K5 not probed; crypto ledger history not read; old crypto cache not attached);
- accidental edit to `CRYPTO_WRITER_INTERLOCK_READY=True` still raises without proven writer-side coordination, before K5 access or export;
- ordinary publisher crypto/current/delayed future-mode fixture tests use an explicit **mock-only** writer lock; they do not claim production support;
- local archive auditor handles no history, SHA identity and accepted receipts, pending unaccepted candidate, orphan/corrupt/invalid receipts, modified candidate, invalid timestamps, oversized payload, unsafe directory, unexpected files, read-only behavior and explicit no-external-backup status.
- Native test run alongside prior five public regressions at new exact successor SHA; **PR #49's 117-test PASS is historical, not valid for this modified candidate**.
- Only after exact new SHA passes in isolated VPS checkout, a further bounded read-only actual VPS archive inventory may be authorized; no credentials, no private data output, no backup or restore operations.

## 6. Immutable release disposition

This milestone can close **only** as `V0_3_DESIGN_AND_SELECTED_OFFLINE_SAFETY_PASS` after native tests. It **CANNOT** close actual backup durability, completed crypto writer-lock safety, crash-atomic cloud-to-VPS acceptance, or installed publisher cutover gates without later independent operational proofs and separate owner actions. Keep production K3/K4/K5 tasks, original Product Publish, PRs, source ledgers and hosted snapshots unchanged.
