# AI-v1 frozen feature definitions

_Status: FROZEN PRE-ACTIVATION — 2026-09-28_

This file removes implementation ambiguity from the feature families listed in `docs/ai-v1-architecture.md`.

All calculations use **completed bars only** and are evaluated as-of the AI inference timestamp.

## Base notation

For H1 bar index `t`:

- `O_t, H_t, L_t, C_t` = completed H1 open/high/low/close;
- `V_t` = H1 tick volume;
- `S_t` = H1 spread field converted to price units with the source symbol's point size;
- `TR_t = max(H_t-L_t, abs(H_t-C_{t-1}), abs(L_t-C_{t-1}))`.

For returns:

`ret_n = C_t / C_{t-n} - 1`

for `n in {1,4,12,24}`.

## ATR

Use Wilder ATR(14):

1. true range as defined above;
2. initial ATR = arithmetic mean of the first 14 true-range values in the retained calculation window;
3. subsequent ATR:
   `ATR_t = ((ATR_{t-1} * 13) + TR_t) / 14`.

Feature:

- `atr_14` = current completed-H1 Wilder ATR(14).

## ATR percentile

`atr_percentile_252` compares the current `atr_14` to the **previous 252 completed H1 ATR values**, excluding the current bar.

Definition:

`count(previous_atr <= current_atr) / count(previous_atr)`

Range 0–1.

If fewer than 252 previous valid ATR observations exist, the snapshot is invalid for AI-v1.

## EMA features

Use standard recursive EMA with `alpha = 2/(n+1)` and `adjust=False` semantics.

H1:

- `ema20_h1`
- `ema50_h1`
- `price_vs_ema20_h1_atr = (C_t - ema20_h1) / atr_14`
- `price_vs_ema50_h1_atr = (C_t - ema50_h1) / atr_14`
- `ema20_slope_h1 = ema20_t / ema20_{t-3} - 1`
- `ema50_slope_h1 = ema50_t / ema50_{t-3} - 1`

H4 uses completed H4 bars only:

- `ema20_h4`
- `ema50_h4`
- `price_vs_ema20_h4_atr`: latest completed H4 close minus H4 EMA20, normalized by H4 ATR(14);
- `price_vs_ema50_h4_atr`: same for EMA50;
- `ema20_slope_h4 = ema20_t / ema20_{t-3} - 1`;
- `ema50_slope_h4 = ema50_t / ema50_{t-3} - 1`.

## RSI

Use Wilder RSI(14) on completed H1 closes.

Feature:

- `rsi_14` in [0,100].

## Prior-20 structure

The structure window uses the **20 H1 bars immediately before t**, excluding the current completed signal-state bar.

- `prior20_high = max(H_{t-20}, ..., H_{t-1})`
- `prior20_low = min(L_{t-20}, ..., L_{t-1})`
- `range_position_20 = (C_t - prior20_low) / (prior20_high - prior20_low)`
- `distance_prior20_high_atr = (prior20_high - C_t) / atr_14`
- `distance_prior20_low_atr = (C_t - prior20_low) / atr_14`

If `prior20_high == prior20_low`, the snapshot is invalid.

## Previous UTC-day structure

Using bars whose timestamps belong to the previous complete UTC calendar day:

- `previous_day_high`
- `previous_day_low`
- `distance_previous_day_high_atr = (previous_day_high - C_t) / atr_14`
- `distance_previous_day_low_atr = (C_t - previous_day_low) / atr_14`

If the prior UTC day contains no valid H1 bars because the instrument did not trade, use the most recent previous UTC day with valid bars and record that date in the snapshot metadata.

## True-range expansion

Use the median true range of the 20 H1 bars immediately before t, excluding `TR_t`.

`tr_expansion_ratio = TR_t / median(TR_{t-20}, ..., TR_{t-1})`

If the denominator is zero or unavailable, the snapshot is invalid.

## Tick-volume z-score

Use the 20 H1 tick-volume observations immediately before t, excluding `V_t`.

Population standard deviation (`ddof=0`):

`volume_z_20 = (V_t - mean(V_{t-20:t-1})) / std_pop(V_{t-20:t-1})`

If standard deviation is zero, set `volume_z_20 = 0` and include a feature-quality flag `ZERO_VOLUME_VARIANCE`.

## Return-sign agreement

Use signs of `ret_4`, `ret_12` and `ret_24`.

`return_sign_agreement` is one of:

- `ALL_UP` if all three > 0;
- `ALL_DOWN` if all three < 0;
- `MIXED` otherwise.

Exact zero counts as mixed.

## Realized volatility regime

Compute 24-H1 realized volatility from completed H1 log returns:

`rv24_t = std_pop(log(C_i/C_{i-1}) for the latest 24 completed H1 returns)`.

Compare current `rv24_t` with the previous 252 valid `rv24` observations, excluding current.

Percentile buckets:

- `LOW`: percentile < 0.33
- `NORMAL`: 0.33 <= percentile <= 0.67
- `HIGH`: percentile > 0.67

If fewer than 252 previous valid values exist, snapshot invalid.

## Deterministic trend regime

Use completed H1 and H4 EMA state.

`TREND_UP` if all are true:

- H1 close > H1 EMA20 > H1 EMA50;
- latest completed H4 close > H4 EMA20 > H4 EMA50;
- H1 EMA20 slope > 0;
- H4 EMA20 slope > 0.

`TREND_DOWN` is the exact inverse.

`RANGE` if neither trend condition holds and both are true:

- abs(H1 close - H1 EMA50) / H1 ATR14 <= 0.50;
- abs(H1 EMA20 - H1 EMA50) / H1 ATR14 <= 0.25.

Otherwise `MIXED`.

This deterministic regime is an input feature. It is separate from the model's returned `regime` classification.

## Session bucket

Frozen UTC buckets:

- `ASIA`: 00:00 <= hour < 07:00
- `LONDON`: 07:00 <= hour < 13:00
- `NEW_YORK`: 13:00 <= hour < 21:00
- `LATE`: 21:00 <= hour < 24:00

These are descriptive fixed UTC buckets, not claims about official exchange sessions.

## Spread / execution context

- `spread_price` = latest completed H1 spread field multiplied by the source symbol point size;
- `spread_atr_fraction = spread_price / atr_14`.

If spread is unavailable, the snapshot is invalid for AI-v1.0 rather than silently substituted.

## Data age

H1 timestamps identify bar opens.

`source_bar_close_utc = source_bar_open_utc + 1 hour`

`data_age_seconds = inference_started_utc - source_bar_close_utc`

The frozen publication guard requires 0 <= `data_age_seconds` <= 300.

A negative value indicates use of an incomplete/future bar and is invalid.

## Feature quality

Every snapshot carries:

- `feature_schema_version = "AI-v1.0"`
- list of quality flags;
- canonical JSON SHA-256 hash.

Canonical serialization requirements:

- UTF-8;
- JSON object keys sorted recursively;
- no NaN/Infinity;
- compact separators `,` and `:`;
- timestamps normalized to UTC ISO-8601 with `Z`;
- numeric values serialized from deterministic Python numeric outputs without display rounding before hashing.

## Excluded inputs

AI-v1.0 feature snapshots contain no:

- S02 signal or position state;
- S02 performance metrics;
- news/sentiment;
- account/balance data;
- user identity;
- incomplete bar;
- future label/outcome.

Any addition requires a new protocol version after activation.
