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
