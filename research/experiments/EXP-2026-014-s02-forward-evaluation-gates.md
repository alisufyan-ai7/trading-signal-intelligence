# EXP-2026-014 — S02 Forward Evaluation Gates

**Status:** PROTOCOL FROZEN BEFORE FIRST FORWARD TRADE  
**Created:** 2026-09-21

## Objective

Define in advance how long the S02/XAUUSD v0.1 forward test should run and when evidence reviews are allowed, so the project does not stop or promote based on a few convenient trades.

The activated forward protocol remains unchanged.

## Historical frequency context

The frozen XAUUSD S02 v0.1 baseline produced 1,033 historical trades across roughly eight years of stored history, approximately 10–11 trades per month on average. Actual live frequency can vary materially by regime.

This frequency is used only for scheduling estimates, not as a pass criterion.

## Forward evidence gates

### Gate F0 — operations

Runs continuously from activation.

Requirements:

- Task Scheduler remains healthy;
- ledger verifies;
- no silent historical backfill;
- protocol fingerprints remain unchanged;
- missed/skipped signals remain visible.

Operational faults are investigated immediately, independent of strategy P&L.

### Gate F1 — first 20 completed forward trades

Purpose: execution/lifecycle audit only.

Review:

- signal freshness;
- entry timestamp/open fidelity;
- stop/target/time-stop handling;
- modeled costs;
- missed/skipped-signal rate;
- hash-chain integrity.

**No strategy promotion, rejection or tuning from F1 alone.**

Historical-rate estimate: around 2 months, but no calendar deadline is assumed.

### Gate F2 — interim strategy review

Trigger only when **both** are true:

- at least 50 completed forward trades;
- at least 90 calendar days since activation.

Review without changing v0.1:

- net expectancy R;
- profit factor;
- cumulative/max drawdown R;
- win rate and payoff distribution;
- long/short decomposition as diagnostic only;
- execution/missed-signal completeness;
- comparison with frozen historical OOS ranges.

F2 may justify continuing or rejecting v0.1, but a favorable F2 does **not** by itself promote the strategy to candidate.

Historical-rate estimate: roughly 4–5 months, implying approximately Jan–Feb 2027 if frequency resembles history.

### Gate F3 — primary candidate decision

Trigger only when **both** are true:

- at least 100 completed forward trades;
- at least 180 calendar days since activation.

This is the first planned point at which the project may consider S02/XAUUSD v0.1 for candidate status.

A favorable decision requires, at minimum:

- positive forward net expectancy after frozen costs;
- no material ledger/protocol integrity breach;
- acceptable drawdown relative to the historical robustness evidence;
- no dependence on retroactive parameter selection;
- adequate operational capture with missed signals explicitly accounted for.

Historical-rate estimate: roughly 9–10 months at the long-run historical frequency, implying approximately Jun–Jul 2027. Actual timing is trade-count driven and may be later.

## Failure / change discipline

- Do not stop because of a small losing streak.
- Do not promote because of a small winning streak.
- Do not change v0.1 parameters during the activated forward test.
- A material implementation/protocol change requires a separately versioned activation.
- If F2/F3 evidence is poor, reject/pause v0.1 rather than optimizing it in place.
- Any new S02 variant becomes a separate hypothesis.
- S03/S04/S05 research may proceed separately without contaminating the activated S02 record.

## Parallel work while forward evidence accumulates

The project does not need to wait idle.

1. **G2 source rights — start/continue immediately.**
   Obtain written commercial-use clarification or identify a production data source with explicit derived-signal rights.

2. **Forward-verification hardening — next few weeks.**
   Add periodic external anchoring/backup procedures without modifying frozen signal semantics.

3. **G4 lightweight customer discovery — can begin during forward collection.**
   Interview/test the value proposition and presentation of verified signals. Do not build a full production SaaS or make performance claims from the immature forward sample.

4. **Other strategy families — optional parallel R&D.**
   S03/S04/S05 may be researched under separately frozen protocols. They must not alter the active S02 forward test.

## Product transition if F3 passes

If F3 is favorable:

1. promote S02/XAUUSD to candidate/extended forward status;
2. continue the immutable record rather than stopping it;
3. resolve G2 production-data rights before commercial deployment;
4. begin a small G4 beta around verified signal cards, alerts and transparent performance;
5. evaluate production data/execution differences before public performance claims.

If F3 fails, archive/reject or pause v0.1 and move to separately specified hypotheses rather than retuning the active record.
