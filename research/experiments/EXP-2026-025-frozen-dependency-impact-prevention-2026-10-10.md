# EXP-2026-025 — Frozen Dependency Change-Impact Prevention Gate

**Status:** PREPARED ON ISOLATED DRAFT BRANCH ONLY; NATIVE OFFLINE TESTS PENDING; NOT INSTALLED AS A REQUIRED MAIN CHECK; NOT DEPLOYED.

## Authorization and location

Owner requested: *"proceed with recommended next priority"* following EXP-2026-024's 117 exact-commit Windows offline PASS and real VPS **read-only** registry compatibility PASS. This authorizes preparing a permanent pre-merge safeguard in GitHub, **not** merging protected branches, altering existing production binaries/tasks/ledgers, launching scans, or posting website snapshots.

Independent branch: `governance/frozen-dependency-change-impact-gate-20261010` created directly from production `main=47687d8d0e21523e417899a71dddc886ecf25d73`; it does NOT rebase/rewrite stacked draft PRs #46, #48 or #49. This independence is intentional: prevention tooling can be reviewed without modifying correction evidence or crypto code.

**Original incident, unchanged:** AI-v1.2.1's frozen activation (Oct 7) SHA-256 pinned Windows CRLF `config/instruments.json` at `b92b80d1...4491ca`. A later Oct 8 commit `561fcff64b96ca6eb03ef76d70db7f02f92a9625` added BTC-adjacent Binance ETHUSDT and SOLUSDT canonical mappings, changing the Windows CRLF hash to `f2f3d993...cd1681`. Frozen verification **correctly remains FAIL** for one of 34 historical artifacts; the separately approved PR #49 compatibility proof qualified *new derived product operational readiness*, not historical integrity. The five critical safety boundaries (private source-ledger preservation, active lineages, event/scheduler state, non-actionable public crypto and broker disabled) remain unchanged.

## Mechanism

A strictly read-only Python tool `scripts/check_frozen_dependency_impact.py` is designed to be executed **from the trusted target/base commit** against an untrusted candidate PR SHA. It:

1. Reads the *base commit* Git objects for the currently active, explicitly registered anchor files and the source that declared their original pinned artifact maps:
   - AI-v1.1 `research/forward/AI-v1.1-activation-2026-09-30T114412Z.json` with **both** `V11_ARTIFACT_PATHS` and `FROZEN_DECISION_ARTIFACT_PATHS`.
   - AI-v1.2.1 `research/forward/AI-v1.2.1-expansion-activation-2026-10-07T093543Z.json` with `EXPANSION_ARTIFACT_PATHS` (including `config/instruments.json`).
   - AI-v1.3 `research/forward/AI-v1.3-crypto-expansion-activation-2026-10-09T195556Z.json` with `ARTIFACT_PATHS` (also includes `config/instruments.json`).
2. Extracts source maps using strictly limited Python AST constants, string concatenation and static dictionaries. **Never imports or executes** activation/runtime, provider, broker or trading code. Every extracted map key must match exactly the frozen anchor's digest key registry (64 lowercase hex) or the entire check fails closed.
3. Builds a union of all pinned paths, all anchor and map-definition source paths, GitHub CODEOWNERS and guard workflow/script. Blocks changes of **any** of these, regardless of whether an edit appears additive, and blocks new/edited/deleted/renamed AI activation and correction evidence.
4. Computes changed candidate paths using Git merge-base and a binary-safe `git diff --no-renames --name-only -z`; deleted/renamed protected files also fail. No network/provider/secret usage inside the Python gate. A prior *known* historical hash mismatch does **not** whitelist a new edit or automatically fail an unrelated documentation PR.
5. Reports deterministic `FROZEN_DEPENDENCY_CHANGE_IMPACT=PASS`, `BLOCKED` or `ERROR_FAIL_CLOSED`, together with 3-lineage coverage and precise impacted repository paths. No in-PR `--override`, free-text bypass, or unreviewed exception accepted.

### GitHub Actions workflow and enforcement

The additive `.github/workflows/frozen-dependency-change-impact.yml` listens to future PR changes into `main`, **skips draft PRs**, and for non-draft PRs checks out exactly `github.event.pull_request.base.sha`, not the PR's source. It fetches proposed PR head commits as **Git objects only**, validates exact head SHA, and runs the trusted base's `scripts/check_frozen_dependency_impact.py` without provider calls or secrets. It has `contents: read`, a 5-minute timeout, and no trading deployment steps. It does not execute the PR head's Python files; this reduces the bypass surface of changes to the guard script in the candidate.

`.github/CODEOWNERS` identifies the repository owner for the frozen policy, workflow, registry and activation/correction evidence. **GitHub branch protection/ruleset with required passing status `frozen-dependency-change-impact`, code-owner review, prevention of check bypass and restriction on direct push is essential**. Merely adding workflow/CODEOWNERS files on a draft branch is **not active protection**; no ruleset is claimed to be configured by this task. Administrators and repository ruleset limitations must be reviewed explicitly. Self-edits to workflow/security policy require out-of-band, owner-approved governance with clear audit evidence. No secret-based unchecked exemptions are built in.

**First activation bootstrap:** because the script does not yet exist on the current trusted `main`, a ready-for-review PR cannot successfully execute the trusted-base script until the new check is separately authorized and merged under a reviewed one-time bootstrap. Do NOT silently weaken the gate to execute PR-head code. After bootstrap, require the status via branch protection/ruleset. This bootstrap and GitHub Actions minutes are separately owner-controlled. Workflow dispatch/manual running is not required or authorized by this preparation.

### Intentional conservative behavior

- Any change touching frozen AI-v1.1/AI-v1.2.1/AI-v1.3 active artifacts **blocks** until a separately approved successor activation/versioned compatibility governance release is arranged. The guard does not accept a casual bypass string. A future prospective exception requires its own preregistration, exact old/new hashes and safe CI rollout with explicit owner approval.
- New activation anchors require extending the trusted base's registration first, via supervised governance; old active anchors never disappear silently.
- Data/evidence history, observed ledger health and snapshot data are not changed or reclassified. The guard is **prevention**, not a proof that current runtime health or historical data retention is complete. It does not repair PR #49 or replace original runtime attestation.
- GitHub Action minutes and branch protection entitlement/settings are not assumed; until enforced this is prepared documentation/code and offline test evidence only.
- Existing open draft PRs #46, #48, #49 and their frozen public-surface changes may be affected by this future gate. Such releases must be explicitly sequenced/handled through authorized governance; do not bypass the gate silently, retroactively mark historical artifacts PASS, or merge correction PRs without owner authorization.

## Prospective tests

`tests/test_frozen_dependency_change_impact.py` performs only local disposable Git fixture commits and static Git reads. Required cases: safe nonprotected docs PASS; exact path instrument-registry edit BLOCK; arbitrary frozen script/map/anchor edits BLOCK; guarded workflow/script and CODEOWNERS self-change BLOCK; new activation/correction evidence BLOCK; delete/rename protected artifact BLOCK; malformed/missing anchor map keys FAIL CLOSED; path traversal/Windows separators rejected; static AST raises no runtime import side-effects; real three active manifests parse and have expected broad coverage; preexisting historical hash drift never allows a second edit.

Before advancing, run exact-SHA isolated native Windows Python 3.12 pytest on the new test file, optionally existing contract-only suites, with plugin auto-load and bytecode cache disabled. **No** GitHub Actions run, repository merge, VPS task mutation, broker/provider trading or website publication during this preparation. If test fails, correct the new isolated draft only and pin new exact SHA for retest.

## Release gates (all pending)

1. GitHub draft PR reviewed, exact native offline unit tests pass; baseline active-lineage map coverage verified from the exact main base SHA.
2. Confirm the real target protected branch and existing PR exceptions/admissible governance before activation, preserve correction #9 historical evidence.
3. Owner explicitly approves **separate** merge/bootstrap, workflow CI and mandatory branch-protection/ruleset; verify real PR positive/negative detection with a test PR, no bypass.
4. Independently revisit archival backup/retention, K5/publication race and publisher cutover/rollback under separate authorizations. This prevention tool does not grant permission to do them.

All code and approvals apply to **only** `alisufyan-ai7/trading-signal-intelligence`, under this chat's context isolation.
