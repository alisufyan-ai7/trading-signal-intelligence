# EXP-2026-030 — First off-VPS S02 pilot: provider, rights and key-custody readiness

**Status: GitHub-only recommendation; pilot NOT APPROVED FOR EXECUTION.** 2026-10-11.
Continuation of the next milestone after EXP-029. This record deliberately uses only the private repo and owner-supplied evidence in the current project chat. No third-party price/terms lookups or connected provider/account inspections have been performed. **No account provisioning, credentials, cloud uploads, new VPS SQLite reads, encryption runs, deletes or merges.**

## Practical decision

**Recommended first pilot:** Take the **existing successfully recovered S02 backup**, and only after content/rights clearance and explicit owner approval, store one **client-side authenticated-encrypted immutable version** in an **independent private AWS S3 account/bucket**. Perform provider readback and a local isolated authenticated decrypt/reopen integrity and 17-record S02 chain proof. Then add the independently credentialed **Backblaze B2** copy as a *separate later milestone*, not as a prerequisite to testing the first remote failure domain.

Why: First establish **off-VPS protection** for one tiny, already verified artifact without touching the production database. Do not turn the first experiment into a 22-file, two-provider, scheduler, trading or deployment cutover.

The two existing same-VPS TEMP copies (backup and recovered copy) are **not** offsite backups and must not be automatically cleaned or renamed. Current total verified off-VPS copies: **zero**.

### Frozen artifact and correct boundaries

| Item | Exact existing evidence |
| --- | --- |
| Initial VPS copy | One frozen S02 `data/forward.sqlite` online backup, private TEMP `trial-b710c731` |
| Independent local recovery | One distinct private TEMP copy in `vowsig-b1b2-recovery-30c5f3fc`, verified on 2026-10-11 |
| Size / records | 53,248 bytes; 17 records |
| Plaintext SHA-256 | `1e3a07d7f9b8729b96aee9534a1295e876c06dceca496eb3880b61e5872e502c` |
| Original logical manifest SHA-256 | `b19d64c626dd40abe1009eb084012d5aab08d506e35c0cadc18d79c2b4423cf1` |
| Verifier frozen revision | draft PR #53 HEAD `2da5ea34d5277776757de9cc3cbffeb5c1f43a4d`, source Git blob `7b66e01ed7db012f0e0689c53ce398a4f0cfdf86` |
| Origin production code revision | `47687d8d0e21523e417899a71dddc886ecf25d73` |
| Remote protection | **NOT STARTED**: no external object or credential evidence |
| Source rights / privacy | **HOLD for external transmission until scoped review** |

Do not send even an encrypted copy without the appropriate source-owner terms, privacy and region review. Do not assume the ledger contains no raw quote/feature samples simply because its class is S02.

## Owner decision register (recommendations, not silent approvals)

| Decision | Proposed minimal choice | Evidence/state needed before action |
| --- | --- | --- |
| Primary provider | AWS S3, owner-controlled private backup account **separate from production credentials** | Owner confirms an account exists or explicitly authorizes creation; no linked account was inspected |
| First pilot region | One in-region AWS S3 bucket, **region TBD by owner after data-rights/jurisdiction review** | Owner selects exact region; no guessed or auto-created region |
| Secondary provider | Backblaze B2 in separate account/credential domain, *later* | No B2 provisioning/transfer in first pilot |
| Budget ceiling | **Proposed USD $5/month maximum incremental pilot spend** (not a price quote and not approved) | Owner approves cap; verify real service request, retention, API, egress and encryption charges separately before purchasing |
| First encrypted object | One verified **53,248-byte S02** SQLite payload only | Source file currently available locally, digest matches; exact object/manifest contents and rights cleared |
| Confidentiality | Client-side **AES-256-GCM** via maintained, audited library; random per-object nonce; authenticated metadata; server-side encryption too | Crypto library/runtime support, verified envelope format and key recovery independently tested on **mock data**; do not invent ad-hoc AES or share key over Git/chat |
| Encryption/recovery key | Owner-controlled recovery key material preserved **off VPS and off the cloud object-account security boundary** | MFA protected, recoverability proven via offline mock; routine VPS uploader cannot destroy/rotate sole decryption key |
| Object immutability | Private bucket, Block Public Access, versioning; configured Object Lock with a **proposed pilot retention of 7 days** | Owner confirms policy/mode and charges; do not enable indefinite or irreversible policy by default; write identity cannot delete/overwrite protected history |
| Network data rights | HOLD until scoped evidence confirms this S02 record population may be stored encrypted by the chosen external processor/region | Owner's Exness separate commercial **derived-signal** permission does *not*, by itself, establish these backup-transfer rights. Binance commercial conditions remain under review. Actual S02 record payload/source mix has not been inspected for this decision |
| Archive continuity | Preserve local originals and include immutable SHA/object-version/time/region and encryption algorithm ID in a **sanitized** digest-only manifest | No secrets, private rows, sensitive broker metadata, presigned URLs or raw manifest uploaded to GitHub |
| Rollout size | **ONE** remote object first, no schedules/other databases | New owner authorization once readiness is satisfied |

The proposed $5 cap and 7-day lock are design defaults offered for owner acceptance, not live-verified AWS/B2 pricing or a request to charge a card.

### Rights review: minimal concrete evidence to resolve

1. **S02 content class:** the repository's `src/trading_signal_intelligence/forward/ledger.py` has an append-only table `forward_records` with `payload_json`; row payloads have not been opened in this milestone. Before approving remote transfer, determine—under **separate narrowly authorized local inspection** or an independent owner attestation—whether the copied file contains raw Exness quotes/bars, raw Binance market data, customer identifiers, tokens or contractual confidential fields; redact/scope or keep HOLD accordingly. Do not upload or paste private rows here.
2. **Exness permission scope:** existing `docs/legal-data-rights.md` records owner confirmation (Sep 21) of commercial **derived-signal** rights, not blanket raw redistribution or third-party processor/backups. Owner/legal review should confirm encryption-at-rest on third-party provider, processing/storage jurisdiction, retention and deletion and provider subcontractor role.
3. **Binance/other sources:** repo currently treats Binance public API as technically usable for R&D; paid commercial terms and storage/cache/external backup still pending. If any raw/derived Binance-sourced features reside in an S02 record, ensure applicable restrictions are resolved for that record class, not just for `research.sqlite`.
4. **`data/research.sqlite`:** code-intended historical candle store, B0 size 198,176,768 bytes, source mix/rights actually unverified. **Preserve locally; outside pilot and external-transfer HOLD.** The remaining 20 governed ledgers also remain unapproved for new backups/remote transfer.

**Rights gate output must be explicit**: `S02_RIGHT_TO_STORE_ENCRYPTED_OFF_VPS=YES` with evidence location, applicable provider/region and conditions; otherwise `HOLD`. A repository README, API technical access or derived-signal permission alone is insufficient to assert YES.

### Minimal one-object pilot protocol (FUTURE; do not execute)

- Prerequisites: explicit owner approval for named AWS account/bucket/region and cap, rights gate YES, independent key recovery, secure identity with no delete/retention-bypass, tested offline encryption envelope; no active source writes necessary because **only the preserved copy** is used.
- Read the frozen **existing local copy** only; reject size/SHA drift and unknown paths; do not connect to live `data/forward.sqlite`, `research.sqlite` or create new SQLite online copy.
- Locally package client-side authenticated-encrypted payload; record SHA-256 of ciphertext, encryption-envelope schema/version, **nonsecret** key identifier and exact metadata required for restore. Do not print plaintext, key, secret tags or user/provider tokens.
- Upload **one uniquely named, non-overwriting** private encrypted object. Confirm write response, expected identity and server-assigned immutable version and active retention. Fail closed on unknown state or key/ACL/rights error.
- Provider **readback** of the same version into an isolated local recovery scratch. Match ciphertext SHA and AEAD authentication; decrypt using separately controlled key, verify original plaintext SHA exactly, reopen SQLite read-only, check integrity and all 17 S02 hashes/records/ledger head with frozen verifier; preserve all failed attempts as failed.
- Record owner-safe evidence: provider account nickname (non-identifying), region, object ID (sanitized), unique version reference if non-sensitive, UTC, ciphertext and plaintext SHA, verified chain/count and explicit NO-RESTORE/NO-SCHEDULE; no raw DB/manifest in Git.
- Only after success revisit the **second independent provider** and eventual all-governed-ledger coverage. No auto cleanup of temporary evidence.

## Go/no-go checklist

| Gate | Current state |
| --- | --- |
| Native-Windows synthetic S02 copy and verifier | PASS on PR #53 SHA |
| Real single local S02 consistent copy | PASS, owner observed |
| Independent local S02 copy/reopen | PASS, owner observed |
| Complete 22-candidate local B0 metadata | PASS as observed **under `data/` only**, not whole-VPS exhaustive |
| Named owner AWS account + bucket + region | **UNDECIDED / NO PROVIDER ACTION** |
| Owner-approved incremental cost ceiling | **UNDECIDED; $5 proposed only** |
| S02 payload sensitivity and offsite license/processor permission | **HOLD** |
| Encryption envelope and key custody tested offline | **NOT BUILT / NOT TESTED** |
| Configured immutable encrypted vault and least-privilege writer | **NOT IMPLEMENTED** |
| Provider post-upload byte-for-byte readback | **NOT TESTED** |
| Offsite isolated decrypted SQLite 17-record restore | **NOT TESTED** |
| Independent Backblaze B2 copy | **NOT IMPLEMENTED** |
| Other 20 governed ledgers / `research.sqlite` | **NO CURRENT BACKUP PROOF / RIGHTS HOLDS** |
| Full disaster recovery / RPO / RTO / public publishing | **NO-GO** |

## One owner decision that unblocks the next engineering-only step

**Recommended:** authorize **OFFLINE ENCRYPTION ENVELOPE PREPARATION ONLY** on synthetic fixtures in a new draft branch, with no real SQLite files and no provider connections. Separately tell us your desired AWS region and whether you already control a private AWS account, and confirm/modify the $5/month pilot cap. Those selections authorize **neither** provisioning nor a billable upload. A **later separate approval**, conditioned on the legal/source-data rights gate, will be required for a single encrypted real artifact transfer and remote readback.

**No provider/cloud access has been used and no costs incurred in this review.** Keep production and prior draft branches unchanged. No merges, active backup schedulers, trading or crypto publication.
