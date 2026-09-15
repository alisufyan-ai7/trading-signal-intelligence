# EXP-2026-002 — Binance Spot Normalization

**Status:** READY TO RUN  
**Created:** 2026-09-16

## Objective

Verify that Binance public Spot klines can be represented with the same canonical `Candle` model used by the MT5 adapter and establish a direct crypto research baseline.

## Initial symbols

- BTCUSDT -> BTC/USDT
- ETHUSDT -> ETH/USDT
- SOLUSDT -> SOL/USDT

## Checks

- UTC open timestamps
- OHLC invariants
- closed vs current candle handling
- chronological ordering
- duplicate timestamps
- missing expected intervals
- history pagination behavior
- source/source-symbol preservation

## Result

Pending local execution.

## Conclusion

Pending.
