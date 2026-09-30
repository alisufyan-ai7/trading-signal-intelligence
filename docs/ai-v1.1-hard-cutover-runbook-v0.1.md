# AI-v1.0 -> AI-v1.1 Hard Cutover Runbook v0.1

_Status: PREPARED FOR OWNER REVIEW — NOT AUTHORIZED FOR CUTOVER_  
_Date: 2026-09-30_  
_Parent issue: #15_  
_Canonical handoff: `docs/CURRENT-HANDOFF.md`_

## Purpose

This runbook turns the approved AI-v1.1 cutover design into exact, staged VPS
commands with explicit stop conditions.

It does **not** authorize activation.

The owner must first run the read-only review package in Phase A and provide the
output for review. Only after that output is reviewed may the owner explicitly
approve Phase B onward.

## Non-negotiable boundaries

- AI-v1.0 remains active until Phase B is explicitly approved.
- Broker execution remains disabled.
- No AI-v1.0 ledger is rewritten, moved, deleted, or backfilled.
- The legacy AI-v1.0 scheduled task is disabled, not deleted.
- AI-v1.1 starts with three separate activation-only ledgers.
- AI-v1.1 A1/A2/A3 evidence starts from zero.
- No AI-v1.1 performance-bearing run occurs before its activation anchor is
  committed/pushed and activation-only verification passes.
- No parallel AI-v1.0 / AI-v1.1 collection.
- If any stop condition fails, stop at that phase. Do not improvise.
- The old `scripts/supersede_ai_v1_activation.py` is forbidden for this
  performance-bearing v1.0 lineage.

## Governed cutover-control artifacts

The activation bundle now binds these cutover controls in addition to the
existing v1.1 runtime/observability artifacts:

- `scripts/disable_ai_v1_shadow_task_for_v1_1.ps1`
- `scripts/finalize_ai_v1_0_retirement.py`
- `scripts/activate_ai_v1_1.py`
- `src/trading_signal_intelligence/ai_v1/retirement_v1_0.py`
- `src/trading_signal_intelligence/ai_v1/observability.py`
- this runbook.

Additional safety hardening:

- the v1.1 no-current-hour-tick path records an allowed
  `MISSED_INFERENCE` with reason `no_current_h1_tick`; the frozen shared
  v1.0 ledger implementation is unchanged;
- the v1.1 installer refuses to overwrite an existing v1.1 task and requires
  the legacy v1.0 task to remain present and Disabled;
- an activation-only or unhealthy v1.1 runtime is not cloud-publishable.

---

# Phase A — owner read-only proof / review package

**This phase is allowed before cutover approval. It performs no scheduler,
ledger, activation, retirement, provider, MT5, broker, or cloud mutation.**

Run from:

`C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence`

The owner-approved commit SHA must be supplied separately after this runbook is
fully committed. Do not substitute another SHA silently.

```powershell
$ErrorActionPreference = "Stop"

git pull --ff-only
if ($LASTEXITCODE -ne 0) { throw "git pull --ff-only failed" }

$initialStatus = @(git status --short)
$initialStatus
if ($initialStatus.Count -ne 0) {
    throw "Worktree is not clean. Stop before cutover review."
}

$head = (git rev-parse HEAD).Trim()
"repository_head=$head"

# Replace only with the exact owner-reviewed SHA supplied for this cutover.
$ApprovedHead = "<OWNER-APPROVED-COMMIT-SHA>"
if ($head -ne $ApprovedHead) {
    throw "Unexpected HEAD. Expected $ApprovedHead but found $head"
}

# Focused cutover/regression suite. Warnings are errors.
.\.venv\Scripts\python.exe -m pytest -q -W error `
    tests\test_ai_v1_rates_sync_v1_1.py `
    tests\test_ai_v1_runtime_v1_1_isolation.py `
    tests\test_ai_v1_activation_v1_1.py `
    tests\test_ai_v1_observability_v1_1.py `
    tests\test_ai_v1_active_observability.py `
    tests\test_ai_v1_retirement_v1_0.py `
    tests\test_ai_v1_cutover_controls_v1_1.py `
    tests\test_ai_v1_shadow_runtime.py `
    tests\test_ai_v1_observability.py `
    tests\test_product_ai_insights.py `
    tests\test_cloud_ai_runtime_validation.py `
    tests\test_cloud_snapshot_durability.py `
    tests\test_public_snapshot_push_guard.py

"cutover_control_test_exit=$LASTEXITCODE"
if ($LASTEXITCODE -ne 0) { throw "Cutover control tests failed" }

# Reconfirm the prospective v1.1 state is still clean.
.\.venv\Scripts\python.exe scripts\verify_ai_v1_1_pre_activation.py
if ($LASTEXITCODE -ne 0) { throw "v1.1 preactivation verification failed" }

# Capture the exact current v1.0 retirement preview, including task definition
# evidence, to a UTF-8 JSON file. This is still read-only.
.\.venv\Scripts\python.exe scripts\preview_ai_v1_0_retirement.py `
    --output data\ai_v1_0_retirement_preview.json
if ($LASTEXITCODE -ne 0) { throw "v1.0 retirement preview failed" }

# Exact prospective v1.1 activation material. No write.
.\.venv\Scripts\python.exe scripts\preview_ai_v1_1_activation.py
if ($LASTEXITCODE -ne 0) { throw "v1.1 activation preview failed" }

# Consolidated no-mutation cutover preview.
.\.venv\Scripts\python.exe scripts\preview_ai_v1_1_cutover.py
if ($LASTEXITCODE -ne 0) { throw "v1.1 cutover preview failed" }

# Verify public product remains on v1.0 before cutover.
.\.venv\Scripts\python.exe scripts\export_public_snapshot.py `
    --output data\public_snapshot_pre_cutover.json
if ($LASTEXITCODE -ne 0) { throw "pre-cutover public snapshot export failed" }

$pre = Get-Content data\public_snapshot_pre_cutover.json -Raw | ConvertFrom-Json
"public_runtime=$($pre.ai_v1.runtime_version)"
"public_decision_protocol=$($pre.ai_v1.decision_protocol_version)"
"public_status=$($pre.ai_v1.status)"
"public_publish_allowed=$($pre.ai_v1.publish_allowed)"
"broker_execution_disabled=$($pre.ai_v1.health.broker_execution_disabled)"

if ($pre.ai_v1.runtime_version -ne "AI-v1.0") {
    throw "Public snapshot is not still on AI-v1.0"
}
if ($pre.ai_v1.decision_protocol_version -ne "AI-v1.0") {
    throw "Decision protocol mismatch"
}
if ($pre.ai_v1.health.broker_execution_disabled -ne $true) {
    throw "Broker execution boundary failed"
}

# Reconfirm no v1.1 durable runtime evidence exists.
$v11Ledgers = @(
    Get-ChildItem data\ai_v1_1_*.sqlite -File -ErrorAction SilentlyContinue
)
$v11Anchors = @(
    Get-ChildItem research\forward\AI-v1.1-activation-*.json -File -ErrorAction SilentlyContinue
)

"v1_1_live_ledger_count=$($v11Ledgers.Count)"
"v1_1_activation_anchor_count=$($v11Anchors.Count)"

if ($v11Ledgers.Count -ne 0 -or $v11Anchors.Count -ne 0) {
    throw "Unexpected AI-v1.1 state exists"
}

# Show the two scheduler identities without changing them.
Get-ScheduledTask -TaskName "SignalProof AI-v1 Shadow Scan" |
    Select-Object TaskName, State, Description

Get-ScheduledTask -TaskName "SignalProof AI-v1.1 Shadow Scan" -ErrorAction SilentlyContinue |
    Select-Object TaskName, State, Description

"PHASE_A_READ_ONLY_REVIEW=PASS"
```

## Phase A expected conditions

All of the following must be true:

- clean tracked worktree;
- exact owner-reviewed HEAD;
- focused tests pass with no warnings;
- `preactivation_check=PASS`;
- frozen decision artifacts match upstream;
- v1.1 ledger count = 0;
- v1.1 anchor count = 0;
- v1.0 retirement preview:
  - ledgers valid;
  - unresolved signal count = 0;
  - ready for scheduler cutover = true;
  - scheduler available and state = Ready;
  - broker execution disabled = true;
- activation preview:
  - runtime = AI-v1.1;
  - decision protocol = AI-v1.0;
  - gate carry-forward = false;
  - backfill = false;
  - broker execution = false;
  - provider call = false;
  - ledger records created = 0;
  - anchor written = false;
- consolidated preview performs no writes/calls/scheduler changes;
- public pre-cutover snapshot still reports AI-v1.0;
- legacy v1.0 task remains Ready;
- v1.1 task does not exist.

**Stop after Phase A and provide the complete output for owner review.**

No Phase B command is authorized merely because Phase A passes.

---

# Scheduled-task transition diff for owner review

The scheduler semantics intentionally remain the same.

| Property | AI-v1.0 legacy | AI-v1.1 replacement |
| --- | --- | --- |
| Task name | `SignalProof AI-v1 Shadow Scan` | `SignalProof AI-v1.1 Shadow Scan` |
| Legacy disposition | retained, Disabled | active after install |
| Runner | `scripts\run_ai_v1_shadow_task.cmd` | `scripts\run_ai_v1_1_shadow_task.cmd` |
| Cadence | hourly near minute :02 | hourly near minute :02 |
| StartWhenAvailable | true | true |
| MultipleInstances | IgnoreNew | IgnoreNew |
| ExecutionTimeLimit | 10 minutes | 10 minutes |
| LogonType | Interactive | Interactive |
| RunLevel | Highest | Highest |
| Broker execution | disabled | disabled |
| Main semantic change | none | MT5 H1/H4 rates synchronization before inference |

The v1.1 installer refuses installation if:

- a v1.1 task already exists;
- the legacy task is missing;
- the legacy task is Running;
- the legacy task is not Disabled;
- activation-only v1.1 verification fails.

---

# Public snapshot transition for owner review

Before cutover:

- active runtime: AI-v1.0;
- decision protocol: AI-v1.0.

After v1.1 activation but before its first runtime cycle:

- active runtime: AI-v1.1 locally;
- decision protocol: AI-v1.0;
- v1.1 gate counts = zero;
- status = `activation_only_pre_first_cycle`;
- `publish_allowed=false`;
- `transition_blocked=true`;
- prior cloud snapshot remains unchanged.

After the first performance-bearing v1.1 cycle:

- publication is still blocked unless v1.1 runtime/scheduler health is healthy;
- the v1.1 task wrapper runs the runtime verifier after the live scan;
- a failed live run or failed verifier leaves cloud publication blocked;
- only a healthy verified v1.1 runtime is publishable.

---

# Phase B — disable AI-v1.0 issuance

**MUTATION. Requires explicit owner approval after Phase A review.**

Do not run this while the legacy task is Running.

```powershell
.\scripts\disable_ai_v1_shadow_task_for_v1_1.ps1 -ConfirmCutover

$legacy = Get-ScheduledTask -TaskName "SignalProof AI-v1 Shadow Scan"
"legacy_state_after_disable=$($legacy.State)"
if ([string]$legacy.State -ne "Disabled") {
    throw "Legacy scheduler is not Disabled"
}
```

Stop immediately if the script reports the task was already disabled or was
Running. Do not activate v1.1.

---

# Phase C — finalize, commit, and push AI-v1.0 retirement metadata

The finalizer re-reads all three v1.0 ledgers after the scheduler-disable
boundary and requires their hashes, heads, record counts, and record-type counts
to equal the pre-disable preview.

```powershell
.\.venv\Scripts\python.exe scripts\finalize_ai_v1_0_retirement.py `
    --preview-file data\ai_v1_0_retirement_preview.json `
    --confirm WRITE-AI-V1.0-RETIREMENT-METADATA

if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.0 retirement finalization failed. Keep v1.0 disabled and stop."
}

git status --short

$retirementFiles = @(
    Get-ChildItem research\forward\AI-v1.0-retired-*.json -File
)
if ($retirementFiles.Count -ne 1) {
    throw "Expected exactly one v1.0 retirement metadata file"
}

$retirementRel = Resolve-Path -Relative $retirementFiles[0].FullName
git add -- $retirementRel
git commit -m "Retire AI-v1.0 collector before AI-v1.1 cutover"
if ($LASTEXITCODE -ne 0) { throw "Retirement metadata commit failed" }

git push
if ($LASTEXITCODE -ne 0) {
    throw "Retirement metadata push failed. Keep v1.0 disabled and stop."
}

git status --short
```

Do not create v1.1 ledgers until the retirement metadata commit is durably
pushed.

---

# Phase D — create AI-v1.1 activation-only state

**MUTATION. Still no provider call, MT5 call, live inference, scheduler install,
backfill, or broker execution.**

```powershell
.\.venv\Scripts\python.exe scripts\activate_ai_v1_1.py `
    --confirm ACTIVATE-AI-V1.1-LEDGERS

if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.1 activation failed. Do not install scheduler."
}

git status --short

$v11Anchor = @(
    Get-ChildItem research\forward\AI-v1.1-activation-*.json -File
)
if ($v11Anchor.Count -ne 1) {
    throw "Expected exactly one AI-v1.1 activation anchor"
}

$v11AnchorRel = Resolve-Path -Relative $v11Anchor[0].FullName
git add -- $v11AnchorRel
git commit -m "Anchor AI-v1.1 activation"
if ($LASTEXITCODE -ne 0) { throw "AI-v1.1 activation anchor commit failed" }

git push
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.1 activation anchor push failed. Do not install scheduler."
}

git status --short
```

Expected activation state:

- exactly three v1.1 SQLite ledgers;
- exactly one ACTIVATION record in each;
- exactly one aggregate v1.1 activation anchor;
- provider call = false;
- MT5 call = false;
- scheduler installed = false;
- backfill = false;
- broker execution = false.

---

# Phase E — verify activation-only v1.1 and local public transition

No live inference yet.

```powershell
.\.venv\Scripts\python.exe scripts\verify_ai_v1_1_runtime.py --activation-only
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.1 activation-only runtime verification failed"
}

.\.venv\Scripts\python.exe scripts\export_public_snapshot.py `
    --output data\public_snapshot_ai_v1_1_activation_only.json

if ($LASTEXITCODE -ne 0) {
    throw "Activation-only public snapshot export failed"
}

$activationOnly = Get-Content data\public_snapshot_ai_v1_1_activation_only.json -Raw |
    ConvertFrom-Json

"runtime=$($activationOnly.ai_v1.runtime_version)"
"decision_protocol=$($activationOnly.ai_v1.decision_protocol_version)"
"status=$($activationOnly.ai_v1.status)"
"publish_allowed=$($activationOnly.ai_v1.publish_allowed)"
"transition_blocked=$($activationOnly.ai_v1.transition_blocked)"
"valid_inferences=$($activationOnly.ai_v1.totals.valid_inferences)"
"missed_inferences=$($activationOnly.ai_v1.totals.missed_inferences)"
"errors=$($activationOnly.ai_v1.totals.errors)"

if ($activationOnly.ai_v1.runtime_version -ne "AI-v1.1") {
    throw "Activation-only snapshot runtime mismatch"
}
if ($activationOnly.ai_v1.decision_protocol_version -ne "AI-v1.0") {
    throw "Activation-only decision protocol mismatch"
}
if ($activationOnly.ai_v1.status -ne "activation_only_pre_first_cycle") {
    throw "Expected activation-only pre-first-cycle status"
}
if ($activationOnly.ai_v1.publish_allowed -ne $false) {
    throw "Activation-only v1.1 snapshot must not be cloud-publishable"
}
if ($activationOnly.ai_v1.transition_blocked -ne $true) {
    throw "Activation-only transition must remain publish-blocked"
}
if ($activationOnly.ai_v1.totals.valid_inferences -ne 0 -or
    $activationOnly.ai_v1.totals.missed_inferences -ne 0 -or
    $activationOnly.ai_v1.totals.errors -ne 0) {
    throw "Activation-only v1.1 contains performance-bearing evidence"
}
```

Do not run `push_public_snapshot.py` in Phase E.

---

# Phase F — install the AI-v1.1 hourly task

Only after Phase E passes.

```powershell
.\scripts\install_ai_v1_1_shadow_task.ps1 -ConfirmActivatedRuntime

$legacy = Get-ScheduledTask -TaskName "SignalProof AI-v1 Shadow Scan"
$v11 = Get-ScheduledTask -TaskName "SignalProof AI-v1.1 Shadow Scan"
$v11Info = Get-ScheduledTaskInfo -TaskName "SignalProof AI-v1.1 Shadow Scan"

"legacy_state=$($legacy.State)"
"v1_1_state=$($v11.State)"
"v1_1_next_run=$($v11Info.NextRunTime)"

if ([string]$legacy.State -ne "Disabled") {
    throw "Legacy v1.0 task is not Disabled"
}
if ([string]$v11.State -ne "Ready") {
    throw "v1.1 task is not Ready"
}
```

Do **not** manually invoke `run_ai_v1_1_live.py`.

The first performance-bearing cycle must be the first natural scheduled run.

---

# Phase G — verify the first natural AI-v1.1 cycle

After the first natural scheduled run has occurred, inspect the task and log.

```powershell
$v11Info = Get-ScheduledTaskInfo -TaskName "SignalProof AI-v1.1 Shadow Scan"
$v11Info | Format-List LastRunTime,LastTaskResult,NextRunTime

Get-Content data\forward-task-logs\ai_v1_1_shadow.log -Tail 400

.\.venv\Scripts\python.exe scripts\verify_ai_v1_1_runtime.py --include-scheduler
if ($LASTEXITCODE -ne 0) {
    throw "Post-first-cycle AI-v1.1 verification failed"
}
```

Review all three market results in the task log.

Allowed first-cycle outcomes include:

- synchronized inference path;
- `RATES_NOT_SYNCHRONIZED` -> fail-closed `MISSED_INFERENCE`;
- `NO_CURRENT_H1_TICK` -> fail-closed `MISSED_INFERENCE`;
- valid lifecycle-only actions if applicable.

The following are blockers:

- provider/MT5/runtime failure causing nonzero task result;
- invalid ledger;
- frozen artifact mismatch;
- broker execution boundary failure;
- missing market result;
- v1.0 task no longer Disabled;
- v1.1 scheduler unhealthy.

If blocked, disable the v1.1 scheduler and preserve all v1.1 evidence unchanged.
Do not automatically resume v1.0.

---

# Phase H — validated v1.1 public snapshot

Only after Phase G passes.

The scheduled product publisher may publish only when the active v1.1 report is
healthy and no longer activation-only. A failed/activation-only transition is
blocked by `publish_allowed=false`.

For an explicit owner-controlled publish:

```powershell
.\.venv\Scripts\python.exe scripts\export_public_snapshot.py `
    --output data\public_snapshot.json
if ($LASTEXITCODE -ne 0) { throw "v1.1 public snapshot export failed" }

$public = Get-Content data\public_snapshot.json -Raw | ConvertFrom-Json

"runtime=$($public.ai_v1.runtime_version)"
"decision_protocol=$($public.ai_v1.decision_protocol_version)"
"status=$($public.ai_v1.status)"
"publish_allowed=$($public.ai_v1.publish_allowed)"
"broker_execution_disabled=$($public.ai_v1.health.broker_execution_disabled)"

if ($public.ai_v1.runtime_version -ne "AI-v1.1") {
    throw "Public runtime mismatch"
}
if ($public.ai_v1.decision_protocol_version -ne "AI-v1.0") {
    throw "Public decision protocol mismatch"
}
if ($public.ai_v1.status -ne "forward_validation_in_progress") {
    throw "v1.1 runtime is not publication-ready"
}
if ($public.ai_v1.publish_allowed -ne $true) {
    throw "v1.1 snapshot remains publication-blocked"
}
if ($public.ai_v1.health.broker_execution_disabled -ne $true) {
    throw "Broker execution boundary failed"
}
if ($public.ai_v1.legacy_lineage.gate_counts_carried_into_active_runtime -ne $false) {
    throw "Legacy v1.0 gate counts were mixed into v1.1"
}

.\.venv\Scripts\python.exe scripts\push_public_snapshot.py
if ($LASTEXITCODE -ne 0) { throw "v1.1 cloud snapshot push failed" }
```

After cloud push, verify the hosted product separately before declaring the
transition complete.

---

# Fail-closed rules

## Before the first v1.1 performance-bearing cycle

If a failure occurs after v1.0 has been disabled:

- keep v1.0 ledgers unchanged;
- keep v1.0 task Disabled;
- do not invent a new activation;
- do not delete partial v1.1 evidence;
- do not install/run v1.1 scheduler if activation verification has not passed;
- stop for review.

## After any v1.1 performance-bearing evidence exists

Never silently resume AI-v1.0.

Instead:

- disable v1.1 scheduler;
- preserve v1.1 ledgers and anchor unchanged;
- do not backfill;
- diagnose under a separately governed correction/version;
- leave public AI Insights unavailable rather than misrepresent runtime state.

## Completion condition

Issue #15 cutover is operationally complete only after:

1. v1.0 retirement metadata is committed;
2. v1.0 task remains Disabled;
3. v1.1 activation anchor is committed;
4. v1.1 task is installed and healthy;
5. first natural v1.1 cycle is verified;
6. public snapshot reports runtime AI-v1.1 / decision protocol AI-v1.0;
7. v1.0 and v1.1 gate counts remain isolated;
8. broker execution remains disabled.
