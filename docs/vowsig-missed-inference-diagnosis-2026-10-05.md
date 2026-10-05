# VowSig AI-v1.1 missed-inference diagnosis — 2026-10-05

_Status: READ-ONLY DIAGNOSIS COMPLETE; PUBLIC/OBSERVABILITY CORRECTION REQUIRED BEFORE ISSUE #9 WAVE 1_

## Scope and safety

This record documents the owner-run read-only VPS diagnosis of the active AI-v1.1 ledgers.

Production remained at `f365f42c349468abd9a84ab4e2d28f4c0636c262`.

No ledger rewrite, backfill, scheduler change, AI/model change, decision-protocol change, broker action or production cutover was performed.

The run ended with `VOWSIG_MISSED_INFERENCE_DIAGNOSIS_READ_ONLY=PASS`.

## Exact diagnosis

Aggregate state:
- valid inferences: 177
- `MISSED_INFERENCE`: 156
- errors: 0
- signals: 17
- `NO_TRADE`: 109
- completed `EXIT` records: 15

| reason | count | share of MISSED_INFERENCE |
| --- | ---: | ---: |
| `no_current_h1_tick` | 153 | 98.08% |
| `scheduler_gap_or_stale_at_discovery` | 3 | 1.92% |
| `rates_not_synchronized` | 0 | 0% |
| `next_h1_open_unavailable` | 0 | 0% |
| other / unknown | 0 | 0% |

| market | total missed | no_current_h1_tick | scheduler_gap_or_stale_at_discovery |
| --- | ---: | ---: | ---: |
| XAUUSD | 52 | 51 | 1 |
| USTEC | 52 | 51 | 1 |
| US30 | 52 | 51 | 1 |

| effective UTC date | no_current_h1_tick | scheduler_gap_or_stale_at_discovery | total |
| --- | ---: | ---: | ---: |
| 2026-09-30 | 3 | 3 | 6 |
| 2026-10-01 | 3 | 0 | 3 |
| 2026-10-02 | 9 | 0 | 9 |
| 2026-10-03 | 72 | 0 | 72 |
| 2026-10-04 | 66 | 0 | 66 |
| **Total** | **153** | **3** | **156** |

Derived:
- `no_current_h1_tick_count = 153`
- `missed_excluding_no_current_h1_tick = 3`
- candidate non-no-tick miss rate = `3 / (177 + 0 + 3) = 1.6667%`

The 1.6667% value is a technical derived rate only. It is not a profitability or missed-trade rate.

## Weekend interpretation

The weekend spike is real in the ledger but is not evidence of missed profitable trades.

- Saturday 2026-10-03: 72 no-tick rows = 24 hourly boundaries × 3 markets.
- Sunday 2026-10-04: 66 no-tick rows = 22 hourly boundaries × 3 markets through 21:00 UTC.
- Weekend effective-boundary no-tick rows: 138.
- 138 rows are 88.46% of all 156 MISSED_INFERENCE records and 90.20% of all 153 no-tick records.
- Detailed Sunday rows still point to the last XAUUSD tick at 2026-10-02 20:57:59Z and the last USTEC/US30 tick at 2026-10-02 20:54:59Z, with newest H1 open at 20:00Z.

This is strong evidence that the large weekend increase came from the hourly fail-closed scheduler continuing to record `no_current_h1_tick` while the markets/feed had no current tick.

Limitation: the diagnostic did not print every one of the 15 weekday `no_current_h1_tick` rows individually. Do not classify all 153 no-tick rows as proven closed-session events without a deterministic session-state check.

## Post-Friday regression check

Diagnostic cutoff: `2026-10-02T00:00:00Z`.

Since that cutoff:
- `no_current_h1_tick`: 147
- `scheduler_gap_or_stale_at_discovery`: 0
- `rates_not_synchronized`: 0
- `next_h1_open_unavailable`: 0
- other MISSED_INFERENCE reasons: 0

The only three `scheduler_gap_or_stale_at_discovery` records are dated 2026-09-30, one per market.

Conclusion: there is **no evidence of a new AI-v1.1 synchronization/staleness regression after Friday**. The weekend jump is an observability/labeling problem, not evidence that AI-v1.1 suddenly missed 156 trade opportunities.

The three historical stale-discovery misses remain immutable evidence.

## Mutation-safety proof

Database SHA-256 values were byte-identical before and after:

- XAUUSD: `659c08514d7df7b0aeb89209a77ab7048f5feb04046a59fd025504e687b42134`
- USTEC: `5445f168b898f4db838a3ce4d3dea201a61e0dff458dc76f8af88f23b113789e`
- US30: `7faec50ebced827cc11251cad9fdefa6a0f34c1a2870f9e24b41de5a820f20dc`

Runtime/scheduler:
- runtime verification: PASS
- runtime: AI-v1.1
- decision protocol: AI-v1.0
- broker execution: disabled
- scheduler before diagnosis: Ready / last result 0
- runtime scheduler health: true
- final scheduler last result: 0
- production HEAD before and after: `f365f42c349468abd9a84ab4e2d28f4c0636c262`
- worktree-clean precheck/final guards passed

## Root cause of misleading public metric

Production observability counts every immutable `MISSED_INFERENCE` together. Production `web/app.js` renders `Missed opportunities = ai.totals.missed_inferences`.

AI-v1.1 intentionally records `NO_CURRENT_H1_TICK` as `MISSED_INFERENCE` with reason `no_current_h1_tick` so the cycle fails closed and cannot be backfilled later. That ledger behavior preserves evidence. The public label is the defect because it presents heterogeneous operational states as if they were missed trade opportunities.

## Public/observability correction — DESIGN ONLY

No implementation or cutover is authorized by this document.

1. Do not change `scripts/run_ai_v1_1_live.py`.
2. Do not alter AI-v1.1 decision semantics or AI-v1.0 decision protocol.
3. Do not rewrite/delete/migrate/backfill any ledger row.
4. In derived observability, expose exact `MISSED_INFERENCE` reason counts for every reason.
5. Preserve raw `missed_inferences` for evidence/backward compatibility.
6. Add derived fields such as `no_current_h1_tick_count`, `processing_miss_count` / `non_no_tick_missed_count`, exact `missed_reason_counts`, and a separately named processing-miss rate with explicit denominator.
7. Replace public **Missed opportunities**. Recommended top-level presentation:
   - **Processing misses:** 3 (1.67% technical cycle rate at this checkpoint)
   - **No-current-tick cycles:** 153
8. Replace per-market **Missed** with a non-misleading reason breakdown (currently 1 processing miss and 51 no-current-tick cycles per market).
9. Explain publicly that no-current-tick cycles are operational availability events, commonly closed-session periods, and are **not missed trades or profitable opportunities**.
10. Do not automatically relabel every `no_current_h1_tick` as `closed_session` unless a deterministic session-state classifier is separately specified and tested.

Expected implementation boundary if later approved:
- `src/trading_signal_intelligence/ai_v1/observability_v1_1.py`
- `src/trading_signal_intelligence/product/ai_insights.py`
- `web/app.js`
- focused tests

The live inference runner and ledger semantics should remain untouched.

Before cutover require exact implementation commit/package review, focused tests, zero-ledger-mutation proof, runtime/protocol/broker/scheduler checks, public snapshot/UI verification, and separate owner publication approval.

## Issue #9 consequence

Issue #9 Wave 1 remains paused. P030-P039 remain unchanged and unsent.

Resume outreach only after the public surface no longer materially implies that closed/no-tick cycles are missed trading opportunities and the correction has been separately approved and verified.
