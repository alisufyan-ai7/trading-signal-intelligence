# EXP-2026-031 — Crypto research-only as-of publication unblock (review candidate)

**2026-10-11 — DRAFT / UNMERGED / NOT DEPLOYED / SYNTHETIC TEST OUTPUT PENDING.**

## Objective and authority

Owner directed focus back on VowSig's original public AI-v1.3 BTCUSDT / ETHUSDT / SOLUSDT **aggregate research progress**, instead of continuing S3/B2 backup work. Prior owner approval of **public aggregate research visibility only** is recorded in PR #46 comment `6097935100`, and is NOT authority for a merge, VPS data read, snapshot publication, scheduled task change, manual K5 scan or trading. This task authorizes isolated **engineering preparation**, not live rollout. Use only current project chat and private `alisufyan-ai7/trading-signal-intelligence` GitHub repo.

**Branch:** stacked on exact untouched DRAFT PR #51 HEAD `620ee672f22b57fde8f512b4493dcd0f6f562e08`, itself dependent on PRs #49 → #48 → #46. Keep those frozen review heads and their owner-observed Windows test PASS evidence unchanged. Retain PR #50 as independent manual pre-merge frozen-dependency checker. PRs #52/#53/#54 backup work are separately stacked on #51 and **not dependencies of this crypto product task**. Production main remains unmerged at `47687d8d0e21523e417899a71dddc886ecf25d73` as observed when preparing.

## Practical product interpretation: a sealed historical snapshot, not live K5

Original guarded publisher PR #51 correctly refuses to publish **CURRENT** crypto: a K5 writer-side lock does not extend through HTTP acceptance. Holding a lock through a provider request has scheduler/latency risks. **Do not toggle `CRYPTO_WRITER_INTERLOCK_READY`** or modify frozen K5, K3/K4 activation sources, AI-v1.1 correction-governed `ai_insights.py`, AI-v1.2.1 evidence or the public schema.

Instead the proposed first website release is **a true immutable, owner-pinned, sample-as-of aggregate**:

1. On a **future separately authorized**, read-only VPS inspection, the capture tool confirms an already **naturally completed**, recent K5 scan and three BTC/ETH/SOL ledger fingerprints before/after; uses the **already existing** guarded three-program exporter (which validates upstream K3/K4/K5 activation, exact crypto product adapter pin, strict core/expansion registry compatibility and public safety). No model request, manual scan or provider call. If K5 or a ledger changes while assembling, fail closed and do not create the seal. A later writer may append afterwards: that is exactly why the product says **last verified** rather than current.
2. The capture tool serializes only the **schema-v1** crypto public program in a one-shot, `xb` / non-overwrite JSON file `data/crypto-research-asof-v0.1.json`. No ledger paths, raw candles, individual signals, prices, private rationales, requests, credentials or hidden reasoning. It prints the SHA-256, original sample UTC and safe market names. This file is **NOT created or uploaded in this preparation**.
3. Separate **owner review of that exact SHA-256** precedes pinning `VOWSIG_CRYPTO_ASOF_SHA256=<exact sha>` and opt-in `VOWSIG_CRYPTO_ASOF_ENABLED=1`. If these are absent, live publisher behaves like PR #51: fresh independently verified **core + expansion only**, no crypto. If seal is missing, mutated, a symlink, hardlinked, oversized, wrong schema or unsafe, **never attach it**. Fresh core/expansion continue independently.
4. On an owner-authorized **guarded publisher** cycle only, load the already sealed **public data bytes** (not crypto ledgers), check the operator-pinned **entire file SHA-256**, strict shape and per-market counts, convert the preserved source timestamp into a **prominent `DELAYED (last verified <UTC>)` title** and `status=delayed`, mark `health.healthy=false` / `scheduler_healthy=false`. All ledger-verification-as-of evidence, broker-disabled and signal exposure false remain visible. **No new fields** are added to frozen public schema v1. New global `generated_at_utc` refers ONLY to the freshly verified independent core/expansion snapshot.
5. Existing guarded pre-HTTP candidate validators and nested sensitive-field rejection revalidate the entire 3-program payload; local SHA-addressed candidate history, accepted receipts, separately authorized cloud push and atomic local replacement stay in the guarded publisher. An export failure never republishes the old snapshot. Current K5 path stays permanently held by the unchanged always-raising guard; a seal is **not** an exemption for the current path.

### Why this resolves the specific current/writer race

The published crypto payload is an explicit historic fixed *observation* captured before the cloud operation. The K5 writer can append after seal creation without invalidating what the sealed observation said at its original timestamp. Unlike the blocked **current** publisher, there is no promise of contemporaneous live crypto counts during HTTP POST, no need for a K5 writer lock during POST, and no producer process or Task Scheduler change. This does **not prove a single atomic cycle across three separate SQLite databases**; the program describes independently validated market observations at their capture time, not atomic multi-market transactions.

**The seal's local operator pin is a provenance control, not an externally backed cryptographic signature or durable backup.** A compromised operator/VPS could change both approved environment and files. Do not describe as externally immutable or offsite durable.

## Changed paths vs PR #51

- New `src/trading_signal_intelligence/product/crypto_asof_seal_v0_1.py`: allowlist schema-v1 crypto aggregate, strict counts/market/gates, nested sensitive-field rejection, parsing and sample timestamp, no live DB or network calls, SHA-256 pinned read (fail on wrong identity) and strict title-only delayed transformation.
- New `scripts/capture_crypto_research_asof_v0_1.py`: **dormant** real read-only source capture protocol with explicit confirmation and opt-in environment, atomic false if source changes, no provider/scan/scheduler mutation; capture is not authorized to execute yet. Only writes one local sanitized seal on a distinct later authorization.
- Modified `scripts/guarded_product_publish_v0_1.py`: guarded fallback can add prevalidated pinned seal on explicit opt-in without probing K5 or opening crypto ledgers. Existing current crypto strict interlock remains false/unimplemented; default two-program behavior preserved. Delayed v1 schema title parsed exactly, no extra keys required.
- New `tests/test_crypto_asof_publication_v0_1.py`: synthetic-only safety and opt-in mock publisher tests. This file uses fabricated counts, no live SQLite/VPS/network.
- No frozen K5/private-crypto code, task CMD files, public app/web, cloud validation module, AI-v1.1 `ai_insights.py`, correction JSONs or registry changes.

## Important blockers before website deployment

**Engineering gate:** Exact new PR HEAD synthetic native Windows tests and selected prior publisher/crypto/public regression suites must actually run. No PASS claimed based on authoring or static review. Validate real frozen `config/public_validation_program_schema_v1.json` acceptance, malicious field/tamper rejection, missing/bad seal fallback to two programs, no K5 probe/ledger reads during pin-based publication.

**Read-only live preview gate (separate authorization):** first prove one clean real K5/composite report, three genuine markets and C1/C2/C3 in an isolated checkout, no writes, no provider calls or snapshot push, and verify source ledger preservation. Then authorize a single actual public-only seal capture separately; do not treat approval of publication design as authorization to open the real SQLite files or create files in production `data`.

**Website operational gate:** Old `TradingTop Product Publish` task still uses fail-open export→push ordering; a new successor publisher cannot be installed or run concurrently. Requires exact owner-approved containment of old task, rollback, and code/VPS sync. Correct manual frozen-dependency exact-SHA premerge scanner PR #50, per-PR/per-SHA merge approvals, and separately approved hosted sanitized POST/readback all remain required.

**Recovery/durability hold:** existing documented broad B0–B9 offsite-DB backup/restore prerequisite is **not waived**; current one-S02 local backup and independent local recovery PASS do NOT establish whole-corpus protection. A proportionate, explicit owner decision is needed if releasing a strictly sanitized/historical card before full offsite replication. Avoid representing backup as complete. Continue backup design after the original website objective, without silently overriding preexisting no-go.

**Website acceptance when later authorized:** On `vowsig.com/api/validation/programs`, exactly `core-ai-shadow`, `market-expansion-1`, `crypto-expansion-1`; 3 crypto symbols + C1/C2/C3; prominent **DELAYED UTC as-of** label; no crypto BUY/SELL, entry/stop/TP, provider information or execution; stable core/expansion and 9 public markets; broker execution false. If seal invalid, only core and expansion must continue.

## Status and next owner-independent work

Implementation **prepared only**; no native VPS test evidence yet. Reviewer should first run an isolated synthetic-only suite on this SHA, then prospectively inspect first-VPS real three-program compatibility **after separate approval**, instead of spending time on another general-purpose backup wrapper. No merge, credentials, trading, Task Scheduler write, K5 scan, cloud push, or real data capture allowed in this task.

## 2026-10-11 successor correction: strictly nine-ledger one-shot seal capture (NOT EXECUTED)

Following the successful **real-VPS read-only nine-ledger three-program preview** on PR #55 `3e3c073d3045d47d706f15fa2c4d3b5c1b54b3a6` (https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/55#issuecomment-6108148619), owner directed continuation of *engineering preparation only*. The original preview consent is **consumed** and did **not** authorize seal creation.

The previous dormant `scripts/capture_crypto_research_asof_v0_1.py` inadvertently depended on `build_guarded_full_snapshot(root)`; that path assembles website markets, S02 public history, and other source files outside the preview's nine-governed-ledger scope. It is now replaced with `build_three_program_observation(root)` that calls **only**:
- the previously real-verified `build_core_expansion_programs(root)` (three AI-v1.1 plus three AI-v1.2.1 ledgers, read-only), and
- `build_crypto_public_validation_program(root, include_scheduler=True, verify_upstream=True)` (three AI-v1.3 crypto ledgers, read-only),
with the frozen public-crypto-adapter source pin checked against the isolated PR review source checkout rather than unmerged production main.

The one-shot script's `--live-root` option is **required** but it is DORMANT; it still also requires the exact `--confirm CAPTURE-ONE-CRYPTO-ASOF-RESEARCH-SEAL` argument and `VOWSIG_CRYPTO_SEAL_CAPTURE_ENABLED=1`. Providing a path does not imply authorization. The only prospective output remains the exclusive, local `<live-root>/data/crypto-research-asof-v0.1.json` file containing **public-only** crypto aggregates, **not** the full website snapshot; exact SHA-256/bytes printed for separate owner pin review. Never overwrite/recreate a previous seal without new procedure and separate permission.

The prepared implementation pins the exact **nine** active AI ledger relative paths, disallows sidecars/symlinks/empty or oversized ledgers, hashes size/mtime/contents pre/post, and compares all 3 crypto ledger hash-chain heads pre/post. It checks naturally completed/stable K5 with **GET-only** scheduler queries, preserves read-only Git registry/anchor proofs and exception-based held states, validates all 3 program health/broker-execution boundaries and crypto `public_signal_exposure=false`, C1/C2/C3 identity, the frozen v1 validation-program schema, and historic delayed in-memory display. The observer's timestamp is the end of its qualified observation, **not an atomic nine-database snapshot claim**. No K5 scan, MT5, Binance/OpenAI, cloud, trading, live publisher invocation, task mutation or S02/research DB access is in the code path.

An important distinction: pre/post source file SHA and scheduler checks detect observed changes **during** capture, not a universal concurrency lock. A later writer may append normally, and the published card must remain **DELAYED / last verified at UTC**. No current-crypto writer interlock is being enabled.

Synthetic-only test fixtures have been updated/expanded prospectively for the narrow builder, exact S02/full-export exclusion, disabled capture by default, local exclusive-file semantics, corrupt/unauthorized public data, and crypto or nine-ledger drift. **These revised tests have not yet run on the owner's native Windows Python**. Do not reuse prior `159/159 PASS` on earlier SHA as proof for this change. The next engineering gate is ONE isolated exact-SHA native Windows synthetic regression on this updated PR #55 branch. A subsequent **separate explicit owner authorization** is mandatory before any real file is created or any real ledgers are opened again. All PR merges/cutover/hosted push and broad B0–B9 prerequisites are still held.
