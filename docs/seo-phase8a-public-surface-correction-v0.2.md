# AI-v1.1 Public-Surface Correction v0.2 / Supersession Design

_Status: ISOLATED BRANCH IMPLEMENTED / OWNER VPS TESTS PENDING / NOT FOR PRODUCTION MERGE_  
_Date: 2026-10-02_  
_Parent milestone: GitHub Issue #8 — Organic acquisition & SEO v0.1_  
_Branch: `product/vowsig-seo-phase8a-v0.1`_

## 1. Purpose

Phase 8A SEO work needs to change customer-facing files that are already
fingerprinted by the active AI-v1.1 evidence boundary.

The current production correction:

`research/forward/AI-v1.1-public-surface-correction-2026-09-30T215809Z.json`

is valid, upstream, immutable provenance for the VowSig rebrand.

It must not be rewritten, replaced in-place or deleted.

The v0.2 mechanism introduces an ordered supersession chain so later
non-decision public-surface changes can be governed without mutating historical
corrections or weakening the frozen decision-artifact boundary.

## 2. Non-goals

This mechanism does not authorize or change:

- AI model/provider;
- prompt/policy;
- feature definitions;
- decision schema;
- guardrails;
- lifecycle;
- cost model;
- inference cadence;
- S02;
- AI-v1.1 ledgers;
- activation records;
- A1/A2/A3 thresholds;
- scheduler cadence;
- MT5 behavior;
- provider calls;
- backfill;
- broker execution.

It is only a public/non-decision artifact-governance mechanism.

## 3. Backward compatibility

The existing v0.1 correction remains valid as the legacy root correction.

Production behavior before a v0.2 correction exists remains unchanged:

- zero corrections -> activation hashes only;
- exactly one valid legacy v0.1 correction -> current production behavior;
- one legacy correction plus a valid ordered v0.2 chain -> newest v0.2 tip is
  the active public-surface correction.

Therefore introducing the new verifier code does not require rewriting the
existing v0.1 JSON.

## 4. Correction chain model

The legacy v0.1 correction is sequence 1.

Every v0.2-schema correction contains:

- `correction_kind = AI-v1.1-public-surface-v0.2`;
- `correction_schema_version = 2`;
- monotonically increasing `sequence_number`;
- exact `supersedes_correction` path;
- exact SHA-256 of the predecessor correction bytes;
- exact original AI-v1.1 activation anchor path + SHA;
- full effective hashes for the existing public-surface correction allowlist;
- exact tracked `web/` tree manifest;
- VowSig brand + canonical-domain identity;
- explicit false mutation/broker flags.

The verifier builds the chain by predecessor links rather than filename order.

## 5. Fail-closed chain rules

The verifier rejects:

- more than one legacy v0.1 root;
- unknown correction kinds;
- orphaned v0.2 corrections;
- two successors of the same predecessor (fork);
- wrong predecessor path;
- wrong predecessor SHA-256;
- non-monotonic sequence numbers;
- wrong runtime or decision-protocol version;
- wrong brand or canonical domain;
- wrong activation anchor;
- correction overrides outside the frozen allowlist;
- incomplete v0.2 override set;
- invalid SHA-256 values;
- invalid/missing tracked-web manifest;
- an upstream correction mismatch;
- any frozen/non-correctable AI-v1.1 artifact mismatch.

A partial or ambiguous correction state therefore fails closed rather than
silently choosing a correction.

## 6. Existing activation-bound public artifact boundary

v0.2 preserves the existing narrow allowlist:

- `observability_source_v1_1`;
- `product_publish_task_runner_script`;
- `cloud_app_source`;
- `cloud_snapshot_verifier_script`;
- `ai_ui_script`;
- `ai_ui_index`.

The allowlist still has no overlap with
`FROZEN_DECISION_ARTIFACT_PATHS`.

Every v0.2 correction records the **full effective hash set** for those six
artifacts, even when only one changed. This prevents a successor correction
from accidentally dropping a prior public-surface override.

## 7. New exact tracked-web-tree boundary

The v0.1 correction guarded `web/index.html` and `web/app.js` through the
activation-bound artifact list, but other public files such as
`web/styles.css` were outside that hash boundary.

v0.2 adds:

`tracked_web_artifact_hashes`

This is an exact manifest of every Git-tracked file under `web/`.

The active v0.2 verifier:

1. obtains the Git-tracked `web/` file list;
2. hashes every tracked web file;
3. requires the exact path set to match the correction manifest;
4. requires every hash to match;
5. cross-checks `web/index.html` and `web/app.js` against the existing
   activation-bound artifact overrides.

This means future Phase 8A additions such as:

- market HTML pages;
- education HTML pages;
- `robots.txt`;
- `sitemap.xml`;
- CSS changes;
- approved public images/assets

cannot silently bypass the public-surface integrity check when the active
correction uses the v0.2 schema.

Untracked local files are not part of the evidence manifest; correction
creation requires a clean tracked worktree and production files must be
committed before correction creation.

## 8. Builder behavior

New builder:

`scripts/create_vowsig_public_surface_correction_v0_2.py`

Exact confirmation token:

`CREATE-VOWSIG-PUBLIC-SURFACE-CORRECTION-V0.2`

The builder:

1. requires a clean tracked worktree;
2. requires exactly one AI-v1.1 activation anchor;
3. verifies runtime/protocol/broker boundary;
4. validates the currently active public-surface correction chain;
5. uses the active chain tip as the predecessor;
6. verifies all non-correctable AI-v1.1 artifacts still match activation;
7. verifies every frozen decision artifact still matches activation;
8. records the complete current six-artifact public override set;
9. records the exact Git-tracked `web/` tree manifest;
10. rejects a byte-identical no-op successor;
11. writes one new correction JSON only.

It has no MT5, provider, ledger, scheduler or broker implementation dependency.

## 9. Why v0.2 is reusable

The v0.2 schema is a chain schema, not a one-off SEO hash.

After the first v0.2 correction, a later non-decision public-surface change may
create another v0.2-schema successor with:

- the next sequence number;
- the prior correction path/SHA as predecessor;
- a new full six-artifact hash set;
- a new exact tracked-web manifest.

The verifier code does not need another format change merely because the public
surface changes again.

Any future expansion outside the existing public allowlist + tracked `web/`
tree requires separate governance; it must not be silently added.

## 10. Planned Phase 8A implementation constraint

To remain inside the v0.2 governance boundary, the first SEO implementation
should prefer:

- customer content/assets under the tracked `web/` tree;
- route/response/header changes inside the already-governed
  `cloud_app.py`;
- existing public publisher/verifier files only where necessary.

Do not introduce new public-serving Python modules outside this boundary during
the first SEO implementation unless they receive separate explicit governance.

## 11. Test coverage implemented on the isolated branch

New tests cover:

- a valid legacy -> v0.2 chain selects the unique tip;
- correction forks fail closed;
- wrong predecessor hashes fail closed;
- exact tracked-web manifest mismatches fail artifact verification;
- builder confirmation gating;
- builder mutation flags remain false;
- builder contains no MT5/provider/ledger/scheduler trading dependency strings.

Existing v0.1 tests remain in place and must continue to pass.

## 12. Required isolated verification before website changes

On a clean isolated worktree for the branch:

1. run the existing v0.1 correction tests;
2. run the new v0.2 correction tests;
3. run observability/runtime regression tests;
4. prove frozen decision artifacts unchanged;
5. prove production ledgers are not touched;
6. do **not** run the v0.2 builder yet unless explicitly instructed for an
   isolated correction-generation checkpoint;
7. do not merge;
8. do not deploy.

The first goal is to prove the supersession mechanism itself before editing the
website.

## 13. Later correction-generation sequence

After the mechanism tests pass and the first SEO implementation is reviewed:

1. commit all approved public-surface code/content on the isolated branch;
2. run the v0.2 builder once with the exact confirmation token;
3. inspect the generated predecessor link, six effective hashes and full
   tracked-web manifest;
4. run the complete artifact/frozen-decision verifier locally;
5. commit/push the generated correction anchor;
6. prove the correction is upstream-valid;
7. only then prepare a separately approved production cutover.

## 14. Production cutover boundary

No production merge is authorized by this design document.

A later production cutover must again prove:

- active AI-v1.1 runtime/ledger health before pause;
- exact ledger heads/counts;
- broker execution disabled;
- scheduler state controlled;
- reviewed branch head exact;
- correction chain upstream-valid;
- frozen decision artifacts unchanged;
- exact ledger continuity across cutover;
- hosted VowSig SEO/public surface correct;
- natural post-cutover AI-v1.1 lineage continuity.

## 15. Current status

- [x] live Phase 8A baseline complete;
- [x] v0.2 supersession design documented;
- [x] isolated verifier implementation added;
- [x] isolated builder implementation added;
- [x] fail-closed unit tests added;
- [ ] owner/VPS isolated tests passed;
- [ ] mechanism accepted for Phase 8A website implementation;
- [ ] website SEO implementation started;
- [ ] correction anchor generated;
- [ ] production cutover approved.

No production website mutation has occurred.
