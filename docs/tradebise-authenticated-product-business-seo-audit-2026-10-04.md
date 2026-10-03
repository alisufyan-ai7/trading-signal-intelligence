# Tradebise product, business and SEO audit — authenticated/visual access blocked

Research date: 2026-10-04 Asia/Karachi; retrieval/capture UTC: 2026-10-03. Repository main reconciled at 099f8e89599023769ed29aa023c7916d4560ce10. Research branch only; no merge or product/runtime changes.

## Coverage and access result

**34 public-source routes reviewed; two historical browser page states (homepage/login); zero durable Tradebise screenshots.** Login adds one distinct route to the public set: 35 inspected/discovered-source paths in total. Robots and sitemap were separately requested but not retrieved, making 37 requested paths including failures. These counts do not imply 35 successful browser renders or authenticated access.

The earlier cloud sign-in reached Cloudflare Verification failed. The owner's local session is separate. A fresh handoff was requested under renewed authorization, but automatic approval review rejected it as repeating the already-failed one-attempt handoff. The preceding safe-URL observation was also blocked by native-credential protection; no filled form was captured. No additional authentication attempt, alternate cloud route, fingerprint/network change or CAPTCHA bypass followed the rejection.

This report preserves the complete available first-party source review and an explicit UI/capture backlog. **The comprehensive authenticated and screenshot requirement is not complete.** Web-retrieved text is distinct from the cloud page and may reflect a crawler snapshot or hidden UI scaffolding; payment-success, account-security, counters and viewer states in that text do not establish actual user/session state. Source provenance: [public evidence index](../research/competitors/tradebise/2026-10-04/public-evidence.json), [route/state inventory](../research/competitors/tradebise/2026-10-04/route-state-inventory.json), [capture index](../research/competitors/tradebise/2026-10-04/README.md).

## Public routes, templates and navigation

Homepage, ten required symbol pages, Learn/catalog plus all 15 linked articles, About, Advertise, Support, Privacy, Terms, Risk Disclaimer and the newly discovered /promotion were retrieved. The 34 contextual article links were resolved; each landed within the existing article/legal set. No extra category URL or pagination was exposed in the retrieved Learn list. This is a statement about observed source links, not proof that client-side search or authenticated menus have no additional routes.

| Template | Requested routes / coverage | Evidence and limits |
|---|---|---|
| Market terminal | / and /signals/{symbol} | Public text repeats the application shell; actual loaded prices, generated calls and ads not verified in cloud |
| Crypto | btcusdt, ethusdt, solusdt | [BTC](https://tradebise.com/signals/btcusdt), [ETH](https://tradebise.com/signals/ethusdt), [SOL](https://tradebise.com/signals/solusdt) |
| Metals | xauusd, xagusd | [Gold](https://tradebise.com/signals/xauusd), [Silver](https://tradebise.com/signals/xagusd) |
| Forex | eurusd, gbpusd | [EUR/USD](https://tradebise.com/signals/eurusd), [GBP/USD](https://tradebise.com/signals/gbpusd) |
| Stocks/indices | aapl, tsla, us30 | [Apple](https://tradebise.com/signals/aapl), [Tesla](https://tradebise.com/signals/tsla), [US30](https://tradebise.com/signals/us30) |
| Editorial | /learn plus 15 /learn/{slug} articles | [Catalog](https://tradebise.com/learn); all canonical observed URLs indexed in evidence JSON |
| Commercial | /advertise, /promotion | Direct booking/quote and coin-promotion payment form; no submission |
| Information/legal | /about, /support, /privacy, /terms, /risk-disclaimer | Public source review; no account/support action |

## Signal product and methodology

Historical homepage browser observation showed market search, four timeframes, watchlist, Trending/Gainers/Losers, signal-generation/registration prompts and performance figures. Interaction outcomes for those controls remain unverified. Symbol source text supplies a common direction/entry/target/SL and analysis interface, last-call/result areas and waiting placeholders. Some retrieved snapshots expose one main target; refreshed text exposes TP1–TP3. That is a source-version/UI-format difference, not a verified entitlement distinction. [Market shell](https://tradebise.com/signals/btcusdt), [Alternative retrieved template](https://tradebise.com/signals/gbpusd), [Multi-target fields](https://tradebise.com/signals/xauusd).

The signal-reading article describes BUY/SELL/WAIT, entry, target, stop, reasoning and timeframe interpretation. An educational BTC example has entry 67,200, target 69,800 and SL 65,850; **it is an instructional example, not an audited live issuance**. An indexed US30 snippet showed BUY near 51,349.92, ended/target 51,780.5 and SL 50,975.79. Its exact issuance, timeframe, completeness and live resolution were not confirmed. [Signal explanation](https://tradebise.com/learn/how-to-read-a-tradebise-signal), [Illustration](https://tradebise.com/learn/how-to-set-a-stop-loss), [Indexed result route](https://tradebise.com/signals/us30).

The AI explanation characterizes the engine as software that consistently applies rules to momentum, trend/structure and price history; it describes buy/sell/abstain with structure-based targets/stops. The founder claims more than 2,000 algorithm variants were tested. No model identity, training/test data, weights, reproducible algorithm, out-of-sample evaluation or calibrated forecast accuracy is supplied by these statements. The timeframe article explicitly says each resolution is analysed independently rather than blended, leaving comparison to the user; the broad multi-timeframe-confirmation positioning does not establish an automatic fusion algorithm. [Engine description](https://tradebise.com/learn/ai-trading-explained), [Founder claims](https://tradebise.com/about), [Timeframe implementation claim](https://tradebise.com/learn/multi-timeframe-analysis).

| Displayed claim | Provenance | Interpretation |
|---|---|---|
| 5,000+ markets | Historical homepage + public mission text | Site coverage claim; no enumerated universe verification |
| 375,261 signals; 93% success; 26,137 stops | Earlier homepage browser observation | Exact historical site claim; refreshed source has blank counters. Not current/live verified totals |
| Every call has a stop; losses shown beside wins | Homepage positioning | Live complete population not independently reconciled |
| 19,000+ registered traders | Advertise page | Commercial audience claim, not measured users/traffic |
| More than 2,000 algorithm variants | About page | Founder statement, not documented experimental evidence |

Success definition, TP level used, ongoing-call treatment, sample dates, repeat calls, revisions, bid/ask/slippage/fees and complete losing history remain unknown. A quality-of-signal article itself cautions that win definitions, unresolved positions and measurement period must be specified. The privacy policy states signal-history deletion after 30 days; whether aggregate counters retain a separately auditable population is unresolved. [Outcome-quality discussion](https://tradebise.com/learn/what-makes-a-good-trading-signal), [Retention policy](https://tradebise.com/privacy).

## Business model and conversion

Observed/public positioning supports a **funnel hypothesis**: indexed market/editorial pages → free tool/content → ad inventory and registration → paid usage/alerts. Coexisting acquisition pages, quotas, ad products and paid tiers support this inference. No channel attribution, conversion analytics, revenue, retention or causal funnel effectiveness was measured.

| Offer | Stated commercial terms | Availability certainty |
|---|---|---|
| Standard | $14.99 for 30 days, USDT, no automatic renewal | Public terms; actual checkout not opened |
| Premium with alerts | $19.99 for 30 days; includes Telegram new-signal/result messages | Terms describe it; retrieved app shell also marks alert surfaces as forthcoming, requiring verification |
| Alerts plus bot | $29.99 with forthcoming label in source shell | Source-only roadmap offer; no functional bot or execution permission established |
| Coin promotion | Custom agreed amount/duration; OxaPay crypto form; manual activation | Public commercial page, no payment initiated |

[Plans/payment terms](https://tradebise.com/terms), [App-shell plan labels](https://tradebise.com/signals/ethusdt), [Promotion purchase surface](https://tradebise.com/promotion).

Source shells include a free allowance of two calls/day, Standard 12/day, free watchlist cap five versus unrestricted paid list, registration and premium-preview messaging. These are publicly retrieved UI copy, not tested quotas or eligibility. A payment dialog stub displays $19, while terms specify $14.99/$19.99. Hidden/stale/default dialog content may explain the difference; actual payable amount was not verified. Payment processor is labelled OxaPay. Never equate source payment-success text with a transaction. [Quota copy](https://tradebise.com/signals/btcusdt), [Dialog stub](https://tradebise.com/signals/gbpusd), [Authoritative posted plan description](https://tradebise.com/terms).

Support says crypto confirmation precedes activation, premium stops after 30 days, and one active session per account is permitted. This may affect a future cloud login's local-session continuity; it does not explain the separately observed Cloudflare rejection. Refund language excludes poor trading outcomes but describes correcting activation/incorrect-charge faults. Founder-operated support aims at 24-hour replies with paid users prioritised; quality/SLA untested. [Support/activation/session rules](https://tradebise.com/support).

## Advertising audit

| Page/type | Observed or offered inventory | Physical count / placement certainty |
|---|---|---|
| Earlier homepage | Two Advertisement-labelled areas, direct-booking/self-promotion; SevioAd/adx.ws labels | Historical browser observation only; no durable screenshot; exact current fill unknown |
| Signal-page commercial offer | Native placement before signal; banner between signal and chart (728×90 desktop, 320×100 mobile) | Two offered placements on every market page; not a verified rendered total |
| Application shell | 300×250 ad-placeholder text near market navigation | Source-only; relationship to the two marketed slots and actual fill unresolved |
| Coin promotion | Boosted top-of-list coin and optional homepage slide-up linking into its market | Sponsorship product, not independent trending rank; actual campaign not sampled |
| Learn/About/legal/support | No ad-placement labels exposed by retrieved text | Cannot infer zero ads from a text extractor; density unverified |

[Placement and booking description](https://tradebise.com/advertise), [Shell placeholder](https://tradebise.com/signals/eurusd), [Sponsored discovery product](https://tradebise.com/promotion).

Advertise claims human campaign review and rejects gambling, guaranteed-return, unlicensed fund-handling, malicious and adult categories. Booking is via email quote with placement, market, duration, creative and budget; no fixed rate is published. It claims every advertisement is labelled. Earlier homepage labels support limited sample separation, but signal-page labelling, mobile density, sticky/interstitial behavior and ad-versus-analysis separation still require screenshots. Promotion claims sponsorship changes visibility but not algorithm output; independence is not audited. Actual CPM/CPC, revenue split, provider relationships, fill, tracking/consent and sponsored-selection impacts remain unknown. No advertiser inquiry/payment was submitted.

## SEO architecture

| Dimension | Observable evidence | Unknown / caution |
|---|---|---|
| URLs | Lowercase /signals/{symbol}, descriptive /learn/{slug}; separate information/commercial paths | All possible symbol routes not enumerated; 5,000 markets ≠ 5,000 indexed pages |
| Title/H1 | Symbol-specific title and same symbol/direction/level H1 pattern across all ten; homepage multiasset positioning | Exact metadata retained once in source index; canonical and description head tags not available |
| Editorial | 15 articles across five topic labels; author/date/read-time; H2/H3 sections | Category labels appear without separate category links in retrieved catalog |
| Internal links | Homepage ten popular markets; footer informational links; catalog articles; 34 contextual cross-links; article-end product CTA | Client-side links/search outcomes not reconciled |
| Breadcrumb-like text | Back-to-markets and generic site/select-market trail | Structured BreadcrumbList schema not observed; generic trail does not prove selected symbol |
| Related content | Contextual in-body article links | No distinct related-card module established by text |
| Pagination | No pagination in retrieved 15-guide catalog | Dynamic pagination unknown |
| Programmatic pattern | Ten symbol routes share extensive shell/copy with substituted symbol | Distinct useful body/data and actual indexability untested; repetition is not proof of rankings |
| Conversion placement | Signup cues in navigation, product CTA after education, quota/upgrade scaffolding | Real impressions/conversion/notification delivery unmeasured |
| Robots/sitemap | Both public endpoints requested | Retriever Internal Error; no content/status obtained, no absence/404 claim |
| Schema/head | Page titles/H1 observable | Canonical, robots meta, JSON-LD, OG/description source tags and hreflang unverified |

[Homepage](https://tradebise.com/), [Symbol template](https://tradebise.com/signals/aapl), [Editorial hub](https://tradebise.com/learn), [Contextual-link example](https://tradebise.com/learn/reading-market-structure).

No measured rankings, search traffic, index coverage, backlinks, Core Web Vitals, canonical consolidation or ad-layout stability evidence was collected. The reusable pattern memo is a proposal constrained by current VowSig gates, not an implementation or forecast of SEO success.

## Legal/privacy and inaccessible states

Risk disclaimer says the platform is algorithmic analysis, is not a licensed broker/adviser or registered financial institution, and does not guarantee accuracy/results; third-party data may be delayed. This is a site disclosure, not independent regulatory verification. [Risk disclosure](https://tradebise.com/risk-disclaimer).

Privacy describes account/watchlist/device/visitor/rate-limit data, optional notifications/2FA and crypto transaction references; declares seven-day search/activity and 30-day signal/security-log retention. It claims no cross-site profiling ad networks/advertising cookies. That claim needs technical verification alongside the earlier third-party ad-provider observation; the audit does not assert a privacy violation or validate provider behavior. [Data policy](https://tradebise.com/privacy).

| State / requirement | Status and remaining work |
|---|---|
| Cloud login/CAPTCHA | Failed verification; credential-protected observation; automatic review rejected renewed handoff. No further attempt performed |
| Search, market dropdown, four timeframe results | Controls observed/source-described; click outcomes, persistence and call quotas untested |
| Watchlist, Trending/Gainers/Losers, news | Public shell exists; list contents/ranking rules/add behavior untested |
| Performance drilldown / recent results | Source scaffold; exact outcome population and history untested |
| Notifications/alert markets/Telegram | Source plan/settings copy; no permissions, Telegram linking or delivery test |
| Account/profile/security/payment history | Source-only placeholders; actual authenticated menu/data inaccessible |
| Registration/reset/payment states | Blank source scaffolds; no new account/agreement/reset/payment initiated |
| Bot offer / trading platforms | Forthcoming/source-only; functional behavior and permissions unknown |
| Prize promotion scaffold | Source includes a football-vote/BNB giveaway and paid-odds cue; whether live/visible/available is unverified. No participation |
| Mobile/ad templates | All physical placements, scroll coverage and responsive differences lack screenshots |
| Robots/sitemap/head schema | Retrieval/observability gaps explicitly retained |

All **34 public routes need durable visual evidence**, and the authenticated state backlog needs successful cloud access before reconciliation. The zero-entry screenshot manifest is intentional and honest; source documents/hashes are not substituted for screenshots. No passwords, OTPs, CAPTCHA tokens, cookies, API keys, card or owner-account data were retained. Read-only metadata/source text contains placeholders only and was summarized rather than committing secret-bearing login content or wholesale articles. The audit remains blocked at the visual/authenticated boundary.

