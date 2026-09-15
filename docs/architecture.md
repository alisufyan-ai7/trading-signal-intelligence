# Architecture

_Last updated: 2026-09-16_

## Design principle

Broker/exchange adapters are replaceable. Strategy code must never depend on Exness-specific, MT5-specific, or Binance-specific naming/objects.

```text
Sources
  ├─ MT5 terminal (Windows) ─ Exness demo for R&D
  └─ Binance REST / WebSocket
             │
             ▼
      Source adapters
             │
             ▼
       Normalization
             │
     ┌───────┼────────┐
     ▼       ▼        ▼
  bars     ticks    metadata
     │       │        │
     └───────┼────────┘
             ▼
       Quality checks
             │
             ▼
      Feature engine
             │
             ▼
      Strategy engine
             │
             ▼
     Candidate signals
             │
       ┌─────┴─────┐
       ▼           ▼
   risk engine   context/AI
       │           │
       └─────┬─────┘
             ▼
       verified signal
             │
      immutable ledger
             │
     ┌───────┴────────┐
     ▼                ▼
 dashboard          alerts
```

## Canonical data model

All connectors should converge on source-tagged UTC records. Minimum bar fields:

- `source`
- `source_symbol`
- `symbol` (canonical)
- `timeframe`
- `timestamp_utc`
- `open`, `high`, `low`, `close`
- `volume` (with a flag describing tick/real/base volume semantics)
- `spread` when available
- `is_closed`

The canonical model must preserve enough source metadata to reproduce a research result.

## MT5 connector

The official MetaTrader5 Python integration communicates with the installed MetaTrader 5 terminal. Relevant capabilities include:

- terminal/account status
- instrument enumeration (`symbols_get`)
- instrument metadata / latest tick
- historical bars (`copy_rates_*`)
- historical ticks (`copy_ticks_*`)
- market depth when supported

MT5 timestamps are handled in UTC. Historical availability depends on what the terminal can access and its chart-history settings.

Reference: https://www.mql5.com/en/docs/python_metatrader5

## Binance connector

For crypto, use Binance's direct public market-data interfaces rather than routing Binance prices through MT5.

- REST: historical/backfill and exchange metadata
- WebSocket market streams: live updates
- No trading permission is required for endpoints documented with security type `NONE`

References:
- https://developers.binance.com/en/docs/products/spot/rest-api
- https://developers.binance.com/en/docs/catalog

## Data-quality layer

Before feature calculation:

- enforce monotonic timestamps
- normalize to UTC
- detect duplicate bars
- detect missing expected intervals
- mark current/incomplete candles separately
- detect stale streams
- validate OHLC invariants
- retain spread where available
- retain source and source symbol
- optionally compare overlapping crypto prices between MT5 and Binance as a sanity check, not as a price-merging mechanism

## Strategy isolation

A strategy accepts normalized data/features and returns a candidate signal. It must not call external APIs directly.

This makes it possible to replace a data source without changing strategy logic and prevents backtests from silently depending on broker-specific implementation details.

## AI boundary

AI is downstream of quantitative candidate generation. Initial AI responsibilities:

- explain a setup in plain language
- summarize invalidation/risk
- classify contextual news/event risk when a licensed source is available
- answer questions from structured signal/performance data
- assist research documentation

AI does not get authority to invent unbounded trades outside the strategy/risk framework.
