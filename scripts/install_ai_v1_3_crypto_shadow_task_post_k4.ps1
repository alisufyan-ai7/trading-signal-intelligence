param(
    [string]$TaskName = "VowSig AI-v1.3 Crypto Shadow Scan",
    [string]$CoreTaskName = "SignalProof AI-v1.1 Shadow Scan",
    [string]$ExpansionTaskName = "VowSig AI-v1.2.1 Expansion Shadow Scan",
    [switch]$ConfirmK5Installation
)

$ErrorActionPreference = "Stop"

# Post-K4 successor: safe by default. Task registration is separately owner-gated.
# The original K3-frozen installer remains byte-for-byte unchanged.
if ($TaskName -cne "VowSig AI-v1.3 Crypto Shadow Scan" -or
    $CoreTaskName -cne "SignalProof AI-v1.1 Shadow Scan" -or
    $ExpansionTaskName -cne "VowSig AI-v1.2.1 Expansion Shadow Scan") {
    throw "K5 requires the exact preregistered task names"
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$runner = Join-Path $repoRoot "scripts\run_ai_v1_3_crypto_shadow_task.cmd"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$verifier = Join-Path $repoRoot "scripts\verify_ai_v1_3_crypto_runtime.py"

if (-not (Test-Path $runner)) { throw "Task runner not found: $runner" }
if (-not (Test-Path $python)) { throw "Python venv executable not found: $python" }
if (-not (Test-Path $verifier)) { throw "Runtime verifier not found: $verifier" }

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    throw "AI-v1.3 crypto task already exists. Stop for review rather than overwriting it."
}

$parallelNames = @($CoreTaskName, $ExpansionTaskName)
$parallelState = @{}

foreach ($ParallelName in $parallelNames) {
    $task = Get-ScheduledTask -TaskName $ParallelName -ErrorAction SilentlyContinue
    if ($null -eq $task) { throw "Required parallel task missing: $ParallelName" }
    $info = Get-ScheduledTaskInfo -TaskName $ParallelName
    if ([string]$task.State -notin @("Ready", "Running")) {
        throw "Parallel task must be Ready or Running: $ParallelName ($($task.State))"
    }
    if ([int64]$info.LastTaskResult -ne 0) {
        throw "Parallel task last result must be 0: $ParallelName ($($info.LastTaskResult))"
    }
    $parallelState[$ParallelName] = [pscustomobject]@{ State = [string]$task.State; LastTaskResult = [int64]$info.LastTaskResult }
}

# K4 evidence is mandatory; K3's --activation-only flag is NOT valid after K4.
if (-not (Test-Path -LiteralPath $legacyInstaller -PathType Leaf)) { throw "Frozen K3 installer missing" }
if ((Get-FileHash -LiteralPath $legacyInstaller -Algorithm SHA256).Hash -ine $expectedLegacySha256) {
    throw "Frozen K3 installer changed; refusing K5"
}
if (-not (Test-Path -LiteralPath $k4Marker -PathType Leaf)) { throw "K4 attempt marker missing" }
$k4Evidence = Get-Content -LiteralPath $k4Marker -Raw | ConvertFrom-Json
if ($k4Evidence.authority -cne "RUN-AI-V1.3-CRYPTO-FIRST-CYCLE" -or
    $k4Evidence.mode -cne "ONE_SHOT_NO_RETRY" -or
    $k4Evidence.production_head -cne "926407c223efa5265b8c2c56668ba684cd950da2" -or
    $k4Evidence.activated_anchor_sha256 -ine $expectedK4AnchorSha256 -or
    $k4Evidence.expected_h1_close_utc -cne "2026-10-09T21:00:00.0000000Z" -or
    $k4Evidence.broker_execution_enabled -ne $false -or
    $k4Evidence.public_signal_exposure_enabled -ne $false -or
    $k4Evidence.crypto_scheduler_installed -ne $false) {
    throw "K4 owner authorization marker inconsistent"
}

# Default runtime verification: full ledger, K3 upstream and artifact hashes,
# public/broker safety and parallel lineage, WITHOUT scheduler-health gating.
# Do not pass --include-scheduler until after K5 task installation and natural run.
Write-Host "Verifying full post-K4 AI-v1.3 runtime before K5 task registration..."
$verifyLines = & $python $verifier
$verifyExit = $LASTEXITCODE
if ($verifyExit -ne 0) {
    throw "Post-K4 full runtime verification failed; no scheduler change"
}
$verified = ($verifyLines -join "`n") | ConvertFrom-Json
if ($verified.runtime_verification -cne "PASS" -or
    $verified.activation_only_required -ne $false -or
    $verified.crypto.health.healthy -ne $true -or
    $verified.crypto.health.ledgers_valid -ne $true -or
    $verified.crypto.health.activation_anchor_upstream_valid -ne $true -or
    $verified.crypto.health.crypto_artifacts_valid -ne $true -or
    $verified.crypto.health.activation_anchor_matches_ledgers -ne $true -or
    $verified.crypto.health.public_signal_exposure_disabled -ne $true -or
    $verified.crypto.health.broker_execution_disabled -ne $true -or
    $verified.parallel_ai_v1_2_1_runtime.runtime_verification -cne "PASS") {
    throw "Post-K4 runtime verification safety invariants failed"
}
$expectedMarkets = @{
    BTCUSDT = @{ head = "5d30b294ea3bce57fbfb7ae324c2290e03b142a03f6bafd98090de35514b35e2"; terminal = "NO_TRADE" }
    ETHUSDT = @{ head = "24dc7e6ed71270a573de1cdc9d1473534d84bd1a3dc70ed57ff95619d50f2233"; terminal = "REJECTED_INFERENCE" }
    SOLUSDT = @{ head = "fdc2b6f8b81e5bff1a43a0c8f5541038ecade9089860d02cce4ec4d3e7a36eba"; terminal = "SIGNAL" }
}
foreach ($symbol in @("BTCUSDT", "ETHUSDT", "SOLUSDT")) {
    $market = $verified.crypto.markets.$symbol
    $expect = $expectedMarkets[$symbol]
    if ($null -eq $market -or
        $market.records -ne 4 -or
        $market.current_head_hash -cne $expect.head -or
        $market.ledger_verification.valid -ne $true -or
        $market.counts_by_type.ACTIVATION -ne 1 -or
        $market.counts_by_type.MISSED_INFERENCE -ne 1 -or
        $market.counts_by_type.INFERENCE -ne 1 -or
        $market.counts_by_type.($expect.terminal) -ne 1) {
        throw "K4 frozen ledger evidence mismatch for $symbol; stop for review"
    }
}
Write-Host "K5_POST_K4_COMPATIBILITY_PREFLIGHT=PASS"
Write-Host "K5_FROZEN_K3_ARTIFACTS=UNCHANGED"
Write-Host "K5_K4_LEDGER_BASELINE=PASS"

# Preview mode is intentionally non-mutating; separate INSTALL authority required.
if (-not $ConfirmK5Installation) {
    Write-Host "K5_PREVIEW_ONLY=PASS"
    Write-Host "K5_TASK_REGISTRATION=NOT_ATTEMPTED"
    Write-Host "K5_PROVIDER_CALLS=NONE"
    exit 0
}
Write-Host "K5_EXPLICIT_INSTALLATION_CONFIRMATION=TRUE"

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(4)
if ($nextRun -le $now) { $nextRun = $nextRun.AddHours(1) }

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "VowSig AI-v1.3 24x7 BTCUSDT/ETHUSDT/SOLUSDT parallel shadow scan. Hourly near UTC minute 04. Public signal exposure and broker/exchange execution disabled."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -ErrorAction Stop | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
$taskDef = Get-ScheduledTask -TaskName $TaskName

[pscustomobject]@{
    TaskName = $TaskName
    State = [string]$taskDef.State
    NextRunTime = $taskInfo.NextRunTime
    LastRunTime = $taskInfo.LastRunTime
    LastTaskResult = $taskInfo.LastTaskResult
    Runner = $runner
    WorkingDirectory = $repoRoot
    ScheduledMinute = 4
    CoreParallelTask = $CoreTaskName
    ExpansionParallelTask = $ExpansionTaskName
    PublicSignalExposureEnabled = $false
    BrokerExecutionEnabled = $false
} | ConvertTo-Json -Depth 4
