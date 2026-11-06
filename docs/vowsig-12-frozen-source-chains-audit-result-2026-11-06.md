# VowSig — frozen 12-source hash-chain audit result (2026-11-06)

**Result: REPORTED TECHNICAL CHAIN PASS, ALL 12 SOURCES.** The owner provided the full PowerShell output of a one-time, **read-only local audit** of the prior privately captured twelve SQLite copies; a separate review parsed and reconciled the output. This document does **not** say the audit was performed from GitHub or that original SQLite file bytes were supplied to the reviewer. It does not constitute external legal/data rights, H1/H4 crypto K5 opportunity completeness, certified after-cost net R or a complete signed historical universe.

**Pinned private frozen dataset:** `freeze-20261106T073629Z-468dff8f` (private under VPS user's LocalAppData / VowSig / SourceReleaseAudit). Manifest SHA-256 `51e315b291eb98fdd70f512c3c2e06fa302bd1215e0f353ad9e0541385673f99`, originally pinned along with the 12 private frozen file SHA256 values and their terminal records in `docs/vowsig-vps-12-ledger-frozen-copy-manifest-2026-11-06.md`.

Owner CLI returned `status=FROZEN_12_SOURCE_CHAINS_PASS`, `source_files_verified=12`, `event_rows_verified=11103`, `manifest_sha256_verified=true`, `frozen_file_sha256_verified=true`, `source_chains_verified=true`; `crypto_k5_verified=false`, `source_rights_verified=false`, `after_cost_history_verified=false`, `full_platform_history_verified=false`. All 12 per-file statuses were `chain=PASS` and program/model/symbol/count pairs exactly match the preceding frozen manifest. The script recomputed canonical JSON and SHA-256 for each row, validated the previous-hash and sequence chain and terminal head, verified file digest before/after, and checked record-category totals. It did not print raw ledger rows, feature snapshots, trade prices, account identifiers or secrets.

| Program | Market | Checked rows | Sequence-chain SHA256 reported |
|---|---|---:|---|
| AI-v1.1 | XAUUSD | 1381 | `73e30c2beda4f59f76f595fa9728066ba76c21aaec9698e328e862ac8f9c3581` |
| AI-v1.1 | USTEC | 1388 | `f72a8cf64b9992e2b81729aed2e087ab5f05f06928bc19e7b3685d0516cbb9fe` |
| AI-v1.1 | US30 | 1383 | `699c4104f95e226b98f1d8efb34f68ad20aa96d83c49bc098038009b7bad56bd` |
| AI-v1.2.1 | EURUSD | 1150 | `07420fc29c833bf7c7a7239727b8aa7db531810a0612bfa692af5c8d3d44a099` |
| AI-v1.2.1 | XAGUSD | 1109 | `93b73d46bc785549ef3dc421a9bce8d045a63fa4dcae1eeb0021fbc34c9eac87` |
| AI-v1.2.1 | USOIL | 1110 | `ac8e2ffd447bc64c1dfb902016f2774b786fc911f2c1874b18232f033ac81fa2` |
| AI-v1.3 | BTCUSDT | 1148 | `cafd116ceee74af7e74c43d9eec191d965103a1f81c9f81c3da7021bffebf509` |
| AI-v1.3 | ETHUSDT | 1158 | `524e682fbd17907d025c45c8a4685049e6377333f4ef743dbc2b282f92641008` |
| AI-v1.3 | SOLUSDT | 1152 | `b633946eb3821fcd75eb061f266df05dbe5b3da65d5ac154273a9992a9ddd9b2` |
| S02-v0.1 | XAUUSD | 35 | `aede7dc4c9d6b128eed0ddad50a401f756b6c80bb2bfaa97a2fbe2145b7d31b1` |
| S02-v0.1 | USTEC | 48 | `35a4d9914b230f62e8c32b24b2590b2980101b7a31815a9f5321041380c1a49a` |
| S02-v0.1 | US30 | 41 | `981fd862f43a853c3f297692b234353fb2c34386d21028a71d048bcc3cc7d52f` |

**Operational decision:** DO NOT repeat live source inventory, frozen copy capture or the twelve-file chain audit absent concrete tampering/provenance incident. Reuse these pinned snapshots and receipts for one bounded remaining technical lifecycle/recorded-cost and crypto activation sanity review. K5 H1/H4 opportunity proof, source rights and independent performance attestation require external evidence/human reviewers; neither a successful script nor a healthy public publication snapshot substitutes for them.

**Public VowSig distinction:** A read-only anonymous check of `https://vowsig.com/api/health` on Nov 6 returned `launch_mode=research_beta`, `launch_ready=true`, `snapshot_pending=false`, `ready_collector_count=3`, `snapshot_generated_at_utc=2026-11-06T07:05:43.936727+00:00`. The existing vowsig.com beta uses a bounded public snapshot, not the full nine-market private Performance Lab. Current hosted `/api/v2/public/markets` and `/api/v2/public/history-summary` returned 404. Reuse proven existing production publisher; do NOT infer the new authenticated PR #93 full production release has shipped.

**Release safety:** no PR merge, production deployment, live collector restart, broker call or source changes authorized; existing postlaunch PostgreSQL cold recovery exception preserved.
