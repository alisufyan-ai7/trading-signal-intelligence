# AI-v1.2.1 P3 First-Natural-Run Verification Correction v0.1

_Status: PRE-P3 EXECUTION / OPERATIONAL TOOLING CORRECTION ONLY — 2026-10-07_

## Reason

The published activation-bound task runner executes:

`verify_ai_v1_2_1_runtime.py --include-scheduler`

from inside the scheduled task itself.

The scheduler health probe requires both:

- task state `Ready` or `Running`; and
- `LastTaskResult == 0`.

On the first natural run, the task is still `Running` and Windows Task
Scheduler has not yet published the completed success result. Therefore the
task can fail its own scheduler-health verification even when the AI-v1.2.1
shadow cycle and ledger verification are otherwise healthy.

P3 must not install that first-run behavior.

## Governance treatment

The P3 approval token was granted, but no scheduler installation has been
performed. The approval remains unexercised while this pre-install defect is
corrected and reverified.

Do not modify any activation-bound artifact.

The following remain byte-identical:

- `scripts/run_ai_v1_2_1_live.py`
- `scripts/run_ai_v1_2_1_shadow_task.cmd`
- `scripts/install_ai_v1_2_1_shadow_task.ps1`
- AI-v1.2.1 activation anchor;
- AI-v1.2.1 ledgers;
- AI-v1.2 failed evidence;
- AI-v1.1 runtime/ledgers.

## Additive P3-safe runner

New runner:

`scripts/run_ai_v1_2_1_shadow_task_post_p2.cmd`

It performs:

1. one normal `run_ai_v1_2_1_live.py` scheduled cycle;
2. if the cycle fails, preserve the exit code and skip the secondary verifier;
3. if the cycle succeeds, run `verify_ai_v1_2_1_runtime.py` without
   `--include-scheduler`;
4. return zero only if both the cycle and non-scheduler runtime verification
   succeed.

It intentionally does not perform scheduler-aware verification while the task
is still running.

## Additive P3-safe installer

New installer:

`scripts/install_ai_v1_2_1_shadow_task_p3.ps1`

It preserves all post-P2 preconditions from the published correction and also:

- verifies the activation-bound legacy installer remains unchanged;
- verifies the activation-bound original task runner remains unchanged;
- verifies the activation-bound live runner remains unchanged;
- verifies the new P3-safe runner by its expected Windows CRLF SHA-256;
- refuses to overwrite an existing AI-v1.2.1 task;
- supports `-PlanOnly` with no mutation;
- requires `-ConfirmP2Passed` for installation;
- keeps the task hourly at minute :03;
- keeps broker execution disabled and public exposure disabled.

Before publication, detached `-PlanOnly -ActiveRepoRoot <production>` verification hashes the new runner from the candidate worktree while planning its eventual production path. Mutation mode still rejects an external active-root bridge and therefore can only run from the published production repository.

Expected Windows CRLF SHA-256 of the new P3-safe runner:

`aa4a1dbab8d85c90aaac3fd72a8b3dccfc62d99df080eeea9462c96024451454`

## P3 closure sequence

After this correction is separately tested, published, reconciled and approved
for installation:

1. install the task;
2. do not manually start it;
3. wait for the first natural :03 scheduled run;
4. require the task to return to `Ready`;
5. require `LastTaskResult == 0`;
6. only after task completion run
   `verify_ai_v1_2_1_runtime.py --include-scheduler`;
7. verify AI-v1.1 remains healthy;
8. verify failed AI-v1.2 evidence remains immutable;
9. verify public exposure remains disabled;
10. verify broker execution remains disabled;
11. verify production Git remains exact/clean.

No second manual P2 cycle is permitted.
