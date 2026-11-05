# VowSig mobile-first experience and competitor design review — 2026-11-06

## Owner direction / scope
Design must be **mobile-first**, visibly more refined and usable than the initial engineering-oriented beta. Benchmark the presentation principles from TradingTop and Tradebise without reproducing their proprietary branding, designs, unverified figures or commercial mechanics. Work only in PR #93; main, production website, production Railway, Windows collector/publisher, execution, notifications, paid entitlements and source rights remain unchanged.

## Evidence available
- Repo historical authenticated competitor teardown: `docs/tradingtop-authenticated-teardown-and-product-gap-2026-09-28.md` and redacted captures under `research/competitors/tradingtop/2026-09-27/`.
- Repo October 4 authenticated Tradebise desktop Free study: `docs/tradebise-authenticated-product-business-seo-audit-2026-10-04.md` and redacted captures under `research/competitors/tradebise/2026-10-04/`.
- Existing four-way synthesis: `docs/competitor-synthesis-waqarzaka-tradebise-tradingtop-vowsig-2026-10-04.md`; still authoritative for the **limits of competitor performance claims** and disallowed paid/execution features.
- New public landing pages checked November 6: TradingTop promotes compact AI-centered hero and action paths; Tradebise foregrounds search, market/timeframe context, saved lists, outcome tiles and bottom mobile navigation labels. This is a **presentation comparison only**, not certification of either competitor's performance or actual mobile test.
- Existing VowSig member HTML/CSS/JS inspected at PR #93 HEAD; mobile breakpoint previously flattened the full desktop sidebar into horizontally scrolling links and hid `.sidebar-bottom`, removing the visible sign-out affordance on small screens.

## Mobile-first product experience target
Use a deliberate **information hierarchy**, rather than crowding everything on the first screen:
1. **Current status and trust:** Fresh / delayed / unavailable source and the SHADOW_ONLY boundary. Never label archived scheduler state current.
2. **What matters:** Nine discoverable symbol cards; only three eligible core markets may have sanitized research details, subject to the true source policy.
3. **What happened:** Losses, NO_TRADE, issuance/expiry and traceable outcomes with provenance and no fabricated net-R.
4. **Return journey:** Search/filter, watchlist, saved research, Learn, settings and clear sign-out.
5. **Owner:** diagnostics remain owner-only behind server-side role and MFA, with no false source or profitability claims.

## Design decisions implemented in draft
- `web/member/index.html`: fixed mobile navigation (Home, Signals, Markets, Saved, More) with More exposing History, Learn, Account, public evidence and securely reachable Sign out. Desktop rail remains at >=900px.
- `web/member/member.js`: mobile and desktop sign-out controls share the same POST with CSRF and session-cookie revocation. No client-side credential storage or new privileged API.
- `web/member/member.css`: mobile-first base, 320px fallback, 44px+ touch actions, stronger contrast/focus states, elevated research cards, consistent mint-on-deep-navy tokens, condensed status and legible disclosure, safe area bottom padding, responsive tables, reduced motion.
- `web/index.html`: factual evidence strip with nine monitored markets, shadow-only research and wins/losses/NO_TRADE (not a performance or live-signal claim).
- `web/styles.css`: clearer editorial hero hierarchy, more focused high-contrast CTAs, polished status panel and better phone-size spacing while retaining all AI + S02 benchmark sections.
- `tests/test_vowsig_member_browser_p3.py`: real local Chromium browser fixture at 320/375/768px checks mobile nav and More/Account/Sign out reachability, lack of horizontal overflow and CSRF-bound logout. The complete member integration suite still requires exact-HEAD CI and actual authenticated staging acceptance.

## Deliberately not copied
- Tradebise's live BUY/SELL generation, 5,000+ marketed markets, paid alerts, upgrade quota or execution/Bot controls.
- TradingTop's claimed AI accuracy, compute credits, equity curves or broker-linked auto trading.
- Fake verification ticks, made-up performance cards, fake live charts/market prices, unverified testimonials or intentionally misleading green badges.
- Third-party copyrighted logos, illustrations or branded interface art.

## Design QA acceptance / next work
- The FIRST browser acceptance is 320px, 375px, 390px and 768px portrait; then desktop 1280px/1440px, keyboard-only and reduced motion.
- Must prove viewport never horizontally overflows; essential navigation and sign-out remain touch/keyboard accessible; focus visible; disabled/empty/data-stale states clear.
- Check account dashboard, markets, watchlist add/remove, Signal Center, History, Learn, Settings and owner-only diagnostics on actual staged app, not only mocked fixture.
- Real member browser must login via verified Auth0, preserve watched markets across refresh, revoke logout old session, re-login, and enforce server-side three-vs-six market details. A screenshot alone is not live authentication proof.
- Visually review typography, density, hierarchy, hit targets, contrast, mobile top/bottom chrome, benchmark disclosure and history tables against dated competitor *presentation* references. Iterate based on actual test findings. No production release until all other PR #93 gates pass.
- Current staging snapshot absent and staging market data acceptance HOLD; truthful empty states are an acceptable UI state, not permission to fake data.

## Release / access constraints
New UI is in **draft PR #93 only** until staging is separately deployed at the exact tested SHA. Production release remains an owner-authorized exact-SHA merge and one fully enabled launch. Railway PostgreSQL offsite cold restore is explicitly the owner's immediate post-launch exception and must not become a false prelaunch blocker.
