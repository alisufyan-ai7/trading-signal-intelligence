# P2 owner Performance Lab: independently signed, complete-cohort historical metrics (2026-11-04)

## Owner decision and scope

Complete all VowSig features before full, enabled production launch. Do not stage a feature-disabled production launch. **Railway PostgreSQL recurring S3/Backblaze backup is deferred until immediately AFTER the launch by explicit owner risk acceptance**; see \`docs/vowsig-one-release-backup-last-feature-first-2026-11-04.md\`. No actual launch has been approved for an exact SHA yet. Auth0 Free $0 only, no broker execution or billing. One public release must include free customer accounts, full functional owner/admin dashboard, and independently source-verified historical analytics.

## Implementation increment (PR #93, review only)

- \`verified_history.py\` is a pure read-only verification gate with **Ed25519** detached independent-auditor signature over deterministic canonical JSON. It rejects unsigned data, duplicate JSON keys, unknown fields, missing rights/source-review proof, invalid reviewer/UTC dates, record/count/hash mismatches, missing after-cost net R, mixed cohorts, nonfinite numbers and incomplete projection flags. A separately audited *original* immutable source ledger must underlie the signed manifest. Test signatures are made with ephemeral test-only keys; no real private signing key, performance record or source access is committed.
- \`outcome_population_sha256\` recomputes a canonical SHA256 of the **entire projected source cohort** (source entity ID, source record hash, lifecycle, cost version, after-cost combined R, close time and cohort), not the bounded public snapshot. It sorts IDs deterministically, requires a unique population and caps at 250k results. Any deleted/extra/changed trade invalidates signed completeness.
- \`PostgresAccountStore.admin_verified_performance\` uses the pinned reviewer public key and a signed attestation, reads the projected facts under a read-only database transaction, and only returns one **verified complete cohort** if the signed source manifest matches a PostgreSQL projection with \`ingest_status=verified\` AND \`completeness_verified=true\`. No app writes, promotion, signature issuance, or broker execution. If any verification fails, the API returns \`performance=null\` with a closed status. With no configured proof, nothing is published.
- \`GET /api/v2/admin/performance\` continues to require fresh owner MFA. When an attested cohort exists it can return normalized after-cost win rate / expectancy / drawdown, proper closed denominator and adverse outcome counts. It explicitly marks \`verified_full_cohort_history=true\` but **\`verified_full_history=false\`** and \`platform_history_population_reconciled=false\` until every required market, lineage, model version and time window has an independently reconciled audit. No global profitability claim may be made from one cohort.
- Owner Performance Lab browser now conditionally renders those verified cohort metrics; otherwise it displays the prior explicit \`Source-reconciled performance unavailable\` message. UI always labels research-only R, never real-money account profit, and does not display expansion per-signal details.

## Private production verifier config (not currently set)

All three must be supplied together in the eventual approved release environment:

- \`VOWSIG_HISTORY_SIGNED_ATTESTATION_PATH\`: trusted read-only local file with the signed \`{attestation,signature_ed25519_b64u}\` envelope. This is NOT generated from GitHub's bounded public snapshot.
- \`VOWSIG_HISTORY_REVIEWER_PUBLIC_KEY_PATH\`: trusted **PUBLIC** Ed25519 reviewer key PEM (no private key on Railway).
- \`VOWSIG_HISTORY_REVIEWER_PUBLIC_KEY_SHA256\`: hex SHA256 of exact trusted reviewer public PEM bytes, fixed from an independent owner-approved audit, checked before loading attestation.

No keys or attestations are configured by this PR. A compromised signing key or an auditor who did not examine the original immutable ledgers would invalidate the meaning of "independent"; an Ed25519 signature only authenticates a declared reviewer, not underlying data truth by itself. The owner must review a source-ledger audit with immutable hashes, source rights, expected population, adverse statuses, gross-to-net cost calculation, bounded UTC windows and completeness receipts. The audit reviewer holds the private signing key outside the website runtime. The migration/release pipeline may only promote quarantined datasets following explicit authorized audit, never because the app receives a signed file alone.

## Still necessary to satisfy the owner's entire release

1. Independently obtain and reconcile the authoritative original ledgers and versioned cost rules, for every required lineage/cohort/market/time range; sign multiple audit manifests with explicit cross-cohort coverage and an independently approved universe manifest. Current one-file per-cohort path is an implementation increment, **not complete multi-cohort production coverage**.
2. Implement a guarded, auditable offline promotion path for only independently accepted projections, alongside full event completeness and regression checks. Only the migrator/ingester identity can update read model statuses; runtime role cannot write outcomes.
3. Complete functional owner Command Center, AI model/market reliability screens, signal explorer, growth/security/audit, true free MFA enrollment and owner bootstrap/recovery, and the customer verified-history navigation.
4. Real Auth0/Resend registration and login, least-privileged authenticated Railway DB integration, full privacy/permission/CSRF checks and exact-SHA staging/rollback acceptance.
5. One fully enabled production launch on separately approved exact SHA, carrying documented temporary DB-recovery risk. **Immediately after launch** implement encrypted scheduled PostgreSQL backup to existing S3/B2 where scoped credentials permit and PROVE a separate restore.

**Current truth:** No production source-ledger evidence is available from this chat and repository, thus no historical performance data has been certified by this work. Existing synthetic CI fixtures are never user-facing claims.
