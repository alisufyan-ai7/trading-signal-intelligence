# EXP-042 — pinned boto3/botocore fake HTTP compatibility proof on Windows VPS

**Owner instruction (2026-10-23):** Proceed with the next milestone following EXP041 / merged PR #74. **PREPARATION and isolated VPS offline-only testing, no provider API calls/credential use, no installs, no VPS deployments and no scheduled task edits.**

**Repository:** \`alisufyan-ai7/trading-signal-intelligence\` ONLY. Starting GitHub \`main=bc00e87cfaafe03127fde3d1ddda5154801e3d92\`; EXP040 one-shot operator is unchanged and still has \`REAL_PROVIDER_REQUESTS_ENABLED=False\`. EXP041/B6 request guard is merged but is not attached to the real operator; EXP042 is independent offline interoperability evidence, not an activation.

## 1. Why this experiment exists

EXP041's 122/122 Windows tests validated **simulated** before-send events and decrypted/restored fake SQLite, but did not exercise real boto3/botocore serializers, signers, parsers or event dispatch. Before any network activation, those behaviors need review against a fixed SDK, with **zero actual egress** and without ever loading provider-issued secrets.

\`scripts/exp042_pinned_sdk_fake_http_proof.py\` implements one such proposed SDK-transport simulation. It uses the exact B1/B3 synthetic fixture and EXP040's synthetic input function; B4's bounded two-provider pilot and B5's call-order/roles, plus B6's URL/headers/body/authorization \`before-send.s3\` request verifier. It then exercises the **real pinned SDK's** \`put_object\` / \`get_object\` / \`head_object\` methods but intercepts each signed \`AWSPreparedRequest\` event and returns only in-process fake \`AWSResponse\` bytes. AWS returns fake version ID, B2 HEAD gives fake 404, B2 PUT/GET give fake receipts and bytes. Two independent B3 authenticated SQLite restores must match the original captured synthetic file. No real network requests are intended or permitted.

## 2. Exact proposed SDK pins and supply-chain metadata

**Pins chosen for compatibility research, NOT installation authority:**
- \`boto3==1.43.114\`, PyPI 2026-10-14, wheel \`boto3-1.43.114-py3-none-any.whl\`, SHA-256 \`d9cac2eb921ce674970cef1c9ad750f85ee3a846aedcf188d18368fb9eb6da23\`.
- \`botocore==1.43.114\`, PyPI 2026-10-14, wheel \`botocore-1.43.114-py3-none-any.whl\`, SHA-256 \`d1c441a22e93e158de5b1e026205f5d6d67a4545d10540c5090c62dccb3a9eca\`.
- PyPI sources: https://pypi.org/project/boto3/1.43.114/ and https://pypi.org/project/botocore/1.43.114/. Botocore is documented as Apache-2.0 and Python 3.12 compatible. PyPI lists **no Trusted Publishing provenance** for these release files. Hashes only provide integrity relative to the shown files; they are NOT independent security audits.
- The repository's current \`pyproject.toml\` has **no boto3/botocore dependency**, so do **not** assume the existing isolated VPS test interpreter contains this exact pair.
- These two package hashes are preparatory metadata, not a full reproducible dependency lock: compatible \`s3transfer\`, \`jmespath\`, \`python-dateutil\`, \`urllib3\` and other transitives must be resolved, vetted and hash pinned if a **future owner-approved isolated package acquisition** becomes necessary. No \`pip download\` or \`pip install\` is authorized in EXP042.

## 3. Hard offline transport protection and limits

The EXP042 entry point accepts ONLY \`--offline-only\` and uses a non-echoing parser. It first checks that the inherited EXP040 cloud switch remains disabled. It reads **local installed package version metadata** (no package download, no API) and **fails closed** if boto3/botocore are missing or do not match both exact pins.

For exact already-installed pins, it:
1. Patches socket connect/connect_ex/create_connection to reject all TCP connects before importing SDK packages or creating clients; restores originals in \`finally\`. This is an **in-process fail-safe only**, not a firewall or isolation from other processes.
2. Supplies hardcoded deliberately invalid FAKE access/secret values directly to the boto3 Session and S3 clients; never retrieves default profiles, real credentials, or owner keys. Uses the fixed B4 endpoints/regions with SigV4, total SDK attempts=1, TLS verification, path addressing, timeouts and optional S3 checksum config.
3. Replaces each of FOUR client \`_endpoint.http_session\` objects with a **deny-all** fake transport *before* any S3 method call. The fake transport's \`send\` raises unconditionally, including when a before-send event fails to intercept.
4. Attaches B6's proposed \`before-send.s3\` validation handlers first. Separate mock-response handlers registered after B6 produce in-process botocore \`AWSResponse\` only if **that event has already passed the exact B6 fence**. No actual HTTP transport \`send\` is needed or permitted.
5. Checks that exactly five signed/validated pre-send events occurred in AWS PUT + GET and B2 HEAD404 + PUT + GET order; that B4 independently authenticated both synthetic restores; that the four deny transports report ZERO \`send\` invocations; and that no real provider credential or cloud mode was ever enabled.

**Important: this design might FAIL on a given SDK.** Real serialization can differ from mock assumptions (checksum headers, URL encoding, SDK hook dispatch priority, B2 version headers, body framing, mock streaming body behavior, or region choice). Such a failure is **STOP/HOLD**, not permission to relax any guard. No change to B4/B5/B6 or EXP040 activation without a narrowly reviewed subsequent PR and new native Windows tests.

## 4. Mandatory tests and truth in reporting

New \`tests/test_exp042_pinned_sdk_fake_http_proof.py\` checks pin matching and fail-closed missing SDK, no-echo argument refusal, deny-all transport and socket blocker, fake-only credentials, and an actual signed SDK fake-wire smoke test **ONLY when the exact versions are already present**.

**No false PASS when the SDK is unavailable:** the true SDK test explicitly SKIPS with \`EXP042 SDK COMPATIBILITY HOLD\` if missing/unpinned, and the **standalone operator CLI must return nonzero HOLD**. A green pytest suite with any such skip **does NOT close** SDK compatibility. Conversely, do not infer runtime PASS from static GitHub checks or inherited previous EXP041 122/122 Windows tests.

Owner must execute an SHA-pinned disposable GitHub checkout using the already existing isolated VPS Python; run new unit tests + prior EXP041/EXP040/B5/EXP038/B4/B3/B1 offline suites; run the explicit EXP042 CLI and record whether it returns PASS or HOLD. Frozen-dependency checker must pass and production VPS checkout remain clean. Retain any FAIL/STOPPED immutable and retest only after a reviewed fix at a new exact head. No modifications on production VPS.

### Acceptance semantics

- **EXP042_STATIC_PREPARED:** GitHub three-new-file exact diff and source checks PASS. No native tests required for the status.
- **EXP042_OFFLINE_UNIT_PASS:** native Windows new+prior regression suites PASS, frozen dependency and unchanged production PASS; SDK functional test may be SKIPPED. This is **not** SDK compatibility PASS.
- **EXP042_PINNED_SDK_FAKE_TRANSPORT_PASS:** only when the standalone SDK proof using **exact installed versions** completes FIVE signed before-send hooks + two authenticated synthetic restores + ZERO HTTP \`send\` calls; observed runtime/pytest results must support.
- **EXP042_HOLD_MISSING_SDK:** no exact pinned installed pair; must first obtain separate approval to acquire/install SDK into a **disposable nonproduction** VPS test environment. Resolve transitive wheel hashes and licensing/security before any installation.
- **EXP042_FAILED_CLOSED:** SDK/hooks/serializer/transport reject or other unexpected result; do not use cloud.
- A successful EXP042 is still NOT real AWS/B2 recovery, a $0 billing guarantee, or approval to use the SDK or keys with actual providers.

## 5. Provider and data constraints unchanged

- All code and test execution on **Windows VPS only**, under manual RDP, isolated disposable checkout. No owner's personal-machine execution.
- Four restricted writer/read-only restore identities stay in private MFA password manager **off VPS** until a separate exact one-time **owner-approved real provider pilot**. Never paste them to ChatGPT/GitHub/source, CLI args, environment, logs or files. Future masked entry still exposes keys temporarily in VPS process memory, which cannot be guaranteed zeroized.
- Owner confirmed AWS versioning Enabled, all four Public Access blocks and B2 Private, and reported zero-cost eligibility. **Free Tier/credits do not constitute an enforceable $0 spend cap**; no actual provider call, not even HEAD, unless hard $0 risk is resolved and fresh API approval is obtained.
- No real data backup, production \`research.sqlite\`, AI shadow ledgers, paid/third-party market feeds, provider account changes, scheduling, deployment, network downloads, SDK installations or cloud charges.
- PR #68 IAM/credential documentation remains separate and unmerged.

**Status at authoring: EXP042 DRAFT PREPARATION; SDK pin availability on owner's isolated Windows VPS UNKNOWN; no package install, real network request or live cloud activation.**

## EXP042 second attempt and prospective diagnostic correction (2026-10-23)

**Immutable owner VPS result (original tested HEAD `73e06ae176da45344316bf0268ebfc8ba04be379`):** PR #76's seven-wheel acquisition PASSED (17 unit tests, SHA-256 of all seven wheels, active dependencies, new disposable VPS environment). The original PR #75 SDK proof then **FAILED CLOSED** on the **first fake AWS PUT**, producing B4 `SyntheticS3PilotRejected("synthetic upload ambiguous; stop, do not retry")`. SDK-overlay suite: **131 PASSED, 1 FAILED**. Production remained unchanged. Overall EXP042 HOLD. Full evidence in PR #75 and Issue #67. Earlier 131 PASS/1 SKIP missing-SDK HOLD remains independently immutable.

**Narrow prospective change on DRAFT PR #75:** The source retains `PROVIDER_CALLS_ALLOWED=False`, EXP040 `REAL_PROVIDER_REQUESTS_ENABLED=False`, four deny-all transports, fake-only credentials and socket denies. The new `--diagnostic-only` adds a read-only fixed-boolean event observer before B6, and reports only boolean request-shape categories (HTTPS, host/path, body byte-match, content type/length, SigV4 region and AWS conditional PUT) and counts of SDK before-send events, B6 accepted events, mock response events and denied HTTP transport invocations.

**Never printed:** raw URLs, Authorization headers, access key IDs, signatures, object IDs, ciphertext, plaintext, exception messages or provider response contents. B4/B5/B6 validations remain unchanged. This output is not itself a secure audit of all secrets held in Python process memory; it is fixed-field diagnostic output.

**Semantics:** `--diagnostic-only` deliberately returns nonzero exit code 2 and `EXP042_FAKE_HTTP_DIAGNOSTIC_HOLD` on a stopped mock operation. The diagnostic is NOT a restored backup or permission to retry an ambiguous real upload. Any eventual fix must target the observed fake-SDK mismatch, preserve fail-closed B4/B5/B6 checks, and be retested at a NEW SHA.

**Next permitted step:** exact new PR #75 checkout on the existing Windows VPS; reuse (do NOT reinstall) the previously verified isolated seven-wheel environment if it still exists; run negative/offline tests excluding the original known failing integration, then the sanitized `--diagnostic-only`, frozen dependency guard, and production unchanged postflight. NO provider API calls, owner credentials, real databases, package installation, production updates, task modifications or GitHub merge.

## EXP042 third VPS attempt: 134/134 negative checks PASS; exact body field failure; further offline diagnosis required

Owner's 2026-10-23 VPS transcript `Pasted text(20261023-093338).txt` at exact prior PR #75 HEAD `eb94b59d2de7cf9d9111281ccc7763b7d25258f2`: disposable SHA verification and seven installed SDK pins PASS; 134 native offline pytest PASSED with known SDK integration DESELECTED; frozen dependency PASS (113 protected paths / 3 changed); production unchanged; sanitized `--diagnostic-only` exited intentionally nonzero/HOLD.

First real botocore 1.43.114 fake-HTTP AWS PUT pre-send event **observed 1**, B6 **accepted 0**, fake responder invoked **0**, deny transport send invoked **0**. Checked HTTPS scheme/host, exact object path, method PUT, SigV4 scope, no query, correct Content-Type and Content-Length, AWS `If-None-Match: *`, no transfer-encoding or security token — all TRUE. Only false predicate: `body_exact_bytes`. That single predicate was defined as **`type(body) is bytes and body == ciphertext`**, so it cannot distinguish a seekable SDK body stream from corrupted/different byte content. It is not yet safe to amend B6 on this evidence alone. Original SDK fake-HTTP compatibility remains **HOLD**.

**Prospective narrow diagnostic v2:** Add helper `_safe_body_shape` ONLY to the inert EXP042 PR #75 proof script, without changing B4/B5/B6 or EXP040. Record separate fixed booleans `body_is_bytes_type`, `body_bytes_match`, `body_has_stream_methods`, `body_stream_seekable`, `body_stream_at_zero`, `body_stream_full_payload_match`, and `body_stream_cursor_restored`. For a body with callable read/seek/tell/seekable, it only reads at most expected encrypted envelope length + 1 if seekable and at offset zero, then attempts to restore the original cursor. It emits only fixed boolean values, not the body, type name, credentials, path, or exception message. This is fake-only instrumentation under the existing socket/HTTP deny layer. No SDK package installation needed.

**Acceptance:** This v2 diagnostic is **not yet tested on the Windows VPS**. Exact-HEAD native negative tests, SDK pin overlay, `--diagnostic-only` JSON nonzero/HOLD, frozen dependency check and clean production postflight are required. The known failing full SDK integration remains intentionally deselected until a separate reviewed B6 or proof correction is justified by these flags and tested. Do not merge PR #75/#76, activate provider calls, handle owner secrets or contact AWS/B2. Prior failed/HOLD outcomes remain immutable.
