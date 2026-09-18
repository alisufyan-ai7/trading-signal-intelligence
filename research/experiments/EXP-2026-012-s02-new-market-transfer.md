# EXP-2026-012 — S02 New-Market Transfer

**Status:** COMPLETE — PARTIAL TRANSFER; USTEC + US30 SUPPORTIVE BY FROZEN RULE  
**Created:** 2026-09-18

## Objective

Test whether the unchanged S02 Structure Breakout v0.1 mechanism transfers beyond the original FX/XAU universe after XAU passed the planned historical parameter and temporal robustness stages.

No S02 result on the markets below had been viewed when this protocol was frozen.

## Predeclared transfer universe

1. XAG/USD — Exness MT5 `XAGUSD`
2. NASDAQ 100 — Exness MT5 `USTEC`
3. S&P 500 — Exness MT5 `US500`
4. DOW 30 — Exness MT5 `US30`
5. WTI — Exness MT5 `USOIL`

Do not remove a market after results are seen.

Binance crypto is excluded because exchange volume semantics and execution-cost modeling differ from the frozen MT5 S02 research model. Crypto requires a separate protocol.

## Rules

Use the exact unchanged S02 v0.1 baseline:

- H1 prior-20 structure;
- 0.10 ATR breakout margin;
- gap-open exclusion;
- 1.25x true-range expansion;
- 1.10x tick-volume expansion;
- H4 EMA50 regime + 3-bar slope;
- next-H1-open entry;
- 1.75 ATR stop;
- 2.5R target;
- 72-bar timeout;
- 1.25x signal-bar MT5 spread cost proxy.

No parameter selection from EXP-2026-010 is allowed.

## Splits

Use the existing frozen split convention:

- development: before 2023-01-01 UTC;
- validation: 2023-01-01 through 2024-12-31 UTC;
- final test: 2025-01-01 onward.

## Descriptive transfer-support flag

A market is flagged as historically transfer-supportive only if:

- validation net expectancy > 0;
- final-test net expectancy > 0;
- validation trades >= 50;
- final-test trades >= 50.

This flag is descriptive only and does not create candidate status.

## Outputs

Runner: `scripts/run_s02_transfer.py`

- `outputs/s02_transfer_v0_1.json`
- `outputs/s02_transfer_v0_1.csv`

The CSV is a combined trade ledger for all five markets.

## Discipline

- Preserve all five results.
- Do not tune rules to any transfer market.
- Do not drop negative markets.
- Do not infer that cross-market transfer substitutes for live forward evidence.
- Exness remains an R&D source pending G2 commercial-rights resolution.


## Result — 2026-09-18

| Market | Development | Validation | Final test | Frozen support flag |
|---|---:|---:|---:|---|
| XAG/USD | -0.1303R | -0.0839R | +0.1432R | NO |
| NASDAQ 100 / USTEC | +0.0621R | +0.1243R | +0.0122R | YES |
| S&P 500 / US500 | +0.0630R | +0.0283R | -0.0331R | NO |
| DOW 30 / US30 | -0.0049R | +0.0936R | +0.0123R | YES |
| WTI / USOIL | +0.0388R | -0.1466R | -0.1493R | NO |

All validation/final splits exceed the frozen 50-trade minimum.

### Ledger integrity

The combined 4,674-trade ledger passes the same basic mechanical checks used on earlier S02 runs:

- signal timestamp < entry timestamp;
- entry timestamp <= exit timestamp;
- no overlapping positions within any market;
- holding periods are 1–72 bars;
- ordinary stop gross R is -1 within floating-point tolerance;
- target/gap-target gross R is +2.5 within floating-point tolerance.

### Diagnostics

USTEC and US30 are the only markets that satisfy the frozen descriptive support rule. Their final-test expectancy is nevertheless small (~+0.012R/trade each) and should not be treated as strong independent confirmation.

XAGUSD gross validation expectancy is +0.0666R/trade but net validation is -0.0839R/trade; mean modeled cost is about 0.150R/trade in validation. Its 2025 and 2026 results are positive, but the full validation period fails after costs.

US500 is mildly validation-positive and final-negative. USOIL is clearly negative in both OOS splits.

A post-result cost diagnostic on USTEC/US30 shows the tiny final-test edge remains positive at 2.0x the raw spread-cost multiplier but turns slightly negative around 3.0x. This is supplemental fragility context, not a predeclared transfer criterion.

## Disposition

The transfer experiment provides **partial** cross-market support, not broad validation.

The primary forward hypothesis remains XAUUSD S02 v0.1 unchanged. USTEC and US30 remain secondary historical observations. No new parameter search is opened from these results.
