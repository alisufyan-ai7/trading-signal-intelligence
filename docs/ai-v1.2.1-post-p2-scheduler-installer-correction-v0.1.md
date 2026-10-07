# AI-v1.2.1 Post-P2 Scheduler Installer Correction v0.1

_Status: PRE-P3 / OPERATIONAL TOOLING CORRECTION ONLY — 2026-10-07_

## Reason

AI-v1.2.1 P2 passed with exactly three valid inferences at the 10:00 UTC boundary. The activation-bound scheduler installer was written before P2 and still verifies the successor with `--activation-only`.

That precondition is intentionally false after a successful performance-bearing P2 cycle, so the activation-bound installer cannot be used for P3.

## Governance treatment

Do not modify the activation-bound installer, runtime, live runner, task runner, activation anchor, or ledgers.

This correction is additive operational tooling only:

`scripts/install_ai_v1_2_1_shadow_task_post_p2.ps1`

It does not change AI-v1.2.1 decision semantics, model/provider parameters, policy, features, guardrails, market universe, synchronization behavior, lifecycle/cost logic, recorded evidence, hourly task runner, scheduled minute (:03), public exposure boundary, or broker execution boundary.

The original activation-bound installer SHA-256 remains:

`87c83b36aa16d880c5ae1ec4244577da7112755812ad75058f284a00e8b06257`

The activation-bound task-runner SHA-256 remains:

`5d4c4435bba10f00a67d5225b057a1a366f8e6b05cd31ade2d46827a08730132`

The activation-bound live-runner SHA-256 remains:

`2079531bd99abf48f7ab81c621b979c703be26e707319db3610a0bc26bb95dd9`

## Frozen P2 evidence required before installation

The post-P2 installer refuses to proceed unless full AI-v1.2.1 runtime verification passes, read-only observability is healthy, the frozen P2 counts match exactly, each market has exactly one valid P2 inference, the three successor ledger SHA-256 values match the P2 PASS evidence, the successor scheduler is absent, and the parallel AI-v1.1 scheduler is healthy.

Frozen P2 ledger SHA-256:

- EURUSD: `02fea7c7e9edc7b294be331acf6689b72738559e11f85125a6971610c6251f81`
- XAGUSD: `47941806a6241bb72acffaa89705bf842db20f8e2b90ecd5c3c61ea86e103eae`
- USOIL: `842d428aef53f2bd5c27b36271c54946ec214a0a9b5ab5cf2c1d873ec4502b8b`

## Plan-only mode

`-PlanOnly` executes all post-P2 preconditions and prints the exact planned scheduler definition but performs no task registration.

This mode is required for VPS verification before P3 publication/installation.

## P3 installation and closure

The published P3 token remains:

`AI_V1_2_1_SCHEDULER_INSTALL`

After explicit owner approval, the installer may be run with `-ConfirmP2Passed`.

Registration alone does not close P3. Closure requires: task registered at minute :03 with the frozen task runner; no public exposure or broker execution; one first natural scheduled run; LastTaskResult = 0; full `verify_ai_v1_2_1_runtime.py --include-scheduler` PASS; AI-v1.1 healthy; production Git clean.

No manual second P2 cycle is permitted.
