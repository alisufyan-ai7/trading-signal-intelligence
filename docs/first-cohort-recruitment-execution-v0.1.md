# First Cohort Recruitment Execution v0.1

_Status: ACTIVE PREPARATION — OWNER APPROVAL REQUIRED BEFORE SENDING_  
_Date: 2026-10-04_  
_Parent: GitHub Issue #9 — First cohort G4 customer-value evidence v0.1_

## Objective

Source and recruit the first 10–20 real VowSig research-beta reviewers now
that pre-cohort readiness has passed.

This document controls prospect selection and outreach execution. It does not
authorize bulk messaging, paid promotion, scraping, account automation or
unsolicited mass outreach.

## What counts as a qualified prospect

Prioritize people who visibly/publicly appear to:

- actively follow or trade XAU/USD, NASDAQ 100 or DOW 30;
- already use MT5, TradingView or another market-analysis workflow;
- discuss signals, market analysis, AI trading tools or trade planning;
- have recent activity suggesting they are an actual market participant rather
  than an inactive account;
- can plausibly spend 5–10 minutes reviewing VowSig and submitting feedback.

Do not prioritize based on follower count alone.

Exclude:

- accounts that appear automated/spammy;
- signal sellers whose main incentive is to promote their own competing product;
- people whose profile suggests they are underage;
- anyone whose only relevance is crypto if they do not engage with a supported
  VowSig market;
- private individuals whose contact information is not publicly intended for
  outreach;
- anyone who has asked not to receive promotional/research messages.

## First-batch composition

Build a first prospect pool of **30–40 relevant individuals**, not 30–40 sent
messages automatically.

Target mix:

- 12–15 XAU/USD-focused traders;
- 8–10 NASDAQ 100 / USTEC-focused traders;
- 5–8 DOW 30 / US30-focused traders;
- 5–7 multi-market traders who actively discuss signals/tools/AI analysis.

Overlap is allowed; the pool target is total unique people.

The first owner-approved send batch should be smaller:

- **10–15 direct messages** initially;
- then review replies/delivery friction before sending the next batch.

## Preferred sourcing channels

Use public communities where individual traders already discuss the relevant
markets.

Priority order:

1. public trader profiles/posts with a normal direct-message/contact mechanism;
2. community/forum participants with recent market-specific discussions;
3. moderator-approved research-beta posts in trading communities;
4. referral from a respondent to one additional relevant trader.

Do not scrape private groups, bypass messaging limits or create automation to
mass-contact users.

## Prospect tracker states

Track every person using only the minimum public information needed for
recruitment:

`identified -> owner_approved -> message_sent -> delivery_known -> seen_known -> replied -> visited -> feedback_submitted -> follow_up_complete`

Important:

- `message_sent` does not mean reached;
- `delivery_known` or `seen_known` should only be recorded when the platform
  actually exposes that state;
- Issue #9 cohort count = real `feedback_submitted`, not messages sent;
- the existing synthetic Issue #7 feedback row never counts toward the cohort.

## Minimum tracker fields

- prospect_id — local non-identifying sequence such as P001;
- platform/community;
- public profile/display handle;
- market relevance;
- reason qualified;
- discovery URL;
- owner approval status;
- outreach date/time UTC;
- message variant;
- delivery/seen state if available;
- reply state;
- beta visit self-reported/known if available;
- feedback submitted yes/no;
- follow-up required;
- notes.

Do not store private email/phone numbers unless the person has explicitly
provided them for contact and they are needed. Never store passwords, broker
IDs, trading account numbers, balances or other sensitive financial data.

## Direct-message variant A — concise

> Hi — I’m testing VowSig, a research-beta market intelligence product for
> XAU/USD, NASDAQ 100 and DOW 30.
>
> It publishes AI BUY / SELL / NO_TRADE decisions with reasoning and keeps the
> signal/outcome history visible. It is shadow-only and does not place broker
> trades.
>
> I’m looking for a small number of active traders to spend 5–10 minutes on
> https://vowsig.com and tell me what is clear, confusing or missing. I’m not
> asking you to follow any trade.
>
> If you’re open to reviewing it, the feedback form is on the page. I’d
> especially value your view on alerts, markets, trust/evidence and whether a
> product like this would ever be worth paying for.

## Direct-message variant B — evidence-led

> Hi — I’m doing a small research-beta review of VowSig
> (https://vowsig.com).
>
> The main idea is that AI decisions are not shown as isolated screenshots:
> BUY / SELL / NO_TRADE, reasoning and subsequent signal/outcome history stay
> visible as forward evidence. Broker execution is disabled.
>
> I’m trying to learn whether active traders actually find that useful and
> understandable before adding paid plans, alerts or more markets.
>
> If you trade/follow XAU/USD, NASDAQ 100 or DOW 30 and can spare 5–10 minutes,
> I’d appreciate one honest feedback submission. No trade-following is
> requested.

## Moderator/admin permission request

> Hi — I’m running a small product-research cohort for VowSig, a research-beta
> market-intelligence tool covering XAU/USD, NASDAQ 100 and DOW 30.
>
> I’d like permission to make one transparent feedback-recruitment post for
> active traders. It would clearly state that the product is shadow-only, does
> not place trades, makes no guaranteed-return claim, and that I’m asking for
> product feedback rather than trade-following.
>
> Would one such post be acceptable under your community rules?

## Public research-beta post

> I’m looking for 10–20 active XAU/USD, NASDAQ 100 or DOW 30 traders to review
> VowSig: https://vowsig.com
>
> It is an early research beta that shows AI BUY / SELL / NO_TRADE decisions,
> reasoning and visible forward signal/outcome history. It is shadow-only and
> does not execute broker orders.
>
> I’m not asking anyone to copy trades. I want honest feedback on:
> - whether the signals/reasoning are understandable;
> - whether the evidence/history increases trust;
> - what is missing;
> - which alerts/markets matter;
> - whether this type of product would ever be worth paying for.
>
> The review takes about 5–10 minutes and the feedback form is on the site.

## Follow-up rule

Do not chase non-responders aggressively.

Recommended:

- one initial message;
- at most one short follow-up after several days if the platform norms allow it;
- no further contact if they do not engage.

Example:

> Just following up once in case this got buried. No problem if it isn’t
> relevant — I’m only looking for a small number of active traders to give
> product feedback on VowSig.

## Evidence-quality rules

Useful feedback should be:

- from a real person who appears relevant to the supported markets;
- submitted after they have had a reasonable chance to inspect the product;
- kept separate from test/synthetic rows;
- interpreted as product/customer evidence, not trading-strategy validation.

Do not modify AI-v1.1 or S02 because one user dislikes or likes a decision.

## Recruitment checkpoints

### Checkpoint R1 — first 10–15 sends

Review:

- delivery/seen state where available;
- replies;
- beta visits where known;
- feedback completions;
- obvious message confusion.

Do not change product functionality at R1 unless there is a clear blocking
usability defect.

### Checkpoint R2 — day 5–7

If fewer than five useful real submissions exist:

- inspect whether the problem is prospect quality, channel restrictions,
  message clarity or product friction;
- revise outreach before increasing volume;
- then source/send another 20–40 relevant prospects if justified.

### Checkpoint R3 — first aggregate evidence

Trigger when either:

- 10–20 real feedback submissions exist; or
- a smaller cohort has already exposed a repeated, material product blocker that
  should be fixed before further recruitment.

Produce an aggregate report before Phase 8B or a paid pilot.

## Current commercial questions to resolve

The cohort should help determine:

- whether alerts should be the first paid-value feature;
- whether $25–$50/month feels plausible;
- whether higher pricing requires more markets/deeper workflow;
- whether education is useful or distracts from the terminal;
- whether a Free-with-ads / Paid-ad-free model is acceptable;
- whether users value immutable evidence enough to differentiate VowSig from
  ordinary signal publishers.

## Hard boundaries

Do not:

- auto-send invitations;
- bulk scrape people/contact details;
- buy lead lists;
- use unsupported win-rate/profit claims;
- imply subscribing will make the user money;
- offer compensation without a separately approved plan;
- deploy ads/pricing/alerts before the cohort evidence;
- enable broker execution;
- change the frozen AI decision protocol.

## Next action

1. source the first 30–40 qualified public prospects;
2. prepare the first 10–15 owner-review batch;
3. owner approves recipients + exact outreach message;
4. send;
5. record funnel states;
6. review at R1.
