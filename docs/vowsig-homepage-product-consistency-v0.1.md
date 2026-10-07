# VowSig Homepage Product Consistency v0.1

_Status: isolated implementation / not approved for production publication_

Parent tracker: #30

Implementation issues: #31, #32, #33, #34, #35.

## Objective

Make the public homepage easier to interpret without changing any trading,
research, evidence or execution semantics.

The correction addresses five presentation risks found after the scalable
multi-lineage observability release:

1. legacy/S02 collector health was presented as generic whole-system health;
2. snapshot age was not surfaced, allowing an old snapshot to continue looking
   operational;
3. S02 benchmark sections visually followed AI sections without sufficiently
   explicit lineage attribution;
4. AI-v1.2.1 expansion markets overlapped with S02 transfer-research markets
   without enough explanation that those evidence programs are independent;
5. customer-facing copy exposed implementation details and the homepage showed
   too much evidence at once.

## Freshness semantics

The public cloud health endpoint derives snapshot freshness from the immutable
snapshot generation timestamp.

- fresh: age < 90 minutes;
- delayed: age >= 90 minutes and < 150 minutes;
- stale: age >= 150 minutes;
- unknown: timestamp missing/invalid;
- missing: no cloud snapshot exists.

The homepage treats delayed, stale, unknown and missing states as attention
states. Freshness does not mutate evidence and does not change scheduler
health.

## Lineage attribution

The homepage must keep these separate:

- Core AI-v1.1 shadow intelligence: XAU/USD, NASDAQ 100, DOW 30.
- AI-v1.2.1 expansion validation: EUR/USD, XAG/USD, WTI; aggregate research
  progress only, with no entry/stop/target/alert details.
- Frozen S02 benchmark: its own historical, forward and transfer-research
  evidence.

Overlap in market symbols does not imply pooled evidence.

## Customer-facing hierarchy

The homepage keeps recent records visible but initially shows only the newest
five AI decisions and newest five AI shadow signals. Older records remain in
the same page inside an explicit expandable disclosure; they are not deleted
from the public snapshot or DOM when rendered.

The hero changes from "Find the trade" to "See the setup" so the research-beta
positioning does not imply guaranteed trade discovery.

## Branding

Current public/snapshot product metadata should use VowSig. Historical
identifiers and operational compatibility names that are not customer-facing
remain unchanged, including existing environment-variable and scheduled-task
identifiers where renaming would create deployment risk.

## Hard boundaries

This milestone does not authorize or change:

- AI-v1.1 / AI-v1.2.1 model, provider, prompt, policy, features or guardrails;
- S02 strategy behavior;
- lifecycle/cost semantics;
- gate thresholds or evidence counts;
- scheduler definitions/cadence;
- ledgers, history or backfill;
- broker execution;
- AI-v1.2.1 public signal-detail exposure.

## Governance

The implementation changes governed public-surface artifacts. Before any
production publication, it requires:

1. focused/static tests;
2. applicable runtime/public regression on the owner VPS;
3. a reviewed successor public-surface correction in the existing correction
   chain;
4. exact candidate freeze;
5. separate owner publication-only approval;
6. production cutover plus hosted freshness/multi-lineage verification.

No production mutation is authorized by this document.
