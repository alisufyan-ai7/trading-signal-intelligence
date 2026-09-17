# EXP-2026-003 — MT5/Binance Collector Soak Test

**Status:** QUEUED  
**Created:** 2026-09-17

## Objective

After EXP-2026-002 establishes acceptable history quality, run the connectors continuously to validate operational reliability before any live forward-test signal engine is trusted.

## Minimum scope

- MT5 source: EURUSD, XAUUSD, USTEC, USOIL, BTCUSDT
- Binance source: BTCUSDT
- duration: at least one full trading day, preferably including a session transition
- record reconnects, stale quotes, missing candles, duplicate candles, clock drift and source errors

## Exit criteria

- reconnect behavior is deterministic
- no silent data loss
- duplicate handling is idempotent
- stale-source detection works
- current/open candle transitions to closed exactly once
- source outages are recorded rather than hidden

This experiment remains queued until EXP-2026-002 is substantially complete.
