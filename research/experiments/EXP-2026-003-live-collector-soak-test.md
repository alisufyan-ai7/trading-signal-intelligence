# EXP-2026-003 — Live Collector Soak Test

**Status:** BLOCKED BY EXP-2026-002  
**Created:** 2026-09-17

## Objective

After representative symbols and history behavior are validated, run the MT5/Binance collectors continuously and measure operational reliability rather than one-shot API success.

## Planned measurements

- reconnect behavior after terminal/network interruptions
- stale quote detection
- missed/duplicate candle boundaries
- timestamp monotonicity
- process memory growth
- source latency observations
- broker/session transitions
- weekend/reopen behavior
- logging/recovery behavior

## Exit criteria

Define exact thresholds after EXP-2026-002 establishes the instrument/session baseline.
