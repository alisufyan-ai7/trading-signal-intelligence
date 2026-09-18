# EXP-2026-012 — S02 New-Market Transfer

**Status:** PROTOCOL FROZEN — DATA BACKFILL / RUN NEXT  
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
