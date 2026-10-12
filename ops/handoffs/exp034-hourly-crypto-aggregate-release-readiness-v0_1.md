# EXP-034 — one-task hourly crypto aggregates release-readiness and rollback plan

**Status: RELEASE PREPARATION ONLY — NOT MERGE-READY OR DEPLOYMENT AUTHORITY.**
Prepared 2026-10-12 for the sole feature PR #63 directly against production `main`. This document describes **future owner-approved stages**, not commands to run now. Use only this repo and the active project chat.

## Intended output and immutable safety boundaries

The customer-facing product is actionable AI trading-signal research; **this scope publishes only public BTCUSDT/ETHUSDT/SOLUSDT aggregate research progress** and frozen C1/C2/C3 status, never crypto BUY/SELL entries, prices, stops, targets, alerts, raw observations, credentials, provider payloads, or broker/exchange orders. The existing production **EXP-031 fixed historical DELAYED card** is valid and must survive all current-evidence HOLDs. Keep `CRYPTO_WRITER_INTERLOCK_READY=False`. `VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1` is OFF by default. No change to K5 crypto scanner, economics, risk, activation, frozen gates, or existing core/expansion tasks.

## Evidence pinned for this preparation (recheck every exact SHA at execution)

- GitHub main reviewed: `a4f00578c00c5e23eb4fae073cf2df18c78d9a0a`. Owner-observed live Windows VPS `main` was clean at ancestor `8ec0e82ea340682d92f9a62acf85171b7715bf5d`; four actual K5 observation source/config blobs were identical across those commits. **Do not mistake VPS checkout for remote main or fast-forward it without a separate owner decision.**
- PR #63 core guarded-publisher/product source at verified exact ancestor `ab049b73e78e12e753bcfb473e1aed5671de2f2b`: short-path Windows 3.12 existing-repo seven-module suite **157/157 PASS**. Later source changes in the consolidated branch were confined to one-shot handoff/test and documentation; verify that fact again before merging. Source code still requires fresh manual frozen-dependency review.
- Owner-run native Windows one-shot read-only K5 inspection on separate reviewed standalone file/test: **8/8 synthetic PASS** and **real K5 PASS**, with BTC/ETH/SOL 64 valid inferences each (192 total), 1 completed SOL shadow trade, 0 current open signals, 9 historic missed inferences, zero reported errors, broker/public crypto signal exposure disabled. Natural H1 close `2026-10-12T14:00:00Z`, K5 run `14:04:04Z`, observation `14:56:08Z`; inspection was **outside** the publication 15-minute window. This one-shot private K5 access authorization is CONSUMED.
- Four installed Windows Scheduled Tasks were GET-only observed Ready/last result 0: core `:02`, expansion `:03`, K5 crypto `:04`, and **same existing** `TradingTop Product Publish` `:05`. Its action calls `C:\ProgramData\VowSig-EXP031-HourlyPublisher\guarded-task-runner.ps1`, NOT the legacy publisher. The reviewed EXP-031 process-local launcher (Git blob `87527ebd20eef7900eb9657912efa3557107968b`) pins the old DELAYED seal and sets `VOWSIG_GUARDED_PUBLISH_ENABLED=1` and `VOWSIG_CRYPTO_ASOF_ENABLED=1`; it does **not** set the future current-crypto opt-in.
- The exact existing-task EXP-031 Stage→Enable and first **natural** guarded hosted semantic-readback publication previously PASSED, see Issue #47 comment `6112078271`. Hosted storage full-byte SHA is NOT proved by semantic readback. TaskScheduler/Operational 100/102 log query returned `K5_TASK_HISTORY=UNAVAILABLE`; this is **inconclusive**, not proof of K5 failure, log disabled, or completion latency.
- Original crypto `DELAYED` seal SHA256 `f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4`, 3048 bytes, as-of `2026-10-11T12:07:21.257601Z`. Preserve local one-shot marker, accepted archives/receipts and original ProgramData rollback package. Never regenerate, overwrite or treat historic as current.

## Hard timing contract — no clock manipulation

For source-attested CURRENT research progress, existing prospective PR #63 uses these independent checks:

1. K5's **completed natural** task must report Ready, last result 0, stable before/after reads, and observed last-run age **0–900 seconds** (15 min). A :04 *start* is **not** evidence it has completed at :05.
2. Frozen report/source, full three-ledger hash chains, terminal evidence for the same completed H1, C1/C2/C3, broker/public-off and double-read stability must all pass. An incomplete K5 cycle or concurrent writer causes crypto-only HOLD, never action.
3. A completed epoch must be captured at **H1 close + 0–20 minutes**. The separate public consumer expiry is **under 90 minutes from its verified capture**, not a waiver of the 20-minute original capture bound.
4. Base core+expansion must be freshly and independently exported and checked; the guarded publisher makes **one** sanitized staged/archived snapshot and **one** guarded POST. If prospective crypto proof fails, core+expansion still publish and the previously pinned historic crypto card remains visibly **DELAYED**. Do not falsely advertise a missed/current K5 cycle.
5. Public counts cannot regress against prior accepted current aggregates or the pinned historical baseline. No private source details may appear in stdout, logs or public snapshots.

**Proposed scheduling hypothesis (NOT APPROVED):** retaining the **same publisher task** and shifting its trigger from :05 to approximately **:10 UTC** would allow about six minutes after K5's :04 start, and nominally leaves ~10 minutes for source attestation before the strict H+20 capture limit. It is neither evidence that K5 always completes in six minutes nor a guarantee that the public snapshot posts on time. The process must still FAIL CLOSED for crypto if K5 is not Ready/successful/recent. Existing notifications, core+expansion publisher freshness, timeout budget and hosted POST duration must also be evaluated. The actual installed task action must be reconciled again before staging; no second publisher task may be created.

## Release stages and owner authority — sequential, reversible

### R0 — final candidate / manual frozen dependency check (GitHub-only, no owner task edits)

- Reconcile the exact prospective candidate HEAD/base and changed paths. No unreviewed source additions; preserved historical failed test results. Current diff was 15 paths at initial inspection; **recalculate** after documentation updates.
- Run the owner-required **trusted manual frozen-dependency impact checker** for the exact base/head under short native Windows review checkout. Inspect any exceptions, and do not reinterpret the existing AI-v1.2.1 historic registry mismatch. Confirm original K5 scanner, frozen activation/config, S02/core/expansion/risk/provider and broker pathways unchanged.
- Verify all 7 original publication regression modules at their actual tested source blob anchors (157/157 native predecessor PASS, not a blank check for future code changes), plus the dedicated one-shot probe synthetic 8/8 at its verified SHA. If release code changes, rerun exact new-code native tests before requesting merge.
- Explicitly sign off the future task-scoped EXP-031 launcher successor as a *separate protected ProgramData artifact* with exact expected old/new file SHA-256. It must retain old seal/marker preflight and child-process-only guarded/asof settings while adding only `VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1=1`. Never set the variable globally or weaken interlock/frozen K5. The launcher source must be reviewed and tested *before* deployment; this document itself installs nothing.

### R1 — owner exact-SHA GitHub merge permission only

Request owner approval naming PR #63 exact HEAD and current exact base, after R0 PASSES. Normal merge once only. Merge permission **does not** authorize VPS sync, task schedule/action edit or HTTP POST.

### R2 — separately owner-approved VPS fast-forward source sync only

Check live original exact clean HEAD, frozen inventory, current local snapshots/accepted receipts, EXP-031 original task XML/action/trigger, deployed ProgramData launcher hash, and rollback assets. Acquire a reversible source checkpoint and follow only the approved fast-forward path. No execution, trigger, providers, or publication during sync. Stop if the live checkout or guarded startup differs. Re-check all frozen source contract hashes.

### R3 — separately approved same-task action/launcher/timing staged cutover

- Keep exactly **one** existing `TradingTop Product Publish` task and all three scanner tasks unchanged. Do **not** invoke `Start-ScheduledTask` or create another publisher. Avoid overlapping old/new processes.
- Make a protected local byte-for-byte copy of the EXP-031 ProgramData runner and export original task XML/action/trigger (no secret or raw ledger in GitHub). Verify SHA against source and avoid overwriting old rollback artifacts.
- In a quiet window, stage the reviewed opt-in successor and **only if separately approved**, retime this same task to the validated trigger (candidate :10). Verify exact action, trigger, principal, concurrency policy, disabled/enabled state, and rollback path. Always keep old historical seal enabled as fallback. Never change K5 :04, core :02, expansion :03, or provider/model/risk settings.
- Test readiness/freshness only through permitted **natural** runs; any future private K5 read for actual current-aggregate generation requires its **own explicit prospective production activation authority**, because the earlier one-shot read-only verification was already consumed. No special manual K5 scan.

### R4 — owner-approved unattended publication / hosted readback, then observe

- Distinguish authorization to enable recurring current-aggregate K5 reads and guarded cloud POST from source merge or task retime. No automatic current crypto release merely because code exists in `main`.
- For a natural H1 cycle after approved activation, verify source read accepted or safe HOLD, new public `crypto-expansion-1` is `collecting` only on actual verified completed epoch, BTC/ETH/SOL exact cohort, counts and C1/C2/C3 intact, core/expansion current and healthy, catalog 9 markets, public safety flags false and no crypto actionable detail. Confirm at most one hosted snapshot POST per natural task cycle, local archive/accepted receipt and semantic GET. Do **not** claim full hosted byte-digest proof absent independent hosted byte comparison.
- Observe multiple later natural H1 cycles, including at least one missing/incomplete K5 case: it must publish independent core+expansion and retain the pinned historical **DELAYED** crypto card rather than invent current data. Natural frequency/long-term reliability cannot be proved by one success.

### Rollback and stop conditions

- Any changed or dirty source, unexpected task action/trigger, changed ProgramData launcher or historic seal, provider call outside frozen scanner, unsafe public field, multiple publisher processes, missing accepted archive, failed GET, wrong C1/C2/C3, or unexpected HEAD => **STOP**. Do not rerun a failed cloud POST blindly; its remote acceptance may be ambiguous.
- If an owner-approved activation fails, restore only the original single publisher's reviewed task action/trigger/launcher using preserved exact private local XML and runner hashes, leaving all core/expansion/K5 scanners and append-only private K5 ledgers untouched. Restoration itself requires explicit owner approval after exact failed-state review.
- Retain all historic verified failed attempts, accepted/pending snapshots, original as-of seal, rollback anchors and monitoring evidence. No deletions, rewriting old failures, backfill, alerts, individual crypto signals or trades.

## Next decision boundary

**Current state:** real K5 read-only PASS, new aggregate implementation source native Windows 157/157 PASS on exact checked ancestor, EXP-031 historical publisher active, feature opt-in OFF, PR #63 DRAFT/unmerged, live scheduler :05 with no proven K5 finish dependency. **R0 final exact-SHA manual frozen check and reviewed task-scoped launcher/timing design are still outstanding.** Do not request owner merge/deployment/activation approval until these are prepared and independently verified. Avoid repeated task-history queries: event log evidence was inconclusive.
