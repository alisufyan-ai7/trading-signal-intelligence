# Changelog

## 2026-10-26 — GitHub pull request history preservation and queue cleanup

- Reduced **18 originally open PRs to 2**: [PR #87](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/87) (39-file, exact-source S02 encrypted dual-cloud/GFS draft) and [PR #50](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/50) (independent draft frozen-dependency CI guard). No implementation merge or production VPS deploy.
- Merged historic product two-document PR #58; preserved 26 Oct24 VowSig operational/GFS documents plus 11 byte-identical historical AWS/SDK files via PR #86; preserved all EXP043–050 preparatory backup notes via PR #88.
- Closed already-main PRs #48/#49/#51/#55, archived historical PRs #68/#75/#76, and superseded stages #77–#85 without deleting branches; original 131-commit stage/integration sequence retained at SHA `0c16270e4fca9f1f0124acf776ee4d2a0604de83` under `archive/pr85-original-stacked-backup-history-20261024`.
- Candidate #87's full **39 files** (5 operator scripts, 16 recovery modules, 18 tests) Git-tree-verified byte-identical with original PR85; focused Windows regression and security review remain mandatory. No S3/B2 deletion or new backup run was performed by this cleanup. See [full PR audit](docs/pr-queue-review-2026-10-24.md).

## 2026-10-24 — VowSig backup, recovery, scheduler and GFS durability

- **REAL PASS:** encrypted one-shot S02 `data/forward.sqlite` backup (30 records) to AWS S3 and Backblaze B2 with exact-version cold restoration from both providers; backup ID `backup-8bce80179c524ace8f4a52cb702b3716` (EXP053).
- **REAL PASS:** first daily Interactive Windows Task Scheduler 04:15 VPS-local run of isolated ProgramData encrypted AWS/B2 backup, independently verified recovery; backup ID `backup-83688210120f48fa8dd62491720df132` (EXP054–055). Natural next-day recurrence not yet observed; full Windows logoff prevents this Interactive job.
- **GFS:** 30 daily / 8 weekly / 12 monthly deterministic read-only retention preview, protected milestone pinning, least-privilege AWS reader `s3:ListBucketVersions` correction, two retained real cold restores PASS and paired four exact AWS + four exact B2 cloud data/receipt versions PASS (EXP056–059). **No deletions; cloud pruning is NOT enabled**; new code remains in open draft PR #85.
- Backups cover **one S02 SQLite only**, not all application/research/IP. Old failed experiments preserved; no merge or live trading. See [current operations](docs/vowsig-operational-status-2026-10-24.md), Issue #67.

## 2026-09-16

- Initialized project source of truth.
- Selected local MT5 + Python as the initial multi-asset R&D connector.
- Selected Binance direct public APIs as the primary crypto research connector.
- Marked Exness commercial production-data use as blocked pending written clarification.
- Added project architecture, research plan, data-rights notes and decision log.
- Added normalized market-data models, MT5/Binance adapters, probes and quality checks.
- Added initial S01 Trend Pullback hypothesis and strategy research discipline.
- Added first MT5 and Binance research experiment templates.
