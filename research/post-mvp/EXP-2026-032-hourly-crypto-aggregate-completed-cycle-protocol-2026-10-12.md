# EXP-2026-032 — Current Crypto Aggregate Hourly Publication: Completed-Cycle Protocol Preparation

**Created:** 2026-10-12. **Status:** isolated offline prototype for owner review; NOT enabled, NOT native-Windows qualified, NOT integrated or approved to publish.  
**Parent:** [Issue #57, Workstream B](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/57).  
**Project scope:** Only this TradingTop Analysis chat and `alisufyan-ai7/trading-signal-intelligence`.  
**Exact baseline:** production GitHub `main=a4f00578c00c5e23eb4fae073cf2df18c78d9a0a`, tree `a1d4f12738eeb1865d298a15583c77d6180c95ec`.  
**Primary goal:** Show fresh **hourly aggregate** evidence for AI-v1.3 BTCUSDT/ETHUSDT/SOLUSDT, **without** exposing crypto entries/stops/targets/rationales, activating crypto signals, trading, or altering the frozen K5 model/risk/cost/ledger semantics.

## 1. Real current starting state

- Existing K5 shadow scanner is separate from the public product publisher. Its first natural compatible run PASS is in [Issue #40](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/40). Last privately verified 2026-10-11T18:54:23Z crypto report: 132 valid inferences, 1 completed SOL shadow trade, no ongoing signals, 0 errors; this is a **dated observation**, NOT today's current report.
- The existing guarded publisher `scripts/guarded_product_publish_v0_1.py` has `CRYPTO_WRITER_INTERLOCK_READY=False`. Fresh core/AI-v1.2.1 publication continues while crypto attaches only an independently approved **historical, fixed DELAYED** seal. The public screenshot still shows 114 crypto inferences and sample 2026-10-11T12:07:21.257601Z; these are intentionally historic, not current K5 evidence.
- EXP-031 one-shot historical release and first naturally scheduled guarded publication were **CLOSED PASS** in [Issue #47](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/47#issuecomment-6112078271). Preserve the consumed historical capture, immutable archive/receipt, published date labels and rollback evidence. Hosted full server-stored snapshot-byte digest was not verified.
- Frozen review gates remain: **C1 100 inferences/20 completed trades**, **C2 500/50/60 days**, **C3 1000/100/120 days**, and none authorizes public actionable crypto signals or broker orders.

## 2. Chosen future consistency architecture

**Immutable, verified completed-cycle public-only handoff**, instead of flipping the existing K5 writer-interlock flag or trying to read mutable live SQLite throughout a network POST.

Proposed flow:

1. **Complete existing K5 run unchanged.** Only after a normal, naturally completed task, a separately approved successor read-only producer observes exact task identity, state `Ready`, successful last result, completion timestamp and no active K5 writer process. Do not initiate, delay, rerun or rewrite a K5 cycle. Do not accept manually inferred success from an elapsed minute.
2. **Capture private evidence in memory.** Existing K5 reader must verify the actual three ledger hash chains, frozen source/artifact identities, activation/upstream anchors, source chronology, and approved public/broker boundaries. Independently bind exactly **one shared completed H1 cycle** across BTC/ETH/SOL from actual terminal records, not merely matching wall-clock times. Recheck exact source heads/task status after observation. If a writer ran, an incomplete record exists, a cohort differs, health is false or any mismatch exists, **HOLD** and produce no current seal. No raw private report to file, chat, GitHub, provider or public API.
3. **Sanitize & create immutable aggregate epoch.** Use the existing strict public crypto allowlist and frozen C gate semantics. Preserve all three markets, including weak/inactive/error counts. A short-lived per-H1 envelope contains `cycle_close_utc`, `captured_at_utc`, a SHA-256 commitment to the three private ledger heads/terminal statuses **without publishing the heads**, and the exact sanitized crypto validation-program payload (still `public_signal_exposure=false` and `signal_details_included=false`). The commitment is **not** independent provenance verification; an audited producer must attest the underlying records.
4. **Atomic spool and trusted reference.** Write to a restricted existing private spool with create-once/atomic visibility; never overwrite a previously accepted epoch. A separately reviewed trusted pointer/receipt must bind file path + SHA-256 + completed cycle and survive crashes. Do not treat a digest read from an attacker-controlled filename or mutable self-manifest as a sufficient trust root. Protect spool/receipt with Windows ACLs, no reparse-point/hardlink abuse, audit and rotation. The offline module contains a low-level atomic-spool prototype only, **not** these production ACL/pointer guarantees.
5. **Publisher reads only completed sealed public bytes** (not K5 SQLite) and verifies the externally trusted SHA-256 reference, immutable file properties, exact market/gate schema, strictly non-regressing completed cycle, clock freshness and public privacy flags. Accept as **CURRENT aggregate-only** only if capture is under 90 minutes old and other frozen release checks pass. It must never re-label stale crypto as fresh.
6. **Maintain independent publication.** If the newest completed epoch is absent, stale, corrupt, unsafe, partially written, regressing, or any verifier is unavailable, preserve fresh **core+expansion** publication, and display the unchanged, prominently `DELAYED` crypto history (or safe absence); do **not** publish an unsafe crypto claim, silently fall back to old private report, mutate a ledger or retry frozen hours.
7. **Preserve established publisher and as-of release contracts.** Existing `TradingTop Product Publish` hourly task continues unchanged until owner separately approves and verifies a safe transition. No second competing publisher and no duplicate HTTP POST in the same cycle. Current historical as-of seal remains immutable; the new epoch path is optional and fail-closed.

**Why this avoids the main race:** the consumer sees only a fully materialized, validated, atomically published, self-contained historical point-in-time *aggregate*. The actual private K5 writer may later advance without mutating those approved bytes. This is not enough alone for production: the separate producer attestation and trusted publication pointer must still be designed and proven under Windows concurrency.

## 3. This branch's exact implementation boundary

Two additive files:

- `src/trading_signal_intelligence/product/crypto_completed_epoch_v0_1.py`: **offline-only** pure envelope constructor and externally SHA-pinned reader with strict schema through the existing `crypto_asof_seal_v0_1.py` validator; three-market same-cycle terminal proof shape; SHA commitment instead of raw ledger heads; <90m freshness, <=20m post-H1 capture bound, monotonic/no-regression; atomic, no-overwrite local spool prototype; privacy and content size checks.
- `tests/test_crypto_completed_epoch_v0_1.py`: offline synthetic input and fault matrix; no live SQLite, provider, network, Task Scheduler, cloud tokens, private K5 report or publication.

This branch **does NOT** modify `scripts/guarded_product_publish_v0_1.py`, the existing as-of seal, any runtime/AI/K5/K3 frozen sources, gates, cost policy, public schemas, web assets or Task Scheduler tasks. It **does NOT** enable any flag. These additions are preparation, not an hourly-crypto release.

### Exact local synthetic verification evidence

On the assistant's isolated Linux Python test directory, run:

`PYTHONPATH=src python -B -m pytest -q -p no:cacheprovider tests/test_crypto_completed_epoch_v0_1.py`

Actual observed output: **21 passed in 0.06s** (one later repetition).  
**Important parity limitation:** the isolated local runtime used an explicit **test-only stand-in** for the preexisting private `crypto_asof_seal_v0_1.py` allowlist import, because only the new two files were materialized locally. **The shim was NOT committed.** The 21 results validate the protocol mechanics under that stand-in, **NOT** full actual-repository validation. The full repository's real allowlist and publisher tests, Python 3.12 native Windows, fault injection and integration remain **PENDING**. Source files committed to the review branch matched local `git hash-object` exactly (record their verified Git blobs in PR).

Representative cases tested: coherent three-market H1 epoch; proof omission from serialized output; missing/mixed terminal market; unfinished/ERROR cycle; bad source hash; extra proof keys; impossible capture times; stale/future epoch; epoch rollback; missing/bad digest, tampered bytes and duplicate JSON keys; public signals accidentally exposed; missing market, bad aggregate or broker enabled; duplicate immutable spool write; directory symlink denial.

### Prototype limitations that MUST be resolved before any production request

- This module **cannot establish real terminal proofs itself**; caller-supplied proof shapes are assumed pre-verified. The producer must bind those values to genuinely observed private ledgers and verify multi-market epoch closure and Task Scheduler completion.
- This module **cannot verify source provenance** from the SHA-256 commitment alone. It must be combined with a trusted producer and receipt/manifest rooted in a separately controlled identity; external `expected_sha256` cannot simply be copied from an untrusted filename.
- No K5 race/fault-injection or staging/atomicity test under native Windows has occurred. Windows file permissions, backup writers, ACLs, reparse points and crash recovery must be evaluated separately.
- No publisher/source-integration exists; the public crypto card will **remain DELAYED** until prospective publisher + producer source are implemented and verified.
- The frozen public validation schema must remain unchanged unless a separate, fully validated version/correction is prospectively approved. Do not assume a new public field or UI badge can be added silently.
- Full private report, per-market ledger head hashes, individual decisions, features, provider payloads, market prices and tokens must never be written to the public epoch envelope.
- Current data alone does NOT justify customer-facing crypto entry/SL/TP, alerts, exchange orders, or trading profit claims.

## 4. Explicit next gates

**Gate A — this review only:** verify exact review branch against current `main`, files-only diff, inspect contract and test fixture; no merge. Owner separately authorizes isolated Windows synthetic suite if appropriate. Manual exact-SHA frozen-dependency-impact verification is required again **immediately before any merge**.

**Gate B — producer/integration design + native tests:** after owner review, separately implement source-proof capture and immutable trusted pointer in a **new successor proposal** (not K5 frozen source alteration), isolate from the existing publisher until completed. Test K5 Running/Ready transitions, concurrent writes during pre/post read, partial market writes, stale/latest cycle, open handles/WAL, bad hashes, symlinks/reparse points, file crash boundaries, clock skew, bad provider quota, publisher failure and safe core/expansion fallback. Validate with **the actual Windows Python 3.12 repository** and frozen source hashes, no real private ledger access in synthetic tests.

**Gate C — real private read-only dry run:** separate explicit owner permission for a bounded on-VPS observation. Do not consume prior one-time permissions; do not print or upload full private report. Require no private mutations and same three-market exact epoch proof.

**Gate D — separately owner-approved release:** exact-SHA substantive/manual review; merge/sync only under separate named approval; installer/task changes separately approved; one controlled publication with accepted receipt/public GET; continuous natural hourly evidence including failure recovery; unchanged core/expansion nine-market contract and historical as-of evidence. Never manually start K5 or enable broker execution.

**Success criteria for the ultimate feature:** public BTC/ETH/SOL counts are truly fresh or explicitly stale, match verified independent private source, never leak private trade details, never regress, and never stop safe core/expansion publication when crypto is degraded.

**NO PRODUCTION MUTATION AUTHORIZED BY THIS DOCUMENT OR REVIEW BRANCH.**
