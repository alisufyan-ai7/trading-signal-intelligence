# EXP-2026-023 — VowSig Guarded Product Publisher v0.1

## Scope and ownership

Status: **PROSPECTIVE / DRAFT / OFFLINE-TESTS PENDING / NOT DEPLOYED**.

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

Notification step executes after verified candidate export, before upload; any failure blocks upload. After notifications, the guard checks K5 task stability and compares all crypto ledger fingerprints again. It rechecks the staging bytes and full public validation schema. Only then does it invoke ONE push of the fresh staged file (never --optional, no fallback to the old snapshot). A successful push is followed by atomic replacement of the local data/public_snapshot.json. A held gate never invokes the push.

### Availability tradeoff

If crypto is incomplete, the guard withholds the **whole** update, leaving the last accepted core and expansion public snapshot available but potentially aging to stale. There is no unreviewed fallback exporter for core/expansion only. Such an independent-lineage fallback needs additional design and explicit separate scope. The current legacy scheduled publisher remains unchanged until a later owner-approved safe cutover.

### Known limits to review

- State=Ready plus LastTaskResult=0 and recent LastRunTime proves a completed reported Scheduled Task cycle, but not that data came from exactly one cross-market SQLite transaction; pre/post full-hash ledger fingerprints detect intervening writes, and existing full crypto runtime verification is required by the export builder.
- No shared exclusive writer lock on K5, so extremely narrow races after the final guard and before upload remain to be addressed by publisher/K5 phase sequencing, task cutover and final acceptance.
- The installed old publisher can race any candidate run unless separately disabled in a bounded maintenance window. The guarded script cannot solve the old publisher's behavior without a future authorized task-action cutover.
- Future native Windows tests and a zero-network live-data *preview* in an isolated checkout are required; offline fixture success alone is insufficient for merge or deployment.
- Preserve original Task Scheduler XML/action and original snapshot SHA for rollback. After cutover, restore normal schedule only after verified hosted snapshot and immutable correction/source integrity.
- Keep current correction #9 unchanged. New add-on scripts are not included in the existing AI-v1.1 artifact correction allowlist; an independently reviewed source-integrity/packaging strategy is required before deployment.

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
