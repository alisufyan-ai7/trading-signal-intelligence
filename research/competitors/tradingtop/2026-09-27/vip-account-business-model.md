# TradingTop VIP account and business model — authenticated observation

Captured 2026-09-27 UTC in the user-authorized signed-in browser session. Source pages are TradingTop's own UI. This is a point-in-time product analysis; displayed balances, rewards, terms and performance are not independently verified. Screenshot links and SHA-256 hashes are in [the capture index](README.md). No password, payment details, broker credentials, referral URL or session tokens are recorded.

## Internal route inventory

| Sidebar item | Observed URL | What the page showed | Capture |
|---|---|---|---|
| My VIP | `/myvip` | Free Trial, $0 withdrawal amount, “Withdrawal Record,” “Pay Now,” VIP start “Invalid Date” and blank end; per-symbol email update reminder switches | [19](tradingtop-20260927-19-myvip-overview.jpg), [32](tradingtop-20260927-32-myvip-alerts-stocks-indices.jpg), [33](tradingtop-20260927-33-myvip-alerts-forex-crypto.jpg) |
| TOP Compute Records | `/topRecords` | Operation Type, TOP Coin and Operation Time columns; “No records” in the table while pagination showed “Total 2” | [20](tradingtop-20260927-20-top-compute-records.jpg) |
| My Invitation | `/myinvitation` | Referral link field, Copy Link, zero invited people and zero “times obtained,” invitation record columns for registration, reward, payment and commission; agency agreement overlay | [21](tradingtop-20260927-21-invitation-agency-agreement.jpg), [23](tradingtop-20260927-23-agency-commission-tiers.jpg), [24](tradingtop-20260927-24-invitation-dashboard.jpg) |
| My Promotions | `/mytrades` | $0 withdrawal amount and $0 frozen amount; Transaction History table with “No Data” | [25](tradingtop-20260927-25-promotions.jpg) |
| Account Settings | `/myseting` | Avatar, nickname, gender, email edit and mobile bind; no changes submitted | [26](tradingtop-20260927-26-account-settings.jpg) |
| View AI Logs | `/ai-history` | Same AI Execution Log reached in the earlier research pass, with aggregate metrics and outcome rows | [27](tradingtop-20260927-27-ai-logs-from-account.jpg) |

The account avatar links to `/user`. Opening it redirected to `/myvip`, so it is an entry route to the same account page; [capture 34](tradingtop-20260927-34-account-landing.jpg) records the destination. The six sidebar destinations above were opened. The invitation dashboard is obscured by its agreement overlay in capture 24; its structure and zero counters were visible in the DOM. The overlay's “confirm” button was **not** pressed.

## TOP utility and growth loop

The “About TOP” dialog on `/myvip` calls TOP an AI compute unit for access to AI models and strategy systems. It says the unit can let users experience the decision framework, analysis and automated execution features before subscribing. The page first displayed 300 TOP and later displayed 200 TOP. We did not reconcile the ledger and cannot attribute the difference to a specific action. The records screen's empty table versus “Total 2” pagination is another UI inconsistency.

| TOP acquisition action shown | TOP awarded | Validity shown |
|---|---:|---|
| New registration | 300 | 7 days |
| Bind phone number | 50 | Permanent |
| Invite one person who registers and binds phone | 100 | Permanent |
| Invited user purchases quarterly subscription | 1,990 | Permanent |
| Invited user purchases annual subscription | 3,990 | Permanent |
| Invited user purchases lifetime subscription | 9,990 | Permanent |
| Complete account opening/transfer | 500 | Permanent |
| Bind an auto-trading account successfully | 1,000 | Permanent |

| TOP consumption action shown | TOP charged |
|---|---:|
| Manual signal: gold, Bitcoin or indices | 100 each |
| Manual signal: forex, other cryptocurrency, other commodity or US stock | 50 each |
| T1 model | 200/day |
| T2 model | 200/day |

The modal does not list a T3 model charge, despite T3 appearing in the model marketplace. It does not state TOP's cash value or whether it can be bought independently. See [acquisition](tradingtop-20260927-28-about-top-acquisition.jpg), [manual signal costs](tradingtop-20260927-29-about-top-consumption.jpg), and [model costs](tradingtop-20260927-30-about-top-model-cost.jpg).

The email reminder area lists instruments across gold, commodities, forex, cryptocurrencies, US stocks and indices. It says “After subscribing, you will receive email alerts for signal updates.” Switches appeared off in the captured account. We did not toggle any, so actual delivery, plan gating and frequency remain untested.

## Agency agreement and commission economics

Opening `/myinvitation` displayed a TradingTop Agency Agreement modal. It identifies TRADINGTOP LTD as Party A and describes the software as real-time forex signals with analysis, trading recommendations, stop loss and take profit guidance. These are the site's statements, not verification of registration, legal effect or product performance.

| Paid users attributed to agent | Subscription commission displayed |
|---:|---:|
| Fewer than 10 | 20% |
| 10–49 | 30% |
| 50–99 | 35% |
| 100 or more | 40% |

The agreement additionally says five free signal access opportunities per referred registration, commission on net receipts after third-party platform fees, credit after a 30-day non-refund period, minimum withdrawal $100, and processing within one business day after staff verification. It describes a one-calendar-month agreement that automatically renews unless terminated in writing three days in advance. Its pricing clause describes an annual subscription model, while the observed [pricing page](tradingtop-20260927-02-pricing-clear.jpg) displays monthly, quarterly, annual and lifetime options. The agreement's five signal opportunities and About TOP's 100 TOP after a referred user binds a phone are separately stated mechanisms; whether they stack is unverified. The exact referral link and any payout method were not copied or tested.

## Business model interpretation

| Mechanism | Direct UI evidence | What remains inference or unknown |
|---|---|---|
| Paid access | Free, monthly, quarterly, annual and lifetime tiers with TOP allocations; Pay Now on VIP page | Actual checkout methods, taxes, renewal/refund behavior and realized revenue |
| Metered access | TOP spent per manual signal and per model day; trial TOP expires after seven days | Whether TOP is purchasable separately, all entitlement rules and accounting accuracy |
| Affiliate acquisition | Unique referral link and 20–40% tiered subscription commission agreement | Actual commission payouts or affiliate conversion economics |
| Broker and execution activation | TOP awarded for account opening/transfer and auto-trading binding | Whether TradingTop receives broker referral fees; no such fee was established |
| Retention | Per-symbol email reminders and AI logs/track record | Actual alert deliverability, repeat usage or subscription conversion |

The combined UI suggests subscription revenue and referral distribution, with TOP acting as a trial and usage meter. A broker referral revenue stream is plausible but **not proven** by these pages. TradingTop's footer says it provides informational and technical services, does not itself hold client funds or act as broker, and that auto trading requires user authorization. These are company claims, not an external audit.

## Boundaries and follow-up

- The “Pay Now” click was rejected by automatic browser approval review because it enters a purchase flow; no checkout or payment screen was opened. The withdrawal control and agency agreement “confirm” were not used. We did not bind a phone, alter profile fields, subscribe to email, invite a person, connect a broker or trade.
- The agency overlay remained visible after an attempt to use its visually identified close icon; capture 24 is therefore an overlay view, not an unobstructed dashboard screenshot.
- `/user` was opened and redirected to `/myvip`. The six menu routes internal to the VIP account were traversed. This does not claim exhaustive coverage of unrelated site sections.
- The initially captured screenshot called “full-page” (31) is still a viewport image because the site uses an inner scroll area. Captures 32–33 record lower instrument rows. All screenshot bytes are retained unchanged.
- For this repo's product, keep credit economics separate from signal quality; test entitlement and expiry behavior explicitly; disclose any referral incentives; and show net, per-strategy evidence rather than treating marketing accuracy as independently audited performance.
