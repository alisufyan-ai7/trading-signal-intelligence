# Strategy Status

| ID | Strategy | Version | Status | Last result |
|---|---|---:|---|---|
| S01 | Trend Pullback | 0.1 | REJECTED — GENERAL FX; XAU LEAD RETAINED | EUR/USD, refreshed GBP/USD and refreshed USD/JPY are negative in validation/final test. XAU/USD is near-flat through validation but strong in 2025–26. See EXP-2026-003 and EXP-2026-008. |
| S02 | Structure Breakout | 0.1 | RESEARCH — XAU HISTORICAL ROBUSTNESS PASSED; TRANSFER + LIVE FORWARD NEXT; NOT CANDIDATE | XAU survives 20/23 exact-spec both-OOS variants and shows six consecutive positive half-years from 2023-H2 through 2026-H1. Full-history development remains weak/non-stationary. See EXP-2026-009 through EXP-2026-012. |
| S03 | Momentum Continuation | 0.1 | IDEA | Not tested |
| S04 | Mean Reversion | 0.1 | IDEA | Not tested |
| S05 | Volatility Expansion | 0.1 | IDEA | Not tested |

Update this board only when an experiment provides evidence for a state change; link the experiment in the relevant strategy specification.

`REJECTED — GENERAL FX; XAU LEAD RETAINED` means S01 v0.1 is not suitable as a general FX strategy candidate. The XAU/USD behavior remains a separate market/regime research lead, not an accepted strategy. Do not retroactively tune v0.1 to the already observed XAU period.

`RESEARCH — XAU HISTORICAL ROBUSTNESS PASSED; TRANSFER + LIVE FORWARD NEXT; NOT CANDIDATE` means XAU survives the frozen parameter neighborhood and shows sustained recent temporal persistence, but the full history is non-stationary and no genuinely new live evidence exists yet. Do not retrofit the observed long-side asymmetry or tune v0.1 to new markets.