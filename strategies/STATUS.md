# Strategy Status

| ID | Strategy | Version | Status | Last result |
|---|---|---:|---|---|
| S01 | Trend Pullback | 0.1 | REJECTED — GENERAL FX; XAU LEAD RETAINED | EUR/USD, refreshed GBP/USD and refreshed USD/JPY are negative in validation/final test. XAU/USD is near-flat through validation but strong in 2025–26. See EXP-2026-003 and EXP-2026-008. |
| S02 | Structure Breakout | 0.1 | RESEARCH — ROBUSTNESS IN PROGRESS; NOT CANDIDATE | Post-baseline local sensitivity: XAU is positive in both OOS splits for 15/17 variants and final-positive for 17/17, while all XAU variants remain development-negative. Exact pre-first-result specification neighborhood is pending. See EXP-2026-009 and EXP-2026-010. |
| S03 | Momentum Continuation | 0.1 | IDEA | Not tested |
| S04 | Mean Reversion | 0.1 | IDEA | Not tested |
| S05 | Volatility Expansion | 0.1 | IDEA | Not tested |

Update this board only when an experiment provides evidence for a state change; link the experiment in the relevant strategy specification.

`REJECTED — GENERAL FX; XAU LEAD RETAINED` means S01 v0.1 is not suitable as a general FX strategy candidate. The XAU/USD behavior remains a separate market/regime research lead, not an accepted strategy. Do not retroactively tune v0.1 to the already observed XAU period.

`RESEARCH — ROBUSTNESS IN PROGRESS; NOT CANDIDATE` means S02 v0.1 has passed the first post-baseline local-sensitivity check on XAU, but the exact originally frozen specification neighborhood, temporal stability, and genuinely new forward evidence are still required. Do not retroactively turn the observed XAU long-side asymmetry into the v0.1 rule set.