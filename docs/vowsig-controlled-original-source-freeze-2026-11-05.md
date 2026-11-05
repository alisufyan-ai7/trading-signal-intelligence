# VowSig original-ledger controlled snapshot capture (draft, 2026-11-05)

## Boundary

The twelve original live Windows VPS SQLite files are accessible (inventory 2026-11-05T02:35:45.711557Z, see PR #93 comment 6648215417), but observed live terminal row hashes are NOT the SHA256 of immutable frozen file bytes. Use exactly the twelve repository-approved sources in `source_inventory.py` and the prior observed sequence/hash pins hardcoded in `private_source_freeze.py`. The source programs remain separate; S02 is not AI performance. The fully tested capture algorithm is being prepared under **DRAFT PR #93 only**. Do NOT switch/check out draft code on the production VPS or modify schedulers, publisher, trading tasks, secrets, backups, or broker.

## Planned private one-time operation

1. On the Windows VPS, pre-provision a new restricted-access dedicated evidence directory **outside** the production checkout and outside the existing S02 backup directories. Restrict ACL to the authorized operator and SYSTEM; do not inherit Users, Authenticated Users or Everyone. Never place copies in the repo, chat, CI, GitHub, Railway, Resend, Auth0, or generic logs. The original databases can contain strategy payloads.
2. After separate execution review, use one owner-initiated single-copy-paste PowerShell block with Python standard-library `sqlite3.Connection.backup()` to copy all twelve sources **one by one**, without stopping tasks or modifying source databases. The operator must review disk space and the private location before execution. The backup API creates a transactionally consistent copy of *each* database; twelve sequential backups are NOT a synchronized single instant across all markets.
3. Refuse missing/symlinked/out-of-root originals or unknown events. Run `PRAGMA quick_check`, exact count/sequence, the **prior observed prefix** record hash, the full SHA256 per copied file, and the existing read-only canonical hash-chain audit on each **copy**. The crypto three-market ACTIVATE event must match the repository's activation-anchor hash and payload. This is *only* a static activation bridge, **NOT AI-v1.3 K5 epoch, cost or natural-cycle certification**.
4. Produce an owner-private `manifest.preliminary.json` with counts, hash heads, full-chain self-consistency and copy SHA256. Emit safe aggregate text only. If any copy/check fails, there is no completed manifest and leftover partial private files are NOT approved. No overwrite and no auto-deletion of evidence. Only the owner can separately approve custody of the raw private copies.
5. The independent reviewer must inspect the completed private copies under separate custody, independently recompute the file SHA256 and complete chain heads from those same copies, reconcile time/population and sign pins. An internally computed digest or the pasted prior inventory is NOT a trusted external source pin. Crypto K5 epoch coverage, source rights, causality, complete lifecycle (including exits, partials, errors, missed/skipped cycles), after-cost net R and all-market universe attestations remain separate.

## Production gating

Do NOT promote self-consistent copied counts into verified profitability. No public expansion signals, no broker execution, no paid Auth0 upgrade, no real signup until the one fully enabled exact-SHA release passes all independent owner/security/history gates. Railway PostgreSQL encrypted S3/B2 recovery is the FIRST immediate post-launch task per D-01 through D-06; until an independent restore has passed, `DATABASE_RECOVERY_UNVERIFIED`.

## Source files and CI

- `src/trading_signal_intelligence/product/accounts/private_source_freeze.py`: private-only snapshot/chain/prefix/crypto activation checks with no real service access.
- `scripts/vowsig_freeze_original_sources.py`: explicit noninteractive guarded standalone CLI, **not deployed to VPS**.
- `tests/test_vowsig_private_source_freeze_p2.py`: synthetic capture, immutability, private evidence, malformed source and crypto activation negatives.
- `.github/workflows/vowsig-accounts-review.yml`: isolated review includes these tests. GitHub CI uses disposable synthetic SQLite only.

No raw ledger source, live database bytes or owner credentials are committed. This is engineering readiness for later authorized local capture, not evidence that the VPS has been frozen.

## Separately pinned offline recheck (draft)

Added `verify_private_frozen_set` and `scripts/vowsig_verify_frozen_sources.py`: takes the completed private run path and an **externally recorded** expected manifest SHA256. It verifies manifest byte hash, each exact approved filename, frozen file SHA256, prior prefix, complete hash-chain and crypto activation bridge, under read-only transactions; it does not sign source rights, verify crypto K5 epochs or validate after-cost outcomes. Supplying the just-computed manifest digest from the same environment is only self-consistency, not independent custody. Neither this tool nor the capture tool should be run on production until the owner reviews a separate one-paste operator procedure.

## Synthetic full-lifecycle population audit

`src/trading_signal_intelligence/product/accounts/private_lifecycle_audit.py` now counts actual distinct SIGNAL, EXIT, PARTIAL_EXIT identities, still-open signals and improper/orphan/out-of-order lifecycle events **only on frozen copies**. S02 `MISSED_SIGNAL`/ `SKIPPED_SIGNAL` remain separate from AI `MISSED_INFERENCE`. A logical mismatch holds full-history verification; no entity IDs or trading payloads appear in receipts. Event linkage is an additional necessary check, NOT sufficient for source rights, financial cost normalization, crypto K5 natural epoch lineage or independent performance acceptance. Synthetic tests cover open/closed/partial and orphan/temporal negative populations. Production original files were not available to this CI.

## 2026-11-05 independent-of-capture-algorithm recheck handoff

Owner VPS execution reported all 12 online SQLite backups complete at 2026-11-05T03:12:55Z; preliminary manifest `bec335b870214b5e770af652869767f54bc960000dd6031278ea0ebf460cbc45` is externally recorded in the PR #93 conversation comment 6648710534 together with 12 observed frozen-file SHA256 values, heads and counts. These are owner observations and **not an independent reviewer signature or custody proof**. The original private files are never uploaded to GitHub.

New `ops/handoffs/vowsig_frozen_source_recheck_inline_v0_1.py` contains the previously owner-exported manifest/file SHA pins and implements a distinct **standard-library-only** read-only verifier. It opens only the private frozen files with `mode=ro&immutable=1`, checks immutable SHA256 from the external owner record both before/after, byte-pin of `manifest.preliminary.json`, complete original hash chains using independently implemented canonical SHA256 calculation, per-version allowlisted event populations, crypto activation record hashes pinned to the repository's activation document, and identity/sequence linkage for SIGNAL/EXIT/PARTIAL_EXIT. Reports only sanitized per-market counts/hold conditions; no IDs/payloads. New synthetic tests cover 12-source successful recheck, wrong pin, mutated private bytes, orphan S02 EXIT and duplicate manifest paths. **No independent reviewer of the actual copied data has run it yet**; the next step is the single paste-ready Python-STDIN PowerShell wrapper from the owner chat.

`SOURCE_ENTITY_ORDER_CONSISTENT` is a limited logical event-order check: still no precise timing/causality, trade eligibility, K5 epoch proof, cost normalization, source rights, cohort entitlement or signed full-universe acceptance. True external audit requires a separately authorized independent reviewer and protected custody of copies; a script running twice on the same VPS is not sufficient. After this recheck, diagnose the nine additional ERROR events with sanitized categories and explicitly review full `EXIT` result/cost payload contracts offline before reporting net R.
