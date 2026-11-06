# VowSig 12-source original-ledger inventory and owner VPS handoff (2026-11-04)

## Scope and status

This is a draft, read-only inventory candidate for **existing** Windows VPS ledger files. It does not create or modify source SQLite, touch the VPS scheduled tasks or broker, migrate production PostgreSQL, publish signals or export original payloads. The exact source files are not present in GitHub. All current tests use disposable synthetic SQLite.

**Preliminary live inventory is not independently pinned or frozen.** A ledger's count and last record hash as read at one moment are not proof that the copy is immutable or its entire chain valid. An authorized independent reviewer must freeze a source snapshot and approve external hashes/counts separately before the cross-check in `docs/vowsig-owner-ops-model-market-source-reconciliation-2026-11-04.md`.

## Source locations pinned to original repo runtime contracts

| Program | Model / protocol | Symbols | Original SQLite paths |
|---|---|---|---|
| core-ai-shadow | AI-v1.1 | XAUUSD / USTEC / US30 | data/ai_v1_1_xauusd.sqlite, data/ai_v1_1_ustec.sqlite, data/ai_v1_1_us30.sqlite |
| market-expansion-1 | AI-v1.2.1 | EURUSD / XAGUSD / USOIL | data/ai_v1_2_1_eurusd.sqlite, data/ai_v1_2_1_xagusd.sqlite, data/ai_v1_2_1_usoil.sqlite |
| crypto-expansion-1 | AI-v1.3 | BTCUSDT / ETHUSDT / SOLUSDT | data/ai_v1_3_btcusdt.sqlite, data/ai_v1_3_ethusdt.sqlite, data/ai_v1_3_solusdt.sqlite |
| s02-forward | S02-v0.1 | XAUUSD / USTEC / US30 | data/forward.sqlite, data/forward_ustec.sqlite, data/forward_us30.sqlite |

These paths are bound to the repository's `shadow_runtime_v1_1.py`, `shadow_runtime_v1_2_1.py`, `crypto_activation_v1_3.py` and `config/launch_universe.json` contracts and asserted in CI. The S02 line is separate supporting validation evidence, **not** an AI-v1.1+ trade population. All AI-v1.3 crypto source proof requires the distinct K5/epoch verifier in addition to hash-chain integrity.

## Verified code and expected results

New `source_inventory.py` contains only the twelve exact paths and read-only SQLite metadata queries through `mode=ro` and `PRAGMA query_only=ON`. It reports fixed source program/model/symbol, relative path, current row count, last sequence/hash, and a strict allowlist of event-type counts. It NEVER includes strategy payloads, order parameters, reasons, feature snapshots, broker credentials, user information, raw source rows, or arbitrary file directory listings. Missing, empty, unreadable, invalid heads or symlinks are distinct and never called PASS. No file is created by the scanner.

The CLI `scripts/vowsig_readonly_source_inventory.py` requires an exact repo root named `trading-signal-intelligence` and `--confirm READ_ONLY_NO_VPS_LEDGER_CHANGES`. It is **only in draft PR #93**, not installed on the currently deployed VPS: DO NOT switch the live Git branch, download/run the draft automatically, alter schedules or merge solely to obtain an inventory.

**Next owner-authorized read-only handoff** can instead use a single, independently reviewed PowerShell/Python standard-library block typed/pasted directly into the current production repository terminal; it must read only these twelve known paths and return sanitized counts/hash heads, not original payloads. No cloud, Git or SQL write operations are needed. Output should be treated as `PRELIMINARY_LIVE_SOURCE_INVENTORY_UNVERIFIED` until a frozen copy and external pins are approved.

## Remaining historical verification process

1. Collect a **read-only 12-source existence/row-count/head inventory** from the authorized Windows VPS; distinguish absent, empty, active and locked databases. Never mistake a live head for a frozen pin.
2. Independently freeze each source ledger **without stopping or modifying live schedulers** using an approved consistent SQLite snapshot mechanism, then calculate immutable file SHA256 and externally review/hash-pin original row counts/head; ensure chain continuity and anchor coverage via the new offline verifier.
3. Verify AI-v1.1, AI-v1.2.1 and crypto AI-v1.3 K5 epoch/source bridges separately, plus S02 validation provenance. Do not pool lineages or model versions.
4. Independently attest all market/cohort/time-window expected populations and complete errors, NO_TRADE, open, closed, rejection and partial exits. Validate versioned after-cost net R rather than using database flags as proof. Obtain source-rights approval and separately signed cohort/universe manifests.
5. Publish only facts satisfying all independent legal/provenance/math gates under a later explicit exact-SHA release approval. Full historical performance must remain unavailable until then.

The owner requires one full-feature enabled public launch; Railway PostgreSQL automated encrypted offsite recovery is intentionally the **first post-launch** implementation by owner approval and temporary accepted risk. That policy does not weaken source-history or admin MFA integrity. GitHub main, Railway and Windows VPS remain unchanged in this review.
