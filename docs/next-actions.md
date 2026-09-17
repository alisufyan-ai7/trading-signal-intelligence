# Current Next Actions

_Last updated: 2026-09-17_

## G1 status

`PASS — RESEARCH DATA`.

EXP-2026-002 established sufficient historical research quality for FX/metals/index/energy and confirmed Binance as the primary long-horizon crypto-history source.

Operational hardening remains queued but does not block strategy research.

## 1. Pull latest research/backtest code

```powershell
git pull
```

## 2. Identify the exact Exness BTCUSDT 24h gap

```powershell
python scripts\mt5_gap_detail.py `
  --symbol BTCUSDT `
  --canonical "BTC/USDT" `
  --timeframe H1 `
  --bars 50000 `
  --min-gap-hours 20
```

Record the timestamp in EXP-2026-002/003. This is operational evidence, not a blocker to S01 because Binance is the primary historical crypto source.

## 3. Build frozen local MT5 research datasets

Backfill both H1 and H4 for the first two S01 instruments:

```powershell
python scripts\backfill_mt5.py --symbol EURUSD --canonical "EUR/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol EURUSD --canonical "EUR/USD" --timeframe H4 --bars 50000

python scripts\backfill_mt5.py --symbol XAUUSD --canonical "XAU/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol XAUUSD --canonical "XAU/USD" --timeframe H4 --bars 50000
```

The local database defaults to `data/research.sqlite` and is intentionally git-ignored.

Check the stored datasets:

```powershell
python scripts\dataset_summary.py
```

## 4. Run the first frozen S01 baseline

The S01 v0.1 specification is already frozen in `strategies/S01-trend-pullback/v0.1.md`. Do not change the rules after seeing these outputs.

```powershell
python scripts\run_s01_backtest.py `
  --symbol EURUSD `
  --canonical "EUR/USD" `
  --output outputs\s01_eurusd_v0_1.csv

python scripts\run_s01_backtest.py `
  --symbol XAUUSD `
  --canonical "XAU/USD" `
  --output outputs\s01_xauusd_v0_1.csv
```

Capture the JSON summaries and preserve the trade ledgers. The first result may be negative; do not optimize v0.1 in place.

## 5. Only after the first engine/results are verified

- inspect sample trades for alignment/look-ahead bugs;
- add GBPUSD and USDJPY H1/H4 datasets;
- run the unchanged v0.1 rules on those instruments;
- run cost stress at 1.0x / 1.5x / 2.0x;
- run walk-forward and parameter-neighborhood experiments;
- decide whether v0.1 is rejected or merits candidate status.

## 6. Binance multi-year crypto persistence

After the MT5 baseline engine is verified, build direct crypto datasets with:

```powershell
python scripts\backfill_binance.py `
  --symbol BTCUSDT `
  --canonical "BTC/USDT" `
  --timeframe H1 `
  --start "2018-01-01T00:00:00+00:00"

python scripts\backfill_binance.py `
  --symbol BTCUSDT `
  --canonical "BTC/USDT" `
  --timeframe H4 `
  --start "2018-01-01T00:00:00+00:00"
```

Do not apply the MT5 CFD spread model to Binance Spot. The crypto execution-cost specification must be frozen separately before evaluating crypto S01 performance.

## G2 remains independent

GitHub issue #1 tracks commercial data rights. Exness is still an R&D source, not an assumed production data source. Strategy research may continue because source adapters are replaceable; paid/public launch remains blocked until production rights are resolved.

## G3 tracking

GitHub issue #2 tracks the reproducible backtest pipeline, S01 validation, OOS/walk-forward work and promotion/rejection decision.

## G4 comes after evidence

Do not spend significant effort on the polished SaaS interface yet. Once a credible immutable forward-test record begins accumulating, prototype the verified signal feed and transparent performance page, then test willingness to pay.
