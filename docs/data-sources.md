# Data Sources

_Last updated: 2026-09-16_

## Source status matrix

| Source | Intended use | Asset coverage | Current status |
|---|---|---|---|
| MT5 + Exness demo | R&D / strategy research | FX, metals, indices, energy, stock CFDs, crypto CFDs (subject to account/server offering) | TECHNICALLY SELECTED; commercial use unresolved |
| Binance direct | Primary crypto research feed | Spot crypto and other Binance market-data products | SELECTED for crypto research; production terms still require formal review |

## MetaTrader 5 via Python

MetaQuotes' official Python integration exposes the data made available by a locally running MT5 terminal. Relevant functions include:

- `initialize()` / `shutdown()`
- `terminal_info()` / `account_info()`
- `symbols_get()`
- `symbol_info()` / `symbol_info_tick()`
- `copy_rates_from()` / `copy_rates_from_pos()` / `copy_rates_range()`
- `copy_ticks_from()` / `copy_ticks_range()`
- `market_book_add()` / `market_book_get()` / `market_book_release()` when supported

References:
- https://www.mql5.com/en/docs/python_metatrader5
- https://www.mql5.com/en/docs/python_metatrader5/mt5symbolsget_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyratesfrom_py
- https://www.mql5.com/en/docs/python_metatrader5/mt5copyticksfrom_py

### Important MT5 research details

- MT5 stores bar/tick time in UTC; code should construct/query UTC timestamps explicitly.
- Returned bars include OHLC, tick volume, spread and real volume fields where available.
- The terminal only returns history available to it; the chart-history / max-bars setting can constrain accessible history.
- A broker's symbols and suffixes/prefixes are not canonical. Symbol discovery and mapping are mandatory.
- Broker CFD prices can differ from direct exchange/underlying-market prices. Preserve the source in every record and do not merge feeds as though they were identical instruments.

## Exness

Exness is useful for R&D because its MT5 environment exposes multiple CFD asset classes through one terminal. We will inspect the actual demo server instrument list dynamically rather than assuming any symbol is present.

### Current restriction

Exness is **not approved as the production feed** for this project yet. See `docs/legal-data-rights.md`.

## Binance

Use Binance directly for crypto research when the target instrument is a Binance market (for example BTCUSDT spot).

The Binance Spot REST documentation distinguishes public market-data endpoints with security type `NONE` from authenticated account/trading endpoints. WebSocket market streams are available for real-time market updates.

References:
- https://developers.binance.com/en/docs/products/spot/rest-api
- https://developers.binance.com/en/docs/catalog

## Canonical symbol examples

| Source symbol | Canonical symbol | Instrument type |
|---|---|---|
| `EURUSD` or broker variant | `EUR/USD` | FX CFD / FX-derived broker instrument |
| `XAUUSD` or broker variant | `XAU/USD` | metal CFD |
| `USTEC` / broker variant | `NASDAQ100` | index CFD |
| `BTCUSDT` | `BTC/USDT` | Binance spot |

The mapping file must include both canonical identity and source-specific contract metadata; a CFD and a spot instrument should not be treated as economically identical merely because their names resemble each other.
