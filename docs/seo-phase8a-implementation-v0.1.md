# VowSig SEO Phase 8A — Isolated Public-Surface Implementation v0.1

_Status: IMPLEMENTED ON ISOLATED BRANCH / TESTS PENDING / DRAFT PR #18 / DO NOT MERGE_  
_Date: 2026-10-02_  
_Branch: `product/vowsig-seo-phase8a-v0.1`_  
_Parent milestone: GitHub Issue #8_

## 1. Scope

This batch implements the first small Phase 8A search/discoverability surface
inside the already-reviewed public-surface governance boundary.

It does not change AI-v1.1 decision behavior, AI-v1.0 decision protocol, S02,
ledgers, inference cadence, scheduler, provider/MT5 behavior or broker execution.

No v0.2 correction anchor has been generated yet.

## 2. Public route changes

### Indexable HTML

- `/`
- `/markets/`
- `/markets/xau-usd/`
- `/markets/nasdaq-100/`
- `/markets/dow-30/`
- `/learn/`
- `/learn/buy-sell-no-trade/`
- `/learn/backtests-vs-forward-results/`
- `/learn/immutable-signal-history/`
- `/learn/shadow-validation/`
- `/learn/signal-lifecycle/`
- `/evidence/`

This is intentionally a small first batch.

### Permanent market aliases

- `/markets/xauusd/` -> `/markets/xau-usd/`
- `/markets/ustec/` -> `/markets/nasdaq-100/`
- `/markets/us30/` -> `/markets/dow-30/`

Aliases are not included in the sitemap.

## 3. Crawler/index controls

### robots.txt

The app now serves `/robots.txt` with:

- `Allow: /`
- disallow guidance for `/api/`, `/healthz`, `/docs`, `/redoc`,
  `/openapi.json`;
- canonical sitemap declaration.

### sitemap.xml

The app serves a deterministic sitemap containing only the twelve canonical
indexable HTML routes.

It excludes:

- APIs;
- health;
- FastAPI framework docs;
- static assets;
- redirect aliases;
- internal/admin/feedback-ingestion routes.

### X-Robots-Tag

The app adds:

`X-Robots-Tag: noindex, nofollow, noarchive`

to:

- `/healthz`;
- every `/api/*` response;
- every `/static/*` response.

The `/static/*` rule is important because the existing StaticFiles mount
exposes the entire tracked `web/` directory. Without this header, the new HTML
source files would also be reachable through duplicate
`/static/...html` URLs. The noindex header keeps those duplicate static paths
out of the intended organic surface without blocking CSS/JavaScript rendering.

### Framework documentation

Production FastAPI configuration now disables:

- Swagger docs;
- ReDoc;
- OpenAPI JSON.

These were confirmed publicly reachable in the pre-implementation live
baseline and are not intended customer acquisition surfaces.

## 4. Root-page changes

The existing live dashboard remains the root product surface.

Added:

- explicit robots index/follow metadata;
- basic truthful `WebSite` JSON-LD;
- primary navigation to Markets / Learn / Evidence;
- persistent footer navigation;
- shared content styling.

The existing live AI/evidence/feedback sections remain intact.

## 5. Market pages

Initial market pages:

1. XAU/USD / internal symbol XAUUSD;
2. NASDAQ 100 / internal symbol USTEC;
3. DOW 30 / internal symbol US30.

Each page:

- has a unique title/description/canonical URL;
- describes the current evidence state without claiming profitability;
- states or links to the shadow/broker-disabled boundary;
- points users back to the live dashboard for current dynamic evidence;
- links into Learn and Evidence pages.

## 6. Learn pages

Initial factual education batch:

1. BUY / SELL / NO_TRADE;
2. Historical backtests vs forward results;
3. Why losses and unresolved outcomes stay visible;
4. What shadow validation means;
5. Signal entry, stop, targets and expiry.

A Learn hub links the batch together.

The copy is deliberately based on frozen/current product mechanics rather than
assumed customer terminology. Issue #9 real-user evidence remains the input for
Phase 8B language/content expansion.

## 7. Evidence hub

The Evidence page explains the separation between:

- AI-v1.1 active shadow runtime;
- AI-v1.0 frozen decision protocol;
- S02 deterministic benchmark;
- historical research;
- immutable forward evidence;
- preregistered future review gates.

It does not publish new performance claims.

## 8. Metadata / structured data

Every new HTML page has:

- unique title;
- unique meta description;
- self-referential canonical URL;
- robots index/follow metadata;
- Open Graph title/description/url;
- Twitter title/description;
- minimal truthful `WebPage` JSON-LD linked to the VowSig WebSite entity.

The root page has a `WebSite` JSON-LD identity.

No ratings, profitability, success-rate or review structured data is used.

## 9. Internal linking

The initial graph now has:

- homepage -> Markets / Learn / Evidence;
- Markets hub -> three market pages;
- market pages -> live dashboard + relevant Learn/Evidence pages;
- Learn hub -> first five education pages;
- education pages -> related education/evidence/dashboard surfaces;
- Evidence hub -> key education/dashboard surfaces.

No intended indexable page is designed as an orphan.

## 10. Test coverage

New `tests/test_seo_phase8a_public_surface.py` verifies:

- exact twelve-route indexable manifest;
- root navigation/canonical/JSON-LD;
- unique canonical metadata on every new page;
- research-beta/non-guarantee disclosure;
- robots policy;
- sitemap contents;
- FastAPI framework docs disabled;
- API/health noindex headers;
- static duplicate HTML noindex headers;
- intended indexable pages are not noindexed;
- permanent alias redirects;
- key evidence-boundary wording;
- no obvious prohibited win/profit marketing phrase in the staged HTML.

Existing branding, cloud runtime and public-surface correction tests must also
continue to pass.

## 11. Governance relationship

This implementation changes activation-bound public files:

- `src/trading_signal_intelligence/product/cloud_app.py`;
- `web/index.html`.

It also changes/adds tracked `web/` files.

Therefore the branch is intentionally invalid against the current production
v0.1 correction until the complete branch is:

1. tested in isolation;
2. reviewed;
3. anchored with one v0.2 correction successor;
4. pushed;
5. reverified as upstream-valid.

That fail-closed state is expected.

## 12. Next checkpoint

Owner/VPS isolated branch tests should now cover:

- Python compilation;
- v0.1 + v0.2 correction tests;
- SEO public-surface tests;
- VowSig branding;
- cloud runtime validation;
- cloud durability unit tests;
- product feedback tests;
- observability/runtime/cutover governance tests.

Do not run the v0.2 correction builder before this implementation test passes.

## 13. Production boundary

PR #18 remains **DRAFT / DO NOT MERGE**.

No production deployment is authorized by this implementation commit set.
