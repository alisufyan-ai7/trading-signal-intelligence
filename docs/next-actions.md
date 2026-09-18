# Current Next Actions

_Last updated: 2026-09-18_

## Current G3 status

S01 Trend Pullback v0.1 remains rejected as a general FX hypothesis.

S02 Structure Breakout v0.1 is:

`RESEARCH — XAU HISTORICAL PARAMETER + RECENT TEMPORAL ROBUSTNESS PASSED; NEW-MARKET TRANSFER NEXT; NOT CANDIDATE`

## Temporal result

The unchanged S02 v0.1 baseline was evaluated from 2019 onward with a protocol frozen before the temporal results were viewed.

For XAU/USD:

- complete half-year windows: 10/15 positive overall;
- six consecutive positive half-years from 2023-H2 through 2026-H1;
- 2023-H2 +0.3471R/trade;
- 2024-H1 +0.1218;
- 2024-H2 +0.0107;
- 2025-H1 +0.1839;
- 2025-H2 +0.2101;
- 2026-H1 +0.3710;
- rolling 12-month windows are positive for every start from 2022-01 through 2025-07 (15 consecutive windows);
- the six most recent fixed-rule prior-12m -> next-6m pairs are all positive-to-positive.

This is sustained recent historical behavior, not a single isolated year.

However, USDJPY is a cautionary control: it shows strong historical temporal persistence yet becomes clearly negative from 2025 onward. Historical persistence is therefore not treated as proof of a durable future edge.

## EXP-2026-012 — frozen new-market transfer universe

Before viewing any S02 result on these markets, freeze the unchanged v0.1 baseline on:

1. XAG/USD — `XAGUSD`
2. NASDAQ 100 — `USTEC`
3. S&P 500 — `US500`
4. DOW 30 — `US30`
5. WTI — `USOIL`

These markets are not removed after results are seen.

Binance crypto is excluded from this experiment because Binance volume semantics and execution costs differ from the MT5/bar-spread model. Crypto gets a separate protocol later.

A descriptive transfer-support flag requires both validation and final-test net expectancy > 0 with at least 50 trades in each split. This flag is **not** candidate promotion.

## 1. Pull the frozen transfer runner

```powershell
git pull
```

## 2. Backfill the five new markets

Run H1 and H4 for each:

```powershell
python scripts\backfill_mt5.py --symbol XAGUSD --canonical "XAG/USD" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol XAGUSD --canonical "XAG/USD" --timeframe H4 --bars 50000

python scripts\backfill_mt5.py --symbol USTEC --canonical "NASDAQ 100" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol USTEC --canonical "NASDAQ 100" --timeframe H4 --bars 50000

python scripts\backfill_mt5.py --symbol US500 --canonical "S&P 500" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol US500 --canonical "S&P 500" --timeframe H4 --bars 50000

python scripts\backfill_mt5.py --symbol US30 --canonical "DOW 30" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol US30 --canonical "DOW 30" --timeframe H4 --bars 50000

python scripts\backfill_mt5.py --symbol USOIL --canonical "WTI" --timeframe H1 --bars 50000
python scripts\backfill_mt5.py --symbol USOIL --canonical "WTI" --timeframe H4 --bars 50000

python scripts\dataset_summary.py
```

## 3. Run unchanged S02 transfer

```powershell
python scripts\run_s02_transfer.py
```

Outputs:

- `outputs/s02_transfer_v0_1.json`
- `outputs/s02_transfer_v0_1.csv`

Upload both outputs and paste the printed JSON.

## Interpretation discipline

Do not tune v0.1 to any new market. Do not select only the successful markets after seeing results.

The purpose is to learn whether the breakout mechanism transfers beyond XAU and FX:

- XAG gives same-asset-class evidence;
- USTEC/US500/US30 give equity-index evidence;
- USOIL gives energy evidence.

Regardless of the historical transfer outcome, XAU still requires an immutable live forward record before G3 can be considered passed.

## Parallel engineering after transfer

If the transfer run completes cleanly, begin the immutable forward-test ledger for frozen S02 v0.1. Original signal parameters and strategy/config hashes must be immutable after issuance.

G2 commercial source rights remains independently open; Exness remains R&D-only for this project.
