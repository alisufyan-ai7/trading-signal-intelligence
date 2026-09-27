# Current Next Actions

_Last updated: 2026-09-27_

## Public beta launch state

The TradingTop public beta is live and has passed end-to-end browser + publisher smoke.

Public URL:

`https://tradingtop-early-access-production.up.railway.app`

Verified:

- no username/password prompt
- Railway deployment healthy
- 3/3 live collectors active in UI
- XAU/USD, USTEC and US30 live-signal cards visible
- XAU historical evidence visible
- USTEC/US30 transfer-support evidence visible
- two immutable completed XAU forward records visible
- six research/monitoring markets visible with explicit labels
- research-beta disclaimer visible
- snapshot publish returns 200
- product-publish wrapper: `export_exit=0 alert_exit=0 push_exit=0`
- `raw_market_data_included=false`

Telegram remains optional and disabled.

## Immediate product work

The infrastructure/deployment track is no longer the launch bottleneck.

Next priorities:

1. add lightweight user feedback / willingness-to-pay capture;
2. decide the first external user cohort and onboarding message;
3. add basic usage/activation measurement if it can be done without slowing launch;
4. optionally enable Telegram alerts for future SIGNAL/EXIT events;
5. continue immutable forward validation unchanged.

## Forward validation

XAU F1 progress remains `2/20` completed trades.

Do not tune or change S02 based on the first two forward losses.

USTEC and US30 remain secondary forward collectors.

## Persistence caveat

There is still no persistent Railway volume.

A Railway restart/redeploy can temporarily clear the cloud snapshot until the hourly Windows publisher republishes it.

The tested product-publish task now successfully restores/publishes the snapshot.
