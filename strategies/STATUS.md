# Strategy Status

| ID | Strategy | Version | Status | Last result |
|---|---|---:|---|---|
| S01 | Trend Pullback | 0.1 | REJECTED — GENERAL FX; XAU LEAD RETAINED | EUR/USD, refreshed GBP/USD and refreshed USD/JPY are negative in validation/final test. XAU/USD is near-flat through validation but strong in 2025–26. See EXP-2026-003 and EXP-2026-008. |
| S02 | Structure Breakout | 0.1 | RESEARCH — XAU HISTORICAL ROBUSTNESS PASSED; FORWARD ACTIVATION NEXT; NOT CANDIDATE | Transfer is partial: USTEC and US30 meet the frozen support flag, while XAG/US500/USOIL do not. Primary forward hypothesis remains unchanged XAUUSD v0.1. See EXP-2026-009 through EXP-2026-013. |
| S03 | Momentum Continuation | 0.1 | IDEA | Not tested |
| S04 | Mean Reversion | 0.1 | IDEA | Not tested |
| S05 | Volatility Expansion | 0.1 | IDEA | Not tested |

Update this board only when an experiment provides evidence for a state change; link the experiment in the relevant strategy specification.

`REJECTED — GENERAL FX; XAU LEAD RETAINED` means S01 v0.1 is not suitable as a general FX strategy candidate. The XAU/USD behavior remains a separate market/regime research lead, not an accepted strategy. Do not retroactively tune v0.1 to the already observed XAU period.

`RESEARCH — XAU HISTORICAL ROBUSTNESS PASSED; FORWARD ACTIVATION NEXT; NOT CANDIDATE` means historical testing has produced a robust recent-regime XAU lead and only partial cross-market transfer. Candidate status now depends on genuinely new immutable forward evidence. Do not retrofit the long-side asymmetry or select a robustness variant.