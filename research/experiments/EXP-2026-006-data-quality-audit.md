# EXP-2026-006 — MT5 Inventory, History Depth, and Data-Quality Audit

**Status:** COMPLETE — RESEARCH DATA PASS  
**Created:** 2026-09-17  
**Executed:** 2026-09-17

## Objective

Move Gate G1 from a successful prototype toward a robust research-data pass by validating representative multi-asset history, data continuity, historical cost fields, and cross-source crypto coherence.

## Step A — inventory and canonical mapping

Observed Exness MT5 category counts:

- Forex: 141
- Stocks: 102
- Forex_Indicator: 60
- Crypto: 31
- Indices: 11
- CryptoCross: 6
- Energies: 3
- Idx_Enlarge: 3

The authoritative mappings are stored in `config/instruments.json`.

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

Excluded/alternate variants include `USTEC_x100`, `US500_x100`, `US30_x10`, `XAUUSD247`, and initial Exness `SOLUSD` with observed `trade_mode=0`.

Broker currency metadata is not treated as canonical identity authority because inconsistent crypto metadata was observed.

## Step B — representative H1 history audits

### EUR/USD — `EURUSD`

- requested / returned: 50,000 / 50,000
- closed: 49,999
- first: 2018-09-04 13:00 UTC
- last: 2026-09-17 12:00 UTC
- span: ~8.0 years
- strictly increasing: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 6 / p95 9 / max 334

### XAU/USD — `XAUUSD`

- requested / returned: 50,000 / 50,000
- closed: 49,999
- first: 2018-03-28 14:00 UTC
- last: 2026-09-17 12:00 UTC
- span: ~8.5 years
- strictly increasing: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 125 / p95 196 / max 1,500

### NASDAQ 100 — `USTEC`

- requested: 50,000
- returned: 41,412
- closed: 41,411
- first: 2019-07-16 07:00 UTC
- last: 2026-09-17 12:00 UTC
- span: ~7.2 years
- strictly increasing: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 249 / p95 343 / max 851

### WTI — `USOIL`

- requested / returned: 50,000 / 50,000
- closed: 49,999
- first: 2018-04-12 20:00 UTC
- last: 2026-09-17 12:00 UTC
- span: ~8.4 years
- strictly increasing: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 18 / p95 59 / max 266

### BTC/USDT — Exness `BTCUSDT`

- requested: 50,000
- returned: 2,575
- closed: 2,574
- first: 2026-06-01 07:00 UTC
- last: 2026-09-17 12:00 UTC
- span: ~108 days
- strictly increasing: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 700 / median 700 / p95 706 / max 980
- one observed 24h gap

Interpretation: Exness/MT5 provides sufficient multi-year H1 history for the initial FX, metals, index and energy research program. Exness BTCUSDT does not provide sufficient history for long-horizon crypto strategy research on this demo server; Binance direct remains the primary crypto research source.

## Step C — Exness/Binance BTCUSDT sanity check

Compared 999 overlapping closed H1 candles from 2026-08-06 21:00 UTC through 2026-09-17 11:00 UTC.

- median absolute close basis: 3.209 bps
- p95 absolute close basis: 10.992 bps
- max absolute close basis: 12.850 bps
- consecutive return samples: 998
- H1 return correlation: **0.999451**
- median absolute H1 return difference: 0.906 bps
- p95 absolute H1 return difference: 2.559 bps
- max absolute H1 return difference: 5.408 bps

The feeds are different instruments/venues and are not interchangeable, but the very high hourly return correlation supports Binance as a cross-source sanity/reference feed.

## Cost-field policy established by this experiment

Historical MT5 bar `spread` values are used as asset-specific cost proxies, not perfect executable bid/ask history.

Research policy:

1. preserve spread in broker points;
2. convert through instrument point size;
3. use bar-level spread as baseline cost proxy;
4. include conservative configurable stress/slippage;
5. validate tick/bid-ask sensitivity before live-execution claims;
6. do not interpret zero-spread bars as automatically costless execution;
7. report cost sensitivity separately from gross alpha.

## Gap interpretation

Raw gaps are not automatically missing data. EURUSD's dominant ~49h gaps align with weekends; XAUUSD/USOIL have recurring daily-break patterns plus weekends; USTEC has recurring CFD session breaks. The single 24h BTCUSDT gap remains an operational anomaly to record.

## Gate conclusion

**G1 — RESEARCH DATA RELIABILITY: PASS, with documented limitations.**

Remaining work is operational hardening rather than a blocker to historical strategy research:

- session-aware gap classification;
- long-running collector reliability (`EXP-2026-007`);
- tick/executable-cost sensitivity before live execution claims.

This experiment does **not** resolve G2 commercial data rights.
