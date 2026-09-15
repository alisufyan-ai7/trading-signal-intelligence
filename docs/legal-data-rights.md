# Data Rights / Commercial-Use Research

_Last updated: 2026-09-16_

This document tracks product/data-rights questions for engineering decisions. It is **not legal advice** and should be reviewed by qualified counsel before commercial launch.

## Product use case to evaluate

The proposed SaaS does **not** need to stream raw broker quotes/charts to end users. The intended flow is:

```text
source market data
   -> internal research/features
   -> proprietary strategy + risk logic
   -> derived signal (direction, zone, stop, targets, score)
   -> AI explanation / performance record
```

That distinction reduces redistribution scope but does not by itself grant rights to use a source's data in a commercial derived product.

## Exness — current finding

### Client Agreement

The current Exness legal-documents page links a Client Agreement updated 24 July 2026. In the Exness (VG) agreement, Part C's prohibited-actions language includes accessing, collecting, scraping, extracting, copying, storing, transmitting, redistributing, reselling or otherwise using Exness market data, price feeds, quotes or other platform data for a purpose other than the client's own genuine trading with Exness, including use with an external/third-party platform, system, product or service.

This language is broad enough that we should **not** assume that reading Exness MT5 quotes into a commercial signal SaaS is permitted merely because the resulting website displays only derived signals.

Source:
- https://www.exness.com/cdn/media/exnessvg/exness_vg_client_agreement.pdf
- Legal documents index: https://www.exness.com/legal-documents/

### API Terms

The current API Terms (version 15 July 2026) state that API access is a limited/personal right and describe the permitted purpose as managing the client's account and executing transactions in good faith. Automated/algorithmic trading is contemplated, but the terms do not establish a general right to build a commercial external signal-data product.

Source:
- https://www.exness.com/cdn/media/docs/exness-api-terms-of-use.pdf

### Engineering consequence

Status: **R&D OK as a technical prototype; production commercial use BLOCKED pending clarification/permission.**

We should avoid building a production dependency that cannot be replaced.

### Question to send Exness

> We are developing a commercial analytics and trading-signal SaaS. We would run an MT5 terminal on our own Windows server, connected to our Exness account, and use the prices/candles internally to calculate proprietary technical indicators and derived trading signals. We would not redistribute the raw Exness price feed, ticks, order book, or live charts. End users would receive only our derived signal outputs (for example direction, entry zone, risk levels, scoring, explanations and historical performance). Is this use permitted? If not under the standard Client Agreement, is there a written commercial-data or partnership authorization available for this use case?

We should retain the response in this repository (redacting personal/account details) before production use.

## MetaQuotes / MT5

MetaQuotes provides an official `MetaTrader5` Python integration for retrieving terminal-provided symbols, bars, ticks and market depth. That confirms technical capability; it does **not** replace the broker/data-owner permission question.

Source: https://www.mql5.com/en/docs/python_metatrader5

## Binance

Binance provides documented public market-data REST/WebSocket interfaces. Its Spot REST docs distinguish endpoints with security type `NONE` as public market data.

Sources:
- https://developers.binance.com/en/docs/products/spot/rest-api
- https://developers.binance.com/en/docs/catalog

### Open legal/commercial check

Before paid production launch, review the Binance Terms/API Terms specifically for:

- commercial analytics / derived-data use
- caching/storage requirements
- attribution requirements, if any
- redistribution/display restrictions
- jurisdiction/entity used by the product

Until reviewed, Binance is **technically approved for R&D**, not marked as legally cleared for every production jurisdiction/use case.

## Decision rule for any source

No production source should be marked `CLEARED` until we can record:

1. exact legal entity / service terms,
2. whether commercial internal calculation of derived signals is allowed,
3. whether raw display/redistribution is allowed (even if we do not plan to use it),
4. storage/caching limits,
5. attribution requirements,
6. rate limits / account requirements,
7. written clarification when terms are ambiguous.
