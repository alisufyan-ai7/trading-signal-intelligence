# EXP-033 native Windows Python 3.12 parity — owner-operated, SYNTHETIC ONLY

**Date:** 2026-10-12. **State:** PREPARED, NOT YET EXECUTED ON WINDOWS. **No native PASS is claimed.**

**Strict scope:** This conversation and private repository `alisufyan-ai7/trading-signal-intelligence` only. This handoff is a stacked sibling/successor review from [PR #60](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/60), which itself depends on [PR #59](https://github.com/alisufyan-ai7/trading-signal-intelligence/pull/59). No existing production source or branch is changed by this handoff. We do not merge, deploy, issue signals, read real K5 SQLite, invoke Binance/OpenAI, modify scheduled tasks or publish to vowsig.com.

## Fixed review identity (verify live refs again immediately before running)

- At preparation, production GitHub `main=a4f00578c00c5e23eb4fae073cf2df18c78d9a0a`.
- Parent PR #59 HEAD: `4fa1860e6df2684dc55de1f9723bdc07bde5d522`.
- Child PR #60 HEAD: `a4f58ea87a3ba1b011fda212d11714daa3d0c56b`.
- Windows synthetic runner branch: `ops/exp033-native-windows-synthetic-parity-20261012`. **The precise current runner HEAD and runner script Git blob must come from the PR's latest reviewed pinned comment/owner copy-paste; do not trust this paragraph as an exact final SHA.**
- Branch relative to PR #60 adds **only** this PowerShell runner and this runbook; no code/test modifications to the K5 bridge.
- Runner: `ops/handoffs/exp033-native-windows-synthetic-parity-20261012.ps1`; must verify its exact Git blob **and native PowerShell AST parse before execution**.

## Executable safety model

The owner runs an exact-SHA, fail-closed PowerShell **bootstrap** supplied alongside the reviewed PR. It:

1. Verifies the existing VPS production repository exists, reads only its origin URL, and checks the origin is the sole approved private GitHub repository (never logs the origin URL/credentials).
2. Uses `git ls-remote --heads` to reconcile remote `main`, PR #59 source, PR #60 source, and runner head against **literal expected SHA-1 values**. Any drift => STOP rather than arbitrarily pull or merge.
3. Clones **only the runner branch** into a brand-new random directory under Windows TEMP with shallow checkout, asserts exactly the pinned SHA, and detaches the review clone. The production Git worktree and .git files remain unchanged.
4. Checks the runner's committed blob and on-disk blob after Git normalization match the **independently pinned runner-script blob SHA**.
5. Native PowerShell `Parser.ParseFile` AST preflight: zero parse errors required **before script execution**.
6. Runs the reviewed checker as a new PowerShell process using the **existing** Windows VPS Python 3.12 `.venv` executable. It **never** creates a venv or calls pip.
7. Runner re-verifies 11 committed file blob SHAs against **on-disk checkout**, including PR #59/#60 source/tests, real immutable as-of strict validator, existing guarded publisher, schema, and pyproject. Requires crypto current-writer interlock `CRYPTO_WRITER_INTERLOCK_READY=False`.
8. Runner performs in-memory Python AST parse, ensures the **real** repo's as-of validator is imported, then executes exactly five test modules from the review clone with `PYTHONPATH=<review>/src`, `PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`, `-p no:cacheprovider` and a scratch TEMP directory under the disposable clone.
9. Runner checks production Git HEAD and tracked status before/after. It prints a final unique PASS marker only if *all* checks pass. Production Git may be at an older checkout commit; **a production pull is NOT required or permitted.**

## Five explicitly selected synthetic/contract test modules

- `tests/test_crypto_completed_epoch_v0_1.py` (new PR #59)
- `tests/test_crypto_epoch_bridge_v0_1.py` (new PR #60)
- `tests/test_crypto_asof_publication_v0_1.py` (existing pinned as-of historical seal)
- `tests/test_guarded_product_publish_v0_1.py` (existing guarded publisher; mocked network)
- `tests/test_crypto_public_validation_v0_1.py` (existing strict public aggregate contract)

The local isolated prior tests were 43/43 with **a test-only stand-in for the existing validator**. This Windows handoff explicitly removes that limitation by executing from a complete Git checkout and importing the real validator. **No Windows result is yet observed**. If a test fails, preserve its FAIL evidence; correct only with a new review/commit/explicit rerun — do not describe as PASS.

## Expected final output markers (not pre-certified)

`EXACT_11_SOURCE_AND_TEST_BLOBS=PASS`  
`FROZEN_CRYPTO_WRITER_INTERLOCK_DISABLED=TRUE`  
`NATIVE_WINDOWS_PYTHON=3.12.x`  
`EXACT_SOURCE_AST=PASS`  
`REAL_REPOSITORY_ALLOWLIST=PASS`  
`NATIVE_WINDOWS_SYNTHETIC_REGRESSIONS=PASS`  
`PRODUCTION_HEAD_AND_TRACKED_STATUS_UNCHANGED=TRUE`  
`EXP033_NATIVE_WINDOWS_EXACT_SOURCE_SYNTHETIC_PARITY=PASS`

Any missing marker, nonzero Python/pytest/Git exit, AST error or unanticipated prerequisite is **STOP / NOT VERIFIED**, not a passed milestone. The output may include failure paths within the disposable clone; **do not paste secrets, environment variables, tokens or a raw private K5 report**. Paste only the script's synthetic-test stdout/summary, review SHA and these markers.

## What Windows parity does not approve

Even on PASS, no real K5 source/ledger has been read, no natural hourly publisher has consumed an epoch, no Windows ACL/key-custody/trusted monotonic receipt persistence or writer overlap/crash test has been performed, and no cloud accepted receipt exists for CURRENT crypto. **It does not prove live hourly publication, profitability, or new trading authority.**

Next technical gate after a verified Windows PASS: review residual prototype defects and prepare separately owner-approved source-authenticated K5 read-only producer and receipt storage, fault/race tests and independent crypto-only publisher integration; first ask the owner before any real private ledger read, VPS scheduled-task change, cloud POST, production merge, or source sync. Mandatory manual frozen-dependency-impact verification and named exact-SHA merge approval are still required for every later merge.

**Owner action:** execute the final **exact-SHA one-block bootstrap** delivered in the companion chat response; share the resulting stdout. Do not use ordinary `git pull` or check out draft branches within the live VPS repository.
