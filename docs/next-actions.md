# Immediate Next Actions

_Last updated: 2026-09-16_

## 1. Run the local MT5 probe

On the Windows machine with MT5 open and logged into the Exness demo account:

```powershell
python scripts\mt5_probe.py --symbol EURUSD --canonical "EUR/USD" --timeframe H1 --bars 100
```

Then update `research/experiments/EXP-2026-001-mt5-symbol-discovery.md` with the non-sensitive findings.

## 2. Run the Binance probe

```powershell
python scripts\binance_probe.py --symbol BTCUSDT --canonical "BTC/USDT" --timeframe H1 --bars 100
```

Confirm the normalized Candle schema works identically for the two source adapters.

## 3. Expand G1 data diagnostics

After symbol discovery, add scripts/tests for:

- historical-depth measurement by timeframe
- missing-bar detection
- duplicate-bar detection
- stale quote detection
- spread distribution summaries
- MT5 vs Binance overlapping crypto comparison for sanity checking

## 4. Resolve G2 in parallel

Send the commercial-derived-signal use question in `docs/legal-data-rights.md` to Exness. Preserve the response (with personal/account data redacted) in this repository.

Do not block strategy R&D while awaiting the answer; keep production source adapters replaceable.

## 5. Freeze S01 v0.1 baseline before backtesting

Before broad parameter search, decide and record:

- pullback tolerance definition
- EMA slope lookback
- stop method for experiment 1
- target (start with a fixed-R baseline)
- spread/slippage assumptions per source/market
- train/test date split

Then implement the first backtest without changing rules based on results mid-run.

## 6. Gate G4 comes after evidence

Do not spend significant time on the polished SaaS interface yet. Once a credible forward-test record begins accumulating, prototype the signal feed + transparent performance page and validate willingness to pay.
