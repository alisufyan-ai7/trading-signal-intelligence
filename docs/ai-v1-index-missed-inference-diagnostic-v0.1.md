# AI-v1 Index Missed-Inference Diagnostic v0.1

_Status: IN PROGRESS — READ-ONLY LIVE LEDGER RUN PENDING_  
_Date: 2026-09-29_  
_GitHub issue: #10_

## Purpose

Diagnose the high USTEC and US30 AI-v1 `MISSED_INFERENCE` rates without changing the activated AI-v1.0 decision system.

Public snapshot checkpoint at 2026-09-29 18:05 UTC:

| Market | Valid inferences | Missed | Missed rate |
|---|---:|---:|---:|
| XAUUSD | 24 | 2 | 7.7% |
| USTEC | 6 | 19 | 76% |
| US30 | 2 | 23 | 92% |

Aggregate: 32 valid inferences and 44 missed inferences.

## Frozen boundaries

This diagnostic does not change:

- provider/model/parameters;
- policy/prompt;
- feature formulas;
- market universe;
- H1/H4 runtime windows;
- scheduler cadence;
- 300-second freshness boundary;
- signal entry/lifecycle;
- TP/SL/cost rules;
- broker execution state;
- existing immutable records.

Stale opportunities remain missed. They are never retrospectively backfilled.

## Relevant runtime behavior

The activated runtime requests MT5 H1/H4 data with:

`current_bar_is_closed=False`

The generic MT5 connector therefore marks the newest returned bar as incomplete whenever `start_pos == 0`.

The runtime then:

1. considers only bars marked closed;
2. identifies post-activation unprocessed completed H1 opportunities;
3. records `MISSED_INFERENCE` instead of calling the provider if data age exceeds 300 seconds;
4. separately records `next_h1_open_unavailable` when a fresh close exists but the current/entry H1 bar is unavailable.

This creates a hypothesis that must be tested rather than assumed:

> if an index has not produced a new H1 row by the near-:02 scheduler scan, its just-finished H1 bar may remain the newest returned row, be treated as incomplete, and only become discoverable later when it is already stale.

## Diagnostic implementation

Files:

- `src/trading_signal_intelligence/ai_v1/missed_inference_diagnostic.py`
- `scripts/diagnose_ai_v1_missed_inferences.py`
- `tests/test_ai_v1_missed_inference_diagnostic.py`

The diagnostic:

- opens all three AI-v1 databases with the existing SQLite `mode=ro` reader;
- hashes each database before and after;
- fails if any bytes change;
- extracts all `MISSED_INFERENCE` reasons and timing;
- derives detection-delay buckets;
- summarizes misses by source-bar UTC hour;
- measures ordinary inference latency;
- compares every missed index close against XAUUSD's outcome for the same close;
- makes no OpenAI call;
- makes no MT5 call;
- makes no broker call.

## Timing categories

The report distinguishes:

- fresh: <=300 seconds;
- late 5–30 minutes;
- late 30–55 minutes;
- late about one hour: 3300–4500 seconds;
- late 75–150 minutes;
- late over 150 minutes.

The approximately-one-hour category is important because it is consistent with a completed bar only becoming visible to the runtime at the next hourly scan.

## Interpretation

The report may classify the current pattern as:

### CONSISTENT_WITH_LATE_INDEX_BAR_DISCOVERY

Requires a substantial index-miss sample plus:

- >=70% of index misses recorded as `scheduler_gap_or_stale_at_discovery`;
- >=50% discovered approximately one hour late;
- >=30% of those index-missed closes having a valid XAUUSD inference on the same source close.

This is **pattern evidence, not causal proof**.

### NEXT_H1_OPEN_UNAVAILABLE_DOMINANT

Used when at least half of index misses are explicitly `next_h1_open_unavailable`.

### MIXED_OR_UNRESOLVED

Used when the immutable timing evidence does not support one dominant mechanism.

## Causal limitation

The current immutable ledger does not preserve the raw timestamp of the newest MT5 H1 row returned at every historical scan.

Therefore a ledger-only diagnostic can show that index bars were discovered late, but it cannot prove what MT5 returned at the original near-:02 scan.

If the result strongly supports late index-bar discovery, the next admissible step is a separate prospective **read-only MT5 boundary probe**. Such a probe must observe raw bar timestamps only and must not alter the activated runtime.

## Governance

No repair is authorized by this diagnostic.

If a future correction changes which H1 opportunities reach the model, it is decision-affecting and requires separately governed prospective versioning/activation. Existing AI-v1.0 evidence remains immutable.
