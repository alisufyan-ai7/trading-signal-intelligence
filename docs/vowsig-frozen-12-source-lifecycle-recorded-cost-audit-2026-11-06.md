# VowSig — consolidated frozen-ledger lifecycle and recorded-cost audit

**Audit evidence date:** 2026-11-06. **State: FROZEN_LIFECYCLE_AND_RECORDED_COST_ARITHMETIC_PASS (owner-executed VPS output, independently reconciled from the shared sanitized transcript).** This is an evidence record, **not** an independently signed full-platform Performance Lab certificate, owner MFA evidence, crypto K5 opportunity proof, source-rights decision, external broker-cost policy acceptance or production release authorization.

## Frozen source identity and controlled execution

The owner executed a single consolidated Python/PowerShell audit **read-only against the existing private frozen copies**, not live source databases. The private source root is the existing LocalAppData/VowSig/SourceReleaseAudit folder containing the private basename `freeze-20261106T073629Z-468dff8f`. Its externally recorded manifest SHA256 is `51e315b291eb98fdd70f512c3c2e06fa302bd1215e0f353ad9e0541385673f99`.

Previous complete owner-provided evidence:
- `docs/vowsig-vps-12-ledger-preliminary-source-inventory-2026-11-06.md` — 12 original observed sources and row-count/head pins.
- `docs/vowsig-vps-12-ledger-frozen-copy-manifest-2026-11-06.md` — twelve SQLite online-backup copies, distinct SHA256 pins, row counts and heads.
- `docs/vowsig-12-frozen-source-chains-audit-result-2026-11-06.md` — **all 12/12 canonical hash chains PASS** and all 11,103 record hashes/sequence continuity verified.

The latest script checked manifest digest and each frozen database's file hash before/after reading; nine AI ledgers' SIGNAL→INFERENCE hash anchor and sequence; SIGNAL/PARTIAL_EXIT/EXIT uniqueness, chronology and referenced signal hashes; gross contribution, recorded cost contribution, net contribution and total combined signal net-R using the recorded source-side cost figures; each exited signal's total position fraction; and the three crypto ACTIVATION payload's `AI-v1.3` version and public-exposure/broker-execution `False` flags. For all twelve files it checked per-ledger signal and exit relationships and counted open signals. S02 is **lifecycle-only**, not cost arithmetic; no independent market-data or broker-cost verification occurred.

**Explicit stdout status:** `FROZEN_LIFECYCLE_AND_RECORDED_COST_ARITHMETIC_PASS`; `source_files_checked=12`; `event_rows_checked=11103`; `recorded_exit_partial_cost_legs_checked=298`; `signal_count=254`; `exit_count=247`; `open_signal_entities=7`; `crypto_activation_exposure_boundary_checked=true`; `raw_source_payloads_exported=false`.

### Per-lineage and market counts reconciled to the owner's actual terminal output

| Program | Market | Rows | SIGNAL | EXIT | PARTIAL_EXIT | Unclosed SIGNAL | ERROR | AI cost legs checked |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| AI-v1.1 | XAUUSD | 1381 | 33 | 33 | 12 | 0 | 110 | 45 |
| AI-v1.1 | USTEC | 1388 | 35 | 34 | 18 | 1 | 110 | 52 |
| AI-v1.1 | US30 | 1383 | 31 | 31 | 16 | 0 | 110 | 47 |
| AI-v1.2.1 | EURUSD | 1150 | 30 | 29 | 10 | 1 | 120 | 39 |
| AI-v1.2.1 | XAGUSD | 1109 | 30 | 29 | 12 | 1 | 112 | 41 |
| AI-v1.2.1 | USOIL | 1110 | 32 | 32 | 15 | 0 | 111 | 47 |
| AI-v1.3 | BTCUSDT | 1148 | 2 | 1 | 0 | 1 | 170 | 1 |
| AI-v1.3 | ETHUSDT | 1158 | 8 | 7 | 5 | 1 | 171 | 12 |
| AI-v1.3 | SOLUSDT | 1152 | 11 | 10 | 4 | 1 | 171 | 14 |
| S02-v0.1 | XAUUSD | 35 | 14 | 13 | 0 | 1 | 0 | 0 |
| S02-v0.1 | USTEC | 48 | 15 | 15 | 0 | 0 | 0 | 0 |
| S02-v0.1 | US30 | 41 | 13 | 13 | 0 | 0 | 0 | 0 |
| **Total** | | **11103** | **254** | **247** | **92** | **7** | **1185** | **298** |

AI-only: 212 SIGNAL, 206 EXIT, 92 PARTIAL_EXIT, **6 unclosed**; all 298 checked AI contribution legs = 206 EXIT + 92 PARTIAL_EXIT. S02 separate: 42 SIGNAL, 41 EXIT, one unclosed; S02 cost legs tested = 0. Crypto 512 ERROR records remain unexplained operational categories, not proof of 512 losing trades or individual incidents.

### Evidence boundary — nothing is silently elevated

- **PASS, technical frozen audit as executed and reported:** consistent snapshot identification, twelve-source hash chains, lifecycle and recorded source-side net-R arithmetic, crypto activation false exposure flags.
- **NOT verified by this audit:** market-data or price/research opportunity completeness; natural crypto H1/H4 K5 coverage and causal upstream epoch; *external* spread/fee/slippage/cost methodology; rights to use or publish each original dataset; independent human auditor custody, signed per-cohort projection completeness and signed entire nine-market universe; actual owner MFA and PostgreSQL access; real hosted authenticated Performance Lab populated metrics.
- Technical cost formulas being self-consistent does **not** establish broker-cost assumptions were appropriate. Seven unclosed source SIGNAL entities are source-event status at capture, not seven current live trade recommendations or real brokerage positions.
- The source records and original scripts were not downloaded from the VPS for a second full audit; this report is a **reconciled owner terminal receipt**. Raw payloads, positions, confidential source values and SQLite files have **not** been committed.

## Freeze and fastest release path

**No more general-purpose VPS inventory, freeze, hash-chain or lifecycle scripts.** Reuse all three receipts unless an actual contradiction is identified. The owner specifically requested one (at most two) further VPS scripts and has completed the single consolidated script.

Remaining authorization/non-VPS work shall be combined where feasible:
1. Complete actual **two-person offline owner identity/MFA** protocol in `docs/vowsig-owner-bootstrap-recovery-signed-operator-2026-11-04.md` with approved independent reviewer and separate operator, then one real owner session and restricted SQL/Performance Lab acceptance. Never handle passwords/factors/private keys in a chat or GitHub.
2. Reuse existing repository crypto K5 evidence and complete independent rights/cost methodology/source-window/whole-cohort review with actual external human attestations. Do not mislabel synthetic CI, current public beta health or the above source output as complete source certification.
3. Reuse the working public beta publisher; verify genuine eligible snapshot integration for the new authenticated release without creating another duplicate publisher solely for staging aesthetics. Keep unapproved historical metrics unavailable.
4. Exact-candidate regression/small mobile smoke, reversible rollback exercise, final distinct reviewer-signed gate bundle and explicit owner exact-SHA merge/deploy approval. No automatic production action.

PR #93 stays DRAFT/UNMERGED pending this evidence. Existing approved exception: Railway PostgreSQL encrypted offsite backup/cold restore **first immediate postlaunch task**, not an added prelaunch blocker.
