# VowSig missed-inference public observability correction v0.1

_Status: REVIEW CANDIDATE ONLY — NO PRODUCTION CUTOVER AUTHORIZED_

## Purpose

Correct the materially misleading public presentation of AI-v1.1 `MISSED_INFERENCE`
records without modifying the frozen AI decision path, live inference runner,
scheduler, broker boundary or immutable ledgers.

Diagnosis source:
`docs/vowsig-missed-inference-diagnosis-2026-10-05.md`.

Review branch:
`product/vowsig-missed-inference-observability-v0.1`.

Branch base:
`ebf926eea5bc3138a782d7d6049bfe567f536b93`.

Production VPS remains:
`f365f42c349468abd9a84ab4e2d28f4c0636c262`.

## Frozen boundaries preserved

This proposal does **not** modify:

- `scripts/run_ai_v1_1_live.py`;
- AI-v1.1 inference/decision semantics;
- AI-v1.0 decision protocol;
- activation anchor or frozen decision artifacts;
- `src/trading_signal_intelligence/product/ai_insights.py`;
- SQLite ledger schema or historical rows;
- scheduler configuration;
- broker execution state;
- market universe;
- backfill behavior.

The initial draft briefly touched `ai_insights.py`, but review identified that artifact
as activation-anchored and outside the current public-surface correction allowlist.
That draft change was reverted. The final review candidate keeps the anchored artifact
exactly equal to `main`.

## Exact correction

### 1. Internal AI-v1.1 observability

File:
`src/trading_signal_intelligence/ai_v1/observability_v1_1.py`

For each market and aggregate totals, keep the existing raw fields unchanged and add:

- `missed_reason_counts`: exact counts of every `MISSED_INFERENCE` reason;
- `no_current_h1_tick_count`;
- `processing_miss_count`;
- `processing_miss_denominator`;
- `processing_miss_rate_excluding_no_current_h1_tick`.

Definitions:

```text
processing_miss_count =
    missed_inferences - no_current_h1_tick_count

processing_miss_denominator =
    valid_inferences + errors + processing_miss_count

processing_miss_rate_excluding_no_current_h1_tick =
    processing_miss_count / processing_miss_denominator
```

The existing raw `missed_inferences` and
`missed_rate_of_processed_opportunities` remain available for immutable evidence and
backward compatibility.

### 2. Cloud/public presentation adapter

File:
`src/trading_signal_intelligence/product/cloud_app.py`

The hosted API reads the already-published immutable snapshot. The new
`_with_public_miss_metrics()` adapter derives public-safe totals using fields already
present in that snapshot:

```text
raw_missed_inferences = totals.missed_inferences
no_current_h1_tick_count =
    min(raw_missed_inferences,
        max(0, totals.sync_operational_counts.no_current_h1_tick))

processing_miss_count =
    raw_missed_inferences - no_current_h1_tick_count

processing_miss_denominator =
    totals.valid_inferences + totals.errors + processing_miss_count

processing_miss_rate =
    processing_miss_count / processing_miss_denominator
```

It adds:

- `totals.no_current_h1_tick_count`;
- `totals.processing_miss_count`;
- `totals.processing_miss_denominator`;
- `totals.processing_miss_rate`;
- `operational_miss_notice`.

It does not mutate the loaded snapshot object.

The no-tick count is explicitly bounded by raw `MISSED_INFERENCE` count so future
`SYNC_STATUS` rows cannot make the public categories exceed the immutable missed
aggregate.

Expected current production rendering from the diagnosed checkpoint:

- raw `MISSED_INFERENCE`: 156, retained but not presented as opportunities;
- no-current-tick cycles: 153;
- processing misses: 3;
- denominator: 180;
- processing-miss rate: 1.6667% (UI: 1.7%).

### 3. Public UI

File:
`web/app.js`

Top AI overview:

- removes **Missed opportunities**;
- adds **Processing misses**;
- adds **No-current-tick cycles**;
- displays processing-miss rate, not legacy aggregate missed rate;
- shows an explanation that no-current-tick cycles are operational availability
  events, commonly closed-session periods, and are not missed trades or profitable
  opportunities.

Per-market cards:

- remove the unseparated **Missed** metric;
- remove **Missed-rate**;
- use `NO_TRADE` in that metric position;
- state that operational miss categories are summarized at aggregate level.

The UI does not fall back to raw `missed_inferences` if separated public fields are
absent. It renders an em dash instead.

## Why per-market processing misses are not shown yet

The existing public snapshot exposes aggregate `sync_operational_counts`, but does not
expose a per-market no-tick breakdown through the anchored AI Insights builder.

Changing that builder is outside the current public-surface correction allowlist.
Therefore this proposal intentionally avoids inventing or approximating a per-market
split. Internal observability has the exact per-market reason breakdown; the public UI
shows only the aggregate separated categories until a separately governed schema change
is justified.

## Tests prepared

### `tests/test_ai_v1_observability_v1_1.py`

Adds a mixed-reason ledger fixture covering:

- `no_current_h1_tick`;
- `scheduler_gap_or_stale_at_discovery`;
- `rates_not_synchronized`;
- `next_h1_open_unavailable`;
- one valid inference.

Asserts exact per-market and aggregate reason counts, no-tick exclusion, denominator,
new processing rate, and preservation of the legacy raw missed rate.

### `tests/test_cloud_ai_runtime_validation.py`

Adds tests that:

- reproduce the diagnosed `177 / 156 / 153` checkpoint;
- assert public output becomes 153 no-tick + 3 processing misses;
- assert denominator 180 and processing rate 1/60;
- prove the input snapshot object is not mutated;
- prove missing counts fail safely to zero;
- prove no-tick public categorization is bounded by raw missed count.

### `tests/test_vowsig_public_miss_metrics_ui.py`

Static regression guard asserts:

- **Missed opportunities** cannot reappear;
- legacy **Missed-rate** cannot reappear;
- aggregate **Processing misses** is present;
- aggregate **No-current-tick cycles** is present;
- per-market raw `missed_inferences` / `missed_rate` are not rendered;
- the UI uses safe missing-field behavior.

## Test execution status

Tests are **prepared but not yet executed** in this chat.

Reason:

- this repository currently has no GitHub Actions workflow;
- this session cannot resolve GitHub from the local container, so an authenticated local
  checkout cannot be obtained here.

No PASS claim should be made until the focused suite is executed in a real repository
checkout.

Recommended focused command after owner review, before any cutover:

```powershell
.\.venv\Scripts\python.exe -m pytest -q \
  tests\test_ai_v1_observability_v1_1.py \
  tests\test_cloud_ai_runtime_validation.py \
  tests\test_vowsig_public_miss_metrics_ui.py
```

Then run the broader public/runtime verification suite appropriate to the existing
public-surface correction runbook.

## Public-surface correction governance

The current correction chain ends at sequence 3:

`research/forward/AI-v1.1-public-surface-correction-v0.2-2026-10-02T123723Z.json`.

If this review candidate is approved for publication, the next governed correction must
be **sequence 4** and supersede that exact sequence-3 artifact.

Current v0.2 validation requires the override set to contain all six allowed public
artifacts, even unchanged ones:

- `observability_source_v1_1`;
- `product_publish_task_runner_script`;
- `cloud_app_source`;
- `cloud_snapshot_verifier_script`;
- `ai_ui_script`;
- `ai_ui_index`.

Only three are proposed to change in this implementation:

- `observability_source_v1_1`;
- `cloud_app_source`;
- `ai_ui_script`.

The sequence-4 anchor must nevertheless carry the exact hashes for all six plus the
complete tracked `web/` manifest, and it must be created only from the final approved
publication commit so upstream/hash verification can succeed.

## Approval boundary

This branch is for review only.

Do not:

- merge it to `main`;
- pull it onto the production VPS;
- create/cut over sequence 4;
- redeploy Railway/public web;
- resume Issue #9 Wave 1;

until focused tests pass and the owner separately approves the exact publication commit
and governed correction package.
