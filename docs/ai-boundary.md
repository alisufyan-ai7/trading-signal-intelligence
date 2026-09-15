# AI Role / Boundary

AI is a downstream intelligence layer, not the sole source of trading direction.

## Appropriate early uses

- explain a quantitative setup
- summarize invalidation and risk
- turn structured metrics into concise user-facing language
- query/summarize our own signal/performance database
- classify contextual information when a suitable licensed source exists
- assist research documentation and code review

## Not an early authority

- unconstrained "predict the next candle" prompts
- changing stops/targets after issuance to improve reported results
- inventing confidence percentages with no calibration
- silently overriding failed quantitative/risk checks

## Cost principle

Call AI on candidate signals/events, not every tick/candle. Cache explanations against immutable signal versions. Model cost should remain small relative to market-data/research/product costs.
