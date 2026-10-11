# EXP-031 — Reversible legacy publisher containment (preparation only)

**Authority:** Owner approved `APPROVE EXP-031 REVERSIBLE PUBLISHER CONTAINMENT PREPARATION` on 2026-10-11. This authorizes drafting/review of a cutover package, **NOT** disabling, pausing, triggering, reconfiguring or restarting any Windows task, synchronizing VPS Git, enabling crypto, changing environment settings or publishing to VowSig.

## Exact identities and hard precondition

- Private repo `alisufyan-ai7/trading-signal-intelligence`.
- Newly merged GitHub production `main`: `8ec0e82ea340682d92f9a62acf85171b7715bf5d` (approved PR #56 normal merge; tree identical to tested candidate).
- **Expected old VPS `main` BEFORE source sync**: `47687d8d0e21523e417899a71dddc886ecf25d73` with **clean** Git worktree. Old Git source **must remain untouched** until contained and separately authorized for update.
- Task to contain, and **only this task**: `TradingTop Product Publish`. Last owner read-only inventory: `Ready`, last result `0`, 1 trigger, `IgnoreNew`, action `cmd.exe /c "<VPS repo>\scripts\run_product_publish_task.cmd"`, old runner Git blob `3c5d292338b65c65e0faa5ffe04c1fb2000efa84`. Task runs roughly minute `:05` hourly, so check the actual **future** next time before any containment.
- Active independent scanners to preserve exactly as-is: `SignalProof AI-v1.1 Shadow Scan`, `VowSig AI-v1.2.1 Expansion Shadow Scan`, `VowSig AI-v1.3 Crypto Shadow Scan`. No manual K5 scan.
- Existing private local approved historical sanitized crypto seal `data/crypto-research-asof-v0.1.json`, 3,048 bytes, SHA-256 `f13921a09c3efb77b4c2a874f58073c3e0cf7d59635d7e1900a50a5f957954c4`; do not regenerate, transfer to Git or edit.
- Current sanitized `data/public_snapshot.json` on VPS is maintained hourly, so its SHA **must be captured at execution time**, not treated as an immutable historical SHA. The last observed SHA `67659AE2C6CEE1A7EEA720ACC057822E40FB4FF197B1DCDE057D772FE1B1BDB9` is only 2026-10-11 15:05-cycle evidence.

## Prepared one-file operator procedure (not run or Windows-validated yet)

`ops/handoffs/exp031-reversible-publisher-containment-20261011.ps1` supports:

- **`-Mode Observe` (default)**: GET-only task state, task XML identity, scanner task definitions, Git/hash baseline, current sanitized snapshot metadata, existing historical seal identity and publisher-process count. Writes nothing; no Git fetch, no scheduler action.
- **`-Mode Contain -Confirm APPROVE-EXP031-CONTAIN-PUBLISHER-ONLY`**: this is a **FUTURE SEPARATELY OWNER-AUTHORIZED MUTATION**, not permitted under the present preparation authority. Requires old clean VPS main, exact old runner, existing pinned seal, old task Ready/last result 0, next run more than 10 minutes away and no observed publisher/export/push processes. Creates a *new restricted local* `%ProgramData%\VowSig-EXP031-PreSyncRollback-<UTC>-<random>` directory with task XML, original task runner, byte-exact current sanitized snapshot, and a SHA-256 manifest; it verifies this evidence and unchanged live state **BEFORE** disabling only `TradingTop Product Publish`. After disabling, requires `Disabled`, no observed publisher process, preserved snapshot SHA, unchanged scanner XML, old Git HEAD and exact seal SHA.
- **`-Mode PreSyncRollback -EvidenceDirectory <exact-private-path> -Confirm APPROVE-EXP031-PRESYNC-ROLLBACK-ONLY`**: a **FUTURE SEPARATELY OWNER-AUTHORIZED** restore of only the old product publisher task, permissible **only while production is still on OLD exact clean Git commit**, old runner/task definition matches the protected evidence and local prior snapshot SHA is unchanged. Does not upload or restore the website. It does NOT permit blindly re-enabling the old publisher **after** new source is deployed.
- Fatal or uncertain status means **STOP / preserve local evidence / no automated source sync or recovery**. An already disabled task must not be reenabled merely to clear an error; distinguish local scheduler rollback from an independently required hosted rollback after a possible cloud POST.

Task XML can contain service account/principal metadata. **Never post private XML, snapshot bytes, task credentials, or manifest contents into GitHub/comments/chat**. Keep locally with administrators/SYSTEM-only ACL; only share SHA, success markers and sanitized state.

## Minimal future release sequence (each permission independent)

1. **Next owner permission: one bounded containment execution** after exact Windows PowerShell syntax validation and default `-Mode Observe` preflight. Run ONLY `-Mode Contain` during a safe natural idle window. Capture private rollback path and terminal PASS markers; do **not** sync Git in the same approval.
2. **After observed `EXP031_PRE_SYNC_PUBLISHER_CONTAINMENT=PASS`**, separately request permission to update only the production checkout from old main to exact merged GitHub `8ec0e82...`; check clean/no publisher and verify seal retained. Old publisher stays disabled. Keep core/expansion/K5 tasks unchanged.
3. Separately authorize the new guarded runner in the **same** publisher Task Scheduler identity with task-scoped `VOWSIG_GUARDED_PUBLISH_ENABLED=1`, `VOWSIG_CRYPTO_ASOF_ENABLED=1`, and `VOWSIG_CRYPTO_ASOF_SHA256=<exact approved pin>`. Never enable current crypto writer interlock or a second publisher task.
4. Separately authorize one sanitized historic three-program cloud publication, then inspect public readback (three program IDs, delayed UTC label, BTC/ETH/SOL, C1/C2/C3 all ineligible, no actionable crypto signal/SL/TP, unchanged nine market statuses). A semantic readback is not proof of hosted exact stored-byte digest.
5. Only after a successful publication/reconciliation, separately resume exactly one hourly guarded publisher and observe one natural cycle.

**Status:** PREPARATION ONLY. No Windows syntax/runtime testing of this new preparation script claimed here; no VPS containment action, task mutation, source sync, merge, cloud POST or publication in this milestone. This process does not imply B0–B9 offsite data durability. Owner has already accepted the limited historical-card-only backup deferral; protecting private research ledgers remains a separate high-priority effort.
