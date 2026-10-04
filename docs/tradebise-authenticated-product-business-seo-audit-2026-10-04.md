# Tradebise authenticated product, business and SEO audit

Current capture pass: 2026-10-04 UTC. Earlier public-source review dated 2026-10-04 Asia/Karachi is preserved separately. Repository main reviewed at 099f8e89599023769ed29aa023c7916d4560ce10. Research branch only; no merge, deployment, strategy or runtime changes.

## Coverage and evidence standard

**73 redacted screenshots, 39 rendered paths, 64 reviewed route/state groups.** The paths comprise all 34 previously researched public routes plus four settings routes and /premium. The states comprise those 39 path-level groups plus 25 material interaction/variant groups; duplicate/replacement captures do not increase the count. All ten requested market routes and all 15 Learn articles have visual evidence. Most non-BTC market pages are Free-account quota gates, not complete signal outputs.

The user successfully logged into this cloud session. Earlier Cloudflare/handoff failures are historical and no longer the authentication blocker. This pass inspected a **Free** account. One of two daily calls was already used on arrival; BTC analysis consumed the remaining allowance. Subsequent market pages showed the two-call gate and reset countdown; charts remained accessible. No purchase or quota bypass occurred.

Evidence: [capture register](../research/competitors/tradebise/2026-10-04/README.md), [manifest](../research/competitors/tradebise/2026-10-04/capture-manifest.json), [route/state inventory](../research/competitors/tradebise/2026-10-04/route-state-inventory.json), [rendered metadata](../research/competitors/tradebise/2026-10-04/rendered-metadata.json), [SHA-256](../research/competitors/tradebise/2026-10-04/screenshot-sha256.json), [privacy checks](../research/competitors/tradebise/2026-10-04/privacy-verification.json). Earlier [public evidence](../research/competitors/tradebise/2026-10-04/public-evidence.json) remains distinct source provenance.

Nineteen attempted files failed to persist; replacements are enumerated and numbers were not reused. Early loading, heavily masked and stale URL/body captures are explicitly identified. A screenshot records a displayed claim, not verified execution/performance. Published images mask owner/contact/ID/session/IP values. Raw screenshots, account body text and OCR are uncommitted. All images passed decoding/hash checks; supplemental OCR found no owner/credential patterns and only public tradebise.com emails. Visual contact-sheet and targeted full-resolution review supplemented OCR.

## Routes, navigation and account surfaces

| Template | Coverage | Boundary |
|---|---|---|
| Terminal | /; btcusdt, ethusdt, solusdt, xauusd, xagusd, eurusd, gbpusd, aapl, tsla, us30 under /signals/ | BTC results reviewed; other routes predominantly quota gates |
| Education | /learn and all 15 linked articles | Full-page captures; five topic labels; no separate category path/pagination found |
| Information | /about, /support, /privacy, /terms, /risk-disclaimer | Read-only content; no outreach |
| Commercial | /advertise, /promotion, /premium | Quote/promotion forms and three plan selections; no payment |
| Settings | /settings/account, /settings/security, /settings/subscription, /settings/stats | Controls/Free entitlement/empty payment history viewed; private values masked |

Header/footer, popular markets, Learn/contextual links and Advertise→promotion were reconciled. Earlier 34 contextual article links resolved within the existing route set. Account navigation exposed Home, Watchlist, alerts/Telegram/upgrade and settings. Watchlist returned the existing sidebar rather than a dedicated route. Crypto, US stocks, Forex/Gold and Indian categories were inspected; Indian selection displayed 58 markets. This does not enumerate the claimed 5,000+ universe. No separate news route surfaced in inspected navigation.

BTC watchlist add succeeded; removal restored the initially empty list. Trending/Gainers/Losers showed different lists. Sample gainers included RAIN +25.81% and STRK +23.69%; losers BTW −34.59% and BR −19.28%, as dated site claims. Ranking/sponsorship independence was not verified.

Search suggestions are visible in **rasters**: XAU currency/metals variants and BTC entries differentiated by exchange. Immediate DOM observations sometimes omitted the newly populated list. Enter retained the homepage/suggestions without selecting. Clicking the visible Binance BTCUSDT suggestion later ended in **US30 quota/chart state** (91); successful BTC search navigation is not claimed. Home/Gainers/Losers sometimes retained an earlier US30 URL/title. These are session observations, not proof all search is broken.

Account settings expose profile/country/member date/ID and browser-alert/Telegram controls. Security shows password validation, active session and 2FA OFF; no reset/enable/password/session action occurred. Browser alerts are advertised free with a target-hit daily cap; Telegram opens the paid gate. My Stats shows usage/Free status and a display toggle, unchanged. Payment history settled to “No payments yet.” Optional notification and featured-coin overlays were observed/dismissed; no notification permission/subscription was accepted.

## Signal fields, examples and methodology

BTC exposes BUY/SELL/WAIT, confidence label, outlook, RSI/market condition, current price, timeframe, last signal with entry/target/SL/status, analysis, additional-target fields and chart. Current **WAIT** can coexist with bullish outlook and a previous BUY/SELL; outlook is not an executable call. WAIT analysis had N/A stops/TP2/TP3. Some fields/charts were blank while loading; 4H was captured with incomplete numeric output, so no complete settled 4H result is claimed.

| Example | Exact displayed values | Limit |
|---|---|---|
| BTC 1H, 15 | Current 85,016.08, WAIT/Low, RSI 59.01. Last BUY near 84,747.51; ended/target 85,037.63; SL 84,202.65; closed 42 minutes ago | Target reached/finished warning; relative time, no audited fill/P&L |
| BTC 1D, 25 | Last BUY near 84,769.99; current 85,016.08; target 85,508; SL 83,468.56; started five hours ago, still open, 33% progress; RSI 55.42 | Open setup, not realized profit |
| BTC 1D, 29 | Last SELL near 85,315.48; ended/SL 86,335.15; target 82,563; closed two days ago; RSI 64.53 | Separate prior stop-loss result, not the open BUY above |
| Stops list, 26 | Five rows including MOVRUSDT/AINUSDT/DASHUSDT/BRUSDT with BUY/SELL/timeframes and SL Hit | Losing results visible; truncated Free history |
| Targets list, 27 | SANDUSDT 4h TP3; MARSCOINUSDT/NEARUSDT/MOVRUSDT 15m TP1; SANDUSDT 1h TP1 | Heading says TP1/TP2 while a row shows TP3; incomplete population |

The all-signals counter opened the same Targets Hit modal (28), not a complete generated-call ledger. Free lists show five rows with upgrade to last 20. Absolute issuance/expiry, fills, costs and revisions were not established. BTC 1D changed between DOM and raster observations: raster 25 verifies the open BUY; raster 29 independently verifies the separate closed SELL. These records must not be combined into one lifecycle.

Education describes algorithms applying rules to momentum, structure and prices; About claims over 2,000 variants tested. No reproducible model identity, training/test data, weights, out-of-sample results or calibration was exposed. The timeframe article says resolutions are analysed independently; broad confirmation language does not prove automatic fusion. Educational examples and historical indexed snippets are distinct from browser examples.

## Performance claims and denominator caveat

Current home began at 378,213 signals / 93% / 26,313 stops; later 378,237 / 93% / 26,314; final Gold raster 92 shows 378,383 / 93% / 26,324. Historical 375,261 / 93% / 26,137 figures remain dated claims. Advertise claims 19,000+ registered traders; UI claims 5,000+ markets. Neither audience nor universe was independently measured.

Public **Dataset JSON-LD defines success as signals that did not hit stop-loss divided by total signals, with ongoing outcomes subject to change**. This is not a completed-trade win rate. Capture 1's schema contained total 77,630, stops 26,308, ongoing 15,530, success 93, modified 2026-10-04. Its stated formula yields **66.11%**, while its total differs from the visible 378,213. Visible total/stops approximately yield rounded 93%, but do not reconcile structured data or unresolved calls. Stale/versioned metadata is a possible explanation; no deception or superiority is inferred.

Complete outcome rules/population, overlapping calls, repeat/revised records, bid/ask, fees/slippage and aggregation remain unknown. Privacy states 30-day signal-history retention; a separately auditable lifetime population was not established. Winning/losing samples improve presentation transparency but do not validate the headline.

## Plans, conversion and commercial mechanics

| Live selection | Price/period | Included claims / verification |
|---|---|---|
| Standard, 10 | $14.99 / 30 days | 12 calls/day, unlimited charts/watchlist, priority support; offer only |
| Alerts, 11/82/90 | $19.99 / 30 days | Telegram new-signal/target-hit messages; Telegram and Choose alert markets open this gate |
| Alerts + Bot, 81 | $29.99 / 30 days | Opens the pair on a supported platform with levels to copy, per offer; actual functionality untested |
| Promotion, 61 | Agreed amount/duration; blank amount form | Boosted Hot Coins/slide-up, manual activation; no submission |

Selected plan/payment buttons agree with prices. USDT BEP20/ERC20/TRC20, OxaPay, no automatic renewal and final/non-refundable crypto sales are displayed. The live banner announces alerts/Bot available, superseding older forthcoming source labels. Terms describes two paid plans while UI offers three; SoftwareApplication schema still prices Premium at **$19**. Earlier source payment-success scaffolding does not establish a transaction.

Support describes confirmation-based activation, 30-day expiry, one active session, paid priority and correction of activation/incorrect-charge faults; not tested. The **funnel inference** is market/editorial discovery → free tool/registration → ads/quotas/paid usage and alerts. Attribution, retention, revenue and conversion were not measured. Bot wording does not establish automatic order execution; no platform connection or trade occurred.

## Advertising and sponsorship

| Surface | Current desktop evidence | Limit |
|---|---|---|
| Terminal/home | Two labelled regions: native above search/signal; banner between analysis and chart | Sampled desktop, dynamic fill |
| Filled ads | Tradebise self-promotion via adx.ws; Sevio/SevioAd “Advertise here” | Provider visibility, not tracking/economics validation |
| Featured coin | Repeated floating slide-up, sometimes blank promotional text | Obscures content; actual paid campaign unidentified |
| Advertise/promotion | Offered native/banner/Hot Coins placement and manual booking/activation | Reach and independence unverified |
| Learn/About/legal/support | No labelled/filled ad modules observed in sampled captures | Does not prove ad-free mobile/future sessions |

Advertise offers 728×90 desktop/320×100 mobile banners, negotiable quotes and manual review; rejects gambling/guaranteed-return/fund-handling and other categories. No inquiry was sent. Promotion claims visibility does not affect algorithm output; unverified. CPM/CPC/revenue/consent were not audited. Provider presence alone does not prove the policy's no-cross-site-profiling claim false.

## SEO and editorial architecture

| Dimension | Rendered evidence | Interpretation |
|---|---|---|
| URLs/headings | Ten lowercase /signals/{symbol} routes, symbol heading/initial title | Template architecture, not rankings |
| Symbol canonical | All ten canonicalize to https://tradebise.com/; index,follow; shared description | Potential clustering; actual search-engine choice unmeasured |
| Consistency | Description 100+ markets versus UI 5,000+; titles sometimes hydrate to generic Tradebise | Metadata/content mismatch, impact unknown |
| Editorial/legal | Unique title/meta, self-canonical; no explicit robots meta/JSON-LD observed | No explicit robots tag does not mean noindex |
| Learn | 15 articles, five labels, author/date/read-time, H2/H3, contextual links/product CTA | No category paths, pagination or distinct related-card module found |
| App schema | Duplicated Organization/WebSite graphs, SearchAction, SoftwareApplication, FAQPage, Dataset | Markup observed; eligibility/validation untested |
| Schema mismatch | Premium $19; Dataset denominator conflict; Web/Android/iOS claim | Native apps unverified; schema volume does not establish accuracy |
| Promotion | noindex; no canonical/description observed | Directive observed, index status not measured |
| Robots/sitemap | Earlier retriever errors; cloud net::ERR_BLOCKED_BY_CLIENT | Client restriction; site contents/status unknown, no 404/bot inference |

Safe head markup/links are retained; article body text is not. No newsletter form surfaced; notification prompts are separate. No search-console, ranking/backlink/indexation, Core Web Vitals or mobile evidence was collected. The [SEO memo](tradebise-seo-patterns-for-vowsig-v0.1.md) proposes useful architecture while avoiding observed consistency problems.

## Completion boundary and remaining gaps

The **accessible desktop Free-account pass is complete**. It is not an unrestricted paid audit or predictive validation.

- Allowance blocks fresh output across other symbols and complete settled 4H; routes/charts/gates are captured.
- Last-20/complete history, paid Telegram/delivery and actual Bot behavior remain gated/untested; no upgrade/payment/platform connection.
- Registration/reset, payment lifecycle, 2FA secrets/setup/disable, logout and prize participation were not triggered. Browser notification permission/delivery and support response remain untested.
- Mobile/native apps, full 5,000-market enumeration, tracking/consent/economics, sponsorship independence and conversion/traffic remain unknown.
- Robots/sitemap contents, aggregate denominator/version consistency, calibrated accuracy and full cost-adjusted outcomes remain unresolved.

Risk/legal pages disclose algorithmic analysis, capital risk, third-party delays and no guarantee; these are publisher disclosures, not independent regulatory verification. Privacy states seven-day search/activity and 30-day signal/security retention. Profile/security controls were read-only. Only reversible BTC watchlist add/remove changed product data and restored initial state. No messages, permissions, purchases, agreements or runtime/product changes followed this research.
