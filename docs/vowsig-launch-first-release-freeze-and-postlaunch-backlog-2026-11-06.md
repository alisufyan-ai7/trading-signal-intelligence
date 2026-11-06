# VowSig — launch-first release strategy, freeze, and post-launch backlog

> **NOVEMBER 6, 2026 — OWNER POLICY DECISION NOW RECORDED:** The owner explicitly approved moving independent historical-performance certification **after** the one fully authenticated production launch. Historical Performance Lab and returns remain N/A until separate signed original-source, rights, crypto K5 and external cost validation. The initial owner solo-MFA path is already approved and passed in staging. The original question about whether these two exceptions would be accepted is now **resolved**; prior statements below describing history certification or a two-person *first owner* ceremony as unconditional prelaunch requirements are superseded by [the signed-gate amendment record](docs/vowsig-owner-approved-first-launch-history-deferral-2026-11-06.md). All other critical gates and exact-commit authorization remain unchanged.


**Decision record date:** 2026-11-06 (Asia/Karachi). **Status: PROPOSED fast-release strategy, with explicitly identified owner-decision items; NOT an exact-SHA merge/deploy approval, NOT a waiver of historical binding security/source gates.** This document records the owner's request to stop scope expansion and favor the earliest safe coordinated production launch, plus the engineering recommendation for owner analytics.

**Repository scope:** only `alisufyan-ai7/trading-signal-intelligence`; continue **draft PR #93**. At review, `main=13aeb2bfe2560d3afef63019e4282361fd552faf` and PR #93 candidate `b1a4e1c6993dccf305a5e02033a750419d8337e4`, UNMERGED. GitHub and staging evidence must be rechecked before a release decision. No production deployment, account/secret/provider change, VPS job change, rollback or trading action is authorized by this memo.

## 1. Goal, scope discipline, and governing conflict

**Goal:** move from feature development to a **single coordinated, fully enabled production release** as soon as the actual essential gates are satisfied. Reuse completed, exact-SHA evidence and resolve only demonstrated blockers. No repeating already successful desktop member acceptance, private-source integrity runs, or staging setup without a concrete reason.

**Hard freeze:** no new commercial features, markets, model/research changes, dashboard feature families, general redesign, pricing, paid Auth0, alerts, payments, broker connectivity, execution or public expansion per-signal details. Fix defects and release integration on the existing PR only.

**Important prior owner decision:** `docs/vowsig-integrated-p1-p5-single-release-plan-2026-11-04.md`, `docs/vowsig-owner-ops-model-market-source-reconciliation-2026-11-04.md` and `docs/vowsig-one-release-signed-gate-and-rollback-2026-11-05.md` require the **working owner/admin Command Center and independently verified original-source historical analytics** as part of the one launch, not as a feature-disabled follow-on. This memo **does not silently supersede that requirement**. The earlier informal suggestion that "advanced owner analytics" might be postponed applies only to **optional new visualizations/reporting beyond the already-approved owner/Performance Lab contract**. Any decision to defer the contract's full nine-market historical certification or otherwise narrow the one-launch scope **requires a separate, explicit owner policy amendment** and an updated release acceptance contract before merging. Until then, those requirements stay prelaunch.

**Existing binding exception:** new Railway PostgreSQL automated encrypted offsite backup/cold restore is **first action immediately post-launch**, under the owner's already-approved temporary customer-data-loss exposure. Show `DATABASE_RECOVERY_UNVERIFIED` until an actual isolated restore passes. Existing S02/AWS/B2 backup infrastructure is not equivalent to Railway PostgreSQL recovery.

## 2. Release sequence — minimum safe path

### Phase 1 — freeze and reconcile (no new feature scope)
1. Freeze the owner-approved feature inventory and candidate code; allow only scoped defect, source-truth, owner-security, integration and exact-release documentation corrections.
2. Recheck PR #93 HEAD/base, latest CI, actual staging/prod deployment SHAs, database role/DDL readiness and publication boundaries.
3. Protect existing production publication/Windows schedulers/backups; broker execution remains disabled. Keep all six expansion/crypto markets restricted to the previously approved research/status level.
4. Maintain a single release evidence table: **PASS / FAIL / BLOCKED / EXPLICIT OWNER EXCEPTION**, linked to existing receipts. An old CI PASS never covers a new HEAD.

### Phase 2 — lean acceptance, not perfection
1. **Exact-SHA CI must be green**, including non-regression account/security/PG18 tests and Chromium UI. Fix real failures, not test assertions by deletion.
2. **Customer/provider integration:** reuse Nov5–6 genuine verified Auth0/member desktop PASS (7 pages, 9 catalog entries, six 403 restrictions, watchlist persistence, preference restoration, logout 200→401, fresh login), plus verified Resend delivery and stage-appropriate DB TLS/role receipts. Only rerun affected flows when code/runtime materially changes. Real production auth callback/session security remains mandatory.
3. **Mobile minimum:** fix any demonstrated horizontal overflow (including 375px), then perform brief actual phone-size layout/nav/sign-out smoke at representative widths. A full six-viewport visual audit and cosmetic tuning may occur after launch, but do not ship known clipping or a hidden logout.
4. **Data/publication:** verify genuine source-rights-cleared production publisher and snapshot continuity read-only first. Staging currently has *no usable snapshot*, no configured stage ingestion token and no persistent snapshot volume; do **not** build an elaborate duplicate system merely to populate demo screens. Instead use an approved, minimally scoped genuine-data acceptance route and clear missing/fresh indicators. Never manufacture records or relax the three-vs-six signal gate.
5. **Owner/admin baseline:** complete actual two-person owner identity/factor enrollment and fresh MFA step-up/recovery; owner-only role/permission/SQL proof; ensure existing operational, market reliability, growth, Performance Lab and source-evidence views genuinely work and fail closed when uncertified. Historical claims require the binding independent, complete, after-cost/source-rights/K5 signatures, not a stale public summary or synthetic rows.
6. **Release rehearsal:** verify exact image/SHA, config and migrations under restricted roles, smoke production-safe integration, test compatible rollback restoring prior application without rewriting DB or touching VPS publisher/trading tasks, and attach sanitized evidence.
7. Submit one compact final release sheet with evidence, approved postlaunch DB recovery exception and any requested **policy changes**, then request owner's explicit **exact-SHA merge and production deploy approval**. No automatic merge on CI success.

### Phase 3 — one authorized coordinated go-live
- Merge **only** exact tested/reviewed SHA following owner approval; deploy the intended full product as one release, not a feature-disabled preliminary launch.
- Perform bounded real hosted smoke: public page/markets, auth+member access, source status, privileged MFA, owner route, disallowed market 403, fresh publisher continuity, read-only DB health and rollback readiness. Record final hashes/receipts and keep old image ready.
- Protect real funds and customers: research-only, no execution, no payments, no unapproved signal alerts, no fabricated historical performance.

### Phase 4 — immediately after launch and progressive improvement
- **P0 FIRST:** implement Railway PostgreSQL encrypted recurring offsite backups to approved S3/B2 storage with separate credentials/prefix, scheduled retention/integrity alerts and a **real isolated restore**; retain `DATABASE_RECOVERY_UNVERIFIED` until independently proved. Monitor storage, connectivity, account health and incidents while this accepted risk exists.
- Only then iterate using actual user feedback and measured reliability, not speculative pre-launch feature additions.

## 3. Explicitly move to after launch (unless a defect is critical)

| Postlaunch item | Launch handling | Postlaunch priority |
|---|---|---|
| Fine-grained visual polish, animations, decorative charts, more redesign iterations | Current accessible layout sufficient once known overflow is corrected; no new visual rewrite | P2 |
| Exhaustive 320/375/390/768/1280/1440 real-device matrix, broad WCAG/CWV/performance tuning | A short representative mobile usability/security smoke is still required; actual blocking accessibility/security defects remain prelaunch | P1 |
| New advanced owner report families, drilldowns, exports, equity-curve visuals, custom cross-cohort comparison charts, filters | Do not add beyond the current approved owner dashboard/Performance Lab read-only contract before launch | P1–P2 |
| New retention/revenue cohort models, marketing funnels, exploratory admin KPIs beyond already available truth | Render unavailable rather than inventing a number | P2 |
| Additional historical storytelling, visual explanations or customer-facing performance claims beyond independently attested population | Uncertified figures remain N/A; binding **complete original source certification** stays prelaunch unless separately amended | P1–P2 |
| Non-reproducible first-session browser interruption | Preserve sanitized incident and monitor; investigate immediately if reproducible, security-impacting or observed in production | P1 conditional |
| Extensive cross-browser/device combinations, non-blocking cosmetic usability | Do not rerun passed desktop journeys absent material change | P2 |
| Optional alert, paid-tier, trading/broker connectivity, extra market signals | Outside release authorization, cannot turn on by default | Separate future owner decision |
| Railway PostgreSQL encrypted offsite cold recovery | Already explicitly owner-accepted exception, not a new prelaunch gate | **P0 immediately postlaunch** |

This list is a *deferral of enhancements*, not a waiver of correctness, access boundaries, owner MFA, genuine records, source rights, required historical attestation, critical security or rollback.

## 4. Should advanced owner dashboard analytics be completed before launch?

**Recommendation: YES for the already-approved dashboard contract, but do not start another expansive dashboard build.**

The existing draft has read-only owner-specific **Runtime observability & operating boundaries**, **Model versions & projected lifecycle populations**, **All-market reliability diagnostic**, **Performance Lab**, **Independent history evidence & reconciliation**, and **Growth, access security & recovery**. These are existing UI/adapter foundations, not proof of live owner MFA, complete real source evidence or reliable populated metrics. The full platform Performance Lab supports signed nine-market manifests and source attestation in code, but real external original ledgers and reviewer custody are not certified merely by CI.

**A strict prelaunch finish line:** (a) working authenticated and MFA-stepped owner view; (b) the above existing panels render accurate real-source/DB aggregates; (c) independent source/cohort/after-cost/crypto K5 rights and population proof for claimed history as required by the binding signed release; (d) unavailable metrics remain explicitly unavailable and restricted market details stay hidden; (e) one concise owner-browser pass and a release smoke. No extra graphs, time-series productization, filters, exports, comparisons or new data pipelines as prerequisites.

If real source-independent proof is materially expensive, escalate one explicit owner decision: preserve the original full-history prelaunch requirement **or** approve a clearly defined narrower first-launch evidence population with honest unavailable displays and an amended signed gate. Do not silently label the latter as already approved. Prioritize operational acceptance over cosmetic scope; do not let the owner dashboard become an endless project.

## 5. Honest current evidence checkpoint

- **Previously real PASS:** Work's 2026-11-05 desktop staging [PR #93 QA #6669604932](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/93#issuecomment-6669604932): verified member dashboard, seven routes, nine markets, restricted six 403, watchlist remove/reload/add/reload, settings restore, logout→401, fresh re-login on staging candidate `dfe03621a38c8ad12bf55a46fe491369d6a9d374`. Not a mobile pass or owner MFA.
- **Older CI PASS:** exact `dfe03621...` [Actions #42106587962](https://github.com/alisufyan-ai7/trading-signal-intelligence/actions/runs/42106587962), separate from newer commits.
- **Newer candidate at memo start:** `b1a4e1c6993dccf305a5e02033a750419d8337e4`; [Actions #42111062643](https://github.com/alisufyan-ai7/trading-signal-intelligence/actions/runs/42111062643) **FAILED**. `accounts-contracts` PASS, `browser-qa` FAIL 1/9 due to **horizontal overflow on member All Markets at 375px** in `test_mobile_directory_and_member_watchlist`; 8/9 Chromium tests PASS. This is a real release-candidate CI problem, not an additional optional dashboard feature. Fix narrowly and recheck exact HEAD; do not claim the new changes are tested/deployed.
- Latest already confirmed staging deployment (before this memo) `eb3e0914-c3c7-4147-84ad-491d661ba37f` remains pinned to `dfe03621...`; the new `b1a4e1...` UI code is **not yet deployed**. Reconcile again when making an actual staging change.
- **Open operational/data gate:** staging public snapshot missing. Source-history attestation/owner onboarding/live expanded owner analytics and rollback have not been proven in this memo. No blanket production-ready status.

## 6. Controls on this memo

- This is a **documentation-only proposal**; no code, Railway, Auth0, Resend, PostgreSQL, VPS, scheduler, model, backup or production mutations are authorized.
- Keep a single final compact launch checklist rather than spawning parallel PRs and repeated audits.
- Owner must explicitly authorize any amendment to the previous one-release source-history/owner feature acceptance contract as well as the final exact-SHA merge/deploy.
