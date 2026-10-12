# EXP034 — owner-approved bounded VPS SOURCE FAST-FORWARD ONLY.
# Do not run the cloud publisher, crypto K5, Task Scheduler mutations, or trading.
# Never use this file to enable VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1.
[CmdletBinding()]
param()
$ErrorActionPreference = "Stop"

$SyncRepo = "C:\Users\Administrator\Desktop\Signal Projects\trading-signal-intelligence"
$SyncOld = "8ec0e82ea340682d92f9a62acf85171b7715bf5d"
$SyncNew = "b900796dd7075a31dd01c89639c9461ef9ee3fb1"
$SyncOriginPattern = '(?i)(^|[:/])alisufyan-ai7/trading-signal-intelligence(\.git)?$'
$SyncRunner = "C:\ProgramData\VowSig-EXP031-HourlyPublisher\guarded-task-runner.ps1"
$SyncRollback = "C:\ProgramData\VowSig-EXP031-PreSyncRollback-20261011T162144Z-824dcdf4"
$SyncSeal = Join-Path $SyncRepo "data\crypto-research-asof-v0.1.json"
$SyncMarker = Join-Path $SyncRepo "data\exp031-one-shot-historical-publication-attempt-20261011.json"
$SyncExpectedSealHash = "F13921A09C3EFB77B4C2A874F58073C3E0CF7D59635D7E1900A50A5F957954C4"

$SyncTaskNames = @(
    "SignalProof AI-v1.1 Shadow Scan",
    "VowSig AI-v1.2.1 Expansion Shadow Scan",
    "VowSig AI-v1.3 Crypto Shadow Scan",
    "TradingTop Product Publish"
)
$SyncExpectedChangedFiles = @(
    "docs/CURRENT-HANDOFF.md",
    "docs/README-FIRST.md",
    "docs/engineering-lessons-and-release-checklist-2026-10-12.md",
    "ops/handoffs/exp034-current-crypto-aggregate-hourly-runner-v0_1.ps1",
    "ops/handoffs/exp034-hourly-crypto-aggregate-release-readiness-v0_1.md",
    "ops/handoffs/exp034-native-windows-readonly-release-verifier-v0_1.ps1",
    "ops/handoffs/k5_bounded_natural_read_only_v0_1.py",
    "ops/handoffs/test_k5_bounded_natural_read_only_v0_1.py",
    "ops/handoffs/vowsig-crypto-hourly-consolidated-windows-verifier-v0_1.ps1",
    "research/experiments/EXP-2026-027-b1b2-synthetic-backup-prototype-2026-10-11.md",
    "research/experiments/EXP-2026-028-single-s02-backup-implementation-preparation-2026-10-11.md",
    "research/post-mvp/vowsig-hourly-crypto-aggregates-consolidated-release-2026-10-12.md",
    "research/recovery/EXP-2026-029-durable-retention-failure-domain-plan-2026-10-11.md",
    "research/recovery/EXP-2026-030-offsite-s02-provider-rights-readiness-2026-10-11.md",
    "research/recovery/vowsig-sqlite-protection-inventory-2026-10-11.csv",
    "scripts/guarded_product_publish_v0_1.py",
    "src/trading_signal_intelligence/product/crypto_completed_epoch_v0_1.py",
    "src/trading_signal_intelligence/product/crypto_epoch_bridge_v0_1.py",
    "src/trading_signal_intelligence/product/crypto_epoch_source_producer_v0_1.py",
    "src/trading_signal_intelligence/recovery/b1b2_single_s02_local_trial_v0_1.py",
    "src/trading_signal_intelligence/recovery/b1b2_synthetic_v0_1.py",
    "tests/test_b1b2_single_s02_local_trial_v0_1.py",
    "tests/test_b1b2_synthetic_v0_1.py",
    "tests/test_crypto_completed_epoch_v0_1.py",
    "tests/test_crypto_epoch_bridge_v0_1.py",
    "tests/test_crypto_epoch_source_v0_1.py",
    "tests/test_guarded_crypto_current_aggregate_v0_1.py"
)

function SyncGitSingle([string[]]$VsgGitArgs) {
    $VsgOutput = @(& git -C $SyncRepo @VsgGitArgs)
    if ($LASTEXITCODE -ne 0 -or $VsgOutput.Count -ne 1) {
        throw "Git identity check failed"
    }
    return ([string]$VsgOutput[0]).Trim()
}
function SyncAssertLive([string]$VsgHead) {
    if ((SyncGitSingle @("branch", "--show-current")) -cne "main") {
        throw "Live Git branch changed"
    }
    if ((SyncGitSingle @("rev-parse", "HEAD")) -cne $VsgHead) {
        throw "Live Git HEAD is not the exact permitted commit"
    }
    $VsgDirty = @(& git -C $SyncRepo status --porcelain --untracked-files=no)
    if ($LASTEXITCODE -ne 0 -or $VsgDirty.Count -ne 0) {
        throw "Live tracked Git worktree is not clean"
    }
}
function SyncTaskSnapshot([bool]$VsgRequireQuiet = $true) {
    $VsgResult = @{}
    foreach ($VsgName in $SyncTaskNames) {
        $VsgTask = Get-ScheduledTask -TaskName $VsgName -ErrorAction Stop
        $VsgInfo = Get-ScheduledTaskInfo -TaskName $VsgName -ErrorAction Stop
        if ([string]$VsgTask.State -cne "Ready" -or [int64]$VsgInfo.LastTaskResult -ne 0) {
            throw "Scheduled task state is not Ready/last-result-zero"
        }
        if ($VsgRequireQuiet -and
            ($VsgInfo.NextRunTime - (Get-Date)).TotalMinutes -le 12) {
            throw "Safe quiet window unavailable (next scheduled task is within 12 minutes)"
        }
        $VsgResult[$VsgName] = Export-ScheduledTask -TaskName $VsgName -ErrorAction Stop
    }
    $VsgPublisher = Get-ScheduledTask -TaskName "TradingTop Product Publish"
    $VsgActions = @($VsgPublisher.Actions)
    if ($VsgActions.Count -ne 1 -or
        $VsgActions[0].Execute -notlike "*powershell.exe" -or
        $VsgActions[0].Arguments -notlike "*VowSig-EXP031-HourlyPublisher*guarded-task-runner.ps1*") {
        throw "Unexpected guarded publisher scheduled-task action"
    }
    return $VsgResult
}
function SyncAssertSealed {
    if (-not (Test-Path -LiteralPath $SyncRunner -PathType Leaf) -or
        -not (Test-Path -LiteralPath $SyncRollback -PathType Container) -or
        -not (Test-Path -LiteralPath $SyncMarker -PathType Leaf)) {
        throw "Guarded publisher, private rollback checkpoint or one-shot marker absent"
    }
    $VsgSealItem = Get-Item -LiteralPath $SyncSeal -ErrorAction Stop
    if ($VsgSealItem.Length -ne 3048 -or
        (Get-FileHash -LiteralPath $SyncSeal -Algorithm SHA256).Hash -cne $SyncExpectedSealHash) {
        throw "Historic DELAYED crypto seal differs from approved bytes"
    }
    $VsgRunnerText = [System.IO.File]::ReadAllText($SyncRunner)
    if (-not $VsgRunnerText.Contains('VOWSIG_GUARDED_PUBLISH_ENABLED') -or
        -not $VsgRunnerText.Contains('VOWSIG_CRYPTO_ASOF_ENABLED') -or
        -not $VsgRunnerText.Contains($SyncExpectedSealHash) -or
        $VsgRunnerText.Contains('VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1')) {
        throw "Installed guarded runner changed or crypto current opt-in already present"
    }
    foreach ($VsgTarget in @("Process", "User", "Machine")) {
        if ([Environment]::GetEnvironmentVariable(
            "VOWSIG_CRYPTO_CURRENT_AGGREGATES_V1", $VsgTarget) -ceq "1") {
            throw "Current crypto aggregate opt-in unexpectedly enabled"
        }
    }
}
function SyncAssertFrozenSource {
    $VsgPinned = [ordered]@{
        "src/trading_signal_intelligence/ai_v1/observability.py" = "b4ba334e6c7c2e54c301251268f5bfe2746c75cd"
        "src/trading_signal_intelligence/ai_v1/crypto_observability_v1_3.py" = "c974d65354ccc17060e0e1c6a85d1e7d9237281e"
        "src/trading_signal_intelligence/ai_v1/crypto_activation_v1_3.py" = "afba5b93cfeb1f849f70f242f137bd16bd24fd6d"
        "config/ai_v1_3_crypto_review_gates.json" = "e74e4102ec71fdea362a460130bcadee61e1777e"
        "scripts/run_product_publish_guarded_v0_1.cmd" = "7fb2dea42cd0ac2bbe3239d9bd364c35106a8231"
    }
    foreach ($VsgFile in $VsgPinned.Keys) {
        $VsgPin = [string]$VsgPinned[$VsgFile]
        $VsgPath = Join-Path $SyncRepo ($VsgFile.Replace("/", "\"))
        $VsgCommitted = SyncGitSingle @("rev-parse", "HEAD:$VsgFile")
        $VsgDisk = SyncGitSingle @("hash-object", "--path=$VsgFile", "--", $VsgPath)
        if ($VsgCommitted -cne $VsgPin -or $VsgDisk -cne $VsgPin) {
            throw "Frozen scanner/config or guarded publisher source hash drift"
        }
    }
}

if (-not (Test-Path -LiteralPath $SyncRepo -PathType Container)) {
    throw "Exact VPS repository absent"
}
$SyncRemote = SyncGitSingle @("remote", "get-url", "origin")
if ($SyncRemote -notmatch $SyncOriginPattern) {
    throw "Origin is not the authorized private GitHub repo"
}
SyncAssertLive $SyncOld
SyncAssertSealed
SyncAssertFrozenSource
$SyncTaskBefore = SyncTaskSnapshot
$SyncRunnerHash = (Get-FileHash -LiteralPath $SyncRunner -Algorithm SHA256).Hash

$SyncHookPath = SyncGitSingle @("rev-parse", "--git-path", "hooks/post-merge")
if (-not [System.IO.Path]::IsPathRooted($SyncHookPath)) {
    $SyncHookPath = Join-Path $SyncRepo $SyncHookPath
}
if (Test-Path -LiteralPath $SyncHookPath -PathType Leaf) {
    throw "Active post-merge hook requires separate review"
}
$SyncConfiguredHookPath = @(& git -C $SyncRepo config --get core.hooksPath)
if ($SyncConfiguredHookPath.Count -gt 0 -and
    -not [string]::IsNullOrWhiteSpace(([string]$SyncConfiguredHookPath[0]))) {
    throw "Custom Git hooks path requires separate review"
}

$SyncRemoteRow = SyncGitSingle @("ls-remote", "--heads", "origin", "refs/heads/main")
$SyncRemoteParts = $SyncRemoteRow -split "\s+"
if ($SyncRemoteParts.Count -ne 2 -or
    $SyncRemoteParts[0] -cne $SyncNew -or
    $SyncRemoteParts[1] -cne "refs/heads/main") {
    throw "Remote main changed from exact approved release"
}
Write-Output "EXP034_VPS_PRE_SYNC_SOURCE_AND_TASKS=PASS"

# Source acquisition is the only operation before the guarded fast-forward.
& git -C $SyncRepo fetch --no-tags origin refs/heads/main
if ($LASTEXITCODE -ne 0) { throw "Git source fetch failed" }
if ((SyncGitSingle @("rev-parse", "FETCH_HEAD")) -cne $SyncNew) {
    throw "Fetched source does not equal the exact merged GitHub commit"
}
& git -C $SyncRepo merge-base --is-ancestor $SyncOld $SyncNew
if ($LASTEXITCODE -ne 0) { throw "Source is not a direct fast-forward" }
$SyncPaths = @(& git -C $SyncRepo diff --no-renames --name-only $SyncOld $SyncNew)
if ($LASTEXITCODE -ne 0 -or $SyncPaths.Count -ne $SyncExpectedChangedFiles.Count -or
    @(Compare-Object ($SyncPaths | Sort-Object) ($SyncExpectedChangedFiles | Sort-Object)).Count -ne 0) {
    throw "Old-to-new source file list differs from 27 reviewed paths"
}
# Added files must not overwrite untracked local files.
$SyncNewPaths = @(& git -C $SyncRepo diff --no-renames --name-only --diff-filter=A $SyncOld $SyncNew)
if ($LASTEXITCODE -ne 0) { throw "Added-file collision check failed" }
foreach ($VsgAdded in $SyncNewPaths) {
    if (Test-Path -LiteralPath (Join-Path $SyncRepo ($VsgAdded.Replace("/", "\")))) {
        throw "An untracked/local file would collide with approved source"
    }
}
SyncAssertLive $SyncOld
SyncAssertSealed
$SyncTaskJustBefore = SyncTaskSnapshot
foreach ($VsgTaskName in $SyncTaskNames) {
    if ($SyncTaskJustBefore[$VsgTaskName] -cne $SyncTaskBefore[$VsgTaskName]) {
        throw "A scheduled task definition changed during source fetch"
    }
}
Write-Output "EXP034_EXACT_FETCH_AND_27_PATH_SCOPE=PASS"
Write-Output "EXP034_OWNER_APPROVED_SOURCE_SYNC_STARTED=TRUE"

# Only permitted production mutation: one Git fast-forward.
& git -C $SyncRepo merge --ff-only $SyncNew
if ($LASTEXITCODE -ne 0) {
    throw "Fast-forward failed; stop without auto-reset, retry or task changes"
}

SyncAssertLive $SyncNew
SyncAssertFrozenSource
if ((SyncGitSingle @("rev-parse", "HEAD:scripts/guarded_product_publish_v0_1.py")) -cne
    "e3f153128d4c65c7c98cfba7427a6e892eca2e29") {
    throw "Approved guarded publisher source blob missing after sync"
}
SyncAssertSealed
if ((Get-FileHash -LiteralPath $SyncRunner -Algorithm SHA256).Hash -cne $SyncRunnerHash) {
    throw "Installed protected guarded task launcher changed"
}
$SyncTaskAfter = SyncTaskSnapshot -VsgRequireQuiet $false
foreach ($VsgTaskName in $SyncTaskNames) {
    if ($SyncTaskAfter[$VsgTaskName] -cne $SyncTaskBefore[$VsgTaskName]) {
        throw "A scheduled task definition changed during source sync"
    }
}
Write-Output "EXP034_EXACT_NEW_GITHUB_MAIN_ON_VPS=PASS"
Write-Output "EXP034_FROZEN_K5_AND_GUARDED_BASE_UNCHANGED=PASS"
Write-Output "EXP034_SAME_FOUR_TASKS_AND_OLD_RUNNER=PASS"
Write-Output "EXP034_CRYPTO_CURRENT_OPT_IN_STILL_DISABLED=TRUE"
Write-Output "EXP034_CONTROLLED_VPS_SOURCE_FAST_FORWARD=PASS"
