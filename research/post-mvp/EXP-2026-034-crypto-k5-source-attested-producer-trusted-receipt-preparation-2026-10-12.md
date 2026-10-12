# EXP-2026-034 — K5 Source-Attested Producer + Immutable Receipt Prototype

**Date:** 2026-10-12  
**State:** DRAFT, UNWIRED, SYNTHETIC TEST SOURCES ONLY; NOT WINDOWS VERIFIED; NO REAL DATA READ.  
**Root objective:** Safe *hourly aggregate-only* AI-v1.3 BTC/ETH/SOL research progress for vowsig.com, independent of public crypto BUY/SELL/entry/SL/TP/alert exposure. The released website remains **DELAYED**.

## 1. Exact lineage and scope

Repository: `alisufyan-ai7/trading-signal-intelligence`; use this conversation + GitHub only.

At branch creation:
- Production `main=a4f00578c00c5e23eb4fae073cf2df18c78d9a0a`.
- [PR #59](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/59) `4fa1860e6df2684dc55de1f9723bdc07bde5d522`: offline immutable completed-cycle aggregate envelope; draft/unmerged.
- [PR #60](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/60) `a4f58ea87a3ba1b011fda212d11714daa3d0c56b`: offline source/report reconciliation + HMAC/preview bridge; draft/unmerged.
- [PR #61](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/61) `c2bde9b22461f3f2685e0159fe8fc1e5b24792f8`: **native Windows synthetic parity CLOSED PASS** for its exact **prior** five-module suite; 142 passed in 2614.21s under short NTFS checkout. Prior overlong-path 15-failure attempt remains preserved and failed. PR #61 is **independent testing documentation**, not merged and not the base of this new candidate.
- This successor is **stacked directly on PR #60** and does not include PR #61 handoff changes. Its three new files are independently reviewed, not implied to inherit PR #61 Windows PASS.

## 2. Actual frozen code interfaces and safety boundaries

The new code imports unchanged frozen source modules:

- `ai_v1.crypto_activation_v1_3.DATABASE_PATHS` / `MARKETS` / `validate_review_gates`: exactly BTCUSDT, ETHUSDT, SOLUSDT and exact frozen C1 100/20/0d, C2 500/50/60d, C3 1000/100/120d.
- `ai_v1.observability.read_records_read_only`: SQLite URI mode=ro, PRAGMA query_only and noninitializing read; `verify_records` uses actual contiguous hash chain.
- `ai_v1.crypto_observability_v1_3.build_report_v1_3`: checks ledger anchors, frozen artifacts, upstream anchor equivalence, Task Scheduler health and frozen gate parameters, with source report PRIVATE.
- `product.crypto_validation.normalize_crypto_validation_report` and `product.ai_insights.build_public_validation_program`: existing aggregate-only public contract, never full crypto report.
- `product.crypto_epoch_bridge_v0_1.prepare_verified_epoch` (PR #60): checks K5 Ready/success, same completed K5 run, exact BTC/ETH/SOL ledger reports and H1 terminal records, source/public market counts, frozen gate progress and short-lag H1 time. All K5 private record arrays remain in process memory.

No frozen source edits, no new strategy/risk/cost changes, no new public API schema, no public signal details, no broker/exchange execution.

## 3. Newly added dormant source-attested producer

`src/trading_signal_intelligence/product/crypto_epoch_source_producer_v0_1.py`:

- Nothing executes at import and there is **no CLI**, no scheduler integration, no command hook, no network call and no provider login.
- `capture_completed_k5_epoch` is a **private-ledger read operation if actually invoked with default real adapters**. It MUST NOT be invoked on the VPS without a fresh, explicit, separately bounded owner authorization. Synthetic tests exclusively inject private **synthetic rows/report/scheduler observations**.
- Computes the candidate source-bar H1 close from the normal K5 Task Scheduler last run, checks K5 ready/success/age (through existing PR #60 bridge), obtains batch 1 from three separate read-only ledgers and independently calls the real hash-chain verifier.
- Reconstructs full private K5 observability (when the default real reporter is invoked): uses `include_scheduler=True`, `verify_upstream=True` and all anchored market/artifact checks.
- Independently loads **frozen crypto gate definitions** and verifies the full report has matching C1/C2/C3 counts and calendar thresholds. The public gate representation is then derived from the strict existing adapter (not caller-supplied market values).
- Re-reads all three ledgers, verifies each full chain, requires identical batch 1/batch 2 record-sequence/head commitments, then repeats the K5 Task Scheduler observation.
- Invokes PR #60 bridge to reconcile task-before/task-after, observed report vs private rows, current cycle terminal results and full public-only aggregates. Mismatch => fail closed; raw report/rows/paths/hashes are never returned.
- **Output:** one JSON-encoded, closed-H1, aggregate-only `crypto-expansion-1` envelope to be further authenticated; a source-verification failure never emits a candidate. No derived tradable signal/price fields.

**Source-authentication limit:** this proves consistent readings through the actual imported verifier and real observability procedures when those default interfaces are later authorized/run. A spoofed injected report/scheduler is not a trusted production input, and a full source proof cannot be asserted from unit tests with mocks. The K5 task may advance between probes; any mismatch holds. No K5 freeze/lock is deployed.

## 4. New immutable receipt storage/consumer candidate

`src/trading_signal_intelligence/product/crypto_epoch_receipt_store_v0_1.py`:

- `stage_authenticated_epoch` accepts the already source-attested public-only bytes from above and an independently supplied secret key **in memory** (no key default, no static production key, no environmental auto-fetch, no key file, no key logged or emitted).
- Creates a SHA256-bound public epoch via PR #59 immutable create-once spool and a SHA256/HMAC-bound receipt via PR #60; fsync + NTFS-compatible atomic hardlink with refusal to overwrite an existing receipt.
- Captures expected scenario: a crash after epoch creation but before receipt commit may leave an **orphan epoch**; that orphan is never eligible for publication absent a later externally attested receipt. Never scans an arbitrary directory and selects the highest filename.
- `consume_trusted_epoch` requires a caller-provided **independently pinned receipt file digest**, the verifying key, and externally maintained previous accepted H1 cycle. It checks canonical receipt encoding, MAC/identity, exact source filename/digest, symlink/hardlink/file-size constraints, **strictly newer than last accepted cycle**, and age before returning the strict sanitized public program.
- NO HTTP, crypto publisher code change, persistent `latest` pointer, key provision, key rotation, trusted high-water cursor, Windows ACL setup or VPS scheduling. A digest coming from the same unauthenticated spool **is not** an independent trust root.

**Persistence limit:** proper source-producer identity, high-water antirollback anchor, secret custody, NTFS reparse-point/hardlink races, Windows ACLs and crash-consistent trusted pointer lifecycle remain separate mandatory follow-on work. HMAC proves receipt origin only if the signing key is protected; it does not by itself prove that the signer observed safe market data. The unsigned epoch producer and the signature must be integrated into one approved authenticated workflow.

## 5. Synthetic fault tests — created but NOT YET EXECUTED

`tests/test_crypto_epoch_source_receipt_v0_1.py` uses the **real repository hash-chain algorithm** to generate artificial, valid ACTIVATION/INFERENCE/NO_TRADE records. Full observability and task state are purpose-built synthetic injection callbacks only.

Covered test scenarios:
- healthy 3-market complete H1 double-read, real record hashes, direct public adapter, no private record/hash/path fields in resulting bytes;
- tampered hash, changing K5 task during observation, report/ledger source-head mismatch, and frozen gate target mismatch;
- valid append-only new ledger record between two independent reads **with both source chains valid**, requiring HOLD (writer concurrency);
- naive timestamp rejected;
- HMAC receipt roundtrip with separately supplied TEST ONLY key, missing key/incorrect key, receipt pin alteration/tamper, stale/duplicate/rollback refusal;
- no-overwrite, simulated receipt-write interruption producing an untrusted orphan epoch, and absent receipt.

**No source Python compiler, pytest, GitHub Actions or native Windows run has occurred for this new candidate.** Do not claim `TEST_PASS` before separate independent testing. PR #61's 142 PASS belongs to older exact source, NOT to EXP-034.

## 6. Next verification gates and owner decisions

**A — exact GitHub review:** inspect new files relative to exact PR #60 HEAD and confirm no existing code/config/strategy/guarded-publisher/scheduler changes. Keep PR draft.

**B — synthetic tests using actual repo (recommended next):** check out exact PR head into a short-path disposable isolated Windows NTFS clone, never alter production checkout; run new source/receipt test module plus PR #59 and #60 two-module synthetic suites and as-of/public/publisher regressions; verify SHA, actual validator and AST first. Maintain readable compact failure summary; no provider calls or private records. Run extended NTFS hardlink/unlink, read race/reparse/ACL experiments only as separately reviewed synthetic tests. If FAIL, preserve output and correct prospectively; do not weaken acceptance.

**C — trusted cursor/key and Windows crash/race protocol:** design a restricted signing identity and independently durable monotonic accepted-cycle anchor with key rotation policy; verify crash windows, file tamper, privilege boundaries, power loss, new K5 run while publisher observes, malicious/symlink/reparse points and safe fallback.

**D — prospective real K5 observation:** require **new, separate owner approval** for a bounded, read-only observation of real K5 source ledgers; earlier one-time permission consumed. Must never print/export private report, capture provider data, backfill or call AI/Binance.

**E — eventual publisher integration:** separate branch/PR and exact-SHA approval. Preserve independent safe hourly core/expansion; crypto CURRENT aggregates only with a trusted receipt + strict privacy validation. On any HOLD, preserve existing fixed, historically labeled `DELAYED` card (or safe absence). A single existing scheduled publisher, single governed POST/acceptance/archived proof, hosted readback and multiple natural hours must prove rollout. No customer-facing crypto entry/stop/target/alert or broker order permitted. Never replace \`CRYPTO_WRITER_INTERLOCK_READY=False\` with \`True\` in this predecessor source.

**No merge, real private source read, account/provider action, trading, VPS source sync or deployment is authorized by creating this review candidate.**
