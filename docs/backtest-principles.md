# Backtesting Integrity Principles

1. **No look-ahead leakage.** Features/signals at time `t` may use only information available by the decision timestamp.
2. **Closed-candle semantics first.** Intrabar strategies require explicit lower-timeframe/tick sequencing.
3. **Costs are part of the strategy.** Spread, commission and slippage assumptions are versioned and included before evaluation.
4. **Separate research and test windows.** Final test windows are not repeatedly reused for tuning.
5. **Report distributions, not screenshots.** Include trade count, expectancy, drawdown, MFE/MAE, regime/year/market breakdown.
6. **Reject parameter cliffs.** A strategy that works only at one narrow parameter combination is not robust.
7. **Retain failures.** Failed strategy versions/experiments remain in Git history/research records.
8. **Avoid survivorship by market selection.** Record the predefined universe before broad tests.
9. **Forward test before product claims.** Backtests are hypotheses about historical behavior, not verified future performance.
10. **Prefer simple baselines.** Complex models must demonstrate incremental value against transparent simpler rules.
