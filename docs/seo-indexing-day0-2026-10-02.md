# VowSig SEO Phase 8A — Day-0 Indexing Baseline

_Status: DAY-0 CAPTURED / PROPAGATION IN PROGRESS_  
_Date: 2026-10-02_  
_Parent: docs/seo-indexing-measurement-v0.1.md_  
_Canonical domain: https://vowsig.com_

## 1. Production state

Production SEO Phase 8A cutover merge:

`5e6b7ae412f79ce11a60ba5f64739d8f2fa951ec`

Current GitHub main at Day-0 capture:

`0655f12db096b027111a10dbbd59bf0553cac4eb`

The technical SEO surface was already production-verified before this indexing
baseline:

- 12 canonical indexable HTML routes;
- canonical sitemap at `https://vowsig.com/sitemap.xml`;
- robots file advertising that sitemap;
- intended public pages indexable;
- APIs/static plumbing explicitly noindexed;
- framework docs/OpenAPI disabled;
- natural post-cutover AI-v1.1 and publisher continuity PASS.

## 2. Google Search Console — Day 0

Property:

`vowsig.com`

Observed state:

- property accessible/verified in Search Console;
- sitemap submitted: `https://vowsig.com/sitemap.xml`;
- submission date shown: 2026-10-02;
- last-read date shown: 2026-10-02;
- sitemap status: `Sitemap could not be read` / `Couldn't fetch`;
- discovered pages: 0;
- discovered videos: 0.

Independent production diagnostics performed after the Search Console error:

### Public browser

`https://vowsig.com/sitemap.xml`

- publicly readable in a private/incognito browser;
- valid XML tree rendered without authentication.

### Browser-style versus Googlebot-style parity probe

For `/`, `/robots.txt`, and `/sitemap.xml`, browser-style and Googlebot-style
requests returned byte-identical responses.

Sitemap result:

- HTTP 200;
- final URL unchanged;
- content type `application/xml`;
- body bytes: 809;
- no `X-Robots-Tag`;
- SHA-256:
  `d4cac29fe3c055b42a90f3614f9e522d9b61fc6c867e99fa63e94bf07f1caf47`.

Interpretation:

There is currently no evidence of a VowSig crawler-specific block, alternate
Googlebot response, redirect mismatch, or malformed public sitemap response.

The Google state is therefore recorded as:

**property verified / sitemap submitted / Google processing-fetch state unresolved**

No production sitemap change is justified from Day-0 evidence.

## 3. Bing Webmaster Tools — Day 0

Site shown in Bing Webmaster Tools:

`vowsig.com/`

Observed sitemap state:

- known sitemaps: 1;
- sitemaps with errors: 0;
- sitemaps with warnings: 0;
- total URLs discovered: 0;
- sitemap URL: `https://vowsig.com/sitemap.xml`;
- last submit: 2026-10-02;
- last crawl: not yet shown;
- status: `Processing`;
- discovered URL count for the sitemap row: not yet populated.

Interpretation:

Bing has accepted the sitemap submission into its processing queue and has not
reported a sitemap error or warning. The current zero-discovery state is a
pre-crawl / pre-processing baseline, not a technical failure.

The exact ownership verification method (DNS/import/other) is not recorded in
this checkpoint because the supplied evidence did not establish that detail.

## 4. Day-0 aggregate baseline

| Metric | Google | Bing |
| --- | --- | --- |
| Property/site active in webmaster tooling | Yes | Yes |
| Sitemap submitted | Yes | Yes |
| Sitemap status | Could not be read / Couldn't fetch | Processing |
| Sitemap errors | Not separately reported | 0 |
| Sitemap warnings | Not separately reported | 0 |
| Discovered URLs/pages | 0 | 0 |
| Last crawl | Not established | Not yet shown |
| Indexed pages | Not yet established | Not yet established |
| Impressions | Not yet established | Not yet established |
| Organic clicks | Not yet established | Not yet established |
| CTR | Not yet established | Not yet established |

## 5. Day-0 decision

Technical sitemap mutation:

**NO**

Reason:

- live sitemap is publicly readable;
- live sitemap passed production cutover verification;
- browser and Googlebot-style responses are identical;
- Bing reports no sitemap error/warning and is still processing;
- Google currently reports a fetch/read condition without corroborating
  production-side failure.

## 6. Observation plan

### Google

- leave the submitted sitemap unchanged;
- do not repeatedly delete/re-add/resubmit during the initial propagation window;
- recheck the Search Console sitemap state after roughly 12–24 hours;
- if the same read/fetch error persists, perform the next-level DNS/TLS/public
  network diagnostic before changing production.

### Bing

- leave the sitemap unchanged while status is `Processing`;
- recheck after Bing has performed a crawl;
- capture discovered URL count, warnings/errors and indexing state when
  populated.

## 7. Scheduled measurement checkpoints

- Day 0: **CAPTURED**
- Day 7: pending
- Day 14: pending
- Day 28: pending

Phase 8B content/conversion expansion remains gated on initial Issue #9
real-user evidence.
