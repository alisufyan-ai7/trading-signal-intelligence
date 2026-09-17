# EXP-2026-007 — MT5/Binance Live Collector Soak Test

**Status:** QUEUED — G1 OPERATIONAL HARDENING  
**Created:** 2026-09-17

## Objective

Run the MT5/Binance collectors continuously and measure operational reliability rather than one-shot API success before a live forward-test signal engine is trusted.

Historical G1 data quality is already sufficient for research; this experiment addresses operational continuity.

## Minimum scope

- MT5: EURUSD, XAUUSD, USTEC, USOIL, BTCUSDT
- Binance: BTCUSDT
- duration: at least one full trading day, preferably including a session transition

## Measurements

- reconnect behavior after terminal/network interruptions
- stale quote/source detection
- missed candle boundaries
- duplicate candle handling/idempotency
- timestamp monotonicity
- current/open candle transitioning to closed exactly once
- clock drift / source latency observations
- process memory growth
- broker/session transitions
- weekend/reopen behavior where applicable
- source errors, outages, logging and recovery behavior

## Exit criteria

- reconnect behavior is deterministic;
- no silent data loss;
- duplicate handling is idempotent;
- stale-source detection works;
- current/open candle transitions to closed exactly once;
- source outages are recorded rather than hidden;
- timestamp ordering remains monotonic after reconnect/recovery.

This file supersedes the two earlier duplicate-ID planning files `EXP-2026-003-collector-soak-test.md` and `EXP-2026-003-live-collector-soak-test.md`.
