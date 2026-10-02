# VowSig SEO Phase 8A — Baseline Audit and Implementation Plan v0.1

_Status: REPOSITORY + LIVE BASELINE COMPLETE / PUBLIC-SURFACE CORRECTION V0.2 DESIGN NEXT / NO WEBSITE MUTATION_  
_Date: 2026-10-02_  
_Parent milestone: GitHub Issue #8 — Organic acquisition & SEO v0.1_  
_Canonical domain: https://vowsig.com_

## 1. Scope and evidence boundary

This document is the first Phase 8A checkpoint.

It audits the current production implementation from the repository and the latest
owner-verified VowSig production state already recorded by the project. It does
not modify the website, AI runtime, S02, ledgers, scheduler, cloud deployment or
broker boundary.

Under the project's current context-isolation rule, no external keyword-volume,
Search Console, third-party crawler, Lighthouse or independent SERP dataset is
used in this checkpoint. Those may be added only through an explicitly admitted
future source/workflow.

Before any website mutation, perform one read-only live HTTP probe to confirm
the repository-derived assumptions for root/robots/sitemap/docs/API status.

**Live probe completed 2026-10-02 and matched the repository-derived baseline.**

## 2. Current public architecture

The current VowSig customer surface is a single FastAPI-served HTML page:

- `GET /` -> `web/index.html`;
- `/static` -> `web/` static assets;
- JavaScript populates live product data from public JSON endpoints;
- no dedicated market, education, methodology or evidence HTML routes exist.

Public/runtime endpoints currently declared by `cloud_app.py` include:

- `/`;
- `/healthz`;
- `/api/health`;
- `/api/evidence`;
- `/api/markets`;
- `/api/ai/insights`;
- `/api/signals`;
- `POST /api/feedback`.

Owner-authenticated/internal endpoints also exist under `/api/internal/...`.

Because FastAPI is instantiated without overriding its documentation URLs, the
framework defaults should be assumed present until the live probe proves
otherwise:

- `/docs`;
- `/redoc`;
- `/openapi.json`.

These are not intended organic landing pages.

## 3. What is already good for discoverability

The root HTML already contains several strong technical foundations:

- `<!doctype html>`;
- `<html lang="en">`;
- mobile viewport metadata;
- one clear H1;
- structured H2/H3 section hierarchy;
- a descriptive HTML title;
- a meta description;
- self-referential canonical URL for the root page;
- Open Graph type/site/title/description/url;
- Twitter card/title/description;
- meaningful static explanatory copy before JavaScript data loads;
- explicit research-beta and non-guarantee disclosure;
- explicit historical-vs-forward separation;
- labels/fieldsets for the feedback form;
- `aria-live` for dynamic feedback status.

The page is not an empty client-side shell. Core positioning, evidence language
and disclosures are present in the initial HTML response.

## 4. Baseline gaps found in the repository

### 4.1 No robots.txt

No `robots.txt` file or root route exists in the repository.

Repository implication:

- no project-controlled crawler policy currently exists;
- `/api/internal/`, FastAPI docs and public JSON endpoints are not explicitly
  separated from intended indexable HTML through robots policy.

Live endpoint behavior still requires the read-only HTTP probe.

### 4.2 No XML sitemap

No sitemap file, sitemap generator or `/sitemap.xml` route exists.

Because the site currently has only one customer-facing HTML route, this has
limited immediate breadth impact, but a sitemap becomes necessary before
launching the planned market/education pages.

### 4.3 No structured data

No JSON-LD / schema.org markup exists.

Phase 8A should initially keep structured data conservative. A basic truthful
`WebSite` identity block may be appropriate. Do not add ratings, performance,
financial-product claims or FAQ markup that is not visibly supported by the
page.

### 4.4 No internal HTML link graph

The current root document has no navigation or meaningful internal anchor-link
architecture because there are no additional customer-facing HTML pages.

This is the largest information-architecture gap for the planned organic
surface.

### 4.5 No dedicated indexable market pages

XAU/USD, NASDAQ 100 / USTEC and DOW 30 / US30 are rendered inside the single
dashboard rather than having their own stable HTML URLs.

That prevents the product from expressing a clean market-specific information
architecture.

### 4.6 No dedicated education/evidence pages

The homepage explains several important concepts, but there are no stable pages
for:

- BUY / SELL / NO_TRADE semantics;
- backtests vs forward validation;
- immutable signal history;
- shadow validation;
- validation gates;
- AI runtime vs decision-protocol distinction;
- S02 benchmark vs AI evidence.

These concepts are suitable for factual Phase 8A content because they can be
grounded in already-frozen project behavior.

### 4.7 Most live evidence is client-rendered

The initial HTML contains explanatory text, but current market status, AI
decisions, signal records and evidence cards are inserted by `web/app.js`
after fetching JSON APIs.

Phase 8A should not depend on dynamic values being the only meaningful content
on future organic landing pages. The explanatory/search-relevant body copy,
headings, disclosures and internal links should exist in initial HTML; dynamic
current evidence can remain a supplemental client-rendered component.

### 4.8 Public JSON and framework documentation need an explicit index policy

The public product APIs are machine-readable product plumbing, not search
landing pages. FastAPI's default documentation/openapi surfaces are similarly
not intended customer acquisition pages.

Phase 8A should define and later implement an explicit noindex policy for:

- `/api/*`;
- `/healthz`;
- `/docs`;
- `/redoc`;
- `/openapi.json`.

For internal endpoints, access control remains the primary protection. Search
policy is not a security control.

### 4.9 Social metadata is incomplete

Root Open Graph/Twitter text metadata exists, but the repository has no
VowSig-specific social preview image declaration:

- no `og:image`;
- no `twitter:image`.

This is a distribution/share-quality gap rather than a core indexing blocker.

### 4.10 No favicon/brand asset is present in the web directory

The current `web/` directory contains only:

- `index.html`;
- `app.js`;
- `styles.css`.

A favicon/social asset set can be added later after brand-asset governance is
decided. It is not required before the technical SEO baseline is accepted.

### 4.11 Performance and Core Web Vitals are not measured in admitted evidence

The page is structurally lightweight in the repository, but no Phase 8A
performance measurement has yet been admitted.

Do not label performance "good" or "bad" from source inspection alone.

### 4.12 The Railway fallback hostname is a potential duplicate-host surface

The project intentionally keeps the Railway-generated hostname as an
infrastructure fallback. The root HTML's canonical tag points to
`https://vowsig.com/`, which is the correct canonical signal.

Before deciding on host-level redirects, confirm whether direct Railway-host
access is operationally required as a fallback. Do not remove that fallback
merely for SEO.

## 5. Critical governance constraint before any SEO website implementation

This is the most important implementation constraint discovered in Phase 8A.

The active AI-v1.1 activation/correction lineage fingerprints customer-facing
files that SEO work would naturally modify, including:

- `web/index.html` -> `ai_ui_index`;
- `web/app.js` -> `ai_ui_script`;
- `src/trading_signal_intelligence/product/cloud_app.py` ->
  `cloud_app_source`;
- other public/publisher artifacts.

The current public-surface correction verifier expects exactly one committed
`AI-v1.1-public-surface-correction-*.json` document and uses its hash overrides
as the effective expected hashes.

Therefore directly changing the current HTML/JS/cloud routing on production
`main` would make AI-v1.1 artifact verification fail closed unless a new
governed correction/supersession mechanism is prepared first.

### Required governance step before website mutation

Before implementing SEO changes that touch activation-bound files:

1. design a public-surface correction **v0.2 / supersession** mechanism;
2. preserve the existing v0.1 correction as immutable provenance;
3. prove the new mechanism cannot override frozen decision artifacts;
4. constrain changes to public/non-decision artifacts only;
5. verify no provider, MT5, ledger, scheduler, backfill or broker mutation;
6. test in isolation;
7. obtain owner approval for the production public-surface cutover;
8. verify ledger/runtime continuity after deployment.

Issue #8 Phase 8A planning may continue before this mechanism exists. Website
mutation must not.

## 6. Initial search-intent map — repository-derived v0.1

This is a first information architecture map, not a claim about keyword volume
or real-user terminology.

### Brand / product understanding

Intent:

- understand what VowSig is;
- understand what it does and does not do;
- understand research-beta/shadow status.

Proposed destination:

- `/`;
- later supporting page: `/learn/what-is-vowsig/`.

### Market intelligence

Intent:

- inspect VowSig's current/public evidence for a supported market;
- understand the market-specific signal/evidence state.

Initial destinations:

- `/markets/xau-usd/`;
- `/markets/nasdaq-100/`;
- `/markets/dow-30/`.

Display names should remain customer-friendly while clearly mapping to internal
symbols:

- XAU/USD -> `XAUUSD`;
- NASDAQ 100 -> `USTEC`;
- DOW 30 -> `US30`.

### Signal semantics

Intent:

- understand BUY / SELL / NO_TRADE;
- understand entry, stop, TP1, TP2, expiry and lifecycle;
- understand why a model may abstain.

Proposed cluster:

- `/learn/buy-sell-no-trade/`;
- `/learn/signal-lifecycle/`.

### Evidence / trust

Intent:

- understand historical vs forward evidence;
- understand why losses/unresolved signals remain visible;
- understand immutable records.

Proposed cluster:

- `/learn/backtests-vs-forward-results/`;
- `/learn/immutable-signal-history/`.

### AI validation / methodology

Intent:

- understand shadow validation;
- understand AI runtime vs decision protocol;
- understand A1/A2/A3 without treating them as marketing claims;
- understand AI vs S02 benchmark/control.

Proposed cluster:

- `/learn/shadow-validation/`;
- later methodology/evidence hub: `/evidence/`.

## 7. Proposed URL / information architecture v0.1

Keep the first surface deliberately small:

`/`
- product overview;
- live VowSig dashboard;
- research-beta status;
- paths into Markets, Learn and Evidence.

`/markets/`
- three supported live-evidence markets;
- evidence labels and methodology links.

`/markets/xau-usd/`
- XAU/USD-specific factual content + dynamic customer-safe evidence.

`/markets/nasdaq-100/`
- NASDAQ 100 / USTEC-specific factual content + dynamic evidence.

`/markets/dow-30/`
- DOW 30 / US30-specific factual content + dynamic evidence.

`/learn/`
- factual education hub.

First factual articles:

- `/learn/buy-sell-no-trade/`;
- `/learn/backtests-vs-forward-results/`;
- `/learn/immutable-signal-history/`;
- `/learn/shadow-validation/`;
- `/learn/signal-lifecycle/`.

`/evidence/`
- methodology/version/evidence-state hub;
- clearly separate S02 benchmark evidence and AI-v1.1 shadow evidence.

Do not create dozens of pages in the first implementation.

## 8. Canonical and redirect policy v0.1

- Canonical host: `https://vowsig.com`.
- One self-referential canonical per indexable HTML page.
- Prefer lowercase, hyphenated, trailing-slash page URLs for content routes.
- Avoid indexable query-parameter variants.
- If symbol aliases are later exposed, redirect aliases to the customer-facing
  canonical slug rather than index both:
  - `/markets/xauusd/` -> `/markets/xau-usd/`;
  - `/markets/ustec/` -> `/markets/nasdaq-100/`;
  - `/markets/us30/` -> `/markets/dow-30/`.
- Keep the Railway fallback decision separate from content-path redirects.

## 9. Index / noindex policy v0.1

### Intended indexable HTML

- `/`;
- `/markets/`;
- the three initial market pages;
- `/learn/`;
- reviewed factual education pages;
- `/evidence/`.

### Intended non-indexable plumbing

- `/api/*`;
- `/healthz`;
- `/docs`;
- `/redoc`;
- `/openapi.json`;
- internal/admin/export/ingest endpoints;
- raw static assets as sitemap entries.

Implementation should use response-level `X-Robots-Tag: noindex` for
non-HTML/API/docs surfaces where appropriate. `robots.txt` is supplemental
crawler guidance, not an access-control mechanism.

## 10. robots.txt plan

Initial policy concept:

- allow intended public HTML;
- disallow crawler exploration of internal/API/framework-documentation paths;
- advertise the canonical sitemap.

Exact file content must be reviewed with the final route map before deployment.

## 11. sitemap.xml plan

The first sitemap should contain only canonical indexable HTML URLs.

Do not list:

- APIs;
- docs/openapi routes;
- static assets;
- feedback submission endpoints;
- internal/admin paths;
- alias/redirect URLs.

Generate or serve the sitemap deterministically from the small approved route
list. Add dynamic last-modified timestamps only if they are truthful and stable.

## 12. Metadata plan

### Root page

Current root already has:

- title;
- description;
- canonical;
- OG title/description/url;
- Twitter title/description.

Before implementation, review whether the title/H1 should communicate the
product category more explicitly while retaining VowSig's existing evidence-first
positioning. Do not change customer language merely for keyword insertion.

### Per-page metadata

Each market/education page should have:

- unique title;
- unique meta description;
- self-canonical;
- truthful OG/Twitter title and description;
- optional shared or page-specific social image after brand-asset approval.

Avoid templated metadata that differs only by market symbol if the page body is
not genuinely unique.

## 13. Structured-data plan

Start conservative:

- `WebSite` for the canonical site identity;
- optional `WebPage`/article-like markup where page content genuinely supports
  it.

Do not add:

- aggregate ratings;
- claimed performance;
- review markup;
- profitability claims;
- unsupported `FinancialProduct` semantics.

Structured data must describe visible content, not create claims absent from the
page.

## 14. Internal-link model

The initial graph should be intentional:

- homepage -> Markets / Learn / Evidence;
- Markets hub -> each market page;
- each market page -> relevant signal-semantics + evidence pages;
- BUY/SELL/NO_TRADE -> live AI Insights / evidence explanation;
- backtests-vs-forward -> Evidence hub;
- immutable-history -> signal record/evidence hub;
- shadow-validation -> A1/A2/A3 explanation;
- Evidence hub -> each market page and relevant educational pages.

No orphan content pages.

## 15. First content set selected for Phase 8A

### Market pages

1. XAU/USD;
2. NASDAQ 100 / USTEC;
3. DOW 30 / US30.

### Factual education pages

First five priorities:

1. BUY vs SELL vs NO_TRADE;
2. Historical backtests vs forward results;
3. Why VowSig keeps losses and unresolved outcomes visible;
4. What shadow validation means;
5. How signal entry, stop, TP1, TP2 and expiry work.

Second wave, still allowed in 8A but not required for first deployment:

- What is VowSig?;
- How immutable signal records work;
- What AI-v1.1 vs AI-v1.0 means;
- What A1/A2/A3 validation gates mean;
- AI shadow decisions vs the S02 benchmark.

Issue #9 may reorder/rewrite/expand these in Phase 8B.

## 16. Measurement plan v0.1

Phase 8A needs measurement before broad content expansion.

### Search/discovery

Where owner-connected tools are later admitted:

- indexed URL count;
- impressions;
- clicks;
- CTR;
- query/page pairs;
- indexing/crawl errors.

### On-site relevance

Use privacy-respecting aggregate events only:

- organic landing-page visits;
- market/learn/evidence page views;
- click-through into live product evidence;
- feedback form start;
- feedback submission;
- later onboarding/signup/alert action if implemented.

Do not collect broker credentials, account identifiers, exact balances or other
sensitive trading/account data for SEO analytics.

### Success principle

Organic traffic is useful only when it reaches relevant product/evidence
surfaces and contributes to measurable user value.

Raw page count and raw visits are not milestone success criteria.

## 17. Phase 8A implementation order after baseline approval

### Checkpoint A — live read-only confirmation

Confirm status/content-type/canonical behavior for:

- `/`;
- `/robots.txt`;
- `/sitemap.xml`;
- `/docs`;
- `/redoc`;
- `/openapi.json`;
- key `/api/*` endpoints;
- Railway fallback hostname versus canonical host.

No mutation.

### Checkpoint B — governance for activation-bound public files

Design and test the public-surface correction v0.2/supersession mechanism before
editing `web/index.html`, `web/app.js` or `cloud_app.py`.

No production cutover without owner approval.

### Checkpoint C — technical SEO implementation

After governance passes:

- add approved routes;
- robots;
- sitemap;
- canonical/meta framework;
- noindex headers for plumbing;
- internal navigation/link foundation;
- minimal structured data.

### Checkpoint D — first small content batch

Publish:

- three market pages;
- up to five factual education pages;
- evidence hub.

Keep live/dynamic evidence supplemental to useful initial HTML.

### Checkpoint E — measurement + Issue #9

Verify discoverability/measurement, then run the controlled Issue #9 cohort in
parallel. Use those findings to revise Phase 8B.

## 18. Live production confirmation — 2026-10-02

Owner-run read-only GET probe against `https://vowsig.com` completed with no mutation.

Observed:

- `/`: HTTP 200 / `text/html; charset=utf-8`;
- title: `VowSig — Research Beta`;
- canonical: `https://vowsig.com/`;
- meta description present;
- robots meta absent;
- JSON-LD absent;
- `/robots.txt`: HTTP 404;
- `/sitemap.xml`: HTTP 404;
- `/docs`: HTTP 200;
- `/redoc`: HTTP 200;
- `/openapi.json`: HTTP 200;
- `/healthz`: HTTP 200;
- `/api/health`: HTTP 200;
- `/api/evidence`: HTTP 200;
- `/api/markets`: HTTP 200;
- `/api/ai/insights`: HTTP 200;
- `/api/signals`: HTTP 200;
- no tested route returned an `X-Robots-Tag` header.

Interpretation:

1. the root page is publicly indexable and already self-canonicalized;
2. crawler policy is not project-controlled yet because `robots.txt` is absent;
3. there is no sitemap yet;
4. FastAPI documentation/OpenAPI surfaces are publicly reachable and currently
   have no explicit noindex header;
5. public JSON endpoints likewise have no explicit noindex header;
6. the live deployment therefore confirms the repository-side technical SEO
   gaps rather than revealing a different production configuration.

The next checkpoint is not a website edit. It is the governed public-surface
correction v0.2 / supersession design required before activation-bound public
files can change.

## 18. Phase 8A status after this checkpoint

Repository-baseline findings:

- [x] current route/metadata architecture inspected;
- [x] robots implementation absent in repository;
- [x] sitemap implementation absent in repository;
- [x] structured-data implementation absent in repository;
- [x] internal-link/page architecture gap documented;
- [x] first market-page set selected;
- [x] first factual education set selected;
- [x] initial URL/information architecture documented;
- [x] index/noindex policy documented;
- [x] metadata/canonical/robots/sitemap plan documented;
- [x] internal-link model documented;
- [x] privacy-respecting measurement plan documented;
- [x] activation-bound website mutation risk identified;
- [x] live read-only endpoint/status probe completed;
- [ ] public-surface correction v0.2/supersession mechanism designed/verified — **NEXT**;
- [ ] technical implementation approved;
- [ ] website changes made;
- [ ] search/indexing measurement connected.

No website mutation is authorized by this document alone.
