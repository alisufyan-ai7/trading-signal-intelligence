# Documentation Index

## CURRENT VOWSIG RELEASE — NOVEMBER 6, 2026 (READ THIS FIRST)

**Older October guidance below is archival, not a current live-release checkpoint.** PR [#93](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93) is the authoritative draft release branch; refresh its exact HEAD, CI and newest comments. The current release is one complete authenticated Free member/owner launch, with uncertified historical performance **N/A** under explicit owner deferral and Railway PostgreSQL S3/B2 recovery **first immediately postlaunch** under acknowledged temporary data-loss risk. No merge/deploy without separate owner exact-SHA approval.

- [**CURRENT STATUS, decision precedence and evidence**](VOWSIG_START_HERE_CURRENT_STATE.md) — owner-approved vs open work; production SQL 001–010 done, four secrets staged, one read-only app-role TLS check still pending; staging member+owner MFA pass.
- [**Complete Railway staging / from-zero production / in-place upgrade / disaster recovery runbook**](vowsig-railway-zero-to-production-rebuild-runbook.md) — network, volumes, TLS public CA pins, PG roles/migrations, secret matrix, Auth0/Resend, publisher, backup, rollback, DNS and verification.
- [**Product specification**](vowsig-product-contract-current.md) — public, Free, owner, all nine markets, Signal Center, UX, data/privacy, permissible history and roadmap.
- [**New-chat continuation + copy-ready prompt**](vowsig-next-chat-execution-handoff.md) — no lost progress and no redundant scripts.
- [**Exact 17-gate release evidence matrix — current PASS vs HOLD**](vowsig-release-gate-evidence-matrix.md) — one final signed release proof checklist; no false source or recovery claims.
- [**Owner-approved history policy amendment**](vowsig-owner-approved-first-launch-history-deferral-2026-11-06.md), [**one-release signed gate**](vowsig-one-release-signed-gate-and-rollback-2026-11-05.md), [**current minimal production setup**](vowsig-production-setup-shortest-path-2026-11-06.md).

**Product release status:** PR #93 DRAFT/UNMERGED, existing `vowsig.com` publisher and `/data` preserved. Dated prior GitHub/VPS/restoration records below remain intact as history, not a claim that all backups or releases are current.

---


## October 26 GitHub PR cleanup

All original 18 open PRs were classified and safely reduced to [two open drafts](pr-queue-review-2026-10-24.md): [#87 S02 backup/GFS code + tests](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/87), and [#50 frozen-dependency governance guard](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/50). Original #85 and older #77–84 backed-up stage history is retained in `archive/pr85-original-stacked-backup-history-20261024`; unique past IAM/SDK files are in [the inert source archive](../research/archive/pr-queue-2026-10-24/README.md). Source evidence EXP043–059 is committed on `main` and the actual Windows operator results remain dated October 24. No executable PR87 release, VPS cutover or cloud GFS expiration occurred during cleanup.

## Start here — latest verified status, 2026-10-24

- [VowSig current operational status and strict handoff](vowsig-operational-status-2026-10-24.md) — active installed daily S02 dual-cloud backup, actual real recoveries, two-provider version audit, source pins and next actions.
- [Read First](README-FIRST.md) and [Current Handoff](CURRENT-HANDOFF.md) — project isolation, frozen production boundary and instructions to reconcile historical checkpoints.
- [VowSig durable-IP backup plan](vowsig-durable-ip-backup-and-recovery-plan-v0.1.md) — original wider *design*, now annotated with actual S02-only implementation scope.
- [Backup evidence EXP053–EXP059](../research/recovery/README.md) and [Issue #67](https://github.com/alisufyan-ai7/trading-signal-intelligence/issues/67) / [draft PR #85](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/85) — immutable owner-run evidence and pending physical GFS deletion boundary.

- `architecture.md` — system boundaries and data flow
- `decision-log.md` — durable dated decisions
- `data-sources.md` — technical source capabilities
- `legal-data-rights.md` — source licensing/commercial-use research
- `source-status.md` — concise source clearance matrix
- `research-plan.md` — phased validation program
- `windows-setup.md` — first MT5/Binance execution instructions
- `next-actions.md` — immediate checklist
- `project-memory-policy.md` — project context isolation rule
- `working-agreement.md` — how future project work should be maintained
- `current-status.md` — concise current state

- `vowsig-durable-ip-backup-and-recovery-plan-v0.1.md` — durable backup/recovery architecture for VowSig code, ledgers, future training datasets and model artifacts
- `vowsig-ai-first-homepage-hierarchy-v0.1.md` — AI-first public homepage hierarchy with S02 retained as supporting deterministic benchmark evidence
- `ai-v1.3-crypto-expansion-compatibility-v0.1.md` — preactivation source/feature/cost compatibility plan for BTCUSDT / ETHUSDT / SOLUSDT
- `ai-v1.3-crypto-expansion-activation-plan-v0.1.md` — staged approval/activation plan for the isolated crypto AI lineage
