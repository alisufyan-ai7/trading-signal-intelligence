param(
    [string]$TaskName = "VowSig AI-v1.3 Crypto Shadow Scan",
    [string]$CoreTaskName = "SignalProof AI-v1.1 Shadow Scan",
    [string]$ExpansionTaskName = "VowSig AI-v1.2.1 Expansion Shadow Scan",
    [switch]$ConfirmActivatedRuntime
)

$ErrorActionPreference = "Stop"

if (-not $ConfirmActivatedRuntime) {
    throw "Refusing AI-v1.3 crypto task installation. Re-run with -ConfirmActivatedRuntime only after separately owner-approved AI-v1.3 activation is committed and verified."
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

Write-Host "Verifying activation-only AI-v1.3 crypto runtime before task registration..."
& $python $verifier --activation-only
if ($LASTEXITCODE -ne 0) {
    throw "AI-v1.3 activation/runtime verification failed. Scheduler was not installed."
}

$now = Get-Date
$nextRun = $now.Date.AddHours($now.Hour).AddMinutes(4)
if ($nextRun -le $now) { $nextRun = $nextRun.AddHours(1) }

$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument ('/c "' + $runner + '"') -WorkingDirectory $repoRoot
$trigger = New-ScheduledTaskTrigger -Once -At $nextRun -RepetitionInterval (New-TimeSpan -Hours 1) -RepetitionDuration (New-TimeSpan -Days 3650)
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Minutes 15)
$principal = New-ScheduledTaskPrincipal -UserId ("$env:USERDOMAIN\$env:USERNAME") -LogonType Interactive -RunLevel Highest
$task = New-ScheduledTask -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "VowSig AI-v1.3 24x7 BTCUSDT/ETHUSDT/SOLUSDT parallel shadow scan. Hourly near UTC minute 04. Public signal exposure and broker/exchange execution disabled."

Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null

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
