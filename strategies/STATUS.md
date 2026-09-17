# Strategy Status

| ID | Strategy | Version | Status | Last result |
|---|---|---:|---|---|
| S01 | Trend Pullback | 0.1 | REJECTED — GENERAL FX; XAU LEAD RETAINED | EUR/USD, refreshed GBP/USD and refreshed USD/JPY are negative in validation/final test. XAU/USD is near-flat through validation but strong in 2025–26. See EXP-2026-004 and EXP-2026-005. |
| S02 | Structure Breakout | 0.1 | RESEARCH — FROZEN BEFORE FIRST RESULT | Rules frozen 2026-09-17; four-market baseline ready. See EXP-2026-006. |
| S03 | Momentum Continuation | 0.1 | IDEA | Not tested |
| S04 | Mean Reversion | 0.1 | IDEA | Not tested |
| S05 | Volatility Expansion | 0.1 | IDEA | Not tested |

Update this board only when an experiment provides evidence for a state change; link the experiment in the relevant strategy specification.

`REJECTED — GENERAL FX; XAU LEAD RETAINED` means S01 v0.1 is not suitable as a general FX strategy candidate. The XAU/USD behavior remains a separate market/regime research lead, not an accepted strategy. Do not retroactively tune v0.1 to the already observed XAU period.

`RESEARCH — FROZEN BEFORE FIRST RESULT` means S02 v0.1 parameters are fixed before any S02 outcome is viewed. Implementation bugs may be corrected, but alpha-rule changes require a new version.