# P2 private original-ledger audit: read-only, externally pinned v0.1 — 2026-11-04

## Purpose and scope

In parallel with free Auth0-independent owner MFA and admin growth analytics, advance **independently verified historical analytics** using the actual source-ledger algorithms already present in this repository. The original source files are on the Windows trading/research host and are **not** present in the GitHub review branch. This milestone creates a read-only verifier and synthetic tests; it does **not** claim any real source history has passed independent audit.

The repository's native sources expose two hash-chained SQLite record formats:

- `src/trading_signal_intelligence/ai_v1/ledger.py`: `ai_records`, append-only triggers, canonical JSON, record ID/entity ID/type/UTC timestamps, `previous_hash` and `record_hash`.
- `src/trading_signal_intelligence/forward/ledger.py`: `forward_records`, the same exact hash material/canonicalization with its own append-only triggers. S02 forward records must not be retroactively counted as live signals before activation.
- AI-v1.3 crypto uses its own three-ledger source verifier and K5 provenance bridge. This v0.1 utility **does not** pretend to cover crypto; the established crypto verifier/epoch capture must be audited separately.

## Implementation

`src/trading_signal_intelligence/product/accounts/source_ledger_audit.py::audit_pinned_source` opens an **existing, nonsymlink local SQLite file with `mode=ro`**, sets `PRAGMA query_only`, begins a read transaction, and validates:

1. An independently supplied 64-hex terminal record hash and exact positive record count, neither borrowed from the same file at the time of verification.
2. The full row sequence from 1 with no missing, extra or reordered entries.
3. Canonical JSON payload, unique JSON object keys, exact chained `previous_hash`, and every record's computed SHA256 using the repository's real ledger code.
4. Exact external head/count at the end. Returns only per-record-type counts, terminal head hash, sequence+hash population digest and explicit `complete_historical_performance_verified=false`, `source_costs_verified=false` and `source_rights_verified=false`. **No raw source row, customer/broker data, trading strategy payload or filesystem path is included in the result.**

All runtime operations are read-only; the utility does not invoke ledger constructors because those initialize schemas. A frozen, authorized read-only snapshot of a running ledger should be used if appends may occur while scanning. Never interrupt running scheduled tasks, create a new ledger, reset history or alter hash-chain head to obtain a PASS.

Synthetic tests in `tests/test_vowsig_source_ledger_audit_p2.py` cover both actual repo ledger algorithms, wrong external pins, tampered payload, removed sequence, symlink and nonexistent-file refusal, and equality of source-file byte SHA256 before/after audit.

## Next real-world evidence, not provided yet

- The owner/authorized independent reviewer must provide a frozen read-only source-file inventory and **separately trusted** durable terminal hash/count for each original AI, S02 and crypto lineage, market and version. Do not paste raw ledger contents or provider credentials to chat/GitHub.
- Exact lifecycle coverage must include NO_TRADE, errors, rejected, skipped/missed, partial exits, closed outcomes, open positions and history time windows; source rights and model/cost versions require separate approval.
- A valid chain pin is not itself independently reviewed after-cost R, a source audit sign-off, or proof of full universe coverage. The existing signed complete-cohort manifest, read-model projection checks, and independently signed full-universe coverage remain mandatory for public historical performance claims.
- This verifier is an isolated engineering tool, not scheduled on the VPS, not installed in production, and not able to access the original files from this chat.

## One coordinated release and risk

Complete customer identity, owner/admin, independent full-history evidence, actual OIDC/DB security and rollback before one **fully enabled** go-live. Owner expressly deferred **new Railway PostgreSQL S3/B2 backup implementation** to immediately after go-live and accepted temporary data-loss exposure; never describe the new database as recovery-protected without a proven restore. Auth0 remains Free $0, broker execution and paid subscriptions remain off.

No merge or production mutation is authorized by this audit tool.
