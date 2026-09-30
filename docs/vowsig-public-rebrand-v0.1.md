# VowSig Public Rebrand v0.1

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

Therefore these changes must not be merged into the active production branch until a separately governed non-decision correction/version has been prepared and verified. Merging them directly under the existing activation would make frozen-artifact verification fail closed.

The rebrand implementation is developed on:

`product/vowsig-public-rebrand-v0.1`

Production `main` remains unchanged until the correction boundary is approved.

## Public changes prepared on the rebrand branch

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

## Required safe-cutover sequence

1. Keep production `main` and AI-v1.1 collection unchanged while the rebrand branch is reviewed.
2. Prove all customer-facing rebrand tests on the branch.
3. Define the separately governed non-decision artifact correction/version that authorizes the changed public files without mixing or resetting AI-v1.1 evidence.
4. Reconcile live ledgers, scheduler health, activation anchor and broker-disabled boundary immediately before the correction.
5. Apply only the approved correction/rebrand changes.
6. Verify AI-v1.1 runtime remains healthy and evidence counts continue from the existing v1.1 lineage with no reset/backfill.
7. Verify `https://vowsig.com`:
   - health endpoint;
   - AI insights endpoint;
   - market endpoint;
   - feedback submission boundary;
   - browser title/copy;
   - canonical metadata;
   - cloud snapshot durability.
8. Keep the Railway-generated domain as infrastructure/fallback unless separately retired later.

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

The milestone is complete only when:

- VowSig is the public customer-facing brand;
- `https://vowsig.com` is the canonical public URL;
- hosted VowSig endpoints and UI verify successfully;
- active AI runtime remains AI-v1.1;
- decision protocol remains AI-v1.0;
- v1.0 and v1.1 evidence lineages remain isolated;
- AI-v1.1 evidence continues without reset/backfill;
- broker execution remains disabled.
