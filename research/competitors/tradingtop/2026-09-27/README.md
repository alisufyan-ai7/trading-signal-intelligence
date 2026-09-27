# TradingTop authenticated research captures — 2026-09-27 UTC

Captured in the user's signed-in TradingTop session for private product research. All images are unedited JPEG browser screenshots. The account sign-in form, password and payment/checkout pages were not captured. This is a point-in-time UI observation, not verification of TradingTop's signal accuracy, order execution, underlying accounts or performance methodology. No broker account was connected and no AI trading was enabled.

## Screenshots

| File | View | SHA-256 |
|---|---|---|
| [01-pricing.jpg](tradingtop-20260927-01-pricing.jpg) | Pricing with install overlay | `3a7d0db8e51b62289dd31c17d19133aeaee15b3251b2acd35fe37700998c41ad` |
| [02-pricing-clear.jpg](tradingtop-20260927-02-pricing-clear.jpg) | Pricing tiers unobstructed | `037a14059db3b07097988144c052a863ca2f389422a97d47b221ec41ccfd1e8a` |
| [03-signal-home.jpg](tradingtop-20260927-03-signal-home.jpg) | Signed-in symbol chooser | `340b58213a4e30b0c9e44d656e5a04baddabfb968b285292a741395537343354` |
| [04-xauusd-signal.jpg](tradingtop-20260927-04-xauusd-signal.jpg) | XAU reasoning text | `1f31f67c7561c538f164c7cbd194f98cc787f83aa43ef083bd304a96e50e0be3` |
| [05-signal-reminder.jpg](tradingtop-20260927-05-signal-reminder.jpg) | Email reminder prompt | `8424ec413f8ad09fb18a1c1a38838920b75138e0d55d992e9c03b347984d32a4` |
| [06-xauusd-levels.jpg](tradingtop-20260927-06-xauusd-levels.jpg) | XAU chart and levels | `b3d1c600841080a4cf46692e231d97325c88f4f424acde58a3ee80c864939f10` |
| [07-xauusd-parameters.jpg](tradingtop-20260927-07-xauusd-parameters.jpg) | XAU chart viewport variant | `b28fae9502a898d56e2507d7366179fbd615f23244074475c0e1b67342bb003f` |
| [08-xauusd-signal-card.jpg](tradingtop-20260927-08-xauusd-signal-card.jpg) | Symbol chooser plus XAU card transition | `d22b2df69709d2fd9056c1cf52c1747c33e0a7ef8e38c8d79bdfe0f96ec3f990` |
| [09-xauusd-detail.jpg](tradingtop-20260927-09-xauusd-detail.jpg) | XAU inference time, entry, TP1/TP2, SL, confidence | `2919d6d3939f1091ba24754021e4e4986bb69b681fa0195ea143b36d85fe86be` |
| [10-ai-logs.jpg](tradingtop-20260927-10-ai-logs.jpg) | Aggregate AI execution log metrics and curve | `26aa5be7562248a88f8437537ea06e5fed5168123c7cde1dd8cabd8f0edcf9fe` |
| [11-ai-log-rows.jpg](tradingtop-20260927-11-ai-log-rows.jpg) | AI log outcome rows and heatmap | `9ec63facb516bcc318e0a80ca93f9b839697a3a8a5a879cceebd3f6179947f21` |
| [12-model-marketplace.jpg](tradingtop-20260927-12-model-marketplace.jpg) | T1/T2/T3 model marketplace | `e4c23996e764583d33191ee856aaebab1cdb8826642a3b0ad377aad94af40646` |
| [13-t2-gold-model.jpg](tradingtop-20260927-13-t2-gold-model.jpg) | T2 gold model overview | `9073a095cf858312f7a240ac1e2cdf11434ea13b221431c09c6fc3c0cbb0d398` |
| [14-t2-performance.jpg](tradingtop-20260927-14-t2-performance.jpg) | T2 three-month metrics | `31b19e617f187392bf8cf4c91b66b4d073e2580177cd692f8395e1f59c816d18` |
| [15-t2-trade-history.jpg](tradingtop-20260927-15-t2-trade-history.jpg) | T2 trade history table | `2394272b38b5ef4e017e7cf97547d5623a2c0fbe83fd433fc4f98b2f0f34019b` |
| [16-t2-execution-logic.jpg](tradingtop-20260927-16-t2-execution-logic.jpg) | T2 selected trade logic panel | `034fb8b9b1409ad94ea91ad83d9cdf7bfe7bb69530b237734515e80598f304ce` |
| [17-t1-performance.jpg](tradingtop-20260927-17-t1-performance.jpg) | T1 three-month metrics | `3f291a4b1f6f8c4205398327934a1170f339a13c9d86d64079c9bf5e6590022c` |
| [18-t3-performance.jpg](tradingtop-20260927-18-t3-performance.jpg) | T3 three-month metrics | `50edf6b64e0089d50dffae5c09515c8946ebcd4b95471cf55c15cdf8cbbc80ee` |

## Observations

- **Plans** (`/price`): Free Trial $0 with 300 TOP one-time; Access $69/month with 5,000 TOP/month; Advanced $199/quarter with 10,000 TOP/month; Pro $399/year with 20,000 TOP/month; Elite $1,599 lifetime with 50,000 TOP/month. These are displayed site prices and allocations at capture time, not a purchase or a pricing recommendation.
- **AI signal flow** (`/tgai`): Symbol chooser lists forex, crypto, stocks, indices and commodities. Selecting XAUUSD displayed a Buy inference dated 26 Sep 2026 00:19 in Asia/Shanghai (UTC+8), with analysis price 4290.61, suggested Buy 4283.4, TP1 4302.5, TP2 4311.2, SL 4267.5 and confidence 58.8%. The date is older than the capture and must not be interpreted as a currently executable setup. A reminder modal offered email notification; Skip was selected, and no subscription was created. The ordinary account showed a disabled question box with an upgrade message.
- **Aggregate AI log** (`/ai-history`): All Symbols / Last 30 Days / Short-Term displayed “Inference Accuracy” 74.00%, “Expected Return per Signal” +31.86, “Realized Risk–Reward Ratio” 1.13, “Total Pips Gained” +196,001.96, “Signal Stability Score” 8.5 and average duration 9h. The table included both target and stop outcomes. Metric definitions, denominator, costs and independent audit status were not established.
- **Model marketplace** (`/modelSelect.html`): T1 Defensive Alpha, T2 Precision Sniping (gold specific), T3 Forex Trend. Each model had an overview, open trades and trade history. The three-month model performance cards are separate from the aggregate AI log and should never be conflated.
- **T2 displayed last-three-month model result** (`/wareorder?model=T2`): 53 trades, realized PnL **-$441.30**, inference accuracy 37.7%, average profit $55.89, average loss $47.25, average holding 5.0h; XAUUSD is the only listed symbol. One selected trade's “AI Execution Logic” panel displayed “no data.” The observed performance is negative despite the separate aggregate AI log's higher displayed inference accuracy.
- **T1 displayed last-three-month result**: 41 trades, realized PnL **+$115.66**, inference accuracy 56.1%, average profit $33.77, average loss $36.73, average holding 18.2h.
- **T3 displayed last-three-month result**: 30 trades, realized PnL **+$143.50**, inference accuracy 70.0%, average profit $14.42, average loss $17.70, average holding 11.6h.
- **Reconciliation limits**: The model overview's balance/equity, deposit/withdrawal tiles, curve and three-month realized PnL were observed but their accounting basis and time windows were not independently reconciled. A displayed percentage is not proof of after-cost expectancy. No claims about real-money account execution follow from these screenshots.

## Product implications for this repository

1. Keep historical backtest, immutable forward signals and any future executed-trade record as distinct datasets, with visible sample size, window, costs and losses.
2. Show issuance time, market timezone, signal status/expiry and entry validity. A previously issued signal must not look current merely because it remains the latest displayed.
3. Use a per-strategy evidence page instead of an aggregate win-rate headline. Surface negative periods such as the observed T2 result.
4. If any execution explanation is offered, distinguish unavailable detail from a complete audit trail. Never imply that a button labelled “View Details” proves explanation data exists.
5. Do not enable broker connection or auto execution based on competitor UI research. The project's own G3 forward evidence remains in progress.

## Reproduction boundaries

The screenshot filenames use the UTC capture date. Site content and price can change; recheck before using these figures in product or pricing decisions. The signed-in observations supersede the earlier public-only audit's statement that pricing and authenticated pages were unverified, while preserving that earlier audit as an accurate record of the first unsuccessful Google OAuth attempt.

## VIP account follow-up — 2026-09-27 UTC

All six sidebar destinations from `/myvip` were traversed. The account `/user` entry redirects to `/myvip`. The [route-by-route findings and business model analysis](vip-account-business-model.md) covers TOP earning and consumption, referral commission tiers, account views and observed limitations. The agreement was read but not accepted. No payment, withdrawal, profile edit, email switch or broker connection was submitted. Automatic browser approval review rejected a click on “Pay Now” because it initiates a purchase flow.

| File | View | SHA-256 |
|---|---|---|
| [19-myvip-overview.jpg](tradingtop-20260927-19-myvip-overview.jpg) | VIP status, withdrawal panel and email alert switches | `edefc1725e3867aae6fb7919ab644ada42cce878ef2205d0b79291ba3606a646` |
| [20-top-compute-records.jpg](tradingtop-20260927-20-top-compute-records.jpg) | TOP usage ledger, empty rows and Total 2 pagination | `bd6e9a9cf0d3845312453543e6069e8f4b1131ffe3b108b1afacaa5a958a0e96` |
| [21-invitation-agency-agreement.jpg](tradingtop-20260927-21-invitation-agency-agreement.jpg) | Agency agreement overlay top | `441438588e5140812f7bc1efa6ac0310de0b55161163b72ea1ffdc148d046d7d` |
| [22-agency-rewards-settlement.jpg](tradingtop-20260927-22-agency-rewards-settlement.jpg) | Agency agreement lower clauses | `5d9a576dae0f46618f82d0af0c278a31226a22351fce375818cddd46d656a1a1` |
| [23-agency-commission-tiers.jpg](tradingtop-20260927-23-agency-commission-tiers.jpg) | Commission tiers and withdrawal terms | `55cc2269dd0cf0fcc05dd41759e5c1af5bb7b9c55d503c419a93319a152af6fc` |
| [24-invitation-dashboard.jpg](tradingtop-20260927-24-invitation-dashboard.jpg) | Invitation dashboard behind agreement overlay | `4c02ad23f71eb73e0b2ab1a8cf90380cca01451be780d832b47053903aac9707` |
| [25-promotions.jpg](tradingtop-20260927-25-promotions.jpg) | Promotion wallet and empty transaction history | `b2363d5434ccefd2bf76f8edac6a4d880eb6616e5f32ab0b31a0887d6242b2b2` |
| [26-account-settings.jpg](tradingtop-20260927-26-account-settings.jpg) | Profile, email and phone bind controls | `9a6b9e53574d04855a385391516d6332bb33cf519a6a7f4dde5f12e9ab005900` |
| [27-ai-logs-from-account.jpg](tradingtop-20260927-27-ai-logs-from-account.jpg) | AI log reached through account menu | `bbb534171635a1b5156337bb39347371c084e91c8535b1b2644f33e874d830f0` |
| [28-about-top-acquisition.jpg](tradingtop-20260927-28-about-top-acquisition.jpg) | TOP definition and reward table top | `035e638c8a791399daa1c88b14e57a2492f85dd6fdb4931eba27392be57b351c` |
| [29-about-top-consumption.jpg](tradingtop-20260927-29-about-top-consumption.jpg) | TOP acquisition lower rows and manual signal costs | `01de5179df2ac9b0aba48f7ba6d335512e89123e458f4ea331624cbff2d2abb6` |
| [30-about-top-model-cost.jpg](tradingtop-20260927-30-about-top-model-cost.jpg) | TOP costs for T1 and T2 models | `6b6e4f7bb2e346eb908ac7c09fb752f5559f27e7f8303a9d85a68f18a7d0f911` |
| [31-myvip-full-page.jpg](tradingtop-20260927-31-myvip-full-page.jpg) | Viewport capture despite full-page option; site has inner scroll | `79d7d87b6793adbbc8da254c29a23479c8523be2b5e2236284f05eb53db2d911` |
| [32-myvip-alerts-stocks-indices.jpg](tradingtop-20260927-32-myvip-alerts-stocks-indices.jpg) | Lower email alert list: stocks and indices | `261ad81ec2d1e3e3162281d13039d656763dee2906e5bcf61a30c425c0b691a4` |
| [33-myvip-alerts-forex-crypto.jpg](tradingtop-20260927-33-myvip-alerts-forex-crypto.jpg) | Final alert rows: forex and crypto | `18a0dcf3dd407e5dd2291e2b036584d59e4d6f999c0d2f0adfb8e1931d567a4b` |
| [34-account-landing.jpg](tradingtop-20260927-34-account-landing.jpg) | /user entry redirected to /myvip | `ccaf69408363f8dac4f440b0d9dd5323155465c70fa1f1d4f78989b4ad53c8b6` |
