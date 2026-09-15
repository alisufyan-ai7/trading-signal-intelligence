# Windows MT5 Research Setup

This is the first local execution path for Gate G1.

## Prerequisites

- Windows machine or Windows VM/VPS
- MetaTrader 5 desktop terminal installed
- Exness demo account logged into MT5 for R&D
- Python 3.11+
- Git

Do not commit MT5 login credentials, broker passwords, investor passwords, or any account identifiers.

## Setup

```powershell
git clone https://github.com/alisufyan-ai7/trading-signal-intelligence.git
cd trading-signal-intelligence
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[mt5,research,dev]"
```

Keep the MT5 desktop terminal running and logged into the intended **demo** account.

## First probe

Start with a symbol that visibly exists in Market Watch, for example:

```powershell
python scripts\mt5_probe.py --symbol EURUSD --canonical "EUR/USD" --timeframe H1 --bars 100
```

If Python does not find the desired MT5 installation automatically, pass the terminal executable path:

```powershell
python scripts\mt5_probe.py `
  --terminal-path "C:\Program Files\MetaTrader 5\terminal64.exe" `
  --symbol EURUSD `
  --canonical "EUR/USD"
```

The probe intentionally avoids printing the account login number. Its useful outputs are:

- terminal connectivity
- broker/server label
- account currency/trade flag
- total instrument count
- first set of symbol names/descriptions/paths
- latest quote for the requested source symbol
- recent normalized bars

## Binance probe

This does not require the MT5 package:

```powershell
python scripts\binance_probe.py --symbol BTCUSDT --canonical "BTC/USDT" --timeframe H1 --bars 100
```

## What to capture for G1

After the first successful MT5 probe, record (without secrets/account IDs):

1. MT5 server label
2. total symbol count
3. exact names for FX, metals, indices, energy, stock CFDs and crypto CFDs
4. available historical depth for M1/H1/H4/D1 on representative symbols
5. whether spread/tick volume/real volume are populated
6. any suffixes/prefixes in instrument names
7. any data gaps or unexpected session behavior

Those findings should be committed under `research/experiments/` rather than left only in chat.

## Security note

The project currently needs only read access to market data. Do not enable or add automated order execution while validating the data and strategy research pipeline.
