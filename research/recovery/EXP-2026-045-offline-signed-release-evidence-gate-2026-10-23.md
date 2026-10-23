# EXP045 — P3 offline signed evidence and release gate (2026-10-23)

_Status: new prospective independent governance layer, **NO LIVE AUTHORITY**, no credentials, source DB access, AWS/B2 calls, scheduler or deployment._

This draft depends on EXP044 PR #78 and EXP043 PR #77. Exact P1/P2 Windows fixture+trusted frozen checkpoint is **CLOSED PASS** for P1 `9b6dca8a22ba9fa39d74ae9472398a23a7af5259` and P2 `b077732a96fd11cbfb9f2bbdb911afb1cded9237`: 18 tests PASS, 113 protected paths unchanged, production unchanged. This new P3 code has NOT been tested on native Windows.

## Critical release-safety distinction

A text document containing 64 hexadecimal digits, even one with an authentic digital signature, **does not independently prove** that the user's cloud bill cannot increase, that storage rights exist, that AWS/B2 bucket Object Lock and versioning are configured, or that a source belongs to the approved class. Earlier P2 `ReleaseAuthorization` only compares hashes and caller-supplied principals; it must NOT be treated as sufficient live-release authority.

This P3 module provides a cryptographically signed **offline review record** and unconditionally refuses live provider requests. The verifier checks Ed25519 authenticity against a trusted public-key fingerprint pinned independently of the document, complete exact-field JSON schema, exact allowed repository/S02 path, both providers/buckets/endpoints/regions, a single 5-signed-request/16MiB envelope limit, valid 7-day UTC review window, exact candidate/source Git revisions, and required evidence fingerprints. It rejects inline credential fields, source expansion, wrong regions, bad signatures, bad pins, expired or not-yet-issued reviews. All tests use disposable synthetic Ed25519 keys generated locally during each test; **these have NO approval authority outside tests**.

It deliberately always returns `OFFLINE_SIGNED_EVIDENCE_ONLY_EXTERNAL_HOLDS` with `live_provider_requests_authorized=False`. No data collector, credential discovery, cloud SDK client construction, API, CLI or task integration exists in P3.

## External work still required to release actual backups

The owner has provided general permission to engineer this system. Do not ask again for generalized development approval. Actual third-party transfer and unattended operation still require verified, grounded accounts/evidence:

1. **Source and processor rights:** Classify actual `data/forward.sqlite` record families using metadata-only inventory where possible. Identify original broker/market/provider provenance and applicability of terms to **encrypted storage** with AWS `us-east-1` and Backblaze B2 `us-east-005`. A derived-signals/publication permission does not automatically cover raw source or private third-party transfer. Never upload `research.sqlite` or other ledgers until separately scoped.
2. **Billing under hard $0:** AWS S3 and Backblaze B2 can charge for PUT/GET/storage/versioning/retention/egress and any extra provider operations; local five-request ceiling is not a provider account spending stop. Verify actual account plan, promos/credits, service eligibility, explicit quotas/caps, Object Lock/lifecycle effects, currency/billing and spending safeguards. **Zero dollars cannot be guaranteed by AWS budget alerts alone.** If indefinite two-provider durability cannot meet $0, leave real upload OFF. Owner may explicitly revise budget in a separate decision, but no automatic budget inference.
3. **Cloud identity:** Four separate, individually scoped writer and reader identities, MFA/off-VPS owner administration, allowlist only exact vault keys and private version operations, permission boundaries and emergency revocation. Existing owner preference keeps real cloud secrets OFF VPS: secure unattended execution will require a separately approved external uploader/short-lived delegation system, not embedding secrets in Windows Scheduled Task, scripts, environment or GitHub.
4. **Encryption key custody:** Independent off-VPS key escrow and offline recovery drill; lost symmetric key irreversibly prevents decrypt even if both cloud objects survive. Source VPS and both provider accounts may simultaneously be unavailable in a disaster.
5. **Vault and restore:** Proof of private bucket region, versioning, retention/Object Lock legal holds, B2 404-before-PUT behavior (B2 atomic no-overwrite not guaranteed), actual SDK signed wire/receipts and independent full-source recovery from both providers. The prior EXP042 fake SDK proof for synthetic B1–B6 is distinct from prospective real-data P2 SDK compatibility.
6. **Operator:** Isolated Windows service identity, ACL-encrypted plaintext scratch; file-handling/retention, alerts and partial failure recovery (AWS succeeds, B2 fails => **HOLD**), no ambiguity retries, S02-only schedule installation after explicit release decision, owner RPO/RTO objectives, code pinning, deployment rollback and S3/B2 account outage exercises.

## Approval gate and next operator action

- Execute exact-SHA local native Windows P3 test suite and the inherited P1/P2 18 synthetic tests in one disposable checkout; source/diff/commit pin first, trusted frozen checker and production integrity postflight. **Zero provider I/O**, no package install or real DB reads.
- Independent review and hardening of the provider SDK client factory, key-handling, Windows ACL, cost/rights attestation source validation, and staged offsite restore.
- Do not merge PR77/78/P3 automatically and never schedule or execute live external backup merely because signed offline evidence is present. Only a future separately governed release component may set an explicit live gate after independent account/billing/rights verification.

P3 is necessary infrastructure for production-grade security governance, **not** a statement that the system is already production-ready.
