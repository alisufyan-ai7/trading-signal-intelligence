# EXP-2026-002 — MT5 Inventory, History Depth, and Data-Quality Audit

**Status:** IN PROGRESS  
**Created:** 2026-09-17

## Objective

Move Gate G1 from a successful prototype toward a robust research-data pass.

This experiment must establish:

1. exact Exness source symbols for the initial research universe;
2. category coverage across the 357-symbol demo universe;
3. available H1 history depth for representative assets;
4. duplicate/gap behavior;
5. historical spread distributions;
6. whether tick volume is consistently populated;
7. how closely the Exness BTCUSDT instrument tracks Binance BTCUSDT Spot over the same closed H1 bars.

## Step A — inventory and canonical mapping

**Status: COMPLETE — 2026-09-17**

Observed category counts:

- Forex: 141
- Stocks: 102
- Forex_Indicator: 60
- Crypto: 31
- Indices: 11
- CryptoCross: 6
- Energies: 3
- Idx_Enlarge: 3

The authoritative mappings are now stored in `config/instruments.json`.

Baseline Exness MT5 symbols:

- EUR/USD → `EURUSD`
- GBP/USD → `GBPUSD`
- USD/JPY → `USDJPY`
- XAU/USD → `XAUUSD`
- XAG/USD → `XAGUSD`
- NASDAQ 100 → `USTEC`
- S&P 500 → `US500`
- DOW 30 → `US30`
- WTI → `USOIL`
- BTC/USD → `BTCUSD`
- BTC/USDT → `BTCUSDT`
- ETH/USD → `ETHUSD`

Initial exclusions/alternate variants:

- `USTEC_x100`, `US500_x100`, `US30_x10`: enlarged-contract variants, not baseline symbols.
- `XAUUSD247`: distinct 24/7 gold variant, not baseline XAU/USD.
- `SOLUSD`: observed `trade_mode=0`, excluded from the initial Exness baseline.

Do not infer mappings solely from `currency_base` or `currency_profit`; broker metadata is inconsistent for some crypto instruments.

## Step B — representative history audits

Run these exact baseline commands:

```powershell
python scripts\mt5_history_audit.py --symbol EURUSD --canonical "EUR/USD" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol XAUUSD --canonical "XAU/USD" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol USTEC --canonical "NASDAQ 100" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol USOIL --canonical "WTI" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol BTCUSDT --canonical "BTC/USDT" --timeframe H1 --bars 50000
```

Optional breadth checks after the representative set:

```powershell
python scripts\mt5_history_audit.py --symbol GBPUSD --canonical "GBP/USD" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol USDJPY --canonical "USD/JPY" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol XAGUSD --canonical "XAG/USD" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol US500 --canonical "S&P 500" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol US30 --canonical "DOW 30" --timeframe H1 --bars 50000
```

For each source record:

- requested bars
- returned bars
- first/last UTC timestamp
- history span
- duplicate timestamps
- whether timestamps are strictly increasing
- gap count and common gap sizes
- tick-volume population fraction
- spread min/median/p95/max in broker points

### Gap interpretation

Raw gap counts are descriptive, not automatically errors:

- FX/metals/indices/energy have expected market closures and weekend gaps;
- individual equities also have exchange session gaps;
- crypto is expected to be much closer to 24/7 continuity.

Unexpected in-session gaps will be investigated separately once trading-session calendars are modeled.

## Step C — Exness/Binance crypto sanity check

Run:

```powershell
python scripts\cross_source_crypto_audit.py --mt5-symbol BTCUSDT --binance-symbol BTCUSDT --canonical "BTC/USDT" --timeframe H1 --bars 1000
```

Capture:

- number of overlapping closed H1 candles
- median and p95 absolute close-price basis (bps)
- hourly return correlation
- median and p95 absolute hourly return difference (bps)

### Interpretation

Exness MT5 and Binance Spot are different venues/instruments. We are not trying to prove identical prices. We want to know whether they move closely enough that Binance can serve as a crypto sanity-check/reference source and whether strategy conclusions are materially source-sensitive.

## Provisional G1 pass criteria

G1 can move to `RESEARCH DATA PASS` when all of the following are true:

- representative FX, metal, index, energy and crypto instruments can be mapped explicitly;
- at least several years of H1 history are available for the intended strategy horizon, or a documented alternative history plan exists;
- duplicate timestamps are zero or explainable;
- material data gaps are understood and compatible with instrument sessions;
- spreads and tick volumes are usable in cost/feature modeling;
- Binance crypto data continues to normalize correctly;
- cross-source crypto behavior is sufficiently coherent for sanity checking;
- remaining source limitations are documented rather than silently ignored.

This experiment does **not** resolve Gate G2 commercial data rights.
