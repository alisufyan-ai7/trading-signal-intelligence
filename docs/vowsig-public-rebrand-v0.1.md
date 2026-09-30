# VowSig Public Rebrand v0.1

## Completion status — 2026-10-01

**COMPLETE / PRODUCTION VERIFIED / NATURAL LINEAGE CONTINUITY PASS / ISSUE #16 CLOSED**

Production merge:

`3dfc548b0cd89de1ac9e19723dec1ad44b39ca50`

Final post-cutover proof established:

- VowSig is live at `https://vowsig.com`;
- hosted title/brand/canonical metadata and `/healthz` report VowSig;
- cloud snapshot durability passes;
- active runtime remains AI-v1.1;
- frozen decision protocol remains AI-v1.0;
- runtime mode remains SHADOW_ONLY;
- broker execution remains disabled;
- AI-v1.0 scheduler remains Disabled;
- AI-v1.1 and product-publisher schedulers are Ready and healthy;
- the first natural post-cutover AI-v1.1 cycle extended all three exact
  pre-cutover ledger heads with valid hash-chain links;
- the first natural post-cutover product-publisher cycle republished the
  continued AI-v1.1 lineage;
- no reset, fork, backfill, decision-artifact change, provider mutation, MT5
  mutation, or broker-execution mutation occurred.

## Decision

VowSig replaces SignalProof AI as the public product brand.

Primary canonical domain:

`https://vowsig.com`

The owner manages `vowsig.ai` separately. This milestone does not configure or redirect that domain.

## Product/version naming

Keep brand and research-runtime identifiers separate:

- public product brand: **VowSig**;
- active runtime: **AI-v1.1**;
- frozen decision protocol: **AI-v1.0**;
- runtime mode: **SHADOW_ONLY**.

Do not rename AI-v1.1 to a VowSig version number.

## Historical provenance rule

Historical evidence stays under the name and identifiers that existed when it was created.

Do not rename or rewrite:

- AI-v1.0 retirement metadata;
- AI-v1.1 activation anchor;
- append-only ledgers;
- historical task logs;
- old commits;
- experiment/preregistration records;
- hashes or fingerprints;
- superseded activation records.

New customer-facing product copy may use VowSig.

## Live-runtime safety constraint

The AI-v1.1 activation anchor fingerprints public/product files that this rebrand needs to change, including:

- `web/index.html`;
- `web/app.js`;
- `src/trading_signal_intelligence/product/cloud_app.py`;
- `scripts/verify_cloud_snapshot_durability.py`;
- `scripts/run_product_publish_task.cmd`.

Therefore these changes must not be merged into the active production branch until a separately governed non-decision correction is prepared and verified. Merging them directly under the existing activation would make frozen-artifact verification fail closed.

The governed correction mechanism used for the completed cutover is:

- `observability_v1_1.py` accepts an optional committed/upstream public-surface correction anchor;
- correction overrides are limited to exactly six non-decision artifact names:
  - `observability_source_v1_1`;
  - `product_publish_task_runner_script`;
  - `cloud_app_source`;
  - `cloud_snapshot_verifier_script`;
  - `ai_ui_script`;
  - `ai_ui_index`;
- every artifact outside that allowlist must still match the original AI-v1.1 activation anchor;
- all frozen decision artifacts must still match the original activation lineage;
- the correction anchor must assert no ledger/provider/MT5/scheduler/backfill/broker mutation;
- `scripts/create_vowsig_public_surface_correction.py` is confirmation-gated and creates only the correction JSON evidence file.

The correction anchor was generated, committed, pushed, and verified byte-identical upstream:

`research/forward/AI-v1.1-public-surface-correction-2026-09-30T215809Z.json`

The implementation branch was:

`product/vowsig-public-rebrand-v0.1`

PR #17 was merged into production only after isolated tests, upstream correction verification, live pre-cutover reconciliation, explicit owner approval, paused-task verification, merged-code verification, hosted VowSig verification, and natural post-cutover lineage continuity proof.

## Public changes deployed

- page/browser title becomes `VowSig — Research Beta`;
- public eyebrow becomes `VOWSIG • RESEARCH BETA`;
- customer-facing SignalProof references become VowSig;
- canonical URL becomes `https://vowsig.com/`;
- Open Graph and Twitter metadata use VowSig;
- cloud app title/product/service metadata use VowSig;
- feedback CSV download filename becomes `vowsig-feedback.csv`;
- cloud durability verification defaults to `https://vowsig.com`;
- product-publisher log banner uses VowSig.

## Deliberately preserved operational identifiers

Existing secret/configuration variable names such as `TRADINGTOP_*` and `SIGNALPROOF_*` are not renamed in v0.1. Renaming them would add deployment-secret churn without customer value and could break the running service.

The Windows AI task names also remain unchanged in this milestone because they are operational/historical identifiers tied to the active runtime.

## Completed safe-cutover sequence

1. Keep production `main` and AI-v1.1 collection unchanged while the rebrand branch is reviewed.
2. Prove all customer-facing rebrand tests on the branch.
3. In an isolated worktree on the rebrand branch, run the focused tests and the confirmation-gated correction builder.
4. Review, commit and push exactly one generated `AI-v1.1-public-surface-correction-*.json` anchor to the rebrand branch.
5. Reconcile live ledgers, scheduler health, activation anchor and broker-disabled boundary immediately before production cutover.
6. Under a separate owner-approved cutover, disable the AI-v1.1 scheduler before merging/pulling the rebrand correction into the live worktree.
7. Verify the committed correction anchor is upstream and the corrected AI-v1.1 runtime verifies healthy before re-enabling the scheduler.
8. Re-enable only the AI-v1.1 scheduler; never re-enable AI-v1.0.
9. Verify the next natural AI-v1.1 cycle continues the existing ledger lineage with no reset/backfill.
10. Verify `https://vowsig.com`:
   - health endpoint;
   - AI insights endpoint;
   - market endpoint;
   - feedback submission boundary;
   - browser title/copy;
   - canonical metadata;
   - cloud snapshot durability.
11. Keep the Railway-generated domain as infrastructure/fallback unless separately retired later.

## Non-goals

- no model/provider/prompt change;
- no feature/guardrail/lifecycle/cost-policy change;
- no scheduler cadence change;
- no trading/broker execution;
- no v1.0 re-enable;
- no v1.1 ledger reset or backfill;
- no historical evidence rewrite;
- no `vowsig.ai` work.

## Completion criteria

The milestone completion criteria were:

- VowSig is the public customer-facing brand;
- `https://vowsig.com` is the canonical public URL;
- hosted VowSig endpoints and UI verify successfully;
- active AI runtime remains AI-v1.1;
- decision protocol remains AI-v1.0;
- v1.0 and v1.1 evidence lineages remain isolated;
- AI-v1.1 evidence continues without reset/backfill;
- broker execution remains disabled.
