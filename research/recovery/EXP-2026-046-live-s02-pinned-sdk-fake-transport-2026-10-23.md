# EXP046 — P4 pinned real-SDK, in-process-only transport compatibility

_Date: 2026-10-23. Status: prospective only; requires exact native Windows verification._

**Parent:** P3 draft PR #79 at `bfc6f4d5873b9e1ab100768192c7a65f78cee04c`, which depends on P2 PR #78 and P1 PR #77. P1/P2 18/18 native Windows synthetic tests and frozen checker PASS; P3 20/20 native Windows signed release-review tests and frozen checker PASS. No producer, real ledger, SDK integration or provider API has been deployed or tested live.

## Narrow experiment

Previously tested P1/P2's 18 fake clients do not model actual boto3/botocore signing, checksum headers, response parser, or client retry events. P4 introduces a **test-only** actual SDK integration against *one synthetic S02 fixture* using exact previously approved seven pinned versions: boto3/botocore 1.43.114, jmespath 1.0.1, s3transfer 0.19.3, python-dateutil 2.9.0.post0, urllib3 2.8.0, six 1.17.0. All SDK clients receive demonstrably fake test credentials. Import and construction occur only under patched `socket.socket.connect` and `connect_ex` denial.

All FOUR boto3 S3 clients' `_endpoint.http_session` transports are replaced *before the first method call* by in-process `AWSResponse` objects. A local fake session rejects any event unless the unchanged P2 signed `before-send.s3` wire fence already validated that exact endpoint/provider/role/method. The fake session returns one AWS 200 PUT/version response and versioned 200 GET, B2 HEAD 404 error, B2 PUT 200/version response, and B2 versioned 200 GET. No actual outbound provider operations, provider account, bucket lookup or real credential request are performed. The requested proof is 5 signed events, 5 in-process fake sessions, independently authenticated S02 SQLite decrypt-and-hash-chain restores from both provider responses and one preflight restore, **zero external transport or socket connects**.

The P4 synthetic fixture inherits the exact P1/P2 source and S02 validation and retains the P3 unconditional release-evidence `live_provider_requests_authorized=False`. Existing B4/B5/B6 and PR #75/76 fake SDK proof remain separate and unmerged. This P4 test does not authorize any change to the P2 production implementation or relax wire fences based on SDK quirks.

## Required safety/acceptance

1. Use single disposable Windows VPS checkout, exact new P4 HEAD and one new test+doc scope, parent ancestry P1/P2/P3, remote GitHub `main` no drift, site-packages from already installed hash-verified SDK, *no PyPI download or installation*.
2. Run original 18 P1/P2 fixture cases + 20 P3 signed-evidence cases + new P4 case. **A failed P4 integration remains a research HOLD**, not authority to bypass signed request checks; expose only synthetic test status, avoid raw temporary session/exception material.
3. Verify trusted frozen dependency checker pinned commit and blob, then production git worktree clean pre/post. No file read from production `data/forward.sqlite` and no live database snapshots, cloud API (including HEAD), credentials, scheduled tasks, publishing or merge.
4. Even P4 PASS would **only** prove compatibility of signed botocore operations with an offline mock transport. Before actual production backup, complete source rights review, provider billing zero-spend guarantees, separate scoped credentials with off-VPS custody, vault Object Lock/versioning/retention, audit-friendly recovery manifests, operator deployment and off-host disaster restoration, plus exact release approval. A signed review alone does not authorize real provider requests.

**Current disposition:** P4 source prepared on draft branch, no native Windows results yet. The P1/P2/P3 previous offline checkpoint stays immutable.
