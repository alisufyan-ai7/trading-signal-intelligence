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

## Full inventory findings

The inventory script categorized all 357 symbols as follows:

| Broker category | Count |
|---|---:|
| Forex | 141 |
| Stocks | 102 |
| Forex_Indicator | 60 |
| Crypto | 31 |
| Indices | 11 |
| CryptoCross | 6 |
| Energies | 3 |
| Idx_Enlarge | 3 |

This confirms broad multi-asset coverage for research. The broker path taxonomy is broker-specific: metals such as `XAUUSD` and `XAGUSD` are located under `Pro\\Forex`, so path/category labels must not be treated as universal asset-class semantics.

### Exact first-universe broker mappings

| Canonical instrument | Exness MT5 source symbol | Digits | Trade mode | Initial research status |
|---|---|---:|---:|---|
| EUR/USD | `EURUSD` | 5 | 4 | include |
| GBP/USD | `GBPUSD` | 5 | 4 | include |
| USD/JPY | `USDJPY` | 3 | 4 | include |
| XAU/USD | `XAUUSD` | 3 | 4 | include |
| XAG/USD | `XAGUSD` | 3 | 4 | include |
| NASDAQ 100 | `USTEC` | 2 | 4 | include |
| S&P 500 | `US500` | 2 | 4 | include |
| Dow 30 | `US30` | 1 | 4 | include |
| WTI crude | `USOIL` | 3 | 4 | include |
| BTC/USD | `BTCUSD` | 2 | 4 | broker comparison/research |
| BTC/USDT | `BTCUSDT` | 2 | 4 | broker comparison/research |
| ETH/USD | `ETHUSD` | 2 | 4 | broker comparison/research |
| SOL/USD | `SOLUSD` | 4 | 0 | exclude initially |

`visible=false` on several instruments means they were not initially shown/selected in Market Watch; it is not interpreted as an unavailable instrument when `trade_mode=4`.

### Explicitly excluded variants for the baseline universe

- `USTEC_x100` — separate enlarged-contract NASDAQ-100 variant; baseline uses `USTEC`.
- `US500_x100` — separate enlarged-contract S&P-500 variant; baseline uses `US500`.
- `US30_x10` — separate enlarged-contract Dow-30 variant; baseline uses `US30`.
- `XAUUSD247` — separate 24/7 gold variant; baseline uses standard `XAUUSD`.
- Crosses such as `BTCXAU`, `BTCXAG`, `XAUAUD`, `XAUEUR`, etc. are not substitutes for the baseline USD instruments.
- `SOLUSD` is excluded from the initial Exness research universe because the observed `trade_mode=0` differs from active baseline instruments.

The authoritative mapping is now maintained in `config/instruments.json`; fuzzy inventory matches are discovery aids only.

## MT5 / Exness findings

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

Do **not** infer canonical instruments solely from MT5 `currency_base` / `currency_profit` metadata. Several Exness crypto symbols expose inconsistent metadata; for example some token/USD symbols report `currency_base='USD'` even though the source symbol/description clearly identifies the token as the base asset. `BTCUSDT` also reported broker-specific `TET` metadata.

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
2. Exness demo exposes a 357-symbol multi-asset universe with the required first-universe FX, metals, indices, energy and crypto instruments.
3. Exact baseline source symbols have been established for the initial research universe.
4. Live bid/ask retrieval works.
5. Historical H1 bar retrieval works.
6. Tick volume and historical spread fields are available for EURUSD.
7. Binance direct public data normalizes to the same internal schema.
8. UTC normalization is consistent across both probes.

## What this experiment does NOT yet prove

- maximum history depth per asset/timeframe
- historical gaps or duplicate rates
- reliability over long-running collection sessions
- real-volume availability on MT5 instruments
- spread distributions across sessions rather than one sample
- crypto CFD price divergence versus Binance Spot
- production/commercial data rights

## Gate impact

**G1 remains `PROTOTYPE PASS — robustness validation in progress`.**

The data architecture is technically viable and the baseline symbol universe is now explicit. G1 should not be considered fully passed until history depth, gaps, session behavior, representative multi-asset history, and cross-source crypto behavior are tested.

## Next experiment

Proceed to **EXP-2026-002 — MT5 inventory, history depth, and data-quality audit** using the authoritative baseline symbols above.
