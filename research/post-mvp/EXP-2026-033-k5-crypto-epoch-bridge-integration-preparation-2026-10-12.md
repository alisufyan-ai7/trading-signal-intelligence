# EXP-2026-033 — K5 Complete-Cycle Source Bridge and Publisher Preview

**Date:** 2026-10-12. **Status:** DRAFT successor engineering candidate, OFFLINE ONLY; **not installed, not integrated, not merged, not approved for any real-ledger read or publication**.

**Stacked on:** draft [PR #59 — EXP-032 immutable crypto completed-epoch protocol](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/59), base HEAD `4fa1860e6df2684dc55de1f9723bdc07bde5d522`. Source production main was `a4f00578c00c5e23eb4fae073cf2df18c78d9a0a` when prepared. Parent PR remains unchanged. If parent is amended, merged or rebased, re-evaluate this child rather than silently moving base.

**Owner objective:** show **CURRENT hourly BTCUSDT, ETHUSDT, SOLUSDT aggregate-only** validation counts/gates on VowSig without disclosing private crypto signal direction, entry/stop/targets, rationale, provider payloads or secrets, and without breaking core/AI-v1.2.1 publication. No exchange/broker execution or public actionable crypto approval.

## 1. What this successor implements

The only implementation file is `src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py`, providing **pure, unwired** functions with dependency-injected verified input:

1. `prepare_verified_epoch`: consumes an **already created** complete K5 private report, separately supplied per-market private records, before/after native K5 task observations, a separately derived public-only crypto program, and a hash-chain verification callback. It rejects any mixed/unfinished/failed H1 epoch, K5 task not Ready/LastTaskResult!=0, unstable task run, invalid upstream/frozen artifacts, ledger head/count mismatch, altered C1/C2/C3 thresholds/calendar, different public counts/timestamps, or non-validated broker/public exposure. It emits only an aggregate, SHA-committed **public-only** completed-epoch envelope from parent PR #59. **It does not read ledgers or run the report itself.**
2. `signed_receipt` / `verify_receipt`: synthetic HMAC-SHA256 authenticated association of one crypto completed-epoch filename, exact byte digest and UTC close. Requires a caller-provided 32+ byte key and uses a **fixture-only** key in tests. No real secret is present. This is a cryptographic *design component*, NOT production key-custody, ACL, rotation or durable monotonic-state implementation.
3. `attach_current_crypto_preview`: pure candidate combining externally supplied **fresh two-program** core/expansion snapshot and independently checked public crypto epoch; validates the authenticated digest and strictly nonregressing, fresh cohort before calling an injected full-snapshot validator. On crypto HOLD, returns a byte-independent copy of the original two-program base and does **not** mutate the caller's object or publish. It has **no HTTP request**, no use of the production publisher, no retry or task changes.

The corresponding new `tests/test_crypto_epoch_bridge_v0_1.py` includes source/task/report/gate tamper, partial cycle, stale/future, authenticated receipt failure, rollback, privacy, full-validator rejection, and preserved-base tests.

**Critically:** the running `scripts/guarded_product_publish_v0_1.py` retains `CRYPTO_WRITER_INTERLOCK_READY=False`, and the hourly protected launcher retains the exact approved `VOWSIG_CRYPTO_ASOF_*` historical pin. The fixed `DELAYED` card still displays 114 historical inferences from October 11 even if current private K5 counts advance. **This candidate does not fix live-site staleness yet.**

## 2. What the source proof can and cannot establish

- The full K5 report is generated elsewhere by `crypto_observability_v1_3.build_report_v1_3` using read-only SQLite with anchored artifact/governance/scheduler checks. That report is PRIVATE: do NOT output or commit it; it contains ledger paths and private record fingerprints.
- All three supplied source record arrays MUST be independently hash-chain verified with the actual repo `verify_records`, including frozen activation identity; the injected verifier in synthetic tests returns a fixture result and **is not equivalent to real hash verification**.
- The producer assumes an independent authorized orchestration process snapshots the three private ledgers only while K5 is complete/stable, cross-checks report's heads, and maintains sealed source identity through receipt creation. This orchestrator is **NOT IMPLEMENTED**.
- The receipt's HMAC prevents arbitrary recipient modification only if the signing key and issuance identity are properly controlled. Current code does **not** provision a key, verify Windows access controls/reparse points, open epoch files from a trusted directory, implement producer authentication, store a crash-safe receipt pointer, independently anchor the latest accepted epoch, or handle secret rotation. None of these may be assumed from unit tests.
- The public crypto seal/producer *must* retain all low-performing/inactive markets, failures and frozen C1/C2/C3 denominators; no historical backfill or changing strategy parameters on early results.
- A strict terminal record requirement may fail closed if the natural K5 cycle records a true MISS/ERROR or no eligible inference. A progress card must be labeled **DELAYED** or withheld rather than faking current evidence. Whether a longer-running K5 task can reliably finish before the existing :05 publisher window is not yet proven.
- For a future true current crypto release, preserve complete fixed 3-program public schema, cryptographic attestation, exact source HEAD safety, eligibility-independent aggregate-only semantics, and single POST+accepted local receipt. No new customer alert/entry/SL/TP publication.

## 3. Test evidence and precise qualification boundary

The two proposed new files are identical to locally tested bytes, independently verifiable via Git blob hashes:
- Source `crypto_epoch_bridge_v0_1.py`: `0f7c6a3af73ee3c5669e114b8903121cc1161397`.
- Test `test_crypto_epoch_bridge_v0_1.py`: `e8e4012d8f53607d6f14577c5852e5b9d2c76008`.

**Observed in assistant's isolated local Python environment:**

`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src pytest -q -p no:cacheprovider tests/test_crypto_completed_epoch_v0_1.py tests/test_crypto_epoch_bridge_v0_1.py`

Result: **43 passed in 0.09s**.

This used the exact proposed new files plus the parent PR #59 code, but **a test-only stand-in for the existing as-of crypto validator**. The stand-in was never committed. Therefore test state is `LOCAL_SYNTHETIC_PROTOCOL_PASS`, **not** `FULL_REPOSITORY_PASS`, `REAL_VALIDATOR_PASS`, `WINDOWS_PASS`, or `PRODUCTION_READY`. Native Windows Python 3.12, actual repository import/contract parity, governed frozen-dependency review, crash/race/ACL tests and any private-ledger test remain **PENDING**.

These tests do not use real K5 SQLite, OpenAI/Binance, Task Scheduler, tokens, remote HTTP or production code. No GitHub workflow was added or invoked.

## 4. Follow-on work that is still necessary

**Stage A — owner-review and native Windows isolated synthetic parity.** Pin exact parent PR #59 and this successor head. Use an isolated temporary Git worktree, not the live production worktree. Verify these blobs and parent files; run source compile, new parent+successor focused tests and existing crypto-as-of/guarded publisher regression tests with the **actual repository's as-of validator**. Static review of exposed fields, causality, crash windows, Windows hardlinks and Python 3.12 behavior. No live SQLite/Task Scheduler modifications or cloud POST.

**Stage B — prospective producer/orchestrator in a NEW separately reviewed proposal.** Implement a post-natural-K5 observer (not a modification to the frozen K5 source), using real read-only `build_report_v1_3` + `verify_records` and independent before/after K5 task observations. Keep the raw report/records entirely in memory. Atomically produce owner-trusted cryptographically authenticated immutable sealed receipts in a Windows ACL-controlled directory. Test anti-rollback and corrupted/missing/truncated receipt behavior. Do NOT silently start K5, delay frozen scanning or backfill previous cycles.

**Stage C — bounded real source observation.** Requires **fresh explicit owner approval**: prior one-shot private K5 quality read permission was consumed. Do one GET/read-only post-completed-cycle proof with no provider/network/private-json upload and no writes to the K5 production ledgers.

**Stage D — guarded publisher integration.** Prospective code/wrapper only after Stage A–C; separate reviewed guard and fallback: current crypto when safe, otherwise original pinned historic **DELAYED** seal, then fresh core/expansion independently. Uphold one publisher task, existing nine-market catalog, all safety hashes and one accepted-snapshot receipt. Run Windows synthetic fault/race suite, exact-SHA frozen-dependency manual check and separate per-PR owner merge/release approvals. Validate public readback and multiple **natural** hourly cycles; never assert remote full stored-byte hash without independent provider verification.

## 5. Current approval status and stop conditions

- **Allowed here:** GitHub-only isolated design, synthetic code/tests, and DRAFT PR creation; no merge.
- **Not authorized:** production main/publisher/K5 modification; source synchronization; native VPS private read; task changes; scheduler starts; public POST; new cloud/secret; current crypto activation; trading or customer crypto alerts.
- If native Windows imports/tests fail, or trusted source proof cannot be established, **STOP without merging**. Keep existing EXP-031 and core/expansion service untouched.
- Before any future merge, the owner requires a separately reviewed exact source commit/changed-path scope and mandatory manual frozen-dependency-impact verification followed by a **separate named exact-SHA merge approval**.

**This is a reviewable stacked draft, not permission to activate hourly crypto website updates.**
