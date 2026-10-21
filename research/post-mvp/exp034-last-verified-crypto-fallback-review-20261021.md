# EXP-034 — last-known verified crypto DELAYED fallback (prospective review)

**Date:** 2026-10-21. **Status:** DRAFT / GitHub-only preparation. No approval to merge, deploy, edit tasks, manually run K5, publish HTTP, expose crypto trading signals or execute trades. Sole context: this chat and private repository alisufyan-ai7/trading-signal-intelligence.

## Immutable incident evidence

- Prior natural CURRENT crypto publication successes on Oct 13 remain PASS.
- Oct 21 owner screenshot showed the original October 11 DELAYED historical card (114 valid inferences, 1 completed shadow trade).
- Owner's Oct 21 read-only VPS evidence: four scheduled tasks Ready/exit 0; K5 last natural run 10:04:04 UTC, publisher 10:05:05 UTC; hosted snapshot generated 10:05:52 UTC and fresh overall, but crypto was DELAYED. Public guarded publisher log showed CRYPTO_CURRENT_AGGREGATE=HELD, alert exit 0, guarded publish exit 0.
- The locally accepted, SHA-256 and receipt-verified previous CURRENT public archive generated 2026-10-21T09:05:54.106602+00:00 preserved **802 valid inferences and 13 completed shadow trades**. The newer DELAYED public archive had 114/1. This proves historical accepted PUBLIC evidence survived; it does not prove the private K5 ledger state at 10:05.
- GitHub Issue #57 preserves actual evidence and failure history. Do not erase failed runs or make new guesses about the specific failed K5 source predicate.

## Narrow correction

The existing guarded publisher already reads, SHA/receipt-verifies and validates previously accepted PUBLIC-only CURRENT archives for count nonregression. But with the immutable writer interlock FALSE it does not use that proof as the display fallback after a crypto-only source HOLD, instead showing the original pinned October 11 seal.

The proposed publisher change (1) under existing process-local CURRENT opt-in, tries the newest accepted CURRENT public aggregate on a crypto HOLD; (2) attaches it only as DELAYED with the actual original archive timestamp and unhealthy current/scheduler flags, no actionable details; (3) if accepted archive provenance is corrupt or absent, uses original pinned historical Oct 11 as a last-resort DELAYED fallback; (4) otherwise publishes healthy fresh core+expansion without crypto. It never falsely upgrades historical evidence to CURRENT. Opt-in OFF must not read cached crypto or K5. Historical immutable seal, tasks, C1/C2/C3, frozen K5 source, broker-disabled and crypto-public-signal-OFF invariants remain unchanged.

**Sanitized failure observability:** current crypto HOLD emits only a fixed category among SOURCE_CAPTURE, EPOCH_VALIDATION, PUBLIC_PROGRAM, ACCEPTED_HISTORY, NON_REGRESSION, PUBLIC_PRIVACY; never source exceptions, paths, private rows, model payloads, credentials or hashes. Accepted-history rejection emits a fixed HELD marker; successful delayed selection labels VERIFIED_ACCEPTED_CURRENT versus PINNED_ORIGINAL_SEAL. Fixed stages narrow the investigation but do **not** identify exact private K5 failure causes.

**Deployment coupling:** source modification changes the publisher Git blob SHA. The dormant tracked EXP034 ProgramData-compatible launcher pin is changed in this PR as well. The installed production ProgramData runner still pins the old approved publisher SHA. NEVER fast-forward the production source by itself, as a source-only update causes an expected fail-closed mismatch and interrupts hourly publishing. A future approved cutover must coordinate exact source and SAME installed launcher under backup/quiet window, preserving existing four task XMLs and rollback packages. This GitHub-only PR grants no such authority.

## Tests and reviewer gates

New synthetic-only offline tests exercise: last accepted CURRENT even when a newer accepted DELAYED archive exists, original count/provenance and unhealthy delayed flags, one guarded mock push, corrupt receipt refusal with pinned seal fallback, opt-in OFF, bounded HOLD categories that never print private exception text, and non-regression classification. Existing guarded publisher/crypto source tests must also remain green.

**Not yet claimed as passed:** native Windows test execution for the new exact SHA, PowerShell AST parse, full existing regression suite, trusted manual frozen-dependency impact assessment, deployed runtime preflight or hosted rollout.

Review in a disposable short-path native Windows checkout of the exact PR SHA. Suggested synthetic command (run only after exact source reconciliation, not in the VPS live tree):

    .\.venv\Scripts\python.exe -B -m pytest -q tests/test_guarded_crypto_delayed_fallback_v0_1.py tests/test_guarded_crypto_current_aggregate_v0_1.py tests/test_guarded_product_publish_v0_1.py tests/test_crypto_completed_epoch_v0_1.py tests/test_crypto_epoch_bridge_v0_1.py tests/test_crypto_epoch_source_v0_1.py

Also execute the original trusted frozen-dependency checker and remaining seven-module publisher tests under owner-reviewed procedure. Do not use ad hoc frozen checks. All tests synthetic-only: no private ledgers, network POST, providers, broker or task mutations.

Separate explicit owner decisions required, in order: final native test and manual dependency review; merge exact PR HEAD; coordinated quiet-window VPS source-plus-installed-runner cutover; natural publisher observation and GET-only public semantic readback. On uncertainty, stop and preserve old environment and evidence. A rollback, if ever required, needs an independently approved exact-state review.
