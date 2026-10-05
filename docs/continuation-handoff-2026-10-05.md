# Continuation handoff — 2026-10-05

_Status: DURABLE CHAT HANDOFF — NEXT CHAT SHOULD RECONCILE THIS FILE + ISSUE #9 + REPO STATE BEFORE ACTION_

## Scope

This handoff is for the **TradingTop Analysis / VowSig** project only.

Use only:
- the current/new project chat;
- private GitHub repository `alisufyan-ai7/trading-signal-intelligence`;
- owner-supplied VPS output/files;
- fresh public research only when explicitly needed.

Do not use unrelated chats/projects/repos/account memory.

## Current durable repository state

- GitHub `main`: `ecb4913b880b308711304289a733bd8808701117`
- Production VPS code must remain at:
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`
- **Do not pull VPS merely because main is ahead.**
- Production code after `f365f42...` is docs/research only unless separately governed.
- Broker execution remains disabled.
- AI runtime remains AI-v1.1 / decision protocol AI-v1.0 / SHADOW_ONLY.

## Issue #9 — first cohort customer-value evidence

Issue #9 remains OPEN.

Pre-cohort readiness is PASS.

The first actual recruitment work produced a qualified/contactable Reddit batch on the unmerged research branch:

- branch: `research/issue9-prospect-sourcing-20261004`
- verified head:
  `b39a90ccbc896785f821f8ec3db6d486c3c3a82f`

Current contactable owner-review set:
- P030
- P031
- P032
- P033
- P034
- P035
- P036
- P037
- P038
- P039

Every nominee visibly exposes **Reddit Open chat** in authenticated public-profile UI.

All remain:
- `owner_approved=no`
- `status=identified`
- no outreach timestamp/message/delivery/seen/reply state
- zero outreach performed
- delivery/read capability unknown

Recommended Wave 1 before the production-metric concern was discovered:
- P031 — Pleasant_Rice3949 — A — NQ research/tool workflow
- P032 — chadiusmaximus — A — NQ regime research/manual trading/journaling
- P034 — Journeystep2me — A — XAUUSD + US30 recent multi-market analysis
- P036 — MapDependent7203 — A — XAUUSD strategy testing/validation mindset
- P037 — PurringAdvertising — A — NQ abstention/risk/replay/session process

Wave 2 held:
- P030
- P033
- P035
- P038
- P039

**Do not send outreach yet.** Issue #9 outreach is temporarily paused pending the production `Missed opportunities` diagnosis below.

## Production metric concern discovered before Wave 1

Owner observed the live VowSig production UI showing approximately:

- Valid inferences: 177
- Shadow signals: 17
- Open signals: 2
- Completed trades: 15
- NO_TRADE: 109
- Missed opportunities: 156 / 46.8%
- Errors: 0
- Net R: -1.540R

The owner correctly questioned why `Missed opportunities` jumped over the weekend after appearing correct on Friday.

### Code-level diagnosis already established

Production commit `f365f42...` confirms:

1. `web/app.js` renders:
   `Missed opportunities = ai.totals.missed_inferences`

2. `scripts/run_ai_v1_1_live.py` records synchronization failure states as immutable
   `MISSED_INFERENCE` records.

3. Specifically, when the synchronization result is **NO_CURRENT_H1_TICK**, the runner appends:

- record type: `MISSED_INFERENCE`
- reason: `no_current_h1_tick`

4. Therefore a normal closed-session/weekend hour can contribute to the same aggregate
   `missed_inferences` total shown publicly as **Missed opportunities**.

5. Other possible `MISSED_INFERENCE` reasons include:
- `rates_not_synchronized`
- `scheduler_gap_or_stale_at_discovery`
- `next_h1_open_unavailable`

### Current interpretation

The public label is potentially misleading because it combines operational reasons that are not equivalent to a missed profitable trade/setup.

Do **not** interpret 156 as “156 trades VowSig should have taken.”

Do **not** delete/rewrite any immutable ledger record.

Do **not** change the runtime, scheduler, AI/model, market universe, broker state or existing ledgers from this finding alone.

## Read-only VPS diagnosis — ALREADY RUN BY OWNER

A read-only diagnostic script was prepared and run by the owner on the VPS.

The script was designed to:

- read all three active AI-v1.1 ledgers using SQLite read-only mode;
- hash all three DB files before and after;
- count every `MISSED_INFERENCE`;
- break counts down by:
  - exact reason;
  - market (XAUUSD / USTEC / US30);
  - UTC date;
- calculate a candidate value:
  `missed_excluding_no_current_h1_tick`;
- verify production HEAD/worktree unchanged;
- verify AI-v1.1 scheduler health unchanged;
- end with:
  `VOWSIG_MISSED_INFERENCE_DIAGNOSIS_READ_ONLY=PASS`
  if no mutation occurred.

### Important next-chat instruction

**Do not ask the owner to rerun the diagnostic unless the supplied output is incomplete or invalid.**

The owner will provide the complete VPS diagnostic output in the new chat.

The next chat must first:

1. reconcile GitHub;
2. read this handoff file;
3. review Issue #9 and the sourcing branch status;
4. inspect the owner-supplied diagnostic output;
5. determine exactly:
   - total `MISSED_INFERENCE` count;
   - count by reason;
   - count by market;
   - count by UTC date;
   - how many are `no_current_h1_tick`;
   - how many remain after excluding `no_current_h1_tick`;
   - whether those no-tick records align with closed/session hours;
   - whether any genuine operational regression occurred after Friday;
   - whether the immutable DBs were byte-identical before/after;
   - whether production HEAD/worktree and scheduler remained unchanged.

## Decision path after diagnosis

If evidence shows the public total is dominated by legitimate closed-session
`no_current_h1_tick` records:

- preserve all immutable records exactly;
- design a **public/observability-only correction**;
- do not change AI-v1.1 decision semantics;
- likely separate closed-session/no-current-tick operational counts from genuine processing misses;
- replace or qualify the customer-facing label `Missed opportunities`;
- govern/publish/cut over separately before Wave 1 if the current display is materially misleading.

If the diagnosis shows real synchronization/stale misses after Friday:

- stop and investigate those reasons first;
- do not hide them through a UI-only correction.

No correction is authorized merely by this handoff.

## GitHub records already supporting this handoff

Issue #9 includes comments recording:
- first-cohort readiness PASS;
- prospect sourcing/contact-route history;
- authenticated Reddit contactability;
- 10 contactable candidates;
- Wave 1 recommendation;
- temporary outreach pause for missed-inference diagnosis.

Relevant research branch files:
- `research/customer-discovery/issue9-first-cohort-prospect-tracker.csv`
- `research/customer-discovery/issue9-first-cohort-prospect-sourcing-2026-10-04.md`
- `research/customer-discovery/issue9-contact-route-verification-2026-10-04.md`
- `research/customer-discovery/issue9-contactable-prospect-sourcing-2026-10-05.md`

Relevant production/runtime files:
- `scripts/run_ai_v1_1_live.py`
- `src/trading_signal_intelligence/ai_v1/shadow_runtime_v1_1.py`
- `src/trading_signal_intelligence/ai_v1/observability_v1_1.py`
- `src/trading_signal_intelligence/ai_v1/rates_sync_v1_1.py`
- `web/app.js`

## Stop point

The next chat should begin from the owner-provided **read-only VPS diagnostic output**.

No outreach and no production change should occur before that output is analyzed.
