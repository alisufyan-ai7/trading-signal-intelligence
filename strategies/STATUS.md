# Strategy Status

| ID | Strategy | Version | Status | Last result |
|---|---|---:|---|---|
| S01 | Trend Pullback | 0.1 | REJECTED — GENERAL FX; XAU LEAD RETAINED | EUR/USD, refreshed GBP/USD and refreshed USD/JPY are negative in validation/final test. XAU/USD is near-flat through validation but strong in 2025–26. See EXP-2026-003 and EXP-2026-008. |
| S02 | Structure Breakout | 0.1 | RESEARCH — XAU PARAMETER ROBUSTNESS PASSED; TEMPORAL STABILITY NEXT; NOT CANDIDATE | Exact pre-first-result neighborhood: XAU is positive in both OOS splits for 20/23 variants and final-positive for 23/23; all 23 remain development-negative. See EXP-2026-009, EXP-2026-010 and EXP-2026-011. |
| S03 | Momentum Continuation | 0.1 | IDEA | Not tested |
| S04 | Mean Reversion | 0.1 | IDEA | Not tested |
| S05 | Volatility Expansion | 0.1 | IDEA | Not tested |

Update this board only when an experiment provides evidence for a state change; link the experiment in the relevant strategy specification.

`REJECTED — GENERAL FX; XAU LEAD RETAINED` means S01 v0.1 is not suitable as a general FX strategy candidate. The XAU/USD behavior remains a separate market/regime research lead, not an accepted strategy. Do not retroactively tune v0.1 to the already observed XAU period.

`RESEARCH — XAU PARAMETER ROBUSTNESS PASSED; TEMPORAL STABILITY NEXT; NOT CANDIDATE` means the XAU historical lead survives the exact originally frozen parameter neighborhood, but it remains negative across development for every tested configuration. Temporal stability and genuinely new forward evidence are still required. Do not retroactively turn the observed XAU long-side asymmetry into the v0.1 rule set.