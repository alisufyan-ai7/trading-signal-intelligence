# Symbol Registry

The canonical research universe is maintained in `config/instruments.json`.

## Policy

- Strategy code operates on canonical instruments, never broker symbol names directly.
- Source adapters translate source symbols into canonical instruments.
- Broker `currency_base` / `currency_profit` metadata is auxiliary only; it is not authoritative for symbol identity.
- Discovery scripts may use fuzzy matching, but fuzzy matches never become production mappings without explicit registry entries.
- Alternate contract variants are modeled as distinct source instruments, not aliases.

## Initial Exness MT5 baseline

| Canonical | Source symbol | Use |
|---|---|---|
| EUR/USD | `EURUSD` | baseline |
| GBP/USD | `GBPUSD` | baseline |
| USD/JPY | `USDJPY` | baseline |
| XAU/USD | `XAUUSD` | baseline |
| XAG/USD | `XAGUSD` | baseline |
| NASDAQ 100 | `USTEC` | baseline |
| S&P 500 | `US500` | baseline |
| DOW 30 | `US30` | baseline |
| WTI | `USOIL` | baseline |
| BTC/USDT | `BTCUSDT` | broker comparison; Binance Spot is primary crypto source |
| BTC/USD | `BTCUSD` | broker comparison |
| ETH/USD | `ETHUSD` | broker comparison |
| SOL/USD | `SOLUSD` | excluded initially; observed trade mode 0 |

## Explicit non-aliases

These are separate broker instruments and must not be silently substituted for the baseline symbols:

- `USTEC_x100` ≠ `USTEC`
- `US500_x100` ≠ `US500`
- `US30_x10` ≠ `US30`
- `XAUUSD247` ≠ `XAUUSD`

The registry should evolve through explicit commits as new sources or instruments are validated.
