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

### Isolated VPS attempt 1 — preserved failure

Exact tested commit:

`56795182ce1ca51e70b0daa3431cf8580bead8ce`

Environment:

- separate detached Git worktree on the VPS;
- production worktree remained on
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- no production checkout/switch;
- no scheduler change;
- no publisher change;
- no ledger mutation.

Results:

- Stage 1 Python compilation: **PASS**;
- Stage 2 focused correction suite: **FAIL — 1 failed, 11 passed**;
- failing test:
  `tests/test_vowsig_public_miss_metrics_ui.py::test_public_ai_ui_does_not_label_raw_missed_records_as_opportunities`;
- exact failed assertion:
  `assert "Processing-miss rate:" in text`;
- Stage 3 regression suite: not attempted;
- full suite: not attempted.

Diagnosis:

The failure was a **stale test assertion**, not evidence of a public-product or
observability implementation failure. The final UI intentionally displays the aggregate
processing-miss rate inside the `Processing misses` value as
`count • fmtPct(t.processing_miss_rate)`. The literal per-market label
`Processing-miss rate:` was removed when per-market raw/unseparated miss metrics were
removed. The canonical design requires the rate to be displayed, but does not require
that literal label.

The test-only correction replaces the stale literal-label assertion with a direct guard
that the UI consumes `t.processing_miss_rate` through `fmtPct(...)`. No production
artifact changed as part of this correction.

Attempt-1 production safety proof:

- production HEAD before/after:
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- production worktree before/after: clean;
- XAUUSD ledger SHA-256 before/after:
  `7a38ce2a8a38b1d136a87d53f1571865e0f8a92fda09f08c106110ca0b14c1f8`;
- USTEC ledger SHA-256 before/after:
  `60457c88d87c30307f0e52c12d2bb909ded3d0d7a311f94564856298d492a620`;
- US30 ledger SHA-256 before/after:
  `9cabb047f00ebfe94c1a00e881be1cefd6252ebadde7e74670b0dc395602a240`;
- AI-v1.1 task before/after: Ready, LastTaskResult 0, definition SHA-256
  `7fd1589aa1e55684897a3b0e908f28ae4cb78ac3789c6f4f20c4917442529b02`;
- publisher task before/after: Ready, LastTaskResult 0, definition SHA-256
  `982d304c4bd9ff3ac859584f1f1a50a31cd5c7f82594cb27fe160c18011435f5`.

### Isolated VPS attempt 2 — preserved baseline-state failure

Exact tested commit:

`faba704cef4515f6f8dc954832b6a23956761ea3`

Results:

- Stage 1 Python compilation: **PASS**;
- Stage 2 focused correction suite: **PASS — 12 passed**;
- Stage 3 governance/runtime/public regression:
  **FAIL — 1 failed, 125 passed**;
- failing test:
  `tests/test_ai_v1_activation_v1_1.py::test_preactivation_report_passes_without_creating_v1_1_state`;
- exact mismatch: expected `preactivation_check == "PASS"`, observed
  `"FAIL"`;
- Stage 4 exact semantics: not reached;
- full repository suite: not attempted.

Diagnosis:

The failure is **baseline post-activation test drift**, not a PR #21 production-code
regression. The failing test, the activation implementation, and the durable activation
anchor are byte-identical on `main` and the tested PR head. The test still assumed that
no AI-v1.1 activation anchor exists, but the current repository intentionally contains:

`research/forward/AI-v1.1-activation-2026-09-30T114412Z.json`

The production implementation correctly defines preactivation readiness as FAIL whenever
an activation anchor already exists. Therefore the observed FAIL is the correct
fail-closed behavior for the current activated repository.

The test-only correction:

1. changes the real repository-state integration assertion to require fail-closed
   `preactivation_check == "FAIL"` with the exact durable activation anchor present;
2. adds a separate prospective clean-state unit case using a temporary root and patched
   pure helpers, preserving explicit coverage that a genuinely clean preactivation state
   would still return PASS.

No production artifact changed as part of this correction.

Attempt-2 production safety proof:

- production HEAD before/after:
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- production worktree before/after: clean;
- XAUUSD ledger SHA-256 before/after:
  `92ccb6cf34860b78becb8eb53a1fda10f4b737ecd0235114ea2db92e6e36f194`;
- USTEC ledger SHA-256 before/after:
  `4331c9ecc6e6e845442c63578c664efd48ac4a4840f063586cfbbf9598d72f49`;
- US30 ledger SHA-256 before/after:
  `614e725ba8879891e153b7ee471c9e3f9f7b506fb6f8050ab5f33b5474b65da3`;
- AI-v1.1 task before/after: Ready, LastTaskResult 0, definition SHA-256
  `7fd1589aa1e55684897a3b0e908f28ae4cb78ac3789c6f4f20c4917442529b02`;
- publisher task before/after: Ready, LastTaskResult 0, definition SHA-256
  `982d304c4bd9ff3ac859584f1f1a50a31cd5c7f82594cb27fe160c18011435f5`.

### Isolated VPS attempt 3 — preserved Windows-path test failure

Exact tested commit:

`e6e353d9cf41dccfcdcc96e3f1f717532a9cb9cb`

Results:

- Stage 1 Python compilation: **PASS**;
- Stage 2 focused correction suite: **PASS — 12 passed**;
- Stage 3 governance/runtime/public regression:
  **FAIL — 1 failed, 126 passed**;
- failing test:
  `tests/test_ai_v1_activation_v1_1.py::test_preactivation_report_fails_closed_after_activation_anchor_exists`;
- exact mismatch: Windows returned
  `research\\forward\\AI-v1.1-activation-2026-09-30T114412Z.json`
  while the test hard-coded the POSIX form
  `research/forward/AI-v1.1-activation-2026-09-30T114412Z.json`;
- Stage 4 exact semantics: not reached;
- full repository suite: not attempted.

Diagnosis:

The observed `preactivation_check == "FAIL"` behavior was correct and the durable
activation anchor was found exactly as intended. The remaining failure was only a
cross-platform path-separator assertion in the test. The production implementation was
not implicated.

The test-only correction canonicalizes the returned path with
`Path(value).as_posix()` before comparison, preserving the exact expected repository
path while making the assertion valid on both Windows and POSIX systems.

No production artifact changed as part of this correction.

Attempt-3 production safety proof:

- production HEAD before/after:
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- production worktree before/after: clean;
- XAUUSD ledger SHA-256 before/after:
  `92ccb6cf34860b78becb8eb53a1fda10f4b737ecd0235114ea2db92e6e36f194`;
- USTEC ledger SHA-256 before/after:
  `4331c9ecc6e6e845442c63578c664efd48ac4a4840f063586cfbbf9598d72f49`;
- US30 ledger SHA-256 before/after:
  `614e725ba8879891e153b7ee471c9e3f9f7b506fb6f8050ab5f33b5474b65da3`;
- AI-v1.1 task before/after: Ready, LastTaskResult 0, definition SHA-256
  `7fd1589aa1e55684897a3b0e908f28ae4cb78ac3789c6f4f20c4917442529b02`;
- publisher task before/after: Ready, LastTaskResult 0, definition SHA-256
  `982d304c4bd9ff3ac859584f1f1a50a31cd5c7f82594cb27fe160c18011435f5`.

### Isolated VPS attempt 4 — required verification PASS

Exact tested commit:

`99ef15ac3f17d6f48ec7dca440bfedba5e0ffdca`

Environment:

- separate detached Git worktree:
  `trading-signal-intelligence-pr21-test-20261005-122435`;
- production worktree remained on
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- PR relation to base at test time: 0 behind, 21 ahead;
- `ai_insights.py` Git blob identity remained
  `8a5991e4fa776c8dfc3a8b7460187ca76e78060d`;
- no production checkout/switch;
- no scheduler change;
- no publisher change;
- no ledger mutation.

Exact commands executed in the isolated PR worktree:

```powershell
C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence\.venv\Scripts\python.exe -m compileall -q src scripts tests
C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence\.venv\Scripts\python.exe -m pytest -q -W error --junitxml=<evidence-dir>\focused.xml tests/test_ai_v1_observability_v1_1.py tests/test_cloud_ai_runtime_validation.py tests/test_vowsig_public_miss_metrics_ui.py
C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence\.venv\Scripts\python.exe -m pytest -q -W error --junitxml=<evidence-dir>\regression.xml <20 required governance/runtime/public regression test files>
```

Results:

- Stage 1 Python compilation: **PASS**;
- Stage 2 focused correction suite: **PASS — 12 passed, 0 failed, 0 errors, 0 skipped**;
- Stage 3 governance/runtime/public regression:
  **PASS — 127 passed, 0 failed, 0 errors, 0 skipped**;
- Stage 4 exact correction semantics: **PASS**;
- warnings: **0 observed**; both pytest stages ran with `-W error`;
- required verification result: **PASS**.

The optional entire-repository pytest suite was **SKIPPED_SAFETY_WINDOW**, not failed.
At that checkpoint only 36.65 minutes remained before the next AI task and 39.70 minutes
before the next publisher task, below the harness's 40-minute threshold. No environment
or code failure occurred in the optional suite because it was not started.

Attempt-4 production safety proof:

- production HEAD before:
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- production HEAD after:
  `f365f42c349468abd9a84ab4e2d28f4c0636c262`;
- production worktree before/after: clean;
- XAUUSD ledger SHA-256 before/after:
  `92ccb6cf34860b78becb8eb53a1fda10f4b737ecd0235114ea2db92e6e36f194`;
- USTEC ledger SHA-256 before/after:
  `4331c9ecc6e6e845442c63578c664efd48ac4a4840f063586cfbbf9598d72f49`;
- US30 ledger SHA-256 before/after:
  `614e725ba8879891e153b7ee471c9e3f9f7b506fb6f8050ab5f33b5474b65da3`;
- all three ledger comparisons: byte-identical `True`;
- AI-v1.1 scheduled task before/after:
  `Ready`, `LastTaskResult = 0`, definition SHA-256
  `7fd1589aa1e55684897a3b0e908f28ae4cb78ac3789c6f4f20c4917442529b02`;
- publisher scheduled task before/after:
  `Ready`, `LastTaskResult = 0`, definition SHA-256
  `982d304c4bd9ff3ac859584f1f1a50a31cd5c7f82594cb27fe160c18011435f5`.

Attempt-4 evidence paths on the VPS:

- summary:
  `C:\Users\Administrator\Desktop\Signal Projects\pr21-vps-test-evidence-20261005-122435\pr21-vps-test-summary.json`;
- transcript:
  `C:\Users\Administrator\Desktop\Signal Projects\pr21-vps-test-evidence-20261005-122435\pr21-vps-test-transcript.txt`;
- isolated tested worktree:
  `C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence-pr21-test-20261005-122435`.

Conclusion:

The required isolated verification of PR #21 has **PASSED** at exact tested commit
`99ef15ac3f17d6f48ec7dca440bfedba5e0ffdca`.

This PASS does **not** authorize merge, production pull, sequence-4 creation, Railway
deployment, public snapshot publication or Issue #9 outreach. The PR remains a draft
review candidate pending the owner's next explicit approval boundary.

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
