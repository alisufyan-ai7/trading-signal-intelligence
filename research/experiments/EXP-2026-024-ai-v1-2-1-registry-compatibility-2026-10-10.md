# EXP-2026-024 — AI-v1.2.1 Instrument Registry Compatibility for Derived Publication

**Status: PROSPECTIVE / OFFLINE TESTS PENDING / DRAFT / NOT DEPLOYED.**

**Owner authority:** `APPROVE AI-V1.2.1 INSTRUMENT REGISTRY COMPATIBILITY CORRECTION PREPARATION ONLY`.
Limited to a new GitHub review branch, prospective compatibility attestation, additive/non-frozen exporter corrections, and offline tests. No permission for merging, production Git checkout, VPS Task Scheduler, scans, broker execution, provider calls, website publication, or changing existing historical artifacts.

## Branch and frozen scope

Stacked branch `research/ai-v1-2-1-instrument-registry-compat-20261010` was created exactly from PR #48 HEAD `3cc0384ee21e66ce0e93bcc4d6a6e855ec21d34d`. PR #48 is itself stacked on PR #46 correction #9 HEAD `13f10339df1410bbbe075371b52b34901ebd121b`. Production main was `47687d8d0e21523e417899a71dddc886ecf25d73`.

**DO NOT MODIFY:** frozen AI-v1.2.1 activation anchor, historical `artifact_hashes`, any 34 historical registered files, `src/trading_signal_intelligence/ai_v1/observability_v1_2_1.py`, K3/K4, correction #9, scheduled tasks, or old `scripts/run_product_publish_task.cmd`.

## Immutable observed incident

On 2026-10-10 native Windows VPS read-only observation:
- Core AI-v1.1 fully healthy. All core and expansion market-ledger/activation matches valid; expansion scheduler healthy, broker disabled, public expansion signal exposure disabled, upstream anchor valid.
- AI-v1.2.1 `health.healthy=False` solely because `expansion_artifacts_valid=False`; 34 artifacts, exactly one mismatch (`instrument_registry`).
- Frozen activation registry expected Windows CRLF SHA-256: `b92b80d18f422ba012b991ca8ba5a538f9212ee2823813d29754f24a804491ca`.
- Current Windows CRLF SHA-256: `f2f3d993fdd171ac43edd5234e18cfbea3eb7cf8da5dc2e6e6d4529613cd1681`.
- Git's LF SHA-256 for current main: `18116bd612a1648371e272d610273958a088a94207c62299e308da42a5e52c74`. Clean worktree with CRLF formatting explains difference from LF. It does NOT explain the actual 14-line content addition relative to frozen activation.

GitHub-verified history:
- historical registry `6155e3599ef907f9e29b6d52dcac045dff3837bc`, LF hash `ff237a840c19b6f3a009a253e122940b6be0091d7f67220a25be4d73175ca40e`, CRLF hash `b92b80d1...` as above;
- new registry commit `561fcff64b96ca6eb03ef76d70db7f02f92a9625`, 2026-10-08 10:39:09 UTC, "Add Binance ETHUSDT and SOLUSDT canonical mappings", exactly +14 lines to `config/instruments.json`;
- all pre-existing registry entries unchanged and two added exact blocks: `ETH/USDT` primary `ETHUSDT`, `SOL/USDT` primary `SOLUSDT`; both `binance_spot`, crypto.
- historical AI-v1.2.1 verifier must continue to report `artifacts_valid=False`. It must NEVER be represented as a historically healthy 34-artifact activation.

## Prospective corrected product decision

**Separate qualification, not rewrite of activation outcome.**

The additive `src/trading_signal_intelligence/product/expansion_registry_compat_v0_1.py` operates solely on an original, unmodified `build_report_v1_2_1` report with historical `health.healthy=False`. It accepts ONLY:

1. `report.runtime_version=AI-v1.2.1`, genuine existing 3-market `EURUSD/XAGUSD/USOIL` ledgers valid and activation anchored.
2. All health invariants except historical artifact match: upstream valid, scheduler healthy, ledger chains valid, public expansion signals disabled, broker disabled. No softening of any other health status.
3. Original artifact verifier specifically `valid=False`, `checked=34`, mismatches **exactly** `instrument_registry` with frozen expected/current CRLF hashes above (implying 33 other artifact hashes match).
4. `git show <historic commit>:config/instruments.json`, `git show <addition commit>:...`, and `git show HEAD:...` contain exactly pinned LF SHA-256 values and approve only current new registry. Raw live checkout registry must equal the known exact approved current LF or CRLF byte representation (no dirty/content drift). Historical and new registry JSON differ by **exactly the two specified additions**, with all previous instrument objects and all non-instrument fields unchanged.
5. Unknown new symbols, source drift, missing historical Git object, nonadditive edits, unsupported end-of-line encodings, any other frozen-artifact mismatch or future registry update all REJECT.
6. On success, **only an in-memory copy of the current product report** gains `health.healthy=True` for *prospective derived-product operational readiness*, accompanied by the exact user-visible title `Expansion Shadow Validation — operational compatibility (historical registry mismatch preserved)`. The original private report `health.healthy=False`, original `expansion_artifacts_valid=False`, frozen anchor and all 34 original artifact checks are **unchanged**.
7. The existing public validation program schema has `additionalProperties=false` both at top level and under `health`. Therefore, **no new public-program JSON fields are introduced**. All original historic SHA-256/commit/33-of-34 proof fields remain internal in the verifier, in this separately registered attestation design and associated GitHub audit evidence; do not present the public health flag as an original historical activation PASS.
8. The dormant guarded publisher reads and re-proves the *original* activation-era unhealthy report on the VPS immediately before any future HTTP push when the exceptional title is present. An out-of-date, unapproved or altered registry, absent pinned Git object, changed other frozen artifact, or newly failed scheduler/ledger/broker/upstream safety check causes publication to be HELD. This is distinct from the future proof that the live publisher cannot race the K5 writer after its last check.
The existing gated core/expansion exporter `scripts/export_guarded_core_expansion_v0_2.py` now uses this attestation only if the expansion report is historically unhealthy; normal verified healthy reports follow the original existing program builder. The new `scripts/export_guarded_full_v0_1.py` first builds that attested core/expansion snapshot, then verifies the original pinned crypto adapter source and full crypto report to produce a 3-program aggregate snapshot if crypto is current. The guarded publisher substitutes this new full exporter, enforces the existing strict public schema, and **independently re-verifies the internal exact registry attestation when the exceptional title is present** before any future push. On failed or Running K5, the independent 2-program path still works, with only accepted historic crypto aggregates allowed as visibly DELAYED.

## Test plan / acceptance gates

- Static self-review and offline mock/fixture tests in `tests/test_expansion_registry_compat_v0_1.py` and `tests/test_expansion_registry_public_integration_v0_1.py`: positive exact delta/CRLF proof, preserved false original report, unknown symbol, modified old entries, future registry, missing Git object, altered expected or current hash, extra artifact mismatches, failed nonregistry health flags, bad scheduler/public/broker flags, frozen public JSON schema with no added keys, independent preupload proof recheck, 2- and 3-program independence, crypto unsafe/missing.
- Re-run all guarded publisher original tests and four existing AI-v1.3 public integration regressions at the new exact HEAD on **isolated Windows checkout**; prior PR #48 result **84 PASS** applies only to `3cc0384...`, NOT automatically this successor.
- Read-only live VPS reconciliation against the same exact SHA, with original 34-artifact false and new product-only compatibility attestation pass; no exporter CLI or cloud POST. Confirm Git history exists on native VPS.
- Separately review source hash governance for all new additive files, production publisher overlap and recovery, archive retention quotas/checksums, cloud durability, K5 between-check race. No old task cutover or merge before explicit later owner authorization.

**STRICT NO-GO:** frozen source/anchor rewrite, broadened artifact whitelist, use new product health as frozen activation PASS, auto-scans, backfills, public actionable crypto signals, broker trading, cloud upload, production source sync/Task Scheduler modifications or merging either draft PR.
