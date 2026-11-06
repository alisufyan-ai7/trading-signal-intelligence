# VowSig — owner-reported 12-ledger consistent frozen-copy capture (2026-11-06)

**Evidence level:** `PRIVATE_FROZEN_COPIES_CAPTURED_AUDIT_PENDING`; owner-executed read-only SQLite online-backup capture of the twelve known original-source paths. **No independent reviewer attestation, complete history, rights approval, crypto K5 or after-cost net-R proof is implied.** The reported SQLite files stay PRIVATE on the same VPS. No database bytes, source payloads, authentication material or full Windows username paths are in GitHub.

## Owner capture receipt

- Private LocalAppData directory basename: `freeze-20261106T073629Z-468dff8f` under `VowSig/SourceReleaseAudit`. This is a reference for the next local audit, not an authorization to publish or delete the files.
- Manifest's `captured_utc`: `2026-11-06T07:36:31.045697+00:00`; each file reports a capture within the immediately preceding ~1.6 seconds. Twelve files are individually transaction-consistent via SQLite's **online backup API**, not an atomic multi-database snapshot.
- Owner stdout reports `FROZEN_SOURCE_CAPTURE=PASS`, `observed_sources=12`, `total_event_rows=11103`, `independent_history_verified=false`, `crypto_k5_verified=false`, `after_cost_performance_verified=false`.
- **Manifest SHA256 (Windows file bytes):** `51e315b291eb98fdd70f512c3c2e06fa302bd1215e0f353ad9e0541385673f99`. This was independently **recomputed from the supplied JSON contents serialized with Python's `json.dumps(indent=2,sort_keys=True)` and Windows CRLF translation**; the hash matches the pasted reported manifest SHA. Re-serializing as LF-only would produce a different digest. This checks *internal transcript serialization integrity*; it does not independently access or hash the private file on the VPS.

## Reported frozen-file SHA256 pins and cross-check

The source count, maximum sequence and terminal record head from each frozen copy **exactly match** the owner's earlier same-day `OBSERVED_UNFROZEN` 12-source inventory (see `docs/vowsig-vps-12-ledger-preliminary-source-inventory-2026-11-06.md`). In each copy, reported `max_sequence=records`, `other_event_type_rows=0`, and sum of listed event categories equals rows. The captured command also ran SQLite `PRAGMA quick_check` successfully on each private copy.

| Lineage | Symbol | Frozen rows | Reported private frozen file SHA256 |
|---|---|---:|---|
| AI-v1.1 | XAUUSD | 1381 | `65556d5e530638d2905963c906a5aede12f59545516fbc968bbc4f2f1e8bc598` |
| AI-v1.1 | USTEC | 1388 | `a5f43b4c4057179f3cda2072e051e42189b57abc50df434a60b91330d68bd4d9` |
| AI-v1.1 | US30 | 1383 | `ed623033899c8f3481cdf41baa8a51899906d5d763231c0a497347024cd4ad75` |
| AI-v1.2.1 | EURUSD | 1150 | `230eb0dc67fd7e897d28a1450d6be95816ad774be1986d20026b30b545db0d8d` |
| AI-v1.2.1 | XAGUSD | 1109 | `930ec29c16e989db295cd4949dab2d226f6e58c0945b8e3a491c517fe6658f1b` |
| AI-v1.2.1 | USOIL | 1110 | `ec75b35a3b8d6d3991f58d328fa0433d67ce8789a30e8d80099962fee48b960e` |
| AI-v1.3 | BTCUSDT | 1148 | `93305d529d68867f60f1f3079ab4fc2c79f90595030c1906fb0b791c4dce4382` |
| AI-v1.3 | ETHUSDT | 1158 | `1536a6461a1fae00d8f235f6d964f879682a2e19cd8b246a9c6955f417ee3f90` |
| AI-v1.3 | SOLUSDT | 1152 | `1a347fe688a204e586df9973862bcdae315b294899e87cd6e9b3bb70fae532d6` |
| S02-v0.1 | XAUUSD | 35 | `07b55cd6b18594775e970d9951ca132ca0dea8cc0b89fb1c384ed6aaa81c53f5` |
| S02-v0.1 | USTEC | 48 | `c1a94eac77186b9e073cfc8f329515f437417a7dd95a2365c5b4570f44f9deba` |
| S02-v0.1 | US30 | 41 | `f962b971f20fe939f856db0df672be87851a2c65b223d7ac7c366607329ffde8` |

**Total:** AI-v1.1 **4152**; AI-v1.2.1 **3369**; AI-v1.3 crypto **3458**; separate S02 **124**; across twelve files **11103 event rows**. These counts are neither verified wins nor completed trade counts. Crypto carries **512 ERROR events**, which require cause classification but do not alone prove an incident or loss.

## Next bounded source-integrity gate — no scope expansion

1. Run one read-only hash-chain audit **against only these 12 frozen copies**, not active `data/` sources. Validate each file's SHA256 **before and after**, canonical payload, record identity, uninterrupted `sequence`, `previous_hash` and `record_hash` using the code contracts in `src/trading_signal_intelligence/product/accounts/source_ledger_audit.py`, `src/trading_signal_intelligence/ai_v1/ledger.py` and `src/trading_signal_intelligence/forward/ledger.py`. Emit safe aggregate PASS/HOLD receipts only.
2. Separate *crypto K5/epoch/activation* provenance from generic hash-chain validation. Do not label a crypto source complete merely because hashes match.
3. Audit full signal/exit/partial-exit/NO_TRADE/error lifecycle and versioned broker-neutral after-cost combined net R; independently review source rights and expected market/lineage/window coverage. No unverified metrics, no rollout of private source records or fake signals.
4. Apply the existing signed cohort and complete nine-market platform-universe gate only after separate independent reviewer approval, with private signing keys **outside Railway and GitHub**.

**Release governance:** the app staging remains on the most recently approved exact-SHA code `52dadc0c9749e5488528c0bb5076fba8340fd21e` (previous exact-HEAD CI green). This documentation-only update does not authorize PR #93 merge, production deployment, modifications to active VPS runtime, keys, source ledgers, provider settings or offsite backups. Owner MFA ceremony and rollback remain separate gates. The approved Railway PostgreSQL offsite recovery exception remains **immediately postlaunch**.
