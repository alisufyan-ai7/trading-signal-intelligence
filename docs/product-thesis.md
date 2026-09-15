# Product Thesis

## Customer promise

**Find the trade. Explain the trade. Show the risk. Prove the record.**

## What we are building

A broker-neutral signal-intelligence product that continuously screens markets using reproducible quantitative strategies, publishes structured trade setups, explains them with AI, and maintains an immutable record of outcomes.

## What we are not building

- an LLM that improvises BUY/SELL calls
- a guaranteed-profit product
- a raw market-data terminal
- a copy-trading/managed-account service in v1
- a system whose marketing depends on an unverifiable headline win rate

## Intended differentiation

1. **Verification:** every issued signal remains in the historical record.
2. **Explainability:** users can see setup factors, invalidation and risk rather than only direction.
3. **Empirical scoring:** quality scores should eventually map to observed outcome distributions.
4. **Broker neutrality:** derived setup zones rather than pretending all broker/exchange prices are identical.
5. **Source transparency:** record which strategy/data-source version produced each signal.
6. **User-controlled filtering:** users choose markets/timeframes/minimum scores instead of the platform making personalized suitability decisions for them.

## Core signal record

A production signal should eventually contain:

- immutable signal ID
- created timestamp UTC
- canonical instrument + source context
- strategy ID/version
- direction
- entry zone
- stop/invalidation
- target(s)
- risk/reward
- quality score + component features
- explanation snapshot
- source/config/version hashes
- lifecycle events
- final outcome, MFE, MAE and realized R

The product's credibility should come from the complete distribution of outcomes, not selective screenshots.
