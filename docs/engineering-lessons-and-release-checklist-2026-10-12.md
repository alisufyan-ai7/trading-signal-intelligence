# VowSig engineering lessons and verification rules — 2026-10-12

**This is a durable operating record for future chats.** Reconcile these lessons with the latest GitHub main, active issue and exact reviewed commits; it does not grant merge, private ledger, production or trading permissions.

## Product and workflow

**Primary product:** subscription AI trading signals (BUY/SELL with entry, stop loss, TP1/TP2, reasoning, validity and verifiable outcomes). Research is primarily an internal means to improve and validate those signals.

**One PR per independently deliverable feature.** Use commits and issue/PR comments for design, tests, fixes and evidence. Five consecutive draft PRs (#59–#63) for one hourly crypto progress feature added avoidable review overhead. For the consolidated feature, use **PR #63 retargeted to main** as ONE release-candidate PR. Preserve old drafts as historical review evidence but do not individually merge them.

## Defects, causes and permanent countermeasures

| What happened | Lesson / mandatory prevention |
| --- | --- |
| EXP-033 first Windows attempt 127 passed/15 failed with paths ~261–315 chars. Later short NTFS path test 142/142 PASS. | Always use a SHORT isolated NTFS checkout and short pytest basetemp before long native Windows runs. Do not weaken tests to hide environment errors. Preserve the original FAIL. |
| Earlier local synthetic 43-pass suite used a stand-in for the existing strict crypto validator. | Do not call shim-only success release qualification. Run real repository validator, exact pinned file blobs and affected native Windows regressions. |
| PR #62 receipt writer demanded `st_nlink==1` before the hardlink staging name was unlinked (two links existed). Corrected in #63; 156 native tests passed on exact corrected SHA. | Test atomic-write lifecycle: staging name -> atomic target -> unlink staging -> final single-link readback, including interrupted writes and collisions. Preserve strict consumer checks. |
| VSG35 consolidated Windows bootstrap failed PowerShell parsing before any command ran: incorrect parentheses around `([System.IO.DriveInfo]::new("C:\\")).DriveFormat` in chat-pasted `if`. | PowerShell parses the **entire** script block before execution. Use a separate `$DriveFormat = ([System.IO.DriveInfo]::new("C:\\")).DriveFormat` assignment followed by `if ($DriveFormat -ne "NTFS") { ... }` instead of dense inline expressions. Native PowerShell AST-check the **exact whole bootstrap** before asking for owner execution; AST of the downloaded runner alone cannot validate the surrounding chat command. Record this `BOOTSTRAP_SYNTAX_FAIL` separately from pytest; zero tests ran. |
| VSG35 seven-module native Windows consolidation run reached 156 PASS / 1 FAIL at exact SHA `e16e54347b4fbc8d49cdc323eb4eb7a1621bb920` due to `NameError: hashlib` in refactored `test_crypto_epoch_source_v0_1.py` (PR #63 evidence `6125238021`). | When splitting or renaming test modules, audit every imported name; removing an import can leave valid Python syntax but fail at runtime. Run a **focused smoke test** of the refactored positive path before the full suite; keep the failed SHA's 156/1 outcome immutable, and repin test Git blob for the next Windows run. |
| Select-mode PowerShell may appear to hang; one native run took 43m34s. | Exit accidental console Select mode with Esc. Interpret test results by final summary, not apparent waiting; never run duplicate potentially concurrent tests. |
| Crypto public card pinned at 114 historical inferences while newer private observation showed 132. | Never confuse private hourly shadow research with sanctioned public freshness. A historical fixed sample stays explicitly DELAYED until trustworthy new aggregate release. |
| `CRYPTO_WRITER_INTERLOCK_READY=False` correctly blocked unsafe current crypto publication. | Never simply flip a flag. Require stable verified double-read, completed K5 status, same BTC/ETH/SOL H1 cycle, private-data sanitation, freshness and accepted-history non-regression. Seal public aggregate in memory so future writer activity cannot alter the posted bytes. |
| Excessive HMAC/key-custody and filesystem research proposed before validating the same-process threat boundary. | For this single-host aggregate-only release, reuse existing fsynced hash-checked accepted-snapshot archives. A new independent key/receipt infrastructure is not mandatory for trusted in-process transport; revisit if separation/adversarial trust boundaries change. |
| Cross-chat handoffs and date-stale `PROJECT.md` or docs can contradict live GitHub state. | Inspect actual main/PR refs and immutable issue checkpoints each time, state observed runtime vs source vs inference separately. Commit source of truth and learning to GitHub before handoff. |
| One-time private read authority already consumed; historical FAILs risk being lost. | Never reopen consumed authorization or relabel immutable failures. Require fresh explicit owner scope for any real private source read and each subsequent production merge, VPS sync, task and hosted POST. |
| Earlier discussions confused public research beta with a fully paid, economically validated signal service. | Preserve owner-defined subscription goal, distinguish shadow from commercially actionable signals and never invent profitability or paying customers. |

## Small mandatory release checklist

1. ONE consolidated review PR against CURRENT main. Code, synthetic tests, user-facing labels and durable lessons in the same PR. Never merge prior draft stack one-by-one.
2. No change to frozen AI runtime, cost rules, broker execution or crypto public actionable controls. Existing `CRYPTO_WRITER_INTERLOCK_READY=False` remains.
3. Optional feature flag defaults OFF. Until separately authorized, current K5 private read path must never execute on VPS; safe historical DELAYED public card persists.
4. Verify actual K5 task completion, anchored sources, all three ledger chains twice, a single common completed H1, exact frozen C1/C2/C3, no private field leaks or stale/future cycles. On mismatch: HOLD.
5. Keep core/expansion independent; one publisher, one upload, immutable accepted archive; never mislabel old crypto as current; prevent regressions against prior accepted current observations.
6. Run *actual repository* native Windows Python 3.12 six-plus-module tests in short-path isolated clone, including opt-in disabled, current, stale, concurrent-writer, fatal safety check, archive and cloud-failure tests.
7. Check and, whenever practical, parse the **complete operator PowerShell bootstrap** before sharing it (not just its downloaded runner). Record exact test SHA, output, failure evidence and next action in GitHub. Correct defects on same feature PR; rerun once with documented new exact SHA.
8. Separate explicit owner approval for (a) bounded real K5 read-only observation, (b) final exact-SHA review/merge, (c) VPS sync, scheduler/timing, enablement and hosted publication. Validate several natural cycles and public GET evidence.
9. New mistakes must be added here with symptom, root cause, preventative test and durable GitHub reference.

**Principle:** Build quickly, test appropriately, protect production. Strict safety at real trust boundaries; no unnecessary PR/governance multiplication.
