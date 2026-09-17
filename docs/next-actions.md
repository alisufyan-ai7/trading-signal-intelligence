# Current Next Actions

_Last updated: 2026-09-17_

## Active experiment: EXP-2026-002

The symbol inventory is complete. Pull the latest connector changes first:

```powershell
git pull
```

Then run the representative history audits:

```powershell
python scripts\mt5_history_audit.py --symbol EURUSD --canonical "EUR/USD" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol XAUUSD --canonical "XAU/USD" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol USTEC --canonical "NASDAQ 100" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol USOIL --canonical "WTI" --timeframe H1 --bars 50000
python scripts\mt5_history_audit.py --symbol BTCUSDT --canonical "BTC/USDT" --timeframe H1 --bars 50000
```

Then run the cross-source crypto audit:

```powershell
python scripts\cross_source_crypto_audit.py --mt5-symbol BTCUSDT --binance-symbol BTCUSDT --canonical "BTC/USDT" --timeframe H1 --bars 1000
```

The MT5 connector now automatically selects valid symbols that are hidden from Market Watch before requesting quotes/history.

## What to evaluate from EXP-2026-002

- maximum H1 history depth actually returned by MT5
- duplicates
- gap patterns and whether they match expected sessions
- tick-volume population
- spread min/median/p95/max
- data differences by asset class
- Exness BTCUSDT vs Binance BTCUSDT basis and return correlation

## After EXP-2026-002

1. Decide whether G1 qualifies for `RESEARCH DATA PASS`.
2. Build persistence/backfill around normalized candles.
3. Run EXP-2026-003 collector soak test.
4. Implement a reproducible backtest engine with spread/cost handling.
5. Freeze and test S01 Trend Pullback baseline before parameter optimization.
6. Continue G2 commercial-data-rights investigation independently of strategy research.

## G2 remains independent

Exness is still an R&D source, not an assumed production data source. Continue seeking written clarification for commercial derived-signal use. Do not block strategy R&D while this is unresolved; keep source adapters replaceable.

## G4 comes after evidence

Do not spend significant effort on a polished SaaS interface yet. Once a credible live forward-test record begins accumulating, prototype the verified signal feed and transparent performance page, then test willingness to pay.
