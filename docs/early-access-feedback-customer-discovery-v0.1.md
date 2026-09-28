# Early Access Feedback & Customer Discovery v0.1

_Status: IMPLEMENTED — LIVE VERIFICATION PENDING_  
_Date: 2026-09-29_  
_GitHub issue: #7_

## Objective

Begin G4 customer-value evidence while AI-v1.0 and S02 continue their existing forward collection unchanged.

The milestone creates a durable, privacy-minimal feedback mechanism for the SignalProof AI research beta and prepares the first controlled onboarding cohort.

## Product questions to answer

The first cohort should help determine:

- whether users understand what each signal means;
- whether issuance, expiry and lifecycle state are clear;
- which signal details are missing;
- whether AI reasoning summaries are understandable;
- whether immutable outcome history increases trust;
- which markets users care about;
- preferred alert channel;
- willingness to pay and acceptable price range;
- what prevents the product from being useful enough to return to.

## Feedback data schema

Required structured fields:

- submission timestamp;
- comprehension rating;
- issuance/expiry/lifecycle clarity rating;
- AI reasoning clarity rating;
- immutable-record trust impact;
- missing-detail selection;
- preferred alert channel;
- willingness-to-pay category;
- price-range category;
- market-interest selections;
- optional free-text feedback.

Do not collect:

- broker credentials;
- API keys;
- passwords;
- account IDs;
- payment-card data;
- exact account balances;
- trading login details;
- sensitive personal or financial information.

## Durable storage design

Preferred v0.1 implementation:

- one SQLite database stored under the existing persistent Railway volume;
- suggested path: `/data/feedback.sqlite`;
- append-only submission rows;
- server-generated UTC timestamps;
- random submission ID;
- no public list/read-all endpoint;
- protected owner export endpoint using a dedicated secret separate from the snapshot ingest token;
- CSV/JSON export for owner review.

The feedback database must remain separate from:

- AI-v1 immutable ledgers;
- S02 forward ledgers;
- public snapshot JSON.

## Public API boundary

Public:

- `POST /api/feedback` with strict schema validation and bounded text lengths.

Private/owner-only:

- feedback count/summary endpoint;
- export endpoint protected by a dedicated owner secret.

Never expose all submissions through an unauthenticated route.

## Retention policy

For the research beta:

- retain submitted feedback for up to 12 months unless the owner chooses earlier deletion;
- use feedback only for product/customer-discovery analysis;
- do not use the feedback store for trading execution or model tuning;
- do not store secrets or broker-account information.

Before broader commercial launch, review this retention policy and add user-facing privacy terms appropriate to the actual production jurisdiction and product.

## UI requirements

The feedback form must:

- be visually separate from signals and performance evidence;
- say it is product feedback, not a trade instruction;
- state not to submit broker credentials or sensitive account information;
- keep completion time short;
- include issuance/expiry/lifecycle comprehension questions;
- include per-strategy/evidence clarity questions where practical.

## Verification

Before external invitations:

1. run focused feedback API/store tests;
2. submit a synthetic feedback record;
3. confirm it is durably stored;
4. confirm public read-all access is impossible;
5. confirm owner export works with the dedicated secret;
6. trigger one controlled Railway redeploy;
7. confirm the synthetic record remains present after redeploy;
8. confirm AI Insights/S02 public product surfaces are unaffected;
9. prepare—but do not automatically send—the first-cohort onboarding message.

## Hard boundaries

No change to AI-v1 or S02 decision behavior is permitted in this milestone.

G4 remains evidence collection, not a pass, until actual user feedback demonstrates customer value/willingness to pay.


## Implementation checkpoint

The first implementation is committed.

Components:

- append-only SQLite feedback store;
- strict privacy-minimal validation;
- public POST-only feedback API;
- dedicated owner-only summary/export API;
- separate owner bearer secret;
- public Early Access Feedback UI;
- local owner configuration/export helpers;
- regression tests for validation, persistence semantics and access boundaries.

The implementation is not yet milestone-complete. It must pass VPS tests and live Railway persistence/access verification before first-cohort invitations are prepared.
