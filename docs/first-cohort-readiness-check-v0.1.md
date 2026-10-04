# First Cohort Readiness Check v0.1

_Status: OWNER-RUN LIVE CHECK REQUIRED_  
_Date: 2026-10-04_  
_Parent: Issue #9 — First cohort G4 customer-value evidence v0.1_

## Purpose

Prove that the existing production research beta is usable for first-cohort
customer research without adding another major feature before outreach.

This is a read-only/read-mostly product-readiness checkpoint. It does not
authorize model, strategy, market, scheduler, broker, pricing, ad, account or
alert changes.

## GitHub/static readiness — PASS

Repository review confirms:

- public brand is VowSig;
- canonical public URL is https://vowsig.com;
- AI-v1.1 remains SHADOW_ONLY with AI-v1.0 decision protocol;
- production UI contains AI Insights, immutable shadow history and evidence;
- the Early Access feedback form is present;
- feedback fields cover comprehension, lifecycle clarity, reasoning clarity,
  immutable-record trust, missing details, alert preference, willingness to
  pay, price range and market interest;
- current price-range buckets include free-only, under $10, $10–$25, $25–$50
  and $50+;
- the first-cohort onboarding draft has been refreshed from the legacy
  SignalProof AI name to VowSig;
- competitor-informed cohort questions are now recorded.

## Live owner-run readiness criteria

Before sending the first invitation, verify only:

1. https://vowsig.com returns successfully;
2. cloud health reports launch-ready;
3. AI Insights reports runtime AI-v1.1, protocol AI-v1.0, SHADOW_ONLY and broker
   execution disabled;
4. XAU/USD, NASDAQ 100 and DOW 30 are visible as the three live-signal markets;
5. immutable AI signal/history evidence is present;
6. the feedback form renders with all required fields;
7. public read-all feedback access remains unavailable;
8. owner feedback summary/export remains accessible with the existing owner
   token;
9. no new synthetic feedback row is created merely for this check;
10. production repository/runtime state is otherwise unchanged.

## Pass decision

If all live criteria pass:

`VOWSIG_FIRST_COHORT_READINESS=PASS`

Then Issue #9 may move from preparation to recruitment.

If any criterion fails, stop recruitment and fix only the blocking product/UI
defect before inviting users.

## Explicitly not required before cohort

Do not delay Issue #9 to add:

- paid plans;
- advertising;
- Telegram/email alerts;
- accounts beyond existing beta behavior;
- more markets;
- community/live sessions;
- search/watchlist terminal expansion;
- broker connectivity;
- auto trading;
- credit/token systems.

Those remain evidence-dependent decisions after the first aggregate cohort
review.
