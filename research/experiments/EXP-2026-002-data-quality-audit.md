# EXP-2026-002 — MT5 Inventory, History Depth, and Data-Quality Audit

**Status:** COMPLETE — RESEARCH DATA PASS  
**Created:** 2026-09-17  
**Executed:** 2026-09-17

## Objective

Move Gate G1 from a successful prototype toward a robust research-data pass by validating representative multi-asset history, data continuity, historical cost fields, and cross-source crypto coherence.

## Step A — inventory and canonical mapping

**Status: COMPLETE**

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

Excluded/alternate variants:

- `USTEC_x100`, `US500_x100`, `US30_x10`: enlarged-contract variants, not baseline symbols.
- `XAUUSD247`: distinct 24/7 gold variant, not baseline XAU/USD.
- `SOLUSD`: observed `trade_mode=0`, excluded from the initial Exness baseline.

Broker `currency_base` / `currency_profit` metadata is not trusted as the canonical identity source because the inventory exposed inconsistent crypto metadata.

## Step B — representative H1 history audits

### EUR/USD — `EURUSD`

- requested: 50,000 bars
- returned: 50,000
- closed: 49,999
- first: 2018-09-04 13:00 UTC
- last: 2026-09-17 12:00 UTC
- history span: 2,934.96 days (~8.0 years)
- strictly increasing timestamps: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 6 / p95 9 / max 334
- common gaps: primarily 49h, consistent with weekend closure; a small number of 2h/holiday-size gaps remain descriptive until session calendars are modeled

For a 5-digit EURUSD quote, median 6 points is approximately 0.6 pip.

### XAU/USD — `XAUUSD`

- requested: 50,000
- returned: 50,000
- closed: 49,999
- first: 2018-03-28 14:00 UTC
- last: 2026-09-17 12:00 UTC
- history span: 3,094.92 days (~8.5 years)
- strictly increasing timestamps: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 125 / p95 196 / max 1,500
- common gaps: 2h daily-break pattern plus ~50h weekend closures

With 3 decimal digits, median 125 points corresponds to approximately $0.125 in price terms.

### NASDAQ 100 — `USTEC`

- requested: 50,000
- returned: 41,412
- closed: 41,411
- first: 2019-07-16 07:00 UTC
- last: 2026-09-17 12:00 UTC
- history span: 2,620.21 days (~7.2 years)
- strictly increasing timestamps: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 249 / p95 343 / max 851
- common gaps: 2h/3h session-break patterns and ~50h weekend closures

With 2 decimal digits, median 249 points corresponds to approximately 2.49 index points.

### WTI — `USOIL`

- requested: 50,000
- returned: 50,000
- closed: 49,999
- first: 2018-04-12 20:00 UTC
- last: 2026-09-17 12:00 UTC
- history span: 3,079.67 days (~8.4 years)
- strictly increasing timestamps: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 0 / median 18 / p95 59 / max 266
- common gaps: 2h daily-break pattern and ~49–50h weekend closures

With 3 decimal digits, median 18 points corresponds to approximately $0.018.

### BTC/USDT — Exness `BTCUSDT`

- requested: 50,000
- returned: 2,575
- closed: 2,574
- first: 2026-06-01 07:00 UTC
- last: 2026-09-17 12:00 UTC
- history span: 108.21 days
- strictly increasing timestamps: yes
- duplicate timestamps: 0
- tick-volume populated fraction: 1.0
- spread points: min 700 / median 700 / p95 706 / max 980
- one observed 24h gap

With 2 decimal digits, the median Exness BTCUSDT spread field corresponds to approximately $7.00.

### Interpretation of history depth

Exness/MT5 provides sufficient multi-year H1 history for the initial FX, metals, index and energy research program. Exness BTCUSDT does **not** provide sufficient history for long-horizon crypto strategy research on this demo server.

This is not a project blocker because direct Binance data is the designated primary crypto research source. Exness crypto is retained as a broker-specific comparison/sanity source and for later execution-environment sensitivity analysis.

## Step C — Exness/Binance BTCUSDT sanity check

Compared 999 overlapping closed H1 candles from 2026-08-06 21:00 UTC through 2026-09-17 11:00 UTC.

Results:

- median close basis: -3.209 bps (Exness relative to Binance under the audit definition)
- median absolute close basis: 3.209 bps
- p95 absolute close basis: 10.992 bps
- max absolute close basis: 12.850 bps
- consecutive return samples: 998
- H1 return correlation: **0.999451**
- median absolute H1 return difference: 0.906 bps
- p95 absolute H1 return difference: 2.559 bps
- max absolute H1 return difference: 5.408 bps

Interpretation: Exness BTCUSDT and Binance Spot BTCUSDT are different instruments/venues and should not be treated as interchangeable price feeds. However, the extremely high H1 return correlation and modest basis make Binance suitable as a strong cross-source sanity/reference feed for the broker crypto instrument.

## Cost-field policy established by this experiment

Historical MT5 bar `spread` values are useful for asset-specific cost modeling and stress analysis. They are **not** treated as perfect executable bid/ask history.

Baseline research policy:

1. preserve historical bar spread in broker points;
2. convert using each symbol's `point` size rather than using a universal pip assumption;
3. use bar-level spread as a cost proxy for baseline backtests;
4. add conservative configurable slippage;
5. later validate execution sensitivity using tick/bid-ask sampling where feasible;
6. do not allow zero-spread observations to imply costless execution automatically;
7. report cost sensitivity separately from gross strategy alpha.

## Gap interpretation

The observed multi-hour gaps are not automatically data defects:

- EURUSD: dominant ~49h gaps align with weekend market closure.
- XAUUSD and USOIL: dominant 2h gaps appear consistent with recurring daily trading breaks, plus weekend closures.
- USTEC: dominant 2h/3h gaps appear consistent with index-CFD session structure, plus weekend closures.
- BTCUSDT: one 24h gap is anomalous for a nominally continuous crypto market and must be timestamped/investigated before broker crypto continuity is considered operationally clean.

Session-aware gap classification will be implemented separately; raw gap counts must not be interpreted as missing data without calendar context.

## Gate conclusion

**G1 — RESEARCH DATA RELIABILITY: PASS, with documented limitations.**

Why it passes:

- explicit mappings exist across FX, metals, index, energy and crypto;
- FX/metals/index/energy have multi-year H1 history sufficient for the planned strategy horizon;
- timestamps are strictly increasing with zero duplicates across all representative audits;
- tick volume is fully populated in the tested samples;
- historical spread fields are available and materially asset-specific;
- Binance crypto data uses the same normalized schema;
- cross-source BTC hourly behavior is highly coherent;
- the short Exness crypto history has a documented alternative: Binance direct history.

Remaining work is operational hardening rather than a blocker to strategy research:

- identify the exact timestamp/reason for the 24h BTCUSDT gap;
- implement session-aware gap classification;
- run EXP-2026-003 long-running collector soak test;
- add persistence/backfill and reproducible research datasets;
- validate tick-level/executable cost sensitivity before any live execution claims.

This experiment does **not** resolve Gate G2 commercial data rights.
