# VowSig safe hourly crypto aggregates — one PR release and verification plan

**Date:** 2026-10-12. **State:** CONSOLIDATED REVIEW CANDIDATE; NOT NATIVE-TESTED ON THIS SHA; OFF IN PRODUCTION.  
**Sole repository:** `alisufyan-ai7/trading-signal-intelligence`. Use only current open chat and GitHub for project context.

## Goal, not a trading authorization

Update the publicly displayed AI-v1.3 BTCUSDT, ETHUSDT, SOLUSDT **aggregate research progress** as K5 completes naturally, ideally once per H1 cycle. Preserve the historical DELAYED card whenever new crypto evidence is not verified. **Never** expose BUY/SELL, entry/stop/TP/rationale, alert contents, raw feeds, model private records, credentials or broker/exchange execution. Frozen crypto C1/C2/C3 economic gates remain unchanged and not automatically actionable.

## Consolidation decision

The owner requested no more serial PR proliferation and no unnecessary key/receipt infrastructure for a single-VPS aggregate-only observation. **Draft PR #63 is the ONE final feature PR**; it should be retargeted against production main once its diff is reconciled. Drafts #59–#62 and independent Windows handoff #61 are **historical evidence**, not a list of required individual merges. Do not delete or falsify prior PASS/FAIL histories.

The original HMAC receipt/spool code and its tests were eliminated from the consolidated diff: that design is unnecessary for sending a source-attested sanitized immutable aggregate through the existing publisher **in the same process**. No new keys or latest-pointer service are provisioned. This does **not** protect against a privileged administrator modifying both runtime and accepted archive; treat that as outside this feature's chosen local-accident threat model and reconsider if publishers move to separate hosts.

## Actual implementation candidate

- Original frozen K5 scanner and AI cost/risk policies untouched.
- Existing `crypto_completed_epoch_v0_1.py` validates exactly three markets, current H1 source close, strict crypto schema, expiry and hash digest in-memory.
- Existing `crypto_epoch_bridge_v0_1.py` checks native Task Scheduler Ready/success/stable run, report/source/public count reconciliation, current completed terminal H1 statuses and no broker/public signal exposure. HMAC helper here is historical prototype code, **not invoked by this release**.
- `crypto_epoch_source_producer_v0_1.py` uses actual read-only AI-ledger interfaces by default, two independent full hash-chain-verified reads and K5/report/frozen C1/C2/C3 checks. Returns only aggregate JSON bytes, with no other I/O except approved read-only probes and no CLI/scheduler entry point.
- `scripts/guarded_product_publish_v0_1.py` has new `_try_source_attested_crypto_aggregate`. It executes **only when the new env opt-in `VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1=1`**. Defaults OFF. It calls the verified producer **inside the same guarded publisher execution**, validates bytes/public shape again, and compares metrics against the last accepted current crypto archive. The existing path then stages, validates, SHA-archives/fsyncs, pushes **once**, writes accepted receipt and atomically updates local public snapshot.
- On any current crypto HOLD, a new core+expansion snapshot is still created. The owner-pinned historical as-of card remains DELAYED if its validated fixed seal exists. No missing or stale cycle is pretended current.
- `CRYPTO_WRITER_INTERLOCK_READY=False` remains unchanged. This design removes the need for a cross-process writer lock **THROUGH the HTTP post** because the publisher never reads mutable K5 data after building an immutable candidate; it does **not** approve enabling the legacy unsafe interlock.
- Existing public schema and live site UI remain unchanged. No new standalone scheduler or competing publisher.

**Design boundary:** A valid K5 source could advance after the final double-read check, but already verified public bytes remain fixed for this publication. The public “current” label applies to the timestamped completed observation, not a promise of a locked live SQLite database. If the same cohort has no safe new completed H1, current generation HOLDS. Future improved observability for MISSED/ERROR cycles is a separate prospective enhancement, not post-result editing.

## Historical exact evidence

- EXP-033 first long-path Windows run FAIL: 127 pass/15 fail (overlong TEMP). Preserve immutable failure.
- EXP-033 exact short NTFS Windows test PASS: 142/142, predecessor PR #61, 2026-10-12.
- EXP-034 corrected receipt prototype exact NTFS Windows PASS: 156/156, earlier PR #63 HEAD `d4a398c3ca7a08c3663c10e7864b37aa605a6ed8`. **This does NOT transfer to the consolidated head**: changed publisher integration, dropped receipt code, new source/publisher tests.
- Current single-PR candidate native Windows test state: **PENDING** until exact-head short-path test output verified and saved.

## Minimal acceptance gates

### A. Current GitHub review / tests (no VPS production mutation)
1. Inspect exact main/head ancestry, no unexpected files, frozen risk/source invariants.
2. Use a disposable short-path **NTFS** checkout and existing Windows Python 3.12, not live Git worktree; exact SHA/checksum verification and PowerShell AST precheck.
3. Run seven actual-repository test modules: completed epoch, epoch bridge, source producer, new current-aggregate publisher integration, as-of historic seal, existing guarded publisher and strict crypto public validation. No shims or live providers.
4. Test switch OFF (no private access), source healthy (safe 3-program candidate), K5/source drift, stale epoch, previously accepted count regression, unsafe crypto privacy, single push and core/expansion safe fallback. Preserve FAIL if any.

### B. Single bounded real K5 proof (SEPARATE owner authorization)
1. Obtain **fresh explicit owner approval** to inspect one naturally completed K5 cycle on the VPS; old one-shot read permissions are consumed.
2. Confirm scheduler starts/completes in time for guarded hourly publisher. Do **not** manually trigger K5 or alter task settings.
3. Read only necessary private source in RAM via unchanged normal verifier; never print/export raw rows/reports, provider payloads, identities, prices or tokens. Output only aggregate result, failure class, healthy status and timestamps. If proof fails: HOLD, no writes.

### C. Exact SHA release (SEPARATE owner decisions)
1. Mandatory manual frozen-dependency impact check against then-current production main and exact candidate.
2. Explicit owner approval for **one** PR merge; then independently approved VPS fast-forward source sync (no unreviewed edits).
3. Leave new opt-in OFF until separate owner approves enabling only aggregate research visibility. Any scheduler timing adjustment requires its own exact review and owner consent.
4. Perform one controlled publicly accepted publication with safe readback (all programs, nine-market catalog, count/timestamps/privacy) then observe multiple **natural** hourly cycles, including a crypto HOLD. Never claim hosted full server-stored snapshot hash if not independently proven.
5. Close or mark predecessor drafts as superseded **only after** this consolidated candidate is independently verified and preserved. Do not merge old drafts.

### D. Mistake-learning mandatory handoff
- [Engineering lessons and prevention checklist](../../docs/engineering-lessons-and-release-checklist-2026-10-12.md) — read before another implementation.
- [CURRENT-HANDOFF](../../docs/CURRENT-HANDOFF.md), [README-FIRST](../../docs/README-FIRST.md), Issue #57 — reconcile on every new chat.
- Add any new FAILED test and correction root cause to issue/PR and engineering lessons, with exact source hashes. Never rewrite an original failure.

**No current real K5 read, production merge, VPS sync, new cloud POST, scheduler change, signal-publication activation, broker order, or commercial signal exposure is granted by this candidate.**
