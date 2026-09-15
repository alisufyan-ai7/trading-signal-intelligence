# Strategy <ID> <Name> — v<version>

**Status:** IDEA  
**Created:** YYYY-MM-DD  
**Last evaluated:** —

## Hypothesis

State the market behavior being tested in falsifiable terms.

## Intended regime

Describe when the strategy should and should not work.

## Instruments / timeframes

List the research universe and execution timeframe(s).

## Features

Define every feature mathematically/algorithmically. Avoid subjective chart language.

## Entry

Specify exact conditions and whether evaluation happens intrabar or only on a closed candle.

## Stop / invalidation

Specify exact stop construction and any time-based invalidation.

## Exit / targets

Specify profit-taking and trade-management rules.

## Costs / execution model

Document spread, commission, slippage and fill assumptions.

## Position sizing

Keep sizing/risk-budget rules explicit and separate from signal alpha where possible.

## Parameters

| Parameter | Baseline | Allowed research range | Reason |
|---|---:|---:|---|
| | | | |

Parameter ranges should be chosen before viewing broad search results.

## Evaluation protocol

- in-sample window
- out-of-sample window
- walk-forward scheme
- minimum sample expectations
- robustness/perturbation tests
- cross-market test
- regime breakdown

## Results

Append dated experiment references; do not overwrite failed results.

## Known failure modes

Document adverse regimes and implementation risks.

## Decision

`IDEA / RESEARCH / CANDIDATE / FORWARD_TEST / ACCEPTED / REJECTED / PAUSED`

Explain the evidence behind the decision.
