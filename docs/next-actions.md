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

## TradingTop/Elirox audit checkpoint — 2026-09-27 UTC

See `docs/tradingtop-elirox-public-audit-2026-09-27.md` for source links, observed public flows and product implications. Authenticated TradingTop views and prices remain unverified because Google's OAuth destination returned a 502 connection error in this Work browser session.

Before external invitations:

1. Choose a distinct public product name; the current page uses the same name as the comparison service.
2. Choose a durable, owner-accessible feedback destination and retention policy. The current Railway filesystem is ephemeral; do not acknowledge feedback into it as durable.
3. Implement a small feedback form and verify persistence across a redeploy. Ask about comprehension, missing signal details, alert preference and willingness to pay; do not collect broker credentials.
4. Select the first cohort and prepare the onboarding message; send no invitations until the preceding steps are complete.

This audit did not recheck the hosted beta. The prior launch verification above is the repository's recorded checkpoint.

## Authenticated competitor research — 2026-09-27 UTC

User-authorized email/password sign-in later succeeded. The earlier Google OAuth failure and “authenticated pages unverified” statement above are historical to the first attempt. Signed-in TradingTop screenshots and hashes are archived in `research/competitors/tradingtop/2026-09-27/README.md`. Pricing, signal card, AI log and T1/T2/T3 model pages were observed. T2's displayed three-month gold result is negative; do not use the aggregate AI log headline as a proxy for T2 model performance.

Keep the product priorities above. Add explicit signal issuance/expiry semantics and per-strategy outcome scope to the first-user comprehension check. No trading or broker connection was performed during this research.
