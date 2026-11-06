# VowSig — owner-executed preliminary live original-ledger inventory (2026-11-06)

**Evidence status: PRELIMINARY_LIVE_SOURCE_INVENTORY_UNVERIFIED. NOT a signed source release, frozen file/hash receipt, source-rights approval, historical performance verification, crypto K5 certification, owner MFA pass or launch authorization.**

Owner supplied a PowerShell stdout transcript of a single read-only Python standard-library query executed inside the existing Windows VPS working directory named `trading-signal-intelligence`. The command opened only the 12 fixed repository-defined SQLite filenames under `data/` with `mode=ro` and `PRAGMA query_only=ON`, obtained table row counts, max sequence, terminal `record_hash` and record-type GROUP BY counts. It did not use the draft PR #93 CLI on the production VPS. No broker, scheduler, publisher, trading, cloud or backup mutation was part of that command.

**Receipt custody:** a ChatGPT conversation upload held the PowerShell transcript; do not commit the original terminal transcript or any private account/credential material. SHA256 of the pretty-printed JSON response block **after stripping surrounding whitespace**: `6462eb059b7c6b06788518ebf71c8f5272ade7040901e6ffbf464061098d4834`. This is a content fingerprint for reconciling the *reported output*, NOT a SHA256 of any SQLite file and NOT an independently pinned immutable source.

## Observed live values — counts and terminal record hashes

| Lineage | Symbol | Event rows | SIGNAL | EXIT | ERROR | MISSED | NO_TRADE | Observed live last record hash |
|---|---|---:|---:|---:|---:|---:|---:|---|
| AI-v1.1 | XAUUSD | 1381 | 33 | 33 | 110 | 269 | 308 | `aa2a215d1d6bf2941747b3bbe81e60c05b557be0b79d83ccc5c477033a806137` |
| AI-v1.1 | USTEC | 1388 | 35 | 34 | 110 | 269 | 315 | `e6a7be190d861d92495d796118066583743f59b53c8af9e2a74d044023b8ecad` |
| AI-v1.1 | US30 | 1383 | 31 | 31 | 110 | 269 | 323 | `a035328b3382f2b8487bf830830b19b7679c045737db8e7950aed9cbc0c70967` |
| AI-v1.2.1 | EURUSD | 1150 | 30 | 29 | 120 | 206 | 255 | `04a5897238e53bcceaa3d25ce84ea102c46a3deb1ec6089347563a124bcb0ca7` |
| AI-v1.2.1 | XAGUSD | 1109 | 30 | 29 | 112 | 223 | 244 | `b79c6e1ec6b28b257d536d7c4867c775050ab721c9b21975ee3ff76e5313ac77` |
| AI-v1.2.1 | USOIL | 1110 | 32 | 32 | 111 | 219 | 220 | `058341236a959e0d56825e45ae6d7ecf88d8d91c7f0ccf62c40163d07fefca8f` |
| AI-v1.3 | BTCUSDT | 1148 | 2 | 1 | 170 | 4 | 313 | `6203a42a722c4a0ad6ac282dbc1232434bda614501bdc17fd44b2164e7d90999` |
| AI-v1.3 | ETHUSDT | 1158 | 8 | 7 | 171 | 4 | 323 | `39f8e20ab0167d66ad6f8a4490ef02dc1565f3b86718281aecd73fb568374a63` |
| AI-v1.3 | SOLUSDT | 1152 | 11 | 10 | 171 | 12 | 302 | `8cbc85bb4d9a3ce4bf242787c230d792a4b6f176324a265ed2b6a89e64b6f9e5` |
| S02-v0.1 | XAUUSD | 35 | 14 | 13 | 0 | 4 | 0 | `178f0ca8b3cb674600e997c161e297a3dd4e90262583529eb58e6deaf94ab1a2` |
| S02-v0.1 | USTEC | 48 | 15 | 15 | 0 | 1 | 0 | `7d9cbe6882f6c6151769d2f1002eb9f6811ebd134bc4440c6638275ca5730af0` |
| S02-v0.1 | US30 | 41 | 13 | 13 | 0 | 1 | 0 | `6aa1e944a8be627148b0f23ebc3e1f57ef9b54d66cb488b1c91576e785dc6aca` |

For **all 12** entries: `status=OBSERVED_UNFROZEN`, `max_sequence=record_count`, and sum of the returned allowlisted record-type counts equals the reported record count. The last fact means this particular filtered output omitted no counted types, but does **not** prove immutable cryptographic chain continuity, event order correctness or complete opportunity coverage.

| Program | AI/S02 event rows | Signal events | Exit events | Error events | Notes |
|---|---:|---:|---:|---:|---|
| AI-v1.1, three core | 4152 | 99 | 98 | 330 | 46 separate PARTIAL_EXIT events; 807 MISSED_INFERENCE |
| AI-v1.2.1, three expansion | 3369 | 92 | 90 | 343 | 37 PARTIAL_EXIT; 648 MISSED_INFERENCE |
| AI-v1.3, three crypto | 3458 | 21 | 18 | 512 | 9 PARTIAL_EXIT; 20 MISSED_INFERENCE; **K5 unverified** |
| S02 separate support | 124 | 42 | 41 | 0 | 6 MISSED_SIGNAL and 32 SKIPPED_SIGNAL, separate protocol |
| **TOTAL** | **11103** | **254** | **247** | **1185** | These are event counts, NOT independent trades, winning trades, net-R or verified historical outcomes |

Signal/exit differences must NOT be treated as proof of exact open positions, nor ERROR as a diagnosed causal problem. Crypto's 512 reported ERROR rows deserve source-aware classification in the owner reliability UI, without asserting why they occurred. No trade profitability or win rate should be computed from these counts.

## Gate decisions and shortest next action

**CLOSED / no reason to repeat:** the 12-name existence inventory is complete in this live observation. Do not ask the owner to rerun the same block or merge code merely to rerun it.

**Still HOLD:** live heads may change each scheduler cycle and are NOT frozen-file hashes. The repository's read-only source-to-projection verifier requires frozen consistent copies, independently pinned SHA256/row count/terminal record hash, strict source chain and projections, and versioned after-cost lifecycle/rights review. The crypto AI-v1.3 population additionally requires its independently verified K5/epoch causal protocol. Full nine-market signed-universe history remains unsigned; unavailable Performance Lab metrics remain explicitly N/A.

**Next owner action, only after authorized:** prepare a **single coherent controlled frozen-copy operation** for the known 12 files using SQLite's online backup API to an isolated private staging/audit directory on the *same VPS*, without altering `data/` source paths, live collection schedules or production publisher. Report per-copy exact file SHA256, count/head and event-type aggregates; keep SQLite copies private and do not upload data or files to GitHub. Independently pin those frozen results and run the existing offline read-only chain/reconciliation/K5/cost review against the copies, not the evolving live files. Check adequate local disk space; avoid secrets and raw payloads in public output. Do not substitute a `Copy-Item` of live SQLite files for a consistent SQLite online backup. Do not use the unapproved collection as a production data release.

Other release gates remain: actual signed owner MFA/bootstrap with two people, real nine-market original-source rights and cost certification, genuine publication continuity, short staging rollback rehearsal, final owner exact-SHA merge/deploy approval. The approved Railway PostgreSQL offsite encrypted cold restore remains the **first immediate postlaunch operation** and not a renewed prelaunch blocker.

## Source of truth

- `docs/vowsig-private-original-source-inventory-and-vps-handoff-2026-11-04.md` — prescribed 12 paths, read-only boundary and frozen source requirement.
- `docs/vowsig-owner-ops-model-market-source-reconciliation-2026-11-04.md` — source authority and exact link verifier.
- `docs/vowsig-p2-owner-attested-history-review-2026-11-04.md` — signed cohort/full-universe requirements.
- `docs/vowsig-launch-first-release-freeze-and-postlaunch-backlog-2026-11-06.md` — no scope expansion; owner previously required a single fully enabled launch.
- The working directory/private source files and independent audit keys are **not present in GitHub**. This document must not claim that they have been reviewed.
