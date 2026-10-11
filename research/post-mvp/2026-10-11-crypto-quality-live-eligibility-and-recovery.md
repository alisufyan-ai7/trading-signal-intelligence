# VowSig post-MVP: crypto research quality, current-data eligibility, recovery

**Date:** 2026-10-11 UTC. **Status:** independent engineering/research PREPARATION, not a new production release.
**Scope:** this TradingTop Analysis chat and private GitHub repo alisufyan-ai7/trading-signal-intelligence ONLY.
**Immutable production anchor:** main 8ec0e82ea340682d92f9a62acf85171b7715bf5d, tested tree d24d3736d0bf6633ad0d05c4a1f1373558f813b9. EXP-031 historical crypto MVP and the first natural hourly guarded publication are CLOSED PASS (Issue #47). Never repeat its one-shot release, recapture its seal, overwrite accepted archives, modify its running publisher or merge frozen drafts to "clean up."

## Three distinct workstreams

The public crypto-expansion-1 card is an intentionally FIXED **DELAYED** BTCUSDT/ETHUSDT/SOLUSDT research observation from 2026-10-11T12:07:21.257601+00:00. Hourly guarded publication refreshes **core and expansion**, not the crypto observation. C1/C2/C3 were ineligible in the saved historic sample; no public actionable crypto or broker execution. The natural publisher 2026-10-11T18:05:05Z successfully passed hosted semantic GET, nine market continuity, and accepted local snapshot/archive/receipt checks; remote stored-file byte digest remains unverified. None of this demonstrates crypto profitability.

The already activated K5 AI-v1.3 private 24/7 Binance Spot shadow scanner is separate. It may gather new observations under its existing frozen K3/K4/K5 approvals. Public snapshot metrics must NEVER be presented as its current results. Do not tune/fork its cohort/policy/schedule/ledgers or infer fresh evidence from the historical sample.

### A. Crypto research quality — measure honestly before any changes

Reuse existing frozen sources:
- EXP-2026-017 preregistration and config/ai_v1_3_crypto_review_gates.json.
- EXP-2026-018 cost protocol and config/ai_v1_3_crypto_cost_policy.json.
- scripts/report_ai_v1_3_crypto_progress.py and crypto_observability_v1_3.py: read-only private report, but its FULL JSON contains confidential ledger paths/hashes/record IDs and is **not for GitHub or public APIs**.
- This isolated branch adds scripts/audit_crypto_research_quality_v0_1.py plus synthetic-only tests. The new tool accepts a previously generated full report via memory/stdin or a local explicitly specified JSON file, reads only the repo's frozen JSON policies, and emits ONLY whitelisted cohort/market aggregate metrics, C1/C2/C3 gaps and observational net-R/expectancy/profit-factor/drawdown. It never opens SQLite, calls Binance/OpenAI, reads credentials, alters files or posts. Running the original private report generator on the VPS still requires separate owner consent; the assistant did NOT run it.

Mandatory methodology:
- Never remove SOL or skip low-activity markets; preserve all three BTC/ETH/SOL, low/negative performance, and NO_TRADE, REJECTED_INFERENCE, MISSED_INFERENCE, ERROR distinctions; no backfills treated as live evidence.
- Preserve completed H1/H4 UTC chronology, Binance Spot base-asset volume (not MT5 CFD/tick-volume), genuine top-of-book bid/ask and <=300-sec feature context, 24/7 weekend/weekday observation split, and fail-closed missing data.
- Frozen proxy cost: taker fee 0.001 per side, 1.0 observed spread round-trip crossing and 1.0 additional spread slippage buffer, total 0.002 * entry midpoint + 2.0 * entry spread; reject cost greater than 0.15R. This is a RESEARCH proxy, not executable short borrow, margin funding, account-size impact, fill-price feasibility or venue fee guarantee. No performance-driven fee discounts.
- Cohort and each market must show actual denominators, net-R expectancy, PF when mathematically defined, drawdown, hold/outcome mix, weekday/weekend counts, and operational miss/error rates. Observational small-N metrics are NOT predictive validity. Existing private read-only report supplies weekday/weekend counts but NOT full weekday/weekend economic outcome attribution or confidence calibration: separately preregister these analyses and review their raw assumptions before adding any implementation. Never make up these values.
- Preserve immutable gate meaning: C1 at 100 valid inferences +20 completed trades, 0-day floor is **operational only**, not economic rejection/tuning permission. C2 at 500/50/60 days is interim economics. C3 at 1000/100/120 days is first publishability/graduation review. All count AND calendar conditions required, no per-market count floor, no gating substitution, no automatic public crypto signal or broker permission at any gate.
- Small-sample uncertainty, confidence calibration, 24/7 weekend regime stratification, realistic executable depth, and stable out-of-sample performance are RESEARCH gaps. Do not optimize thresholds, change symbols, fees, prompt/model or market filters based on early shadow results.

**Next genuine quality evidence action** after exact-SHA synthetic tests: separately authorize one read-only actual-VPS full K5 observability report and pipe its output **in memory** to this aggregate-only quality auditor, without writing the private raw JSON to GitHub or anywhere public. Until this, current private crypto performance is UNOBSERVED by this chat; do not substitute the fixed historical card.

### B. Clarify three meanings of "live" and their separate controls

1. **PRIVATE live market-data collection in K5 SHADOW_ONLY:** Already operating under earlier frozen activation; public Binance Spot data feeds do not imply public trade signals or exchange orders. No further data-collection authorization is inferred.
2. **CURRENT public crypto aggregate observability:** NOT ACTIVE. Production guarded publisher intentionally maintains CRYPTO_WRITER_INTERLOCK_READY=False because writer-side coordination through HTTPS acceptance was not proven. The fixed delayed sample is a safe exception, NOT a toggle for this gate. Next proposed design: K5 produces an immutable public-allowlisted per-completed-cycle aggregate with one causal UTC and consistent BTC/ETH/SOL ledger fingerprints, cross-snapshot SHA and validity horizon, retained separately from private source. The publisher proves one completed immutable identity at acceptance and expires to DELAYED/PENDING if old/missing. Alternative shared writer-publisher lock must be tested for windows running during upload. Both require prospective versioning, native Windows concurrency/crash/race tests, leak prevention, and separate source/governance approval. A boolean flip is forbidden and does not solve TOCTOU.
3. **PUBLIC actionable crypto signals, customer alerts, exchange/broker orders:** NOT AUTHORIZED. Requires a distinct post-C3 decision, defensible economically robust out-of-sample costs and order-book impact, commercial data rights, operational alerts/failsafes, product claims, separate risk/execution safety approval and compliant venue semantics. A shadow SELL is not executable Binance Spot short by assumption. No broker action under this branch.

**Recommendation:** First improve genuine quality measurement. In parallel design (but do not deploy) immutable per-cycle public aggregate consistency. Do not risk the already working nine-market/core/expansion publisher while solving crypto live-data concurrency.

### C. Backup/recovery — re-use existing work, do not pretend hashes equal backups

Grounded existing artifacts and branches:
- docs/vowsig-durable-ip-backup-and-recovery-plan-v0.1.md: SQLite online backup, isolated copies, integrity/ledger chain, encryption, primary AWS S3 Object Lock and independent Backblaze B2 design; no provider infrastructure currently established.
- Draft PR #52 EXP-027: synthetic-only SQLite online backup prototype, 17 synthetic native Windows tests reported PASS for its own SHA, not proof of all real databases.
- Draft PR #53 EXP-028: bounded single-S02 real-ledger backup implementation. Owner has already completed ONE local same-VPS online copy/re-open/chain validation (53,248 bytes, 17 records). Not offsite protection.
- Draft PR #54 EXP-029/030: B0 inventory and provider-rights readiness. B0 reported 22 SQLite candidates: 12 active (three S02, three AI-v1.1, three AI-v1.2.1, three AI-v1.3); 9 retired/failed/superseded; 1 research.sqlite raw-candle store on RIGHTS HOLD. Do not upload the raw-candle store or unclassified private data offsite without rights review.
- Production scripts/audit_guarded_snapshot_history_v0_3.py verifies SHA-named local sanitized archives and accepted receipts; its independent backup and remote byte durability fields remain FALSE. Product history also needs eventually protected offsite recovery.

Practical stages:
- **B0 inventory and rights closure:** confirm each governed active/superseded/failed evidence set, archive classification, path and source rights, WAL/journal conditions, encryption/secret boundaries. Do not blindly copy/commit raw databases, credentials or cloud task XML.
- **B1/B2 consistency tests:** use PR52/53 rather than rewriting backup. Finish real implementation native Windows synthetic tests and governed chain verification. Any actual SQLite online-copy read of live VPS data requires separate owner approval, a bounded single-source scope, no writer change and local private scratch.
- **B3 one-artifact offsite encrypted trial:** Only if owner approves provider, account/region, spend/key custody and offsite rights. PR54 proposes an initial one already-verified S02 copy to encrypted/versioned primary AWS S3 with verified readback, independent decrypt and SQLite+ledger-chain restore. Suggested $5/month cap and 7-day pilot were PROPOSALS, not approved/priced. Do not create/purchase/credentialize provider or transfer any bytes now.
- **B4 secondary independent domain:** Only after S3 one-artifact restore passes, replicate verified encrypted artifact to separate Backblaze B2 identity, readback and restore independently. Expand to all rights-admitted active plus retained failed/superseded ledgers and required accepted publication artifacts and Git history, with versioning, retention and capacity.
- **B5 production rehearsal and monitoring:** Restore onto an isolated host, compare source hashes/anchors/record chains, test corruption, lost VPS, missing accepted receipts and hosted rollback. Verify actual RPO/RTO in practice; current 3-hour/4-hour numbers in design are **not proven SLAs**. Hosted exact stored-byte digest remains unverified until independent provider readback.

**Do not:** deploy backup worker, modify Task Scheduler, create API keys, set up AWS/B2, inspect actual private SQLite, run a restore, or copy public snapshot/crypto seal to GitHub during this preparation. No full offsite backup exists solely because one local file and SHA hashes exist.

### D. Short, owner-independent execution queue

| Priority | What we can do now | Acceptance or permission |
|---|---|---|
| P0 | Keep EXP-031 DONE; natural publisher and three scanners unchanged | Already owner-confirmed; no re-deployment needed |
| P1 | New synthetic quality auditor and tests on an isolated branch; confirm exact frozen schema/cost/gates | Pure development; cannot claim test PASS without actual execution |
| P2 | One owner-approved read-only K5 private quality observation, then sanitized reporting without raw upload | Separate real-source VPS permission |
| P3 | Continue existing PR52–54 synthetic backup/encryption controls; do not duplicate implementations | Offsite provider/rights and real copy remain distinct approvals |
| P4 | Prospective complete-cycle consistency design for *current aggregate only* crypto status | Do not touch frozen K5 or public API until separate reviewed source approval |
| P5 | C1 → C2 → C3 and later independent product/execution safety review | Gates alone never allow real trading |

**Branch boundaries:** All files here are additive. Production main, all existing draft PRs including #48-#55, live tasks/scanners, broker execution, source ledgers, protected .env and cloud publisher remain untouched. These deliverables are evidence/engineering only, NOT results from current real K5 ledgers or completed recovery.
