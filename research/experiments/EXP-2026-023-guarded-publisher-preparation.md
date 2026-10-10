# EXP-2026-023 — VowSig Guarded Product Publisher v0.1

## Scope and ownership

Status: **PROSPECTIVE / DRAFT / v0.2 INDEPENDENT-LINEAGE REVISION — NATIVE OFFLINE RETEST PENDING / NOT DEPLOYED**.

The preceding v0.1 review HEAD e49a0bb0ac2ff4c876054ddeabdca5afb5bb1ae5 had 27 guarded tests and 48 integration regressions PASS (75 total). These passes do **NOT** carry forward to the new v0.2 candidate until rerun.

Owner approval on 2026-10-10: APPROVE VOWSIG GUARDED PUBLISHER PREPARATION ONLY.

This stacked branch begins at PR #46 correction #9 publication commit 13f10339df1410bbbe075371b52b34901ebd121b. It is deliberately separate from production main (47687d8d0e21523e417899a71dddc886ecf25d73). Do not merge PR #46 or this successor, invoke any VPS publisher, install a Windows Scheduled Task, enable broker execution, or publish any website snapshot under this preparation authority.

Frozen K3/K4 artifacts, correction #9, existing script scripts/run_product_publish_task.cmd, and core/expansion/crypto task actions remain untouched.

## Problem and policy

Windows task starts are :02 core, :03 expansion, :04 crypto, :05 publisher. A one-minute difference is not a completion dependency. The existing crypto scheduler observability accepts Running plus a previous LastTaskResult=0 as healthy. Existing product publish wrapper invokes a snapshot push even when export fails, so an older local data/public_snapshot.json can be reused.

Only non-actionable, aggregate AI-v1.3 crypto validation progress has been authorized for eventual public visibility. Entry, stop, target, directional signals, provider details and broker execution remain prohibited. This is not cutover approval.

## Prepared additive mechanism (not activated)

Files:
- scripts/guarded_product_publish_v0_1.py — prospective new guard/orchestrator
- scripts/run_product_publish_guarded_v0_1.cmd — dormant Windows task action candidate
- tests/test_guarded_product_publish_v0_1.py — offline failure-injection suite

Execution requires native Windows, the exact RUN-GUARDED-PUBLISH-V0.1 confirmation token, and VOWSIG_GUARDED_PUBLISH_ENABLED=1 configured in a separately approved cutover. Nothing in this PR sets that environment variable or changes Task Scheduler.

The guard checks K5 scheduler TaskName, *Ready* (never Running), LastTaskResult=0, fresh LastRunTime within 900s, future NextRunTime and explicit timezone. It fingerprints all records in the BTC/ETH/SOL append-only ledgers through their preexisting read-only SQLite reader, then exports only to a brand-new temp path. It requires exactly three programs (core-ai-shadow, market-expansion-1, crypto-expansion-1), healthy crypto status, exact frozen C1/C2/C3 and BTC/ETH/SOL memberships, disabled crypto signal and broker exposure, no private signal keys, and current cloud/push schema validators.

The dormant Windows wrapper executes the preexisting event notification step **independently before** calling the guarded publisher, even if the latter would withhold publication because K5 is still running. A failed event notification stops the wrapper before any new push; it does not silently drop core/expansion alerts when K5 is incomplete. After fresh export and validation, the guarded publisher rechecks K5 stability and compares all crypto ledger fingerprints again. It rechecks the staging bytes and full public validation schema. Only then does it invoke ONE push of the fresh staged file (never --optional, no fallback to the old snapshot). A successful push is followed by atomic replacement of the local data/public_snapshot.json. A held gate never invokes the push.

### Availability tradeoff

If crypto is incomplete, the guard withholds the **whole** update, leaving the last accepted core and expansion public snapshot available but potentially aging to stale. There is no unreviewed fallback exporter for core/expansion only. Such an independent-lineage fallback needs additional design and explicit separate scope. The current legacy scheduled publisher remains unchanged until a later owner-approved safe cutover.

### Known limits to review

- State=Ready plus LastTaskResult=0 and recent LastRunTime proves a completed reported Scheduled Task cycle, but not that data came from exactly one cross-market SQLite transaction; pre/post full-hash ledger fingerprints detect intervening writes, and existing full crypto runtime verification is required by the export builder.
- No shared exclusive writer lock on K5, so extremely narrow races after the final guard and before upload remain to be addressed by publisher/K5 phase sequencing, task cutover and final acceptance.
- The installed old publisher can race any candidate run unless separately disabled in a bounded maintenance window. The guarded script cannot solve the old publisher's behavior without a future authorized task-action cutover.
- Future native Windows tests and a zero-network live-data *preview* in an isolated checkout are required; offline fixture success alone is insufficient for merge or deployment.
- Preserve original Task Scheduler XML/action and original snapshot SHA for rollback. After cutover, restore normal schedule only after verified hosted snapshot and immutable correction/source integrity.
- Keep current correction #9 unchanged. New add-on scripts are not included in the existing AI-v1.1 artifact correction allowlist; an independently reviewed source-integrity/packaging strategy is required before deployment.

## 2026-10-10 revision — no cross-lineage outage or lost accepted snapshot evidence

Owner explicitly requested a PR #48 revision ensuring that incomplete AI-v1.3 does not hold otherwise verified core/expansion website updates. The owner's full scope remains **GitHub-only preparation and offline tests**; this revision is NOT VPS/cutover authority.

The first v0.1 version withheld the entire public snapshot when K5 was Running, missing, failed, stale or changing. That could make even AI-v1.1/AI-v1.2.1 public statistics stale. The prospective v0.2 implementation instead uses:

1. **Fresh current crypto path:** require exact K5 Ready + successful fresh LastTaskResult + upstream and three-ledger fingerprints; export original three-program snapshot into a unique staging path, validate it, recheck K5 and ledger hashes, then publish.
2. **Independent core/expansion fallback:** when K5 is incomplete, crypto export or postcheck fails, or crypto ledgers change, discard that three-program staging attempt and run *new independent* `scripts/export_guarded_core_expansion_v0_2.py` to generate a brand-new current two-program snapshot through the original core and expansion public report builders. The stale `data/public_snapshot.json` is **never** used to supply current core/expansion values.
3. **Historic crypto if available:** only carry forward a previously **accepted** verified crypto aggregate from an append-only, byte-hashed snapshot archive. Set `data_freshness=delayed`, `status=delayed`, health `healthy=false` / `scheduler_healthy=false`, retain true `last_verified_snapshot_at_utc`, and include the original time prominently in the `title`, which the unchanged generic website renders. Never present the last crypto metrics as freshly verified. If no valid prior acceptance exists or archive is damaged, show *only* two current programs (crypto pending), without suppressing healthy core and expansion.
4. **History preservation:** before each attempted upload, retain the exact validated sanitized candidate bytes in a *new* SHA-256-addressed file under `data/guarded-snapshot-history-v0.2/` using exclusive create + fsync; after an upload reports success, append a separate `.accepted` receipt (also exclusive/fsycn). Do not overwrite any previous accepted artifact or modify private append-only AI ledgers. Atomic replacement of `data/public_snapshot.json` occurs only after upload success and acceptance receipt. An interrupted upload may leave a candidate **without** an acceptance receipt; such a candidate is never reused as proven accepted.
5. **No false availability:** a successful read-only core/expansion validation is still mandatory; no fallback is allowed for an unhealthy core/expansion lineage, malformed snapshots, cloud schema failures or source governance failures. An offline pass will not prove operational concurrency or hosted durability.

**New additive file:** `scripts/export_guarded_core_expansion_v0_2.py`. Earlier files remain on the review branch, and the original production runner, original exporter, frozen K3/K4, correction #9 and all current VPS schedulers remain untouched.

**Data semantics:** private crypto/core/expansion SQLite ledgers remain the source of truth; website snapshots are derived publication artifacts. We preserve accepted artifacts prospectively. We cannot guarantee reconstructing *every past unarchived hourly snapshot*, nor atomically commit a single transaction across remote cloud and local disk. Provider/outage and K5 lifecycle gap evidence remains in the untouched ledgers. The `generated_at_utc` of a delayed-crypto publication refers to its **new current core/expansion snapshot**; the crypto's `last_verified_snapshot_at_utc` explicitly refers to older data.

**Open pre-cutover blockers:** narrow race between K5 final check and cloud POST; no shared cross-market writer lock; new core/expansion exporter equivalence to current production under real ledgers; archive retention/rotation/security/storage quota policy; accepted-receipt crash semantics; independent alert completion, historical source backup review and rollback; unchanged old Product Publish task must be contained before cutover; source-integrity provenance for new additive runner/exporter. These are stop conditions, not silently accepted limitations. No public crypto directional signal exposure or broker execution is permitted.

**Required fresh offline tests:** K5 Running while core/expansion *still publish*; current BTC/ETH/SOL success; K5 change during export falling back to 2 programs; failed export with no old-snapshot upload; malformed cached crypto excluded safely; verified old crypto explicitly DELAYED with preserved timestamp; no archive overwrites; failed upload creates no acceptance receipt; no ledger writes; existing 48 public tests unchanged. Repeat native Windows tests against exact revised head only.

## Prospective test matrix

Tests must cover: Running K5 despite prior task result 0; failed or missing task; stale run; invalid timezone; changed task during export; partial market/gate; unhealthy crypto; private signals; stale snapshot; failed exporter with an existing old local snapshot; mid-export ledger mutation; activation disabled by default. Additional native acceptance should cover Windows Task Scheduler output, latest successful K5 report, full three-ledger copy, publisher overlap behavior, and no-stale-publication under failure injection.

Native Windows isolated checkout command (owner may execute after exact PR SHA is communicated):

  python -B -m pytest -q -p no:cacheprovider tests/test_guarded_product_publish_v0_1.py

Do NOT run scripts/guarded_product_publish_v0_1.py, scripts/run_product_publish_guarded_v0_1.cmd, export_public_snapshot.py, notify_forward_events.py, push_public_snapshot.py, or any K5 scanner for these unit tests.

## Future gates (not approved here)

1. Native Windows isolated tests and audit of new source bytes.
2. Full export and publisher safety review; if any existing correction-governed file must change, use new prospective correction, never rewrite #9.
3. Separate owner merge approval for exact commits and controlled final PR review.
4. Separate owner VPS task cutover, task action backup, production sync and rollback approval.
5. Separate owner one-shot sanitized hosted publication and durability check.
6. Re-enable normal publisher only after successful hosted verification and independent frozen-asset proof.

Issue #47 and PR #46 remain open/draft; this successor must remain draft/unmerged pending all gates.
