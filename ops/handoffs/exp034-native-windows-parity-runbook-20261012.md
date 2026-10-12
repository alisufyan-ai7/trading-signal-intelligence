# EXP-034 — Receipt hardlink correction and native Windows synthetic parity handoff

**2026-10-12 status: PREPARED / NOT EXECUTED ON WINDOWS.**

Use ONLY this TradingTop Analysis conversation and the private GitHub repository `alisufyan-ai7/trading-signal-intelligence`. No production mutation is authorized by this branch.

## Exact ancestry and issue found during pre-run review

- Production `main` at preparation: `a4f00578c00c5e23eb4fae073cf2df18c78d9a0a`.
- PR #59 at `4fa1860e6df2684dc55de1f9723bdc07bde5d522`, PR #60 at `a4f58ea87a3ba1b011fda212d11714daa3d0c56b`, PR #62 at `f6c91993f2492dd43198fbe0796a46e904451e9d`. All DRAFT and UNMERGED.
- PR #61's native Windows short-path 142-test PASS applies **only to its exact predecessor scope**; EXP-034 has not been run natively.
- Identified actual bug in PR #62 receipt atomic-write prototype: after `os.link(temporary,target)`, the temporary source and published target both exist, so `st_nlink == 2`; calling strict `_read_once` before unlinking temporary rejects this valid transient state. A standalone file-system reproduction observed link count 2 before unlink and 1 after. No private K5 data involved.
- Correction is isolated on this successor branch **stacked on exact PR #62 HEAD**, leaving PR #62 untouched. It performs strict post-publication receipt readback **after the temporary hardlink has been removed**, and adds a focused regression asserting the transient link is gone. It does not reduce the strict single-link acceptance criterion.

## New code and exact verifier

- Modified only the new candidate source: `src/trading_signal_intelligence/product/crypto_epoch_receipt_store_v0_1.py`, Git blob `afc4feeaa7ba60a6cad66e7b0ec64bd131170cf7`.
- Modified only the new candidate synthetic tests: `tests/test_crypto_epoch_source_receipt_v0_1.py`, Git blob `a6673172c131770d9d2540cfd490ab382b93e5cf`.
- Added `ops/handoffs/exp034-native-windows-synthetic-parity-v0_1.ps1`, Git blob `72c822b017209863309466d3858d0263a217b6e5`.
- Runner reads 14 exact source/test/schema Git blob IDs; detached review checkout only; existing Windows Python 3.12 environment; AST parse; real repository strict crypto validator; no pip/network provider calls; exactly six test files including all five prior PR #61 modules plus EXP-034 new test module. It checks production repo HEAD/status before and after.
- Use a **new short NTFS** clone at `C:\VSG34\r<random>`, with test TEMP/basetemp nested minimally at `<review>\.t`; never use the overlong Windows TEMP path that led to EXP-033 attempt #1 FAIL.
- The owner should run the exact-SHA bootstrap supplied in this chat after checking GitHub refs. It must independently verify this review runner's exact commit SHA, Git blob, on-disk normalized Git blob and native PowerShell AST **before execution**.

## Interpretation / hard boundaries

**A successful six-module test run:** means synthetic/native Windows compatibility of this exact candidate and selected regression modules, **not** functioning live hourly crypto public updates, cryptographic source identity, production key management or concurrency-crash safety in genuine K5.

**A test FAIL:** preserve exact output and classify FAIL; do not silently modify frozen runtime, remove tests, run K5 scans or attempt live publication. The historical failed overlong EXP-033 test remains FAIL despite its later short-path PASS.

This candidate does NOT:
- modify `main`, the K5 scanner, publisher, scheduler, website or any frozen strategy;
- run the dormant producer against real BTC/ETH/SOL private SQLite;
- write receipts on the actual VPS production source, provision keys or update trusted high-water state;
- enable public crypto entry/stop/TP/alerts or broker/exchange execution;
- perform a cloud POST, any merge, installation or VPS source sync.

After a real native Windows PASS, the next owner-approved milestone is **separate** synthetic NTFS fault/concurrency/ACL tests plus design of independently trusted monotonic receipt state and key custody. A bounded real K5 private read requires new explicit permission. Final hourly public crypto aggregate publisher integration requires separate review, manual exact-SHA dependency check, merge, synchronization, and publication authorization.

**Current status until the owner returns output: EXP034_CORRECTED_CANDIDATE_PREPARED / WINDOWS_PARITY_PENDING.**
