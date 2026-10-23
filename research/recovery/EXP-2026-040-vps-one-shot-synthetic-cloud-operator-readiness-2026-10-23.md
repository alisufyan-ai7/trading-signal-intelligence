# EXP-040 — Windows VPS-only one-shot synthetic cloud operator (CLOUD DISABLED)

**Prepared 2026-10-23, DRAFT PREPARATION ONLY.** Scope: this open TradingTop Analysis chat and private repo \`alisufyan-ai7/trading-signal-intelligence\`. Starting frozen GitHub main: \`81e0d3ccb6f8745f0a64ddfe1d651cb54d6e089e\` (PR #72 merged). Existing installed VPS checkout has been independently observed clean at \`d5a139e87a0ee90d5a70f5aa040220fffa7af82a\`; no source synchronization, scheduler task changes or production Python package installation are approved by this EXP.

## Explicit owner decision: VPS ONLY

Owner rejected any execution on a personal computer. All synthetic generation, encryption, future uploads, downloads and recovery must execute on the existing Windows VPS, in a disposable isolated environment under manual RDP supervision. Four separately scoped AWS/B2 writer and reader credentials are currently **held by owner off VPS in an MFA password manager**. They must NEVER be pasted into this chat, PR, logs or source code. Credentials must NOT be installed in VPS profiles, .env files, global environment variables, PowerShell history, task configuration, plaintext files, crash reports or permanent credential stores as part of this pilot.

**Future authorized invocation only:** four credential pairs would be entered via eight manually typed masked Python \`getpass.getpass\` prompts in an INTERACTIVE Windows console. Those eight values would exist only as transient Python/SDK objects and cannot be cryptographically zeroized in CPython, nor can this design guarantee protection against a compromised VPS, debugger, process memory inspection, Windows pagefile, crash dump, terminal recording or malicious administrator. The VPS user account/EDR/RDP, browser password-manager workflow and security posture need separate owner diligence. No keys are requested or imported in this phase. The access-key ID is also masked for convenience.

## New operator source

\`scripts/exp040_vps_one_shot_synthetic_cloud_operator.py\` has two mutually exclusive CLI modes:

- **\`--offline-only\`**: implemented and intended for native Windows verification. It creates a newly marked disposable synthetic two-record S02 SQLite in a \`vowsig-b1b2-fixture-*\` temp directory (fixed B1 scope); B1 captures it; B3 seals it with freshly generated ephemeral AES-256-GCM key; B5 wraps **four in-process fake S3 clients** and B4 enforces AWS fake PUT+GET, B2 fake HEAD404+PUT+GET; both restored SQLite objects are SHA/chain verified independently. No provider SDK import, no credentials, no network, no real data. The temp fixture is discarded on exit. JSON result must show \`EXP040_OFFLINE_VPS_OPERATOR_PASS\`, 5 fake calls, 2 independent restores, ZERO actual provider calls, ZERO credential prompts and \`cloud_mode_enabled=false\`.
- **\`--cloud-pilot\`**: intentionally **HARD DISABLED** in this exact revision by source constant \`REAL_PROVIDER_REQUESTS_ENABLED = False\`. An attempt deterministically raises a fixed error **BEFORE** using \`getpass\`, importing boto3/botocore, constructing clients, preparing a synthetic fixture, or making an S3 request. The exact B4 approval phrase, user input or environment variables cannot override this gate; a SEPARATE owner-reviewed GitHub source revision would be needed to enable it.

Unknown CLI arguments are rejected using a custom parser that NEVER echoes unrecognized values; a key accidentally pasted into command-line arguments must not appear in the program's error output. Unknown authorization modes and CLI \`--key\`/secret flags are prohibited. Credential values have a redacted Python \`__repr__\`. Do not run the future program from a scheduled task. Keep \`getpass\` interactive; avoid running it under PowerShell transcript/recording or unattended redirection.

## Future-only SDK client factory (NOT executable via current cloud mode)

An inert \`_construct_explicit_boto3_client\` describes the intended future four client setup. It verifies the hard source gate **first**, then lazily imports boto3/botocore and uses explicit in-memory per-role credentials passed as named fields BOTH into a new boto3 session and the S3 client; *no credential file, default provider/profile/IMDS lookup is requested*. A specific source review must still test whether the actual SDK version performs any ambient config, instance metadata, certificate bundle, proxy, endpoint redirect, DNS or network behavior outside our assumptions.

Fixed expected settings: \`https://s3.us-east-1.amazonaws.com\` with \`us-east-1\`, \`https://s3.us-east-005.backblazeb2.com\` with \`us-east-005\`; SigV4, path addressing, payload signing, TLS verification on, \`connect_timeout=5\`, \`read_timeout=10\`, pool size 1, \`retries={"mode":"standard","total_max_attempts":1}\`, no supplied proxies. The B4+B5 wrappers enforce exact synthetic object key, SHA-256 hash and <=131072-byte encrypted payload, two AWS SDK method attempts (conditional \`PutObject\` + versioned \`GetObject\`), three B2 attempts (\`HeadObject\` then \`PutObject\` then versioned \`GetObject\`), reader/writer separation, two AES-GCM authenticated readback/restores, and no auto retry/delete after uncertainty. **B2 HEAD/PUT is non-atomic; no overwrite guarantee is claimed.**

**IMPORTANT SECURITY LIMITATION:** five Python SDK method calls do NOT prove five physical HTTP requests. SDK internal requests, redirects, proxies, credential resolution, retries and unexpected S3 endpoint behavior must be independently reviewed and instrumented before a future actual cloud pilot. A Python wrapper is not a security sandbox. The post-cloud result must not claim live-data protection or a $0 billing guarantee.

## Owner-reported cloud readiness

From owner's explicit console inspection (no API calls/settings changes):
- AWS \`vowsig-backup-s3-2026\`, \`us-east-1\`: Versioning **Enabled**, all four Block Public Access switches **Enabled**, owner reported $0/free-tier eligibility.
- B2 \`vowsig-backup-b2-2026\`, \`us-east-005\`: **Private**, owner reported $0/free-tier eligibility.
- Four scoped writer/reader identities exist, reader accesses limited to the \`pilot/\` prefix; key values remain owner-controlled off VPS.
- These are **owner attestations**, not API-verified effective IAM permissions, network compatibility, provider charges or version receipts.
- $0 is an **absolute owner spending constraint**. No finite request/byte cap, budget alert, "free tier" or owner-side estimate guarantees a nonbillable request. On uncertainty, **keep real provider calls disabled** rather than circumvent the requirement. Provider console billing/usage should be rechecked immediately before any fresh owner decision.

## Tests and mandatory gate

\`tests/test_exp040_vps_one_shot_synthetic_cloud_operator.py\` adds offline cases for the hard source deny, command-line-secret anti-echo, transient masked prompts (using synthetic inputs without a real Windows console), no SDK/network in offline, full B1/B3/B4/B5 fake-provider recovery, explicit client factory fail-close, disposable fixture cleanup, restricted source scope and fixed error messages. The previous EXP039 suite was **70/70 native Windows PASS** at earlier source, not a substitute for EXP040 tests.

**NO EXP040 native Windows tests or trusted frozen-dependency checks have been executed at authoring.** Owner must use a SHA-pinned disposable checkout of EXP040 PR branch on VPS, isolated existing Python (not production venv), execute \`--offline-only\`, then EXP040/B5/EXP038/B4/B3/B1 tests, and SHA-pinned frozen-dependency impact checker. Preserve every FAIL_CLOSED or STOPPED result; if changes are needed, use a new PR HEAD with an independently rerun test. No merge without separate exact-head GitHub-only owner approval.

**No actual cloud call is authorized now**, including diagnostic \`HEAD\`, nor any credential prompt, production update, package install, scheduled task change, real SQLite/market-data read, AWS/B2 upload/download or cost. Even if EXP040 merges, \`--cloud-pilot\` MUST remain disabled; enabling it requires separate reviewed code changes plus explicit, narrowly scoped owner permission and validated zero-cost gate. The actual provider smoke test is NOT a live offsite backup of S02 or raw third-party market data; rights, encryption-key recovery custody and privacy remain separate gates.

## Public API reference background (not live tests)

- AWS botocore Config \`total_max_attempts=1\` means one total attempt: https://docs.aws.amazon.com/botocore/latest/reference/config.html
- Boto3 credential chain is bypassed only when explicit credentials are correctly supplied; verify client version rather than assume: https://docs.aws.amazon.com/boto3/latest/guide/credentials.html
- Backblaze B2 uses SigV4 compatible SDK credentials and regional HTTPS endpoint: https://www.backblaze.com/docs/cloud-storage-connect-to-backblaze-b2

**Status: EXP040 PREPARE / DRAFT / OFFLINE TEST PENDING / CLOUD HARD DISABLED.**
