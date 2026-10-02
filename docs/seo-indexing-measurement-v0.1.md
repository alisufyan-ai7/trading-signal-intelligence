# VowSig SEO Phase 8A — Search Indexing & Measurement v0.1

_Status: ACTIVE / OWNER SEARCH-ENGINE SETUP REQUIRED / NO WEBSITE MUTATION REQUIRED_  
_Date: 2026-10-02_  
_Parent milestone: GitHub Issue #8 — Organic acquisition & SEO v0.1_  
_Canonical domain: https://vowsig.com_

## 1. Purpose

Move Phase 8A from a technically indexable production surface into measurable
organic discovery.

This checkpoint has two goals:

1. establish ownership/indexing visibility in the two target search-engine
   webmaster platforms;
2. create a privacy-respecting baseline for organic search discovery before
   Phase 8B content expansion.

The production technical SEO surface is already live and naturally verified.
This checkpoint does not require changing AI-v1.1, S02, ledgers, scheduler,
broker execution, or the current public website files.

## 2. Current production indexing surface

Canonical production domain:

`https://vowsig.com`

Production sitemap:

`https://vowsig.com/sitemap.xml`

Production robots file:

`https://vowsig.com/robots.txt`

Canonical indexable route set:

1. `/`
2. `/markets/`
3. `/markets/xau-usd/`
4. `/markets/nasdaq-100/`
5. `/markets/dow-30/`
6. `/learn/`
7. `/learn/buy-sell-no-trade/`
8. `/learn/backtests-vs-forward-results/`
9. `/learn/immutable-signal-history/`
10. `/learn/shadow-validation/`
11. `/learn/signal-lifecycle/`
12. `/evidence/`

Production verification already established:

- all 12 routes return HTTP 200;
- intended pages are not noindexed;
- APIs/health/static plumbing are explicitly noindexed;
- framework docs/OpenAPI are disabled publicly;
- sitemap contains only intended canonical HTML routes;
- robots advertises the canonical sitemap;
- natural post-cutover AI-v1.1 and publisher continuity passed.

## 3. Measurement principle

The project should measure **relevant discovery**, not raw traffic.

Primary funnel:

search impression  
-> organic click  
-> useful market / education / evidence page  
-> live VowSig product  
-> feedback / onboarding action  
-> later paid conversion only when pricing exists

Phase 8A does not treat impressions or page count as customer-value evidence.

## 4. Privacy boundary

For this first indexing/measurement phase, prefer aggregate webmaster/search
metrics rather than adding a third-party page-view script.

Do not collect for SEO measurement:

- broker credentials;
- account IDs;
- trading account numbers;
- exact balances;
- API keys;
- card/payment data;
- raw market data;
- hidden model reasoning;
- user-level financial profiles.

No new browser analytics script is required for this checkpoint.

## 5. Google indexing setup — owner action

Target property:

`vowsig.com`

Preferred verification approach:

- use a domain-level ownership method that does not require modifying
  activation-bound VowSig public files;
- DNS verification is therefore preferred where available.

After ownership is verified:

1. add/confirm the canonical production property for `vowsig.com`;
2. submit `https://vowsig.com/sitemap.xml`;
3. verify the sitemap is accepted/processed;
4. inspect the root URL and the first market/learn/evidence URLs;
5. record whether each is discovered, crawled and/or indexed;
6. do not force repeated resubmission merely because indexing is not immediate.

No Google verification token, account identifier or private account screenshot
belongs in GitHub.

## 6. Bing indexing setup — owner action

Target site:

`https://vowsig.com`

Preferred ownership path:

- use an account/site import from the already verified search property where
  supported, or;
- use a DNS-based/site-ownership method that does not require modifying the
  activation-bound public files.

After ownership is established:

1. add/confirm `https://vowsig.com`;
2. submit `https://vowsig.com/sitemap.xml`;
3. verify sitemap discovery/processing;
4. inspect the same canonical route set;
5. record aggregate indexing/crawl status.

Do not commit verification secrets/tokens to the repository.

## 7. Why DNS/import is preferred for this project

The VowSig public surface is governed by the AI-v1.1 public-surface correction
chain.

Adding search-engine verification meta tags or public verification files would
create another public-surface byte change and therefore require a new governed
correction successor and production cutover.

If search-engine ownership can be proven through DNS or account import, there is
no reason to mutate the production website solely for site verification.

Therefore:

- **preferred:** DNS / platform import;
- **fallback:** meta tag or verification file only if necessary, and only
  through a new governed public-surface correction/cutover.

## 8. Baseline measurement schema

Create one aggregate checkpoint after both search-engine properties are
verified and their sitemap has been submitted.

Record only non-sensitive aggregates.

### Site-level fields

- checkpoint date/time UTC;
- search engine;
- property/site verified: yes/no;
- sitemap submitted: yes/no;
- sitemap accepted/processed status;
- sitemap discovered URL count;
- indexed page count where reported;
- crawl/index errors where reported;
- total search impressions;
- total organic clicks;
- aggregate CTR;
- average position/ranking metric where reported;
- measurement window;
- notes.

### Page-level fields

For each of the 12 canonical pages, record where available:

- URL;
- discovered: yes/no/unknown;
- indexed: yes/no/unknown;
- impressions;
- clicks;
- CTR;
- average position/ranking metric;
- top non-sensitive query themes if available;
- notes.

Do not store query data that contains personal information or account-specific
identifiers.

## 9. Initial measurement cadence

Until there is meaningful volume:

- **Day 0:** ownership + sitemap submission baseline;
- **Day 7:** first discovery/indexing review;
- **Day 14:** second review;
- **Day 28:** first meaningful Phase 8A organic-discovery review.

After Day 28:

- weekly or biweekly checks are sufficient unless indexing/crawl problems are
  detected.

Do not react to day-to-day ranking noise.

## 10. Phase 8A decision rules

### Continue without changing content when

- URLs are being discovered/crawled;
- indexing is still propagating;
- impressions are low but non-zero;
- no material crawl/canonical problem exists.

### Investigate technical SEO when

- sitemap is rejected;
- canonical pages remain undiscovered after a reasonable observation period;
- intended pages are excluded for a technical reason;
- canonical/redirect conflicts appear;
- robots/noindex unexpectedly blocks canonical pages.

### Do not change content solely because

- a new page has no impressions in the first few days;
- average position fluctuates;
- one search engine indexes faster than another.

Phase 8B wording/content expansion remains gated on Issue #9 real-user
evidence, not short-term ranking noise.

## 11. Organic discovery metrics for Phase 8A

Primary:

- verified search properties;
- sitemap acceptance;
- number of intended canonical pages discovered;
- number indexed;
- impressions;
- clicks;
- CTR;
- landing pages receiving organic impressions/clicks.

Secondary:

- query themes;
- crawl/index exclusions;
- relative market-page discovery;
- relative Learn/Evidence discovery.

Not yet a success metric:

- revenue;
- paid conversion;
- strategy profitability;
- AI trading performance.

## 12. Relationship to Issue #9

Issue #8 Phase 8A may collect search discovery data before Issue #9.

Issue #9 remains necessary before:

- using customer language to rewrite/expand SEO content;
- prioritizing pages based on stated customer needs;
- stronger CTA/conversion copy;
- alert-channel SEO;
- pricing or paid-plan SEO.

Search query themes can be used as an additional evidence source, but they do
not replace real-user G4 evidence.

## 13. Evidence handling

GitHub may store:

- aggregate indexing checkpoint summaries;
- sitemap/index counts;
- impressions/clicks/CTR totals;
- page-level aggregate discovery data;
- non-sensitive query themes;
- screenshots only if they contain no private account data/tokens.

Do not store:

- login emails;
- passwords;
- verification tokens;
- account IDs;
- recovery information;
- unrelated account properties;
- user-level search data.

## 14. Initial owner-action checklist

- [ ] Google search property for `vowsig.com` verified;
- [ ] Google sitemap submitted;
- [ ] Google sitemap accepted/processed status captured;
- [ ] Bing site for `https://vowsig.com` verified/imported;
- [ ] Bing sitemap submitted;
- [ ] Bing sitemap accepted/processed status captured;
- [ ] Day-0 aggregate baseline captured;
- [ ] Day-7 review scheduled;
- [ ] Day-14 review scheduled;
- [ ] Day-28 review scheduled.

## 15. Repository-side work complete at this checkpoint

- [x] canonical production route set defined;
- [x] production robots/sitemap verified;
- [x] privacy-safe measurement schema defined;
- [x] owner/action boundary defined;
- [x] no website mutation required for preferred verification path;
- [x] Phase 8B evidence boundary preserved.

## 16. Next action

Owner verifies VowSig in the target search-engine webmaster platforms using
DNS/import where possible, submits the canonical sitemap, and returns the
non-sensitive status/results.

After that, create the Day-0 indexing/measurement checkpoint in the repository
and begin the first observation window.
