# EXP-2026-001 — MT5 / Exness Demo Symbol Discovery

**Status:** PROTOTYPE PASS  
**Created:** 2026-09-16  
**Executed:** 2026-09-17

## Objective

Validate the first part of Gate G1 by confirming that the local Windows MT5 terminal connected to an Exness demo server exposes a broad asset universe, live quotes, and historical bars usable by the research stack. Also confirm that Binance Spot bars normalize to the same internal candle schema and UTC timeline.

## Environment observed

- MT5 connection: successful
- Exness demo server label: `Exness-MT5Trial15`
- Account currency: USD
- Trading allowed: yes
- Total MT5 symbols discovered: **357**
- Probe symbol: `EURUSD`
- Probe timeframe: H1
- Probe size: 100 bars
- Binance probe: `BTCUSDT`, H1, 100 bars

No account login ID or credentials were recorded.

## MT5 / Exness findings

### Asset coverage

The first symbol page alone confirmed a substantial crypto CFD universe under paths such as `Pro\\Crypto\\...`, including examples:

- BTCUSD
- BTCUSDT
- ETHUSD
- SOLUSD
- XRPUSD
- LTCUSD
- BCHUSD
- BNBUSD
- ADAUSD
- DOGEUSD
- LINKUSD
- DOTUSD
- AAVEUSD
- MATICUSD

The complete 357-symbol inventory still needs categorization for FX, metals, indices, energy and stocks. This is the purpose of EXP-2026-002.

### EURUSD live quote

Observed at `2026-09-17 11:27:03 UTC`:

- bid: 1.14704
- ask: 1.14710
- raw spread: 0.00006
- for a 5-digit EURUSD quote this corresponds to 6 MT5 points / approximately **0.6 pip**
- `last` was null, which is normal for many OTC FX feeds where bid/ask are the relevant prices

### EURUSD H1 bars

- Requested: 100
- Returned: 100
- Timestamps aligned to exact UTC hours
- Previous candles correctly marked closed
- Current H1 candle correctly marked open
- Tick volume populated
- Spread field populated (example: 6 points)
- The probe currently normalizes MT5 `tick_volume`; real-volume availability has not yet been tested separately

Example current bar at probe time:

- timestamp: `2026-09-17 11:00:00 UTC`
- O/H/L/C: 1.14781 / 1.14787 / 1.14688 / 1.14704
- tick volume: 1338
- spread: 6
- closed: false

### Metadata caveat discovered

Do **not** infer canonical instruments solely from MT5 `currency_base` / `currency_profit` metadata. Several Exness crypto symbols expose inconsistent metadata; for example some token/USD symbols report `currency_base='USD'` even though the source symbol/description clearly identifies the token as the base asset.

Canonical mapping must therefore use an explicit symbol registry driven primarily by:

1. source symbol
2. broker path/category
3. description
4. verified manual mapping for the research universe

Broker metadata may be retained as auxiliary information but not as the canonical source of truth.

## Binance findings

The direct Binance Spot probe returned 100 H1 bars for `BTCUSDT` and normalized successfully to the same `Candle` schema.

Confirmed:

- UTC-aligned H1 timestamps
- OHLC populated
- base-asset volume populated
- prior bars marked closed
- current H1 bar marked open
- no broker-style spread field in the kline payload, as expected

This confirms that source-specific adapters can feed a common downstream research representation.

## What this experiment proves

1. Local MT5 Python connectivity works reliably enough to continue research.
2. Exness demo exposes a large multi-asset symbol universe.
3. Live bid/ask retrieval works.
4. Historical H1 bar retrieval works.
5. Tick volume and historical spread fields are available for EURUSD.
6. Binance direct public data normalizes to the same internal schema.
7. UTC normalization is consistent across both probes.

## What this experiment does NOT yet prove

- maximum history depth per asset/timeframe
- historical gaps or duplicate rates
- reliability over long-running collection sessions
- exact FX/metals/indices/energy/stock symbol mappings
- real-volume availability on MT5 instruments
- spread distribution across sessions rather than one sample
- crypto CFD price divergence versus Binance Spot
- production/commercial data rights

## Gate impact

**G1 moves from `IN PROGRESS` to `PROTOTYPE PASS — robustness validation in progress`.**

The data architecture is technically viable. G1 should not be considered fully passed until history depth, gaps, session behavior, and representative multi-asset coverage are tested.

## Next experiment

Proceed to **EXP-2026-002 — MT5 inventory, history depth, and data-quality audit**.
