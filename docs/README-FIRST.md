# Read First

## Latest verified operations — 2026-10-24

**Read [VowSig current operational status](vowsig-operational-status-2026-10-24.md) FIRST.** This is the newest confirmed backup/recovery/GFS handoff; the 2026-10-12 EXP034/crypto notes below are dated history for a separate workstream.

- Real manual S02 AWS+B2 encrypted backup + independent restore **PASS**; separately, real daily Task Scheduler install and first task-run backup + independent restore **PASS** (Issue #67, draft PR #85, research EXP053/EXP055).
- Both protected backup IDs recovered from **both** providers; exact AWS/B2 data + manifest version pairing passed the **read-only GFS inventory** (EXP059); no deletions.
- Automatic daily S02 task installed at 04:15 **VPS local UTC+00** under Interactive Windows user; next natural day needs fresh verification.
- GFS **30 daily / 8 weekly / 12 monthly** policy is coded **in draft PR #85 only**; physical auto-deletion, failure notifications, broader DB coverage and full-server recovery are **not active**.
- Code/runtime safety: remote main and live VPS HEAD differ; the unmerged PR branch is not installed code. No merge, task modification, IAM delete rights or cleanup is authorized by this documentation update.

Project state is in `PROJECT.md` and `docs/current-status.md`. Immediate execution is in `docs/next-actions.md`. This repository is intentionally isolated from unrelated projects.

## 2026-10-12 single-feature handoff

For current work, **first reconcile GitHub main and the latest milestone/PR refs**; the older root PROJECT.md status is dated and not a live runtime report.

- [Engineering lessons / recurring mistake prevention](engineering-lessons-and-release-checklist-2026-10-12.md) — REQUIRED before starting new code, testing, deployment or handoff.
- [Current control handoff](CURRENT-HANDOFF.md) and GitHub Issue #57 — primary continuity record.
- Single release-focused draft PR #63 consolidates the safe crypto hourly progress feature; earlier drafts #59–#62 remain immutable evidence, not a merge queue.
- Do not assert current crypto hourly publication or use real K5 private records without a fresh explicitly bounded owner approval. The public historical crypto sample remains DELAYED until confirmed otherwise by hosted readback.

## 2026-10-12 latest EXP-034 release preparation (NOT merge/deploy)

Read [the one-task EXP-034 release/rollback plan](../ops/handoffs/exp034-hourly-crypto-aggregate-release-readiness-v0_1.md), the **latest overlay** of [CURRENT-HANDOFF](CURRENT-HANDOFF.md), Issue #57 and PR #63 comments. Earlier "synthetic pending" statements are historical, not the latest status: consolidated implementation source tested **157/157 native Windows PASS**; owner-approved **single real K5 read-only PASS** after 8/8 native smoke tests, **15-minute publication window NOT satisfied at :56**, and private-read authority now consumed. Existing owner-approved EXP-031 guarded publisher **already** occupies the single :05 task, with the fixed historical DELAYED crypto fallback. K5 starts at :04, but there is no demonstrated completion-before-:05 guarantee. The installed task action is ProgramData guarded launcher, **not** legacy .cmd. A prospective opt-in EXP-034 launcher exists in the SAME draft PR; it has **not** passed native PowerShell AST/negative-case tests or been installed. Current crypto opt-in remains OFF. Next: final manual frozen-dependency gate and the native launcher tests, then separate exact-SHA owner merge and subsequent VPS sync/activation approvals. Do not merge, deploy, retime or read private K5 from this preparation-only file.
