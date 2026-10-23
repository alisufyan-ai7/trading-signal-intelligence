# EXP-041 — VPS-only real-cloud activation security proposal and offline HTTP request fence

**Date:** 2026-10-23. **Status:** DRAFT / PREPARATION ONLY, actual AWS/B2 network authorization NOT GRANTED.

## Frozen context and owner instructions

Work exclusively in private \`alisufyan-ai7/trading-signal-intelligence\` repository and this current project chat. GitHub \`main\` was pinned at \`eef51f25c924b7f2a41ed480193b6de5ad1db202\` after approved PR #73. The exact merged EXP040 script \`scripts/exp040_vps_one_shot_synthetic_cloud_operator.py\` has **\`REAL_PROVIDER_REQUESTS_ENABLED = False\`**. Nothing in this proposal modifies it, starts a network client, prompts for a secret, installs code/packages, or edits scheduled tasks.

Owner's immutable operating constraints:
- **Existing Windows VPS only**, manual RDP interactive, in a disposable isolated checkout/venv—not owner's personal machine.
- Four scoped credentials remain in owner's MFA password manager **outside VPS**, and must NOT be sent to GitHub/chat or persisted in a VPS profile, file, task, log, command-line argument, environment or PowerShell history. A future separately authorized interactive \`getpass\` session would nevertheless temporarily expose each key in VPS process memory and perhaps Windows paging/crash dumps; no zeroization guarantee.
- AWS bucket \`vowsig-backup-s3-2026\`, \`us-east-1\`: owner confirmed versioning enabled, four public-access blockers enabled, and free-usage/$0 eligibility. B2 bucket \`vowsig-backup-b2-2026\`, \`us-east-005\`: owner confirmed private, free-usage/$0 eligibility. These are **owner console attestations**, not effective permissions or provider rate/bill controls.
- Hard out-of-pocket budget **$0**: free-tier eligibility/budget alerts/byte or request limits are **not an enforceable spending cap**. If the actual account billing cannot guarantee $0 under all failure and retention cases, continue offline-only. Don't redefine owner constraints to "small estimated charges."
- Synthetic-only test bytes, new disposable B1 fixture, B3 AES-256-GCM, B4 bounded pilot, B5 method restrictions. No real Exness/Binance/raw/research.sqlite/production shadow ledgers. No routine production scheduler/task changes, provider account configuration mutations, retries/deletes/cleanup or unintended bucket permissions.

## Why another offline gate was needed

EXP039/B5 and EXP040 pin exactly **five Python SDK calls** (AWS \`PutObject\`, version-specific \`GetObject\`; B2 \`HeadObject\` expected 404, \`PutObject\`, version-specific \`GetObject\`). An SDK method invocation is not an HTTP transmission count, and a client SDK could redirect, retry, choose wrong host, sign for wrong region, add object tags/ACL, or make hidden authentication/network calls. \`_check_client\` inspects configuration metadata but doesn't inspect signed URLs or eventual requests.

EXP041 introduces an independently tested **pure Python** candidate \`src/trading_signal_intelligence/recovery/b6_synthetic_s3_wire_fence_v0_1.py\`. It provides \`SyntheticWireFence\`, to be wired by a FUTURE separately approved driver to a pinned SDK's S3 \`before-send\` hook. **EXP040 still doesn't import or attach it; the real-cloud mode stays source-disabled.** This is defense-in-depth research, not a network security sandbox.

The candidate fence checks each request before a network send:
1. Exact FIVE global ordered pre-send events: AWS writer PUT, AWS reader GET, B2 reader HEAD, B2 writer PUT, B2 reader GET. Wrong order, repeated send (including hidden retry/redirect), role swap, >5 attempts or failure → permanently poisoned gate.
2. Requires corresponding B5 state-machine \`gate.enter\` before accepting that HTTP event. The AWS version query and B2 version query must equal the specific B5 guarded, provider-returned version ID. GET must have exactly one \`versionId\` query parameter, not duplicates.
3. Exact HTTPS regional endpoint host and **path-style** \`/{bucket}/{pilot/synthetic/v1/.../sha256.aesgcm}\`; no alternate domain, port, user info, unexpected query/fragment or raw-data path.
4. AWS PUT requires \`If-None-Match: *\`; B2 deliberately does not assume this header, preserves non-atomic HEAD-before-PUT caveat. PUT is limited to the exact original authenticated B3 ciphertext and digest (<131072 bytes), exact content length and \`application/octet-stream\`. GET/HEAD must have no body.
5. Requires signed SigV4 Authorization prefix/scope for exact provider region and service \`s3\`. Forbids ACL, tags, storage class changes, SSE overrides, copy source, object lock controls, x-amz-meta-*, AWS session token, transfer-encoding, bucket settings or other high-impact headers. No provider-derived URL/auth/secret printed.
6. A proposed \`attach\` registers a prefix-scoped \`before-send.s3\` observer on four independently supplied clients **without making any request**. Its botocore hook dispatch compatibility has not yet been tested with an actual pinned boto3/botocore version; it is a REVIEW REQUIREMENT, **not assumed**.

### Security and compatibility caveats (mandatory before any activation)

The simulated event-hook tests **cannot** guarantee that the actual SDK fires the chosen hook for every request or before transmission. In a future isolated VPS review with an SDK specifically version-pinned from a provider/rights-approved source, a fake HTTP transport must prove:
- Every applicable operation reaches the hook BEFORE any network I/O (not merely fake \`meta.events.emit\`);
- Retries, region redirects, extra ListBuckets/credential probes, error-driven follow-up requests are blocked at the transport boundary;
- Actual signing/URL encoding/headers/path-style match fence assumptions for **both** S3 and B2; adjust only through a reviewed source patch, never relax endpoint or role silently;
- SDK's use of proxies, configuration, CA/TLS verify, IMDS or default credentials is disabled/blocked as appropriate; explicit per-role credentials are required and SDK connection cannot silently fall back to ambient secrets;
- Network egress is restricted to the two explicit HTTPS S3 endpoints on 443, with DNS resolution and actual destination/IP/routing/TLS hostname independently validated. Egress limitations need VPS operator approval, not automatic firewall change.
- No log of signed requests, credentials, object IDs with sensitive identifiers, Python tracebacks with key strings, HTTP Authorization or access-key IDs; process exits without a durable key file. Key values exist transiently and cannot be guaranteed scrubbed from pagefile/memory.
- **HTTP pre-send budget is not a hard spending guard**; even with a five-send fence, successful remote PUTs persist after process failure. There is no guaranteed free object retention/egress or guaranteed $0 charge merely from code.

**No SDK package installation is authorized in this EXP; only existing isolated Python offline tests may run.** Do not put any actual cloud integration into production, connect to providers or change \`REAL_PROVIDER_REQUESTS_ENABLED\` on current main as part of EXP041.

## Offline acceptance gate for this PR

Only THREE **new paths**:
- \`src/trading_signal_intelligence/recovery/b6_synthetic_s3_wire_fence_v0_1.py\`
- \`tests/test_b6_synthetic_s3_wire_fence_v0_1.py\`
- \`research/recovery/EXP-2026-041-wire-request-security-preflight-2026-10-23.md\`

The new tests use no boto3, botocore or network clients. They create a disposable synthetic SQLite fixture, encrypt and authenticate it (B1/B3), feed artificial signed HTTPS request objects through a fake event-dispatcher in a B4/B5 guarded client simulation, and verify two independent decrypted/restored databases. They attempt an unwanted DELETE, wrong host/HTTP scheme, wrong region signing, wrong object path or version, duplicate version query, public ACL/tags/metadata, malformed body, premature/unapproved roles, duplicate PUT, and excess/missing pre-send events. **These are mock requests, not a real HTTP capture.**

Before any merge: owner VPS must verify exact PR HEAD/blob hashes in a disposable checkout; run new B6 plus prior EXP040/B5/EXP038/B4/B3/B1 regression modules using the existing isolated interpreter (previous EXP040 **97 PASS** only at older HEAD), run trusted frozen-dependency check against exact reviewed head, and verify live production checkout unchanged. Keep historical results immutable. GitHub-only merge requires separate exact-HEAD owner approval. Actual cloud pilot remains blocked regardless of a green PR.

## Future decision ladder (not yet authorized)

**A.** EXP041 mock fence + native Windows tests PASS; seek owner approval only for GitHub-only merge. No VPS sync, no provider call.

**B.** Prepare a *separate* tightly reviewed SDK compatibility proof in disposable VPS checkout using only fake/stubbed network transport, no real credentials or buckets. If unavailable on isolated interpreter, seek owner approval to obtain/pin SDK from a known source for isolated test; never auto-install. Provide SHA/license/supply-chain review.

**C.** Prepare a source change that only after explicit owner authorization could enable the one-shot actual synthetic run; pin reviewed SDK and network transport, verify owner-side $0 expense protections, calculate exact potential persistent synthetic storage object size and fees, confirm IAM/B2 prefix scope without broadening, and obtain **another distinct explicit owner authorization for two encrypted PUTs and three permitted read methods**. No automatic retries after ambiguous writes; if first provider fails, do not touch second provider.

**D.** Only a separately authorized real-cloud pilot may report true remote restore durability, and it must still be labeled SYNTHETIC_ONLY_NOT_REAL_APPLICATION_BACKUP. Future real-data backup legality, ownership, retention and key-custody remain separate HOLDS.

**Status: EXP041 DRAFT / OFFLINE only; EXP040 cloud mode DISABLED; no cloud API calls, credentials, package installs, task changes or VPS deployment.**
