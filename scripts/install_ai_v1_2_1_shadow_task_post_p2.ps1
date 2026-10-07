param(
    [string]$TaskName = "VowSig AI-v1.2.1 Expansion Shadow Scan",
    [string]$ParallelTaskName = "SignalProof AI-v1.1 Shadow Scan",
    [string]$ActiveRepoRoot = "",
    [switch]$PlanOnly,
    [switch]$ConfirmP2Passed
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

if (-not $PlanOnly -and -not $ConfirmP2Passed) {
    throw "Refusing scheduler installation. Use -PlanOnly for a no-mutation proof, or -ConfirmP2Passed only after explicit owner P3 approval."
}

$scriptRepoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path

if (-not $PlanOnly -and -not [string]::IsNullOrWhiteSpace($ActiveRepoRoot)) {
    throw "-ActiveRepoRoot is permitted only with -PlanOnly. Installation must run from the published production repository."
}

$repoRoot = if ([string]::IsNullOrWhiteSpace($ActiveRepoRoot)) {
    $scriptRepoRoot
}
else {
    (Resolve-Path $ActiveRepoRoot).Path
}

$runner = Join-Path $repoRoot "scripts\run_ai_v1_2_1_shadow_task.cmd"
$python = Join-Path $repoRoot ".venv\Scripts\python.exe"
$verifier = Join-Path $repoRoot "scripts\verify_ai_v1_2_1_runtime.py"
$reporter = Join-Path $repoRoot "scripts\report_ai_v1_2_1_progress.py"
$legacyInstaller = Join-Path $repoRoot "scripts\install_ai_v1_2_1_shadow_task.ps1"

$ExpectedBoundInstallerSha256 = "87c83b36aa16d880c5ae1ec4244577da7112755812ad75058f284a00e8b06257"
$ExpectedTaskRunnerSha256 = "5d4c4435bba10f00a67d5225b057a1a366f8e6b05cd31ade2d46827a08730132"
$ExpectedLiveRunnerSha256 = "2079531bd99abf48f7ab81c621b979c703be26e707319db3610a0bc26bb95dd9"

$ExpectedP2LedgerHashes = [ordered]@{
    EURUSD = "02fea7c7e9edc7b294be331acf6689b72738559e11f85125a6971610c6251f81"
    XAGUSD = "47941806a6241bb72acffaa89705bf842db20f8e2b90ecd5c3c61ea86e103eae"
    USOIL  = "842d428aef53f2bd5c27b36271c54946ec214a0a9b5ab5cf2c1d873ec4502b8b"
}

$SuccessorLedgers = [ordered]@{
    EURUSD = Join-Path $repoRoot "data\ai_v1_2_1_eurusd.sqlite"
    XAGUSD = Join-Path $repoRoot "data\ai_v1_2_1_xagusd.sqlite"
    USOIL  = Join-Path $repoRoot "data\ai_v1_2_1_usoil.sqlite"
}

function Get-Sha256 {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "Required file missing: $Path"
    }

    return (
        Get-FileHash -LiteralPath $Path -Algorithm SHA256
    ).Hash.ToLowerInvariant()
}

foreach ($required in @($runner, $python, $verifier, $reporter, $legacyInstaller)) {
    if (-not (Test-Path -LiteralPath $required -PathType Leaf)) {
        throw "Required scheduler artifact missing: $required"
    }
}

if ((Get-Sha256 -Path $legacyInstaller) -ne $ExpectedBoundInstallerSha256) {
    throw "Activation-bound legacy scheduler installer changed. Refuse post-P2 installation."
}

if ((Get-Sha256 -Path $runner) -ne $ExpectedTaskRunnerSha256) {
    throw "Activation-bound task runner changed. Refuse post-P2 installation."
}

$liveRunner = Join-Path $repoRoot "scripts\run_ai_v1_2_1_live.py"
if ((Get-Sha256 -Path $liveRunner) -ne $ExpectedLiveRunnerSha256) {
    throw "Activation-bound live runner changed. Refuse post-P2 installation."
}

$existing = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($null -ne $existing) {
    throw "AI-v1.2.1 expansion task already exists. Stop for review rather than overwriting it."
}

$parallel = Get-ScheduledTask -TaskName $ParallelTaskName -ErrorAction SilentlyContinue
if ($null -eq $parallel) {
    throw "Parallel AI-v1.1 task must exist before AI-v1.2.1 installation."
}

$parallelInfo = Get-ScheduledTaskInfo -TaskName $ParallelTaskName
if ([string]$parallel.State -notin @("Ready", "Running")) {
    throw "Parallel AI-v1.1 task must be Ready or Running. Current state: $($parallel.State)"
}
if ([int64]$parallelInfo.LastTaskResult -ne 0) {
    throw "Parallel AI-v1.1 task last result must be 0. Current: $($parallelInfo.LastTaskResult)"
}

Write-Host "Verifying full post-P2 AI-v1.2.1 runtime before task registration..."
& $python $verifier
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.2.1 post-P2 runtime verification failed. Scheduler was not installed."
}

$reportRaw = @(
    & $python $reporter --skip-scheduler
)

if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.2.1 post-P2 observability failed. Scheduler was not installed."
}

$reportText = $reportRaw -join [Environment]::NewLine
$report = $reportText | ConvertFrom-Json

if ([bool]$report.health.healthy -ne $true) {
    throw "AI-v1.2.1 observability is not healthy. Scheduler was not installed."
}

if ([int]$report.totals.valid_inferences -ne 3) {
    throw "Expected exactly 3 frozen P2 valid inferences before scheduler installation."
}
if ([int]$report.totals.errors -ne 0) {
    throw "P2 evidence contains runtime errors. Scheduler was not installed."
}
if ([int]$report.totals.missed_inferences -ne 0) {
    throw "P2 evidence contains missed inferences. Scheduler was not installed."
}
if ([int]$report.totals.signals -ne 2) {
    throw "Expected exactly 2 P2 signals before scheduler installation."
}
if ([int]$report.totals.no_trade -ne 1) {
    throw "Expected exactly 1 P2 no-trade before scheduler installation."
}
if ([int]$report.totals.open_shadow_signals -ne 2) {
    throw "Expected exactly 2 open P2 shadow signals before scheduler installation."
}

foreach ($symbol in $ExpectedP2LedgerHashes.Keys) {
    $path = $SuccessorLedgers[$symbol]
    $observed = Get-Sha256 -Path $path

    if ($observed -ne $ExpectedP2LedgerHashes[$symbol]) {
        throw "AI-v1.2.1 $symbol ledger does not match frozen P2 PASS evidence."
    }

    if ([int]$report.markets.$symbol.valid_inferences -ne 1) {
        throw "AI-v1.2.1 $symbol does not have exactly one P2 inference."
    }
    if ([int]$report.markets.$symbol.errors -ne 0) {
        throw "AI-v1.2.1 $symbol contains an error before scheduler installation."
    }
    if ([int]$report.markets.$symbol.missed_inferences -ne 0) {
        throw "AI-v1.2.1 $symbol contains a missed inference before scheduler installation."
    }
}

if ([int]$report.markets.EURUSD.counts_by_type.SIGNAL -ne 1) {
    throw "EURUSD frozen P2 decision mismatch."
}
if ([int]$report.markets.XAGUSD.counts_by_type.SIGNAL -ne 1) {
    throw "XAGUSD frozen P2 decision mismatch."
}
if ([int]$report.markets.USOIL.counts_by_type.NO_TRADE -ne 1) {
    throw "USOIL frozen P2 decision mismatch."
}

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(3)
if ($nextRun -le $now) {
    $nextRun = $nextRun.AddHours(1)
}

$plan = [pscustomobject]@{
    Mode = if ($PlanOnly) { "PLAN_ONLY" } else { "INSTALL" }
    TaskName = $TaskName
    ParallelTaskName = $ParallelTaskName
    ScheduledMinute = 3
    NextRunTime = $nextRun
    Runner = $runner
    WorkingDirectory = $repoRoot
    InstallerSourceRoot = $scriptRepoRoot
    ActiveRuntimeRoot = $repoRoot
    P2ValidInferences = [int]$report.totals.valid_inferences
    P2Signals = [int]$report.totals.signals
    P2NoTrade = [int]$report.totals.no_trade
    P2Errors = [int]$report.totals.errors
    P2MissedInferences = [int]$report.totals.missed_inferences
    P2OpenShadowSignals = [int]$report.totals.open_shadow_signals
    ParallelTaskState = [string]$parallel.State
    ParallelTaskLastResult = [int64]$parallelInfo.LastTaskResult
    PublicExposureEnabled = $false
    BrokerExecutionEnabled = $false
    MutationPerformed = $false
}

if ($PlanOnly) {
    $plan | ConvertTo-Json -Depth 6
    exit 0
}

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 10)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "VowSig AI-v1.2.1 parallel expansion shadow inference for EURUSD/XAGUSD/USOIL. Hourly near minute 03. AI-v1.1 remains active. Broker execution disabled."

Register-ScheduledTask -TaskName $TaskName -InputObject $task | Out-Null

$taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
$taskDef = Get-ScheduledTask -TaskName $TaskName

if ([string]$taskDef.State -notin @("Ready", "Running")) {
    throw "AI-v1.2.1 scheduler registration completed but task state is unhealthy: $($taskDef.State)"
}

[pscustomobject]@{
    Mode = "INSTALL"
    TaskName = $TaskName
    State = [string]$taskDef.State
    NextRunTime = $taskInfo.NextRunTime
    LastRunTime = $taskInfo.LastRunTime
    LastTaskResult = [int64]$taskInfo.LastTaskResult
    Runner = $runner
    WorkingDirectory = $repoRoot
    ParallelTaskName = $ParallelTaskName
    ParallelTaskState = [string]$parallel.State
    ParallelTaskLastResult = [int64]$parallelInfo.LastTaskResult
    ScheduledMinute = 3
    P2ValidInferences = [int]$report.totals.valid_inferences
    P2Signals = [int]$report.totals.signals
    P2NoTrade = [int]$report.totals.no_trade
    P2Errors = [int]$report.totals.errors
    P2MissedInferences = [int]$report.totals.missed_inferences
    PublicExposureEnabled = $false
    BrokerExecutionEnabled = $false
    MutationPerformed = $true
    Note = "Installation only. P3 closure still requires one natural scheduled run at minute 03 and full runtime verification with scheduler health."
} | ConvertTo-Json -Depth 6
