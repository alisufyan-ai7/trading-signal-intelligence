# EXP049 — P7 prospective no-overwrite encrypted receipt escrow and cold recovery seam

2026-10-23 | Issue #67 | **DRAFT OFFLINE DEVELOPMENT — NOT NATIVE WINDOWS VERIFIED, NOT A REAL OFF-HOST BACKUP**

## Immutable parent and why P7 exists

Parent: exact P6/PR #82 `9a92d59d18138b0a37d1100281fa942ce98afa9d`, native Windows synthetic gate **95 passed in 39.16s** with pinned SDK, trusted frozen dependency change impact **113 protected paths PASS**, clean live production. Full owner output classified and recorded in Issue #67 and PR #82, without overwriting earlier HOLD attempts. All P1–P6 PRs remain draft/unmerged. No P6 source or frozen runtime file is changed by P7.

The P6 `OfflinePrivateReceiptSink` has an injected `commit_and_readback(encrypted_bytes,sha256,run_id)` seam, but its test callback is memory-only; the exact AWS and B2 `VersionId` values are lost if the Windows VPS fails unless the *encrypted* manifest, immutable locator, and separate manifest key survive independently. A callback returning the same bytes is **not proof of an off-host vault**.

## New interface and safety boundaries

New module `offline_immutable_receipt_escrow_v0_1.py` provides:

1. `OfflineImmutableReceiptEscrow`: owner-injected **distinct exclusive-create writer** and **read-only identity** callbacks. The caller must attest independent scoped writer, reader and recovery-custody identities as three syntactically distinct reference SHA-256 values. These digests are NOT independent IAM evidence.
2. Content-addressed, deterministic private receipt object identity `vowsig/private-recovery-receipts/v1/<run_id>/<encrypted_manifest_sha256>.aesgcm`. Neither actual AWS/B2 version ID nor data object key is in that locator. This still requires owner retention of `run_id`, hash, vault endpoint/configuration and AES manifest key **outside the Windows VPS**. NEVER publish actual private object URLs, credentials or plaintext manifests.
3. Byte-limited, AES-manifest-magic and digest preflight **before** callback usage; one **exclusive create** attempt; strict exact acknowledgement schema; independently injected exact readback and byte-for-byte content proof. Any ambiguity, duplicate object, wrong digest or read failure produces a fixed redacted HOLD, with **NO retry, overwrite, delete or fallback**. P6 itself independently opens AES-GCM and validates raw AWS/B2 versions before its synthetic safe result.
4. `open_from_independent_escrow`: read-only cold-restart function with just the escrow reader, stored `run_id` + manifest SHA-256 and a separately supplied 32-byte manifest key. Authenticates and opens the P5 private encrypted AWS/B2 exact-VersionId manifest without the original P6 sink, source database, original uploader or writer credentials. Does **NOT** yet fetch or decrypt backup database ciphertext from either provider.
5. No `boto3` / `botocore` / `socket` / cloud-client factory / CLI / environment credentials / scheduler / local file storage or import-time activity. Test-only callbacks use a fake in-memory vault deliberately **not durable** and synthetic S02 + fake signed transport. No real external API (even HEAD).

**Explicit limitation:** these are **contracts and offline failure-mode tests**, not a guarantee that a future provider enforces exclusive create, independent reader identity, retention, rights, key custody, persistent storage or free usage. In production a backend must establish hard atomic no-overwrite, retention/version immutability and verified independently durable storage. B2's HEAD-before-PUT is NOT an atomic exclusive-create guarantee; it cannot be substituted into this contract without independent controls. Never describe a fake vault or a callback acknowledgement as offhost-persistence proof. P6 public outcome remains `LOCAL_RECEIPT_ONLY`, `offhost_persistence_verified=False`, `real_provider_operation_authorized=False`.

## Prospective acceptance and subsequent integration

- P7 HEAD requires one SHA-pinned Windows VPS disposable review checkout from P6 parent; source-blobs/scope/ancestry proof; combined P1–P7 synthetic tests including existing pinned actual boto3/botocore over in-memory HTTP; exact trusted frozen dependency checker; clean live checkout before/after. No package download/install, source SQLite read, cloud API, credentials, production checkout sync/task change, merge or scheduled upload.
- Test new P6 callback integration; verified AES receipt readback; simulated *new read-only recovery process* without old writer/source/P6 object; wrong key/digest; forged write acknowledgements; missing/corrupt cold reads; redaction; one-shot no-duplicate; no network-capable imports.
- Follow P7 with an **OFF-by-default manual operator and independently reviewed real receipt escrow backend** only after selected off-host storage service, source rights and $0 guarantees are proven, plus exact provider-account evidence, independent owner key escrow, real external cold disaster restore, partial-provider response procedure and alerts. Offline interface syntax must not authorize network execution.
- Owner permits continued GitHub/offline engineering. No real provider requests or real S02 source capture/storage rights, provider credential injection, production task modification, merge or upload are currently authorized.

**Do not merge this P7 draft or any P1–P6 parent until exact owner-approved merge scope is supplied; native Windows gate not yet executed.**
