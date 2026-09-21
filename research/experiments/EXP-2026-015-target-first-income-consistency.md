# EXP-2026-015 — Target-First Income-Consistency Screen

**Status:** EXPLORATORY / NOT A STRATEGY CANDIDATE  
**Date:** 2026-09-22

## Question

Can a mechanically defined Badar-inspired XAUUSD setup family generate enough high-quality opportunities to support the project's conversation-level target of relatively frequent USD 50 profit units and a USD 150–200 daily profit stop from a small account?

This experiment is a strategy screen, not a production backtest.

## Motivation

The chat-derived objective emphasized daily income consistency rather than only long-run expectancy.

Primary exploratory metrics:

- full favorable-target hit before structural stop;
- trade frequency;
- median/average favorable excursion;
- low-output-day frequency;
- >= USD 100 and >= USD 150 day frequency;
- losing-day frequency.

## Dataset

Baseline source:

- Dukascopy XAUUSD one-minute OHLC through the public Market-Data-Lab archive;
- test window: 2026-03-01 through 2026-08-20;
- approximately 230,813 one-minute rows processed;
- resampled 5m/15m bars created mechanically.

Phase-1 exclusions:

- no broker-specific spread;
- no commission;
- no slippage;
- no execution latency;
- no broker-specific contract/tick-value model.

Therefore all dollar translations are indicative only.

## Exploratory Engine A

Chat label: **Badar-inspired liquidity reversal**.

Mechanical screen:

1. 5m swing liquidity;
2. 5m sweep beyond swing and close back inside;
3. 1m internal MSS requiring candle close beyond the internal pivot;
4. displacement threshold around 1.6x recent average one-minute body;
5. three-candle FVG generated after the shift;
6. entry near 50% of FVG;
7. structural/FVG-based stop;
8. main active-session window approximately 06:00–18:00 UTC;
9. target-first label based on a fixed favorable XAU move.

## Results — USD 5 target

Approximately 372 trades/signals over the six-month sample.

Overall:

- USD 5 target-first hit rate: ~29.6%;
- average structural risk distance: ~USD 1.02 XAU;
- median favorable excursion: ~USD 3.30 XAU;
- average price expectancy: ~+USD 0.79 XAU/trade before costs.

Development / holdout split:

### 2026-03 through 2026-05

- trades: ~185;
- USD 5 target-first: ~31.9%;
- average risk: ~USD 1.16;
- median favorable excursion: ~USD 3.46;
- average price expectancy: ~+USD 0.85/trade.

### 2026-06 through 2026-08-20

- trades: ~187;
- USD 5 target-first: ~27.3%;
- average risk: ~USD 0.89;
- median favorable excursion: ~USD 2.98;
- average price expectancy: ~+USD 0.72/trade.

The setup remained positive in this simplified holdout screen, but the target-first rate deteriorated.

## Target-distance sensitivity

Keeping approximately the same entries/stops and changing only the favorable target produced the following later-period target-first rates:

- USD 2: ~48.7%;
- USD 3: ~41.7%;
- USD 4: ~31.6%;
- USD 5: ~27.3%.

Interpretation:

The setup family's typical favorable excursion is materially below USD 5. A universal USD 5 requirement discards many directionally correct but smaller moves.

## Liquidity-source screen

More selective liquidity definitions were tested.

Indicative six-month trade counts after the full confirmation chain:

- previous-day high/low: extremely sparse;
- Asian high/low: very sparse;
- London high/low: very sparse;
- 5m equal highs/lows: sparse;
- 15m swings: moderate;
- broad 5m swing liquidity: highest useful frequency.

Conclusion:

Restricting the setup to only major session liquidity does not provide enough opportunities for the stated daily-frequency objective.

## Daily-output screen

Using indicative 0.10-lot-style Gold economics, one position at a time, maximum four trades/day, approximately -USD 40 soft stop, and +USD 150 profit stop, the Engine A family did not approach the desired daily distribution.

Low-output days remained dominant and USD 100+ days were rare.

This fails the conversation-level consistency objective even though simplified per-trade expectancy was positive.

## Engine B and C exploratory status

### Engine B

Breakout -> retest -> continuation.

The initial implementation was too strict and generated effectively no useful trade sample. Loosening it enough to increase trade count caused holdout expectancy to deteriorate.

Disposition: **do not promote; formulation rejected.**

### Engine C

15m trend regime -> 5m pullback -> 1m resumption.

The strict formulation generated only a small holdout sample and turned negative. Looser variants did not justify promotion.

Disposition: **do not promote; formulation rejected.**

These chat labels are not the repository's formal S01/S02 IDs and should not be conflated with them.

## Key conclusions

1. The Badar-inspired setup is better viewed as one candidate generator than as a complete daily-income system.
2. A fixed USD 5 Gold move is materially more ambitious than the setup family's typical favorable excursion.
3. Increasing trade frequency by loosening confirmation is not a reliable solution.
4. Major-session liquidity improves conceptual quality but is too sparse for the desired frequency.
5. The next research should leverage the repository's already-developed formal strategies instead of duplicating weak ad-hoc B/C formulations.
6. Any daily-income consistency target must ultimately be tested at the portfolio level across multiple strategies and markets.

## Next action

Map the chat objective onto the repository's formal strategy evidence:

- S01 trend pullback;
- S02 structure breakout;
- S03 momentum continuation;
- S05 volatility expansion;

then build a portfolio-level target-first/day-distribution evaluator using frozen existing trade ledgers where possible.

This is preferable to continuing to hand-tune chat Engine B/C variants.

## Promotion status

**NOT PROMOTED.**

No live or automated execution should be based on EXP-2026-015 alone.
