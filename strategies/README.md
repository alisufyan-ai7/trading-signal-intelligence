# Strategy Registry

Strategies are research hypotheses, not marketing claims.

## Lifecycle

- `IDEA` — written hypothesis only
- `RESEARCH` — implementation/backtesting in progress
- `CANDIDATE` — passed initial out-of-sample/robustness criteria
- `FORWARD_TEST` — issuing immutable paper/live-test signals
- `ACCEPTED` — sufficient evidence for product use
- `REJECTED` — evidence does not support continued use
- `PAUSED` — potentially useful, but blocked by data/regime/sample limitations

A rejected version remains in history. We do not quietly retune it and reuse the same version number.

## Initial families

| ID | Family | Initial status | Basic hypothesis |
|---|---|---|---|
| S01 | Trend Pullback | IDEA | continuation after a controlled pullback in an established higher-timeframe trend |
| S02 | Structure Breakout | IDEA | continuation when price closes beyond established structure with sufficient expansion/confirmation |
| S03 | Momentum Continuation | IDEA | persistence after measurable momentum expansion when the higher-timeframe regime agrees |
| S04 | Mean Reversion | IDEA | reversion after statistically stretched movement in a non-trending regime |
| S05 | Volatility Expansion | IDEA | directional movement following volatility compression and confirmed range expansion |

## Minimum strategy specification

Before tuning/backtesting, every strategy version documents:

- hypothesis
- intended market regime
- instruments/timeframes
- exact feature definitions
- exact entry rule
- exact invalidation/stop rule
- exact target/exit rule
- assumptions about candle-close vs intrabar execution
- spread/commission/slippage assumptions
- position-sizing convention
- parameters and permitted search ranges
- known failure modes
- evaluation plan

## Research discipline

We prefer simple interpretable baselines first. Machine learning can be introduced later only if it is tested against strong simple baselines with leakage-safe validation.

Win rate alone is not a success metric. Expectancy, drawdown, robustness and sample quality matter.
